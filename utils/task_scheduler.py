# src/utils/task_scheduler.py
from datetime import datetime
import importlib
import json
import traceback
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from models.task_model import TaskModel
from models.runlog_model import RunlogModel

class TaskScheduler:
    def __init__(self, plugin_name, data_directory):
        self.plugin_name = plugin_name
        self.data_directory = data_directory
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.task_model = TaskModel(plugin_name, data_directory)
        self.runlog_model=RunlogModel(plugin_name, data_directory)

    def load_tasks_from_db(self):
        tasks = self.task_model.get_enabled_tasks()
        for task in tasks:
            self.add_task_to_scheduler(task)


    def add_task_to_scheduler(self, task):
        print(f"【定时任务】添加任务: {task['name']}，应用: {task['app']}")
        job_id = str(task['id'])
        try:
            self.scheduler.remove_job(job_id)
        except Exception:
            pass
        
         
        print("task['freq_value']",task['freq_value'])
        
        cron_parts = task['freq_value'].split()
            # 兼容性处理，防止少参数
        while len(cron_parts) < 5:
            cron_parts.append('*')
        
        
        trigger = CronTrigger(
                minute=cron_parts[0],
                hour=cron_parts[1],
                day=cron_parts[2],
                month=cron_parts[3],
                day_of_week=cron_parts[4]
            )
        
         
        self.scheduler.add_job(
            func=self.run_task,
            trigger=trigger,
            id=job_id,
            args=[task],
            replace_existing=True
        )

    def run_task(self, task):
        print(f"【定时任务】执行任务: {task['name']}")
        print(f"task={task}")
        
        task_id = task['id']
        start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_text = ""
        result = "成功"  # 默认成功
        
        try:
            log_text += f"开始执行任务: {task['name']}\n"
            
            controller_name = task['controller_name']
            method_name = task['method_name']
            params = task['params']
            
            print(f"controller_name={controller_name}")
            print(f"method_name={method_name}")
            print(f"params={params}")
            
            # 将 JSON 字符串反序列化为字典
            params = json.loads(params) if isinstance(params, str) else params
            
            print(f"params={params}")
            
            # 修改类名拼接逻辑
            base_name = controller_name.replace('_controller', '')  # 先移除 _controller 后缀
            class_name = ''.join(word.title() for word in base_name.split('_')) + 'Controller'
            
            print(f"class_name={class_name}")  # 用于调试
            
            # 动态导入并实例化controller
            module = importlib.import_module(f'controllers.{controller_name}')
            controller_class = getattr(module, class_name)
            controller = controller_class(self.plugin_name, self.data_directory)
            
            # 调用指定方法
            method = getattr(controller, method_name)
            method(**params)
            
            log_text += "任务执行成功\n"
            
        except Exception as e:
            result = "失败"
            error_msg = str(e)
            stack_trace = traceback.format_exc()
            log_text += f"任务执行失败: {error_msg}\n{stack_trace}"
            print(f"【定时任务】执行异常: {error_msg}")
        
        finally:
            # 无论成功失败，都记录日志
            self.save_run_log(task_id, result, log_text, start_time)
        
        
      

    def remove_task(self, task_id):
        try:
            self.scheduler.remove_job(str(task_id))
        except Exception:
            pass

    def reload_tasks(self):
        self.scheduler.remove_all_jobs()
        self.load_tasks_from_db()
        
        
    
    def save_run_log(self, task_id, result, log, run_time):
        """
        保存运行日志到数据库
        """
        try:
            # 调用 RunlogModel 的方法保存日志
            log_data = {
                'task_id': task_id,
                'result': result,
                'log': log,
                'run_time': run_time
            }
            self.runlog_model.add_log(log_data)
            print(f"【定时任务】日志已记录: task_id={task_id}, result={result}")
        except Exception as e:
            print(f"【定时任务】记录日志失败: {e}")