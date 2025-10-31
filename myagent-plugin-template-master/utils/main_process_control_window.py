import webview
import threading
import time
import os
import json
from pathlib import Path
import tempfile
import subprocess

class MainProcessControlWindow:
    """主进程中的控制窗口"""
    
    def __init__(self, title="任务控制", plugin_name="",data_directory=""):
        self.title = title
        self.plugin_name = plugin_name
        self.data_directory = data_directory
        self.process = None
        self.window = None
        self.is_paused = False
        self.control_file = None
        self.status_text = "准备就绪"
        
        # 创建控制文件
        self._create_control_file()
        
    def _create_control_file(self):
        """创建进程控制文件"""
        control_dir = Path(self.data_directory) / "process_control"
        control_dir.mkdir(exist_ok=True)
        
        # 使用临时文件确保唯一性
        with tempfile.NamedTemporaryFile(
            dir=control_dir, 
            delete=False, 
            suffix='.json',
            prefix=f'{self.plugin_name}_'
        ) as f:
            self.control_file = f.name
        
        # 初始化控制状态
        self._write_control_state({
            'action': 'run',
            'status': 'running',
            'timestamp': time.time()
        })
        
    def _write_control_state(self, state):
        """写入控制状态到文件"""
        try:
            with open(self.control_file, 'w', encoding='utf-8') as f:
                json.dump(state, f)
            print(f"成功写入控制文件: {self.control_file}")
        except Exception as e:
            print(f"写入控制文件失败: {e}")
    
    def set_process(self, process):
        """设置要控制的进程"""
        self.process = process
        
    def show(self):
        """显示控制窗口"""
        html_content = self._get_html_content()
        
        # 保存对self的引用，以便在Api类中使用
        control_window_ref = self
        
        class Api:
            def position_window(self, x, y):
                """设置窗口位置"""
                try:
                    if webview.windows and len(webview.windows) > 0:
                        webview.windows[0].minimize()
                    
                    x = int(x)
                    y = int(y)
                    if len(webview.windows) > 1:
                        webview.windows[1].move(x, y)
                    return True
                except Exception as e:
                    print(f"移动窗口失败: {str(e)}")
                    return False

            def move_window(self, x, y):
                """移动窗口到指定位置"""
                try:
                    x = int(x)
                    y = int(y)
                    if len(webview.windows) > 1:
                        webview.windows[1].move(x, y)
                    return True
                except Exception as e:
                    print(f"移动窗口失败: {str(e)}")
                    return False
            
            def get_window_position(self):
                """获取窗口当前位置"""
                try:
                    return {"x": 0, "y": 0}
                except Exception as e:
                    print(f"获取窗口位置失败: {str(e)}")
                    return {"x": 0, "y": 0}

            # 🚀 新增：检查任务状态API方法
            def check_task_status(self):
                """检查任务状态 - 前端调用"""
                try:
                    return control_window_ref.check_task_status()
                except Exception as e:
                    print(f"检查任务状态失败: {e}")
                    return {
                        'success': False,
                        'error': str(e),
                        'action': 'run',
                        'status': 'running',
                        'task_info': {}
                    }

            def close_window(self):
                """关闭窗口"""
                try:
                    print("API调用 close_window")
                    
                    # 写入停止状态
                    control_window_ref._write_control_state({
                        'action': 'stop',
                        'status': 'stopped',
                        'timestamp': time.time()
                    })
                    control_window_ref.status_text = "任务已停止"
                    
                    # 终止进程（不等待）
                    if control_window_ref.process:
                        try:
                            control_window_ref.process.terminate()
                        except:
                            pass
                    
                    # 清理控制文件
                    control_window_ref._cleanup()
                    
                    # 恢复主窗口并关闭控制窗口
                    if len(webview.windows) > 0:
                        webview.windows[0].restore()
                        webview.windows[0].maximize()
                    
                    if len(webview.windows) > 1:
                        webview.windows[1].destroy()
                        
                    return True
                except Exception as e:
                    print(f"关闭窗口失败: {e}")
                    return False
            
            def toggle_pause(self, should_pause):
                """切换暂停状态"""
                try:
                    print(f"API调用 toggle_pause: {should_pause}")
                    
                    if should_pause:
                        control_window_ref.is_paused = True
                        state = {
                            'action': 'pause',
                            'status': 'paused',
                            'timestamp': time.time()
                        }
                        control_window_ref._write_control_state(state)
                        control_window_ref.status_text = "任务已暂停"
                        return {"success": True, "status": "paused"}
                    else:
                        control_window_ref.is_paused = False
                        state = {
                            'action': 'resume',
                            'status': 'running',
                            'timestamp': time.time()
                        }
                        control_window_ref._write_control_state(state)
                        control_window_ref.status_text = "任务已继续"
                        return {"success": True, "status": "running"}
                        
                except Exception as e:
                    print(f"切换暂停状态失败: {e}")
                    return {"success": False, "error": str(e)}
        
        def start_window():
            self.window = webview.create_window(
                self.title,
                html=html_content,
                width=450,
                height=230,  # 保持原有高度
                resizable=False,
                frameless=True,
                on_top=True,
                js_api=Api()
            )
            webview.start(debug=False)
        
        # 在新线程中启动窗口
        window_thread = threading.Thread(target=start_window, daemon=True)
        window_thread.start()
        
    def _get_html_content(self):
        """获取窗口HTML内容 - 基于原始样式的简单美化版"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                    font-size: 12px;
                }}
                
                body {{
                    margin: 0;
                    padding: 8px;
                    background: transparent;
                    user-select: none;
                }}
                
                .container {{
                    background: rgba(255, 255, 255, 0.98);
                    border-radius: 8px;
                    padding: 12px;
                    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
                    backdrop-filter: blur(10px);
                }}
                
                .title-bar {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 12px;
                    padding-bottom: 8px;
                    border-bottom: 1px solid #f0f0f0;
                }}
                
                .title {{
                    color: #333;
                    font-weight: 500;
                    cursor: move;
                    flex-grow: 1;
                    padding: 4px;
                    font-size: 12px;
                }}
                
                .close-btn {{
                    cursor: pointer;
                    color: #999;
                    font-size: 16px;
                    width: 24px;
                    height: 24px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border-radius: 4px;
                    transition: all 0.2s;
                    z-index: 10;
                }}
                
                .close-btn:hover {{
                    background: #ff4d4f;
                    color: white;
                }}
                
                .status {{
                    color: #666;
                    margin: 8px 0;
                    line-height: 1.5;
                    font-size: 12px;
                    padding: 6px 8px;
                    border-radius: 4px;
                    min-height: 24px;
                    display: flex;
                    align-items: center;
                }}
                
                .bottom-bar {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-top: 12px;
                }}
                
                .timer {{
                    color: #666;
                    font-family: monospace;
                    font-size: 12px;
                }}
                
                .control-btn {{
                    padding: 6px 16px;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    color: white;
                    transition: all 0.2s;
                    font-size: 12px;
                }}
                
                .control-btn:hover {{
                    opacity: 0.9;
                }}
                
                .control-btn.running {{
                    background: #faad14;
                }}
                
                .control-btn.paused {{
                    background: #1890ff;
                }}
                
                .button-group {{
                    display: flex;
                    gap: 4px;
                }}

                .control-btn.stop {{
                    background: #ff4d4f;
                }}

                .control-btn.stop:hover {{
                    opacity: 0.9;
                }}
                
                .task-info {{
                    margin-top: 8px;
                    font-size: 11px;
                    color: #888;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="title-bar">
                    <div id="draggable-title" class="title">{self.title}</div>
                    <div class="close-btn" id="close-button">×</div>
                </div>
                <div class="status" id="status-text">准备开始处理任务...</div>
                <div class="task-info" id="task-info"></div>
                <div class="bottom-bar">
                    <span class="timer" id="timer">00:00:00</span>
                    <div class="button-group">
                        <button class="control-btn running" id="controlBtn">暂停</button>
                        <button class="control-btn stop" id="stopBtn">结束</button>
                    </div>
                </div>
            </div>
            <script>
                // 状态变量
                let isPaused = false;
                let startTime = Date.now();
                let timerInterval;
                let statusCheckInterval;
                let totalPausedTime = 0;
                let pauseStartTime = 0;
                
                // 拖动相关变量
                let isDragging = false;
                let lastX = 0;
                let lastY = 0;
                let windowX = 0;
                let windowY = 0;
                let lastMoveTime = 0;
                
                // 窗口定位初始化
                function positionWindow() {{
                    try {{
                        if (window.pywebview && window.pywebview.api) {{
                            const screenWidth = window.screen.width;
                            const screenHeight = window.screen.height;
                            const windowWidth = 450;
                            const windowHeight = 230;
                            const padding = 20;
                            
                            windowX = Math.floor(screenWidth - windowWidth - padding);
                            windowY = Math.floor(screenHeight - windowHeight - padding);
                            
                            pywebview.api.position_window(windowX, windowY);
                        }}
                    }} catch(e) {{
                        console.log('定位窗口失败:', e);
                    }}
                }}
                
                // 提高拖动性能的简单节流函数
                function moveWindow(x, y) {{
                    const now = Date.now();
                    if (now - lastMoveTime >= 8) {{
                        windowX = x;
                        windowY = y;
                        
                        const roundedX = Math.round(windowX);
                        const roundedY = Math.round(windowY);
                        
                        if (window.pywebview && window.pywebview.api) {{
                            pywebview.api.move_window(roundedX, roundedY);
                            lastMoveTime = now;
                        }}
                    }}
                }}
                
                // 时钟更新
                function updateTimer() {{
                    if (isPaused) return;
                    
                    const now = Date.now();
                    const diff = now - startTime - totalPausedTime;
                    const hours = Math.floor(diff / (1000 * 60 * 60));
                    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
                    const seconds = Math.floor((diff % (1000 * 60)) / 1000);
                    
                    document.getElementById('timer').textContent = 
                        `${{hours.toString().padStart(2, '0')}}:${{minutes.toString().padStart(2, '0')}}:${{seconds.toString().padStart(2, '0')}}`;
                }}
                
                // 简化的状态更新逻辑
                function checkTaskStatus() {{
                    if (window.pywebview && window.pywebview.api) {{
                        pywebview.api.check_task_status().then(function(result) {{
                            if (result.success) {{
                                const taskInfo = result.task_info || {{}};
                                
                                // 更新窗口标题
                                if (taskInfo.task_type) {{
                                    const titleElement = document.querySelector('.title');
                                    if (titleElement) {{
                                        titleElement.textContent = `${{taskInfo.task_type}} - 任务控制`;
                                    }}
                                }}
                                
                                // 更新状态文本
                                const statusElement = document.getElementById('status-text');
                                if (statusElement && taskInfo.status) {{
                                    statusElement.textContent = taskInfo.status;
                                }}
                                
                                // 检查是否需要自动关闭
                                if (result.auto_close && result.action === 'completed') {{
                                    console.log('任务完成，准备自动关闭窗口...');
                                    
                                    if (statusCheckInterval) {{
                                        clearInterval(statusCheckInterval);
                                    }}
                                    
                                    if (statusElement) {{
                                        statusElement.textContent = '🎉 任务已完成，窗口即将关闭...';
                                    }}
                                    
                                    setTimeout(function() {{
                                        pywebview.api.close_window().then(function() {{
                                            console.log('窗口已自动关闭');
                                        }}).catch(function(error) {{
                                            console.error('自动关闭窗口失败:', error);
                                        }});
                                    }}, 3000);
                                }}
                            }}
                        }}).catch(function(error) {{
                            console.error('检查任务状态失败:', error);
                        }});
                    }}
                }}
                
                // 拖动相关事件处理
                const titleEl = document.getElementById('draggable-title');
                
                titleEl.addEventListener('mousedown', function(e) {{
                    isDragging = true;
                    lastX = e.screenX;
                    lastY = e.screenY;
                    document.body.style.cursor = 'move';
                    e.preventDefault();
                    e.stopPropagation();
                }});
                
                document.addEventListener('mousemove', function(e) {{
                    if (!isDragging) return;
                    
                    const dx = e.screenX - lastX;
                    const dy = e.screenY - lastY;
                    
                    if (dx !== 0 || dy !== 0) {{
                        lastX = e.screenX;
                        lastY = e.screenY;
                        windowX += dx;
                        windowY += dy;
                        moveWindow(windowX, windowY);
                    }}
                }});
                
                document.addEventListener('mouseup', function(e) {{
                    if (isDragging) {{
                        isDragging = false;
                        document.body.style.cursor = 'default';
                    }}
                }});
                
                document.addEventListener('mouseleave', function(e) {{
                    if (isDragging) {{
                        isDragging = false;
                        document.body.style.cursor = 'default';
                    }}
                }});
                
                // 控制按钮事件处理
                document.getElementById('controlBtn').addEventListener('click', function(e) {{
                    e.stopPropagation();
                    
                    isPaused = !isPaused;
                    const newState = isPaused;
                    
                    this.textContent = newState ? '继续' : '暂停';
                    this.className = newState ? 'control-btn paused' : 'control-btn running';
                    
                    if (newState) {{
                        pauseStartTime = Date.now();
                    }} else {{
                        if (pauseStartTime > 0) {{
                            totalPausedTime += Date.now() - pauseStartTime;
                            pauseStartTime = 0;
                        }}
                    }}
                    
                    try {{
                        if (window.pywebview && window.pywebview.api) {{
                            pywebview.api.toggle_pause(newState).then(function(response) {{
                                if (response && response.status) {{
                                    const backendIsPaused = response.status === 'paused';
                                    if (isPaused !== backendIsPaused) {{
                                        isPaused = backendIsPaused;
                                        const btn = document.getElementById('controlBtn');
                                        btn.textContent = isPaused ? '继续' : '暂停';
                                        btn.className = isPaused ? 'control-btn paused' : 'control-btn running';
                                    }}
                                }}
                            }});
                        }}
                    }} catch(e) {{
                        console.log('切换暂停状态失败:', e);
                    }}
                }});
                
                // 关闭窗口
                function closeWindow() {{
                    clearInterval(timerInterval);
                    if (statusCheckInterval) {{
                        clearInterval(statusCheckInterval);
                    }}
                    window.taskStopped = true;
                    
                    try {{
                        if (window.pywebview && window.pywebview.api) {{
                            pywebview.api.close_window();
                        }}
                    }} catch(e) {{
                        console.log('关闭窗口失败:', e);
                        window.close();
                    }}
                }}
                
                document.getElementById('close-button').addEventListener('click', function(e) {{
                    e.stopPropagation();
                    closeWindow();
                }});
                
                document.getElementById('stopBtn').addEventListener('click', function(e) {{
                    e.stopPropagation();
                    closeWindow();
                }});
                
                // 启动
                function initialize() {{
                    try {{
                        setTimeout(positionWindow, 100);
                        timerInterval = setInterval(updateTimer, 1000);
                        statusCheckInterval = setInterval(checkTaskStatus, 500);
                    }} catch(e) {{
                        console.log('初始化失败:', e);
                    }}
                }}
                
                window.taskStopped = false;
                
                if (document.readyState === 'loading') {{
                    document.addEventListener('DOMContentLoaded', initialize);
                }} else {{
                    initialize();
                }}
            </script>
        </body>
        </html>
        """
    
    def _cleanup(self):
        """清理资源"""
        try:
            if self.control_file and os.path.exists(self.control_file):
                os.remove(self.control_file)
        except Exception as e:
            print(f"清理控制文件失败: {e}")
    
    def get_control_file_path(self):
        """获取控制文件路径"""
        return self.control_file

    def check_task_status(self):
        """检查任务状态"""
        try:
            if self.control_file and os.path.exists(self.control_file):
                with open(self.control_file, 'r', encoding='utf-8') as f:
                    control_state = json.load(f)
                    return {
                        'success': True,
                        'action': control_state.get('action', 'run'),
                        'status': control_state.get('status', 'running'),
                        'message': control_state.get('message', ''),
                        'auto_close': control_state.get('auto_close', False),
                        'timestamp': control_state.get('timestamp', 0),
                        'task_info': control_state.get('task_info', {})  # 🚀 新增任务信息
                    }
            else:
                return {
                    'success': False,
                    'action': 'run',
                    'status': 'running',
                    'message': '控制文件不存在',
                    'task_info': {}
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'action': 'run',
                'status': 'running',
                'task_info': {}
            }