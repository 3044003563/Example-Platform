import win32gui
import win32con
import time

class PlaywrightUtil:
    @staticmethod
    def maximize_browser_window():
        """
        最大化浏览器窗口的静态方法
        使用 win32gui 查找并最大化 Chrome 窗口
        """
        def enum_windows_callback(hwnd, _):
            if "Chrome" in win32gui.GetWindowText(hwnd):
                # 确保窗口可见且不是最小化状态
                if win32gui.IsWindowVisible(hwnd) and not win32gui.IsIconic(hwnd):
                    # 最大化窗口
                    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                    return False
            return True
        
        try:
            win32gui.EnumWindows(enum_windows_callback, None)
            time.sleep(0.5)  # 给窗口一点时间完成最大化
            return True
        except Exception as e:
            print(f"最大化窗口失败: {str(e)}")
            return False

    @staticmethod
    def create_browser_context(playwright, user_data_dir):
        """
        创建浏览器上下文的静态方法
        返回配置好的浏览器实例
        """
        return playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            channel="chrome",
            headless=False,
            no_viewport=True,  # 禁用视窗大小限制
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--no-default-browser-check',
                '--no-first-run'
            ]
        )