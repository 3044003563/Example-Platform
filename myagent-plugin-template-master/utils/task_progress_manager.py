import os
import json
import time
from pathlib import Path

class TaskProgressManager:
    """任务进度管理器 - 简化版，只更新状态文本"""
    
    def __init__(self):
        self.control_file = os.environ.get('PROCESS_CONTROL_FILE')
        self.task_info = {}
        
    def init_task(self, task_type, description=""):
        """初始化任务 - 简化版"""
        self.task_info = {
            'task_type': task_type,
            'status': f"准备开始 {task_type}...",
            'start_time': time.time()
        }
        
        self._update_control_file({
            'action': 'running',
            'status': 'running',
            'task_info': self.task_info,
            'timestamp': time.time()
        })
    
    def update_status(self, status_text):
        """更新状态文本 - 简化版"""
        self.task_info['status'] = status_text
        
        self._update_control_file({
            'action': 'running',
            'status': 'running',
            'task_info': self.task_info,
            'timestamp': time.time()
        })
    
    def complete_task(self, final_message):
        """完成任务 - 简化版"""
        self.task_info.update({
            'status': final_message,
            'end_time': time.time()
        })
        
        self._update_control_file({
            'action': 'completed',
            'status': 'completed',
            'task_info': self.task_info,
            'auto_close': True,
            'timestamp': time.time()
        })
    
    def _update_control_file(self, data):
        """更新控制文件"""
        if not self.control_file:
            return
            
        try:
            with open(self.control_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception as e:
            print(f"更新控制文件失败: {e}")