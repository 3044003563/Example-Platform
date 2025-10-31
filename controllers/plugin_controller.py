import gc
import shutil
import tempfile
import importlib
import os
import sys
import traceback
import stat
from datetime import datetime
import time
import subprocess
from pathlib import Path
import json
import threading
from utils.main_process_control_window import MainProcessControlWindow

class PluginController:
    def __init__(self):
        # 实例变量存储当前控制器的ID
        self.controller_id = None
        # 用户数据目录，本地开发环境使用，可以随意设置，如果D盘不存在，可以手工改成C盘
        self.data_directory = "D:\\Data\\MyAgent"
        # 用户ID，在本地开发环境使用，需要设定为自己的用户ID
        # 如果不知道自己的用户ID，可以登录https://myagent.im/admin，然后查看自己的用户ID
        self.user_id="10032"
        self.data_directory=self.data_directory+"\\"+self.user_id
        print("data_directory============="+self.data_directory)
        print("PluginController initialized")
        

    def handle_api_call(self, *args, **kwargs):
        """处理API调用 - 完全透传"""
        print(f"中间层收到 args: {args}")
        print(f"中间层收到 kwargs: {kwargs}")
        
        try:
            
            if args and isinstance(args[0], dict):
                kwargs = args[0].copy()
                print(f"从args[0]提取并转换为kwargs: {kwargs}")
            
            # 🚀 添加系统参数到kwargs中
            if not kwargs.get('plugin_name'):
                manifest_path = Path(__file__).parent.parent / 'manifest.json'
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                    kwargs['plugin_name'] = manifest.get('plugin_name', '')
            
            
            
            # 🚀 直接透传
            return self._call_via_subprocess(*args, **kwargs)
            
        except Exception as e:
            traceback.print_exc()
            return {'success': False, 'message': str(e)}
    
    def _call_via_subprocess(self, *args, **kwargs):
        """通过子进程调用 - 完全透传"""
        
        # 🚀 从kwargs中提取必要的系统参数
        need_control_window = kwargs.get('need_control_window', False)
        plugin_name = kwargs.get('plugin_name')
        data_directory = self.data_directory
        
        kwargs['data_directory'] = data_directory
        
        # 控制窗口逻辑...
        control_window = None
        if need_control_window:
            control_window = MainProcessControlWindow(
                title=f"{plugin_name} - 任务控制",
                plugin_name=plugin_name,
                data_directory=data_directory
            )
        
        control_file_path = ""
        if control_window:
            control_file_path = control_window.get_control_file_path()
            # 将控制文件路径也加入kwargs
            kwargs['control_file_path'] = control_file_path
        
        runner_path = Path(__file__).parent / "plugin_runner.py"
        
        with tempfile.NamedTemporaryFile(delete=False, mode='w+', encoding='utf-8') as tf:
            temp_path = tf.name
            # 将临时文件路径也加入kwargs
            kwargs['temp_path'] = temp_path
        
        # 🚀 极简的命令行参数
        cmd = [
            sys.executable, str(runner_path),
            json.dumps(args),     # sys.argv[1]
            json.dumps(kwargs)    # sys.argv[2]
        ]
        
        print(f"启动子进程命令: {cmd}")
        
        # subprocess逻辑...
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        
        if control_window:
            control_window.set_process(proc)
            control_window.show()
        
        # 等待结果逻辑...
        def print_output():
            try:
                while True:
                    line = proc.stdout.readline()
                    if not line:
                        break
                    print(line, end='')
            except Exception as e:
                print(f"输出处理异常: {e}")

        output_thread = threading.Thread(target=print_output, daemon=True)
        output_thread.start()

        # 等待结果文件
        max_wait_time = 60
        start_time = time.time()
        result_ready = False

        print("等待插件方法执行完成...")
        while time.time() - start_time < max_wait_time:
            try:
                if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                    with open(temp_path, 'r', encoding='utf-8') as f:
                        output = f.read()
                        if output.strip():
                            result_ready = True
                            print("结果已获取，立即返回给前端")
                            break
            except (FileNotFoundError, PermissionError, OSError) as e:
                print(f"读取结果文件时出错: {e}")
            
            time.sleep(0.1)

        # 清理临时文件
        try:
            os.remove(temp_path)
        except Exception as e:
            print(f"清理临时文件失败: {e}")

        if not result_ready:
            print("插件执行超时，未能获取结果")
            return {'success': False, 'message': '插件执行超时'}

        print(f"子进程 {proc.pid} 将在后台继续处理")

        try:
            return json.loads(output)
        except Exception:
            traceback.print_exc()
            return output