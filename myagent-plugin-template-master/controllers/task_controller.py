from datetime import datetime
import importlib
import traceback
from models.task_model import TaskModel
import json


from utils.task_scheduler import TaskScheduler


class TaskController:
    def __init__(self,plugin_name,data_directory):
        self.plugin_name = plugin_name
        self.data_directory = data_directory
        self.plugin_name = self.plugin_name
        self.data_directory = self.data_directory
        self.model = TaskModel(self.plugin_name,self.data_directory)
        self.task_scheduler = TaskScheduler(self.plugin_name, self.data_directory)
        

    
    def get_task_list(self):
        """获取任务列表"""
        try:
            tasks = self.model.get_tasks()
            return {
                'success': True,
                'data': tasks
            }
        except Exception as e:
            return {
                'success': False, 
                'message': str(e)
            }
            
            
            
    
    def toggle_task_status(self, task_id: int, enabled: int):
        """切换任务启用状态"""
        try:
            self.model.toggle_task_status(task_id, enabled)
            
            
            # 更新调度器
            self.task_scheduler.reload_tasks()
            
            return {
                'success': True,
                'message': '更新成功'
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
            
            
    def delete_task(self, task_id: int):
        """删除任务"""
        try:
            # 先删除数据库中的任务
            self.model.delete_task(task_id)
            
            
            self.task_scheduler.reload_tasks()
            
            return {
                'success': True,
                'message': '删除成功'
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
            
            
    def execute_task(self, task_id: int):
        """手工执行任务"""
        try:
            # 获取任务详情
            task = self.model.get_task_by_id(task_id)
            if not task:
                return {
                    'success': False,
                    'message': '任务不存在'
                }
                
            try:
                controller_name = task['controller_name']
                method_name = task['method_name']
                params = task['params']
                
                # 将 JSON 字符串反序列化为字典
                params = json.loads(params) if isinstance(params, str) else params
                
                # 修改类名拼接逻辑
                base_name = controller_name.replace('_controller', '')
                class_name = ''.join(word.title() for word in base_name.split('_')) + 'Controller'
                
                print(f"开始执行任务: {task['name']}")
                print(f"controller_name={controller_name}")
                print(f"method_name={method_name}")
                print(f"params={params}")
                
                # 动态导入并实例化controller
                module = importlib.import_module(f'controllers.{controller_name}')
                controller_class = getattr(module, class_name)
                controller = controller_class(self.plugin_name, self.data_directory)
                
                # 调用指定方法
                method = getattr(controller, method_name)
                result = method(**params)
                
                # 记录执行日志
                start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                log_text = f"手工执行任务: {task['name']}\n"
                log_text += f"执行结果: {result}\n"
                
                # 保存执行日志
                self.task_scheduler.save_run_log(
                    task_id, 
                    "成功", 
                    log_text, 
                    start_time
                )
                
                return {
                    'success': True,
                    'message': '任务执行成功',
                    'data': result
                }
                
            except Exception as e:
                error_msg = str(e)
                stack_trace = traceback.format_exc()
                log_text = f"手工执行任务失败: {error_msg}\n{stack_trace}"
                
                # 保存错误日志
                start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.task_scheduler.save_run_log(
                    task_id, 
                    "失败", 
                    log_text, 
                    start_time
                )
                
                raise Exception(f"执行失败: {error_msg}")
                
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
        