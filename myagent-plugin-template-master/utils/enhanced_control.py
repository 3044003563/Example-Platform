# utils/enhanced_control.py
import functools
import threading
import time
import traceback
import signal
import os
import psutil
import uuid
import json

class EnhancedProcessControl:
    """增强的进程控制类，支持文件控制"""
    def __init__(self):
        self._paused = threading.Event()
        self._stopped = threading.Event()
        self._browser_pids = []
        self._session_id = str(uuid.uuid4())[:8]
        self._paused.set()  # 初始状态：未暂停
        
        # 添加文件控制支持
        self._control_file = os.environ.get('PROCESS_CONTROL_FILE')
        print(f"创建新的进程控制实例 ID: {self._session_id}")
        if self._control_file:
            print(f"启用文件控制: {self._control_file}")
    
    def _check_file_control(self):
        """检查文件控制指令"""
        if not self._control_file or not os.path.exists(self._control_file):
            return
        
        try:
            with open(self._control_file, 'r', encoding='utf-8') as f:
                control_state = json.load(f)
                action = control_state.get('action', 'run')
                
                if action == 'stop':
                    if not self._stopped.is_set():
                        print(f"[{self._session_id}] 文件控制：收到停止指令")
                        self.stop()
                elif action == 'pause':
                    if self._paused.is_set():  # 当前未暂停
                        print(f"[{self._session_id}] 文件控制：收到暂停指令")
                        self._paused.clear()
                elif action == 'resume' or action == 'run':
                    if not self._paused.is_set():  # 当前暂停中
                        print(f"[{self._session_id}] 文件控制：收到继续指令")
                        self._paused.set()
                        
        except Exception as e:
            print(f"[{self._session_id}] 检查文件控制失败: {e}")

    def pause(self):
        """暂停进程"""
        if self._paused.is_set():
            print(f"[{self._session_id}] 暂停进程")
            self._paused.clear()
        else:
            print(f"[{self._session_id}] 进程已处于暂停状态")
    
    def resume(self):
        """继续进程"""
        if not self._paused.is_set():
            print(f"[{self._session_id}] 继续进程")
            self._paused.set()
        else:
            print(f"[{self._session_id}] 进程已处于运行状态")
    
    def stop(self):
        """停止进程"""
        print(f"[{self._session_id}] 停止进程")
        self._stopped.set()
        self.resume()  # 确保暂停的进程也能退出
        self.terminate_browser()
    
    def is_paused(self):
        """检查是否暂停"""
        self._check_file_control()  # 每次检查时都读取文件状态
        return not self._paused.is_set()
    
    def is_stopped(self):
        """检查是否停止"""
        self._check_file_control()  # 每次检查时都读取文件状态
        return self._stopped.is_set()
    
    def register_browser_pid(self, pid):
        """注册浏览器进程ID"""
        if pid and pid not in self._browser_pids:
            self._browser_pids.append(pid)
            print(f"[{self._session_id}] 注册浏览器进程 PID: {pid}")
    
    def terminate_browser(self):
        """优雅地终止浏览器进程"""
        if not self._browser_pids:
            return
        
        print(f"[{self._session_id}] 开始优雅终止已注册的浏览器进程 {self._browser_pids}")
        
        for pid in self._browser_pids:
            try:
                if psutil.pid_exists(pid):
                    process = psutil.Process(pid)
                    
                    # 先尝试优雅关闭
                    print(f"[{self._session_id}] 尝试优雅关闭浏览器进程 {pid}")
                    process.terminate()
                    
                    # 等待进程自然结束
                    try:
                        process.wait(timeout=3)  # 等待3秒
                        print(f"[{self._session_id}] 浏览器进程 {pid} 已优雅关闭")
                    except psutil.TimeoutExpired:
                        # 如果3秒后还没结束，强制杀死
                        print(f"[{self._session_id}] 强制杀死浏览器进程 {pid}")
                        process.kill()
                        process.wait(timeout=2)
                    
            except psutil.NoSuchProcess:
                print(f"[{self._session_id}] 进程 {pid} 已经不存在")
            except Exception as e:
                print(f"[{self._session_id}] 终止进程 {pid} 失败: {str(e)}")
        
        # 清空已终止的进程列表
        self._browser_pids = []
        print(f"[{self._session_id}] 浏览器进程终止完成")
    
    def sleep(self, seconds):
        """可中断的睡眠，支持文件控制"""
        print(f"[{self._session_id}] 开始sleep {seconds}秒")
        end_time = time.time() + seconds
        while time.time() < end_time:
            # 检查文件控制状态
            self._check_file_control()
            
            if self.is_stopped():
                print(f"[{self._session_id}] 检测到停止信号，中断sleep")
                return False
                
            if self.is_paused():
                print(f"[{self._session_id}] 检测到暂停信号，暂停sleep计时")
                pause_start = time.time()
                
                while self.is_paused() and not self.is_stopped():
                    time.sleep(0.1)
                
                if not self.is_stopped():
                    pause_duration = time.time() - pause_start
                    end_time += pause_duration
                    print(f"[{self._session_id}] 恢复执行，sleep时间延长了{pause_duration:.2f}秒")
                
            if self.is_stopped():
                return False
                
            remaining = end_time - time.time()
            if remaining > 0:
                time.sleep(min(0.1, remaining))
        
        return True

def with_enhanced_control(func):
    """增强版装饰器 - 异步版本"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # 创建控制实例
        process_control = EnhancedProcessControl()
        
        if process_control.is_stopped():
            print(f"进程控制已处于停止状态，无法执行任务")
            return {'success': False, 'error': '任务控制器已停止'}
            
        session_id = getattr(process_control, '_session_id', 'unknown')
        
        # 创建结果容器
        result_container = {'result': None, 'exception': None, 'completed': False}
        
        # 保存原始的sleep函数
        original_sleep = time.sleep
        
        # 定义新的sleep函数，在每次sleep时检查控制状态
        def controlled_sleep(seconds):
            # 将长时间的sleep拆分成短时间的sleep，以便更频繁地检查暂停/停止状态
            end_time = time.time() + seconds
            while time.time() < end_time:
                # 检查文件控制状态
                process_control._check_file_control()
                
                # 检查是否应该停止
                if process_control.is_stopped():
                    print(f"[{session_id}] 控制检查：检测到停止信号，中断sleep")
                    raise InterruptedError("任务已被停止")
                
                # 检查是否应该暂停
                if process_control.is_paused():
                    print(f"[{session_id}] 控制检查：检测到暂停信号，暂停执行")
                    pause_start = time.time()
                    
                    # 等待恢复或停止
                    while process_control.is_paused() and not process_control.is_stopped():
                        original_sleep(0.1)  # 这里使用original_sleep
                    
                    # 如果被停止，则终止
                    if process_control.is_stopped():
                        print(f"[{session_id}] 控制检查：在暂停状态下收到停止信号")
                        raise InterruptedError("任务已被停止")
                    
                    # 只有当实际上恢复了才计算暂停时间
                    if not process_control.is_paused():
                        # 计算暂停持续时间，并相应延长结束时间
                        pause_duration = time.time() - pause_start
                        end_time += pause_duration
                        print(f"[{session_id}] 控制检查：恢复执行，延长了{pause_duration:.2f}秒")
                
                # 短暂sleep
                remaining = min(0.2, end_time - time.time())  # 最多sleep 0.2秒
                if remaining > 0:
                    original_sleep(remaining)  # 这里使用original_sleep
        
        # 记录Chrome进程
        chrome_before = set()
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if 'chrome' in proc.info['name'].lower():
                        chrome_before.add(proc.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            print(f"[{session_id}] 获取现有Chrome进程失败: {str(e)}")
        
        # 定义工作线程函数
        def worker():
            try:
                # 替换time.sleep函数
                time.sleep = controlled_sleep
                
                # 执行原始函数
                result_container['result'] = func(*args, **kwargs)
                result_container['completed'] = True
            except InterruptedError as e:
                # 捕获中断异常
                result_container['exception'] = e
                result_container['completed'] = True
                print(f"[{session_id}] 任务被中断: {str(e)}")
            except Exception as e:
                # 捕获其他异常
                if "Target page, context or browser has been closed" in str(e) or "TargetClosedError" in str(e):
                    # 这是因为浏览器已被强制关闭造成的，可以忽略
                    print(f"[{session_id}] 浏览器已关闭，任务已终止")
                    result_container['completed'] = True
                    result_container['exception'] = InterruptedError("任务已被停止")
                else:
                    # 其他真正的异常
                    result_container['exception'] = e
                    result_container['completed'] = True
                    print(f"[{session_id}] 函数执行出错: {str(e)}")
                    traceback.print_exc()
            finally:
                # 恢复原始sleep函数
                time.sleep = original_sleep
                # 确保设置完成标志
                result_container['completed'] = True
        
        # 🚀 改动开始：后台监控线程
        def background_monitor():
            # 等待1秒，让Playwright有时间启动浏览器
            original_sleep(1)
            
            # 检测新的Chrome进程
            try:
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        if 'chrome' in proc.info['name'].lower() and proc.info['pid'] not in chrome_before:
                            # 注册新的浏览器进程
                            process_control.register_browser_pid(proc.info['pid'])
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            except Exception as e:
                print(f"[{session_id}] 注册Chrome进程失败: {str(e)}")
            
            # 主线程循环，监控工作线程状态
            while work_thread.is_alive():
                # 检查是否应该停止
                if process_control.is_stopped():
                    print(f"[{session_id}] 收到停止信号，开始优雅终止...")
                    
                    # 先设置停止标志，让工作线程自然结束
                    process_control._stopped.set()
                    
                    # 等待工作线程自然结束
                    print(f"[{session_id}] 等待工作线程自然结束...")
                    work_thread.join(timeout=5)  # 等待5秒
                    
                    if work_thread.is_alive():
                        print(f"[{session_id}] 工作线程未能自然结束，开始终止浏览器...")
                        # 如果线程还在运行，才终止浏览器
                        try:
                            process_control.terminate_browser()
                        except Exception as e:
                            print(f"[{session_id}] 终止浏览器时出错: {e}")
                        
                        # 再等待一下
                        work_thread.join(timeout=3)
                    
                    print(f"[{session_id}] 停止流程完成")
                    break
                
                # 检查任务是否已完成
                if result_container['completed']:
                    break
                    
                # 简短休眠以减少循环频率
                original_sleep(0.1)
            
            # 线程已结束，清理资源
            try:
                if process_control._browser_pids:
                    print(f"[{session_id}] 任务完成，清理剩余浏览器进程...")
                    process_control.terminate_browser()
            except Exception as e:
                print(f"[{session_id}] 清理浏览器进程时出错: {e}")
                
            print(f"[{session_id}] 后台监控结束")
        
        # 创建并启动工作线程
        work_thread = threading.Thread(target=worker)
        work_thread.daemon = False
        work_thread.start()
        
        # 🚀 关键改动：启动后台监控线程，不阻塞主流程
        monitor_thread = threading.Thread(target=background_monitor, daemon=True)
        monitor_thread.start()
        
        # 🚀 立即返回异步任务状态，不等待完成
        return {
            'success': True,
            'message': f'任务已启动 (Session: {session_id})',
            'task_status': 'started',
            'session_id': session_id
        }
    
    return wrapper

def with_enhanced_control_async(func):
    """异步版本的增强控制装饰器，立即返回，后台执行"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"启动异步任务: {func.__name__}")
        
        # 创建控制实例
        process_control = EnhancedProcessControl()
        
        if process_control.is_stopped():
            print(f"进程控制已处于停止状态，无法执行任务")
            return {'success': False, 'error': '任务控制器已停止'}
            
        session_id = getattr(process_control, '_session_id', 'unknown')
        
        # 保存原始的sleep函数
        original_sleep = time.sleep
        
        # 定义新的sleep函数
        def controlled_sleep(seconds):
            end_time = time.time() + seconds
            while time.time() < end_time:
                process_control._check_file_control()
                
                if process_control.is_stopped():
                    print(f"[{session_id}] 控制检查：检测到停止信号，中断sleep")
                    raise InterruptedError("任务已被停止")
                
                if process_control.is_paused():
                    print(f"[{session_id}] 控制检查：检测到暂停信号，暂停执行")
                    pause_start = time.time()
                    
                    while process_control.is_paused() and not process_control.is_stopped():
                        original_sleep(0.1)
                    
                    if process_control.is_stopped():
                        print(f"[{session_id}] 控制检查：在暂停状态下收到停止信号")
                        raise InterruptedError("任务已被停止")
                    
                    if not process_control.is_paused():
                        pause_duration = time.time() - pause_start
                        end_time += pause_duration
                        print(f"[{session_id}] 控制检查：恢复执行，延长了{pause_duration:.2f}秒")
                
                remaining = min(0.2, end_time - time.time())
                if remaining > 0:
                    original_sleep(remaining)
        
        # 记录Chrome进程
        chrome_before = set()
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if 'chrome' in proc.info['name'].lower():
                        chrome_before.add(proc.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            print(f"[{session_id}] 获取现有Chrome进程失败: {str(e)}")
        
        # 后台工作函数
        def background_worker():
            try:
                print(f"[{session_id}] 后台任务开始执行")
                
                # 替换time.sleep函数
                time.sleep = controlled_sleep
                
                # 等待1秒，让Playwright有时间启动浏览器
                original_sleep(1)
                
                # 检测新的Chrome进程
                try:
                    for proc in psutil.process_iter(['pid', 'name']):
                        try:
                            if 'chrome' in proc.info['name'].lower() and proc.info['pid'] not in chrome_before:
                                process_control.register_browser_pid(proc.info['pid'])
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                except Exception as e:
                    print(f"[{session_id}] 注册Chrome进程失败: {str(e)}")
                
                # 执行原始函数
                result = func(*args, **kwargs)
                print(f"[{session_id}] 后台任务执行完成")
                
            except InterruptedError as e:
                print(f"[{session_id}] 后台任务被中断: {str(e)}")
            except Exception as e:
                if "Target page, context or browser has been closed" in str(e) or "TargetClosedError" in str(e):
                    print(f"[{session_id}] 浏览器已关闭，任务已终止")
                else:
                    print(f"[{session_id}] 后台任务执行出错: {str(e)}")
                    traceback.print_exc()
            finally:
                # 恢复原始sleep函数
                time.sleep = original_sleep
                
                # 清理浏览器进程
                try:
                    if process_control._browser_pids:
                        print(f"[{session_id}] 清理浏览器进程...")
                        process_control.terminate_browser()
                except Exception as e:
                    print(f"[{session_id}] 清理浏览器进程时出错: {e}")
                
                print(f"[{session_id}] 后台任务完全结束")
        
        # 启动后台线程
        bg_thread = threading.Thread(target=background_worker, daemon=False)
        bg_thread.start()
        
        # 立即返回任务状态
        return {
            'success': True,
            'message': f'任务已启动 (Session: {session_id})',
            'task_status': 'started',
            'session_id': session_id
        }
    
    return wrapper