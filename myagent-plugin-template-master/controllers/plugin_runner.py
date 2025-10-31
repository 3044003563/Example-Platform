# douyin-ai/controllers/plugin_runner.py
import sys
import threading
import time
import traceback
import importlib
from pathlib import Path
import json
import os

def run_plugin_method():
    try:
        # 🚀 极简的参数获取
        args_json = sys.argv[1]
        kwargs_json = sys.argv[2]
        
        # 解析参数
        args = json.loads(args_json)
        kwargs = json.loads(kwargs_json)
        
        print(f"子进程接收到 args: {args}")
        print(f"子进程接收到 kwargs: {kwargs}")
        
        # 🚀 从kwargs中提取路由参数
        plugin_name = kwargs.get('plugin_name')
        version = kwargs.get('version')
        controller_name = kwargs.get('controller_name')
        method_name = kwargs.get('method_name')
        data_directory = kwargs.get('data_directory')
        temp_path = kwargs.get('temp_path')
        control_file_path = kwargs.get('control_file_path')  # 🔧 新增：获取控制文件路径
        
        print(f"路由信息: {plugin_name}.{controller_name}.{method_name}")
        
        
        # 🔧 设置控制文件环境变量
        if control_file_path:
            os.environ['PROCESS_CONTROL_FILE'] = control_file_path
            print(f"设置控制文件环境变量: {control_file_path}")
            
            
        
        project_root = Path(__file__).parent.parent
        
        print(f"项目根目录: {project_root}")
        
        # 将项目根目录添加到Python路径（如果还没有的话）
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
            print(f"已添加到Python路径: {project_root}")
        
        # 动态导入和实例化
        module = importlib.import_module(f'controllers.{controller_name}')
        controller_class_name = controller_name.replace('_', ' ').title().replace(' ', '')
        controller_class = getattr(module, controller_class_name)
        controller_instance = controller_class(plugin_name, data_directory)
        
        # 🚀 完全透传参数调用业务方法
        method = getattr(controller_instance, method_name)
        result = method(*args, **kwargs)
        
        # 写入结果文件
        if temp_path:
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(result, ensure_ascii=False))
        
        print(f"方法执行完成: {result}")
        return result
        
    except Exception as e:
        error_result = {'success': False, 'error': str(e)}
        print(f"子进程执行失败: {error_result}")
        traceback.print_exc()
        
        # 写入错误结果
        temp_path = kwargs.get('temp_path') if 'kwargs' in locals() else None
        if temp_path:
            try:
                with open(temp_path, 'w', encoding='utf-8') as f:
                    f.write(json.dumps(error_result, ensure_ascii=False))
            except Exception as write_error:
                print(f"写入错误结果失败: {write_error}")
        
        return error_result

def wait_for_all_threads_to_complete():
    """等待所有非守护线程完成，支持外部控制"""
    control_file = os.environ.get('PROCESS_CONTROL_FILE')
    
    while True:
        # 检查控制指令
        if control_file and os.path.exists(control_file):
            try:
                with open(control_file, 'r', encoding='utf-8') as f:
                    control_state = json.load(f)
                    if control_state.get('action') == 'stop':
                        print("接收到停止指令，终止所有线程")
                        # 强制退出进程
                        os._exit(0)
            except Exception as e:
                print(f"读取控制文件失败: {e}")
        
        # 获取所有非守护线程
        non_daemon_threads = [t for t in threading.enumerate() 
                             if not t.daemon and t != threading.main_thread()]
        
        if not non_daemon_threads:
            print("所有非守护线程已完成")
            break
            
        print(f"等待 {len(non_daemon_threads)} 个非守护线程完成...")
        for thread in non_daemon_threads:
            print(f"   - 线程: {thread.name}")
        
        time.sleep(1)

if __name__ == '__main__':
    run_plugin_method()