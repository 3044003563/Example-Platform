import webview
import os
import sys
import logging


from controllers.plugin_controller import PluginController

 
# 获取项目根目录
current_dir = os.path.dirname(os.path.abspath(__file__))  # src目录
root_dir = os.path.dirname(current_dir)  # 项目根目录

# 确保日志目录存在
log_dir = os.path.join(root_dir, 'data', 'logs')
os.makedirs(log_dir, exist_ok=True)


import tkinter as tk
from tkinter import messagebox
import traceback
from pathlib import Path  # 添加这行导入




# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'app.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def show_error(error_msg):
    """显示错误信息的弹窗"""
    try:
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        messagebox.showerror("MyRPA Error", error_msg)
        root.destroy()
    except Exception as e:
        print(f"Error showing error dialog: {e}")
        print(f"Original error: {error_msg}")


    

class Api:
    
    """API 包装类"""
    def __init__(self):
        self.plugin = PluginController()
        pass


def get_html_path():
    try:
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller 创建临时文件夹，将路径存储在 _MEIPASS 中
            base_path = sys._MEIPASS
        else:
            # 正常运行时的路径
            base_path = os.path.dirname(os.path.abspath(__file__))  # 使用当前文件所在目录


        html_path = os.path.join(base_path, 'views', 'pages', 'main.html')
        
        if not os.path.exists(html_path):
            error_msg = f"HTML file not found: {html_path}"
            logger.error(error_msg)
            show_error(error_msg)
            raise FileNotFoundError(error_msg)
        
        url = 'file:///' + html_path.replace('\\', '/')
        logger.debug(f"HTML path: {url}")
        return url
    except Exception as e:
        error_msg = f"Error getting HTML path: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        show_error(error_msg)
        raise


def main():
    try:
        logger.info("Starting application...")
        
        
        api = Api()
        
       
        html_url = get_html_path()
        
        print("html_url:=============", html_url)
        
  
        
        # 创建窗口
        window = webview.create_window(
            'myagent-demo',
            url=html_url,
            js_api=api,  # 使用 api 字典
            width=1200,
            height=800,
            resizable=True,
            frameless=False,
            easy_drag=False
        )

 
 
        # 启动应用
        webview.start(debug=True)
        #webview.start(debug=False)
        
    except Exception as e:
        show_error(f"Application failed to start: {e}")
        logger.error(f"Application failed to start: {e}")
        raise

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        show_error(f"Fatal error: {e}")
        logger.error(f"Fatal error: {e}")
        sys.exit(1)