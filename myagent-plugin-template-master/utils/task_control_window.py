import webview
import time
import threading



class TaskControlWindow:
    def __init__(self, title="任务控制", width=500, height=300):
        self.title = title
        self.width = width
        self.height = height
        self.window = None
        self.is_running = False
        
    def _get_html_content(self):
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                    font-size: 12px;
                }
                
                body {
                    margin: 0;
                    padding: 8px;
                    background: transparent;
                    user-select: none;
                }
                
                .container {
                    background: rgba(255, 255, 255, 0.98);
                    border-radius: 8px;
                    padding: 12px;
                    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
                    backdrop-filter: blur(10px);
                }
                
                .title-bar {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 12px;
                    padding-bottom: 8px;
                    border-bottom: 1px solid #f0f0f0;
                }
                
                .title {
                    color: #333;
                    font-weight: 500;
                }
                
                .close-btn {
                    cursor: pointer;
                    color: #999;
                    font-size: 16px;
                    width: 20px;
                    height: 20px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border-radius: 4px;
                    transition: all 0.2s;
                }
                
                .close-btn:hover {
                    background: #ff4d4f;
                    color: white;
                }
                
                .status {
                    color: #666;
                    margin: 8px 0;
                    line-height: 1.5;
                }
                
                .progress-bar {
                    width: 100%;
                    height: 4px;
                    background: #f5f5f5;
                    border-radius: 2px;
                    overflow: hidden;
                    margin: 12px 0;
                }
                
                .progress {
                    width: 0%;
                    height: 100%;
                    background: #1890ff;
                    transition: width 0.3s ease;
                }
                
                .bottom-bar {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-top: 12px;
                }
                
                .timer {
                    color: #666;
                    font-family: monospace;
                    font-size: 12px;
                }
                
                .control-btn {
                    padding: 6px 24px;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    color: white;
                    transition: all 0.2s;
                    background: #faad14;
                }
                
                .control-btn:hover {
                    opacity: 0.9;
                }
                
                .control-btn.running {
                    background: #faad14;
                }
                
                .control-btn.paused {
                    background: #1890ff;
                }
                
                /* 拖动样式 */
                .title-bar {
                    -webkit-app-region: drag;
                    cursor: move;
                }
                
                .close-btn, .control-btn {
                    -webkit-app-region: no-drag;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="title-bar">
                    <span class="title">任务控制</span>
                    <span class="close-btn" onclick="closeWindow()">×</span>
                </div>
                <div class="status">准备开始处理任务...</div>
                <div class="progress-bar">
                    <div class="progress"></div>
                </div>
                <div class="bottom-bar">
                    <span class="timer" id="timer">00:00:00</span>
                    <button class="control-btn running" id="controlBtn">暂停</button>
                </div>
            </div>
            <script>
                let isPaused = false;
                let startTime = Date.now();
                let timerInterval;
                let totalPausedTime = 0;
                let pauseStartTime = 0;
                
                function updateTimer() {
                    if (isPaused) return;  // 暂停时不更新时间
                    
                    const now = Date.now();
                    const diff = now - startTime - totalPausedTime;  // 减去总暂停时间
                    const hours = Math.floor(diff / (1000 * 60 * 60));
                    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
                    const seconds = Math.floor((diff % (1000 * 60)) / 1000);
                    
                    document.getElementById('timer').textContent = 
                        `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
                }
                
                // 启动计时器
                timerInterval = setInterval(updateTimer, 1000);
                
                function positionWindow() {
                    console.log("positionWindow called");
                    const screenWidth = window.screen.width;
                    const screenHeight = window.screen.height;
                    const windowWidth = 500;
                    const windowHeight = 300;
                    const padding = 20;
                    
                    // 调试信息
                    console.log("API 对象:", pywebview.api);
                    console.log("可用方法:", Object.keys(pywebview.api));
                    
                    pywebview.api.position_window(
                        Math.floor(screenWidth - windowWidth - padding),
                        Math.floor(screenHeight - windowHeight - padding)
                    ).then(result => {
                        console.log('窗口移动结果:', result);
                    }).catch(err => {
                        console.error('移动窗口出错:', err);
                    });
                }
                
                function waitForApi() {
                    let checkCount = 0;
                    const maxChecks = 50; // 最多等待5秒（100ms * 50）

                    function checkApi() {
                        if (window.pywebview && window.pywebview.api) {
                            // API 已就绪，调用定位函数
                            setTimeout(positionWindow, 100); // 延迟100ms再调用，确保窗口已完全创建
                        } else if (checkCount < maxChecks) {
                            // API 还未就绪，继续等待
                            checkCount++;
                            setTimeout(checkApi, 100);
                        } else {
                            console.error('API 初始化超时');
                        }
                    }

                    // 开始检查
                    setTimeout(checkApi, 100);
                }
                            
                
                 // 页面加载完成后启动 API 检查
                window.addEventListener('DOMContentLoaded', waitForApi);
                
                window.updateProgress = function(current, total, status) {
                    const progress = document.querySelector('.progress');
                    const statusEl = document.querySelector('.status');
                    progress.style.width = (current / total * 100) + '%';
                    statusEl.textContent = status;
                };
                
                window.getTaskStatus = function() {
                    return {
                        isPaused: isPaused
                    };
                };
                
                document.getElementById('controlBtn').onclick = function() {
                    isPaused = !isPaused;
                    this.textContent = isPaused ? '继续' : '暂停';
                    this.className = isPaused ? 'control-btn paused' : 'control-btn running';
                    
                    if (isPaused) {
                        // 记录开始暂停的时间
                        pauseStartTime = Date.now();
                    } else {
                        // 累加暂停的时间
                        if (pauseStartTime > 0) {
                            totalPausedTime += (Date.now() - pauseStartTime);
                            pauseStartTime = 0;
                        }
                    }
                };
                
                function closeWindow() {
                    console.log("关闭窗口");
                    clearInterval(timerInterval);  // 清除计时器
                    pywebview.api.close_window().then(result => {
                        if (!result) {
                            console.error('关闭窗口失败');
                        }
                    }).catch(err => {
                        console.error('关闭窗口出错:', err);
                    });
                }
            </script>
        </body>
        </html>
        """
        
    def create_window(self, main_window=None):
        """创建控制窗口"""
        class Api:
            
            def position_window(self, x, y):
                    """设置窗口位置"""
                    print(f"移动窗口: {x}, {y}")
                    try:
                        webview.windows[0].minimize()
                        
                        x = int(x)
                        y = int(y)
                        webview.windows[1].move(x, y)
                        return True
                    except Exception as e:
                        print(f"移动窗口失败: {str(e)}")
                        return False

            def close_window(self):
                    """关闭窗口"""
                    print("关闭窗口")
                    try:
                        webview.windows[0].restore()  # 恢复主窗口
                        webview.windows[0].maximize()  # 最大化主窗口
                        
                        webview.windows[1].destroy()
                        return True
                    except Exception as e:
                        print(f"关闭窗口失败: {str(e)}")
                        return False

        api = Api()
       

        self.window = webview.create_window(
            self.title,
            html=self._get_html_content(),
            width=self.width,
            height=self.height,
            resizable=False,
            frameless=True,
            on_top=True,
            js_api=api
        )
        
        
            
        self.is_running = True
        return self.window
    
    def run_task(self, task_func, *args, **kwargs):
        """
        运行任务的通用方法
        task_func: 需要执行的任务函数，该函数应接受control_window作为第一个参数
        """
        try:
            # 创建控制窗口
            self.create_window()
            
            # 启动任务线程
            thread = threading.Thread(
                target=task_func,
                args=(self, *args),
                kwargs=kwargs
            )
            thread.daemon = True
            thread.start()
            
            return True
        except Exception as e:
            print(f"启动任务失败: {str(e)}")
            return False

    def update_progress(self, current, total, status):
        """更新进度"""
        if self.window and self.is_running:
            self.window.evaluate_js(
                f'window.updateProgress({current}, {total}, "{status}")'
            )
    
    def get_status(self):
        """获取任务状态"""
        if self.window and self.is_running:
            return self.window.evaluate_js('window.getTaskStatus()')
        return {'isPaused': False}
    
    
        
        

    