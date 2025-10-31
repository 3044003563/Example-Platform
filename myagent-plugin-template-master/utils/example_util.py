from playwright.sync_api import sync_playwright

import win32gui
import win32con
import time


import numpy as np
from PIL import Image

import os
from datetime import datetime


try:
    from utils.playwright_util import PlaywrightUtil
except ImportError:
    from playwright_util import PlaywrightUtil


class ExampleUtil:
    def __init__(self,data_directory:str):
        #self.user_data_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'Google', 'Chromes', 'User Data')
        self.data_directory=data_directory
        #self.user_data_dir ="D:\\Data\\MyAgent\\Chrome\\18925203701"
        self.videos = []
        self.callback = None
        self.total_videos = 0  # 添加总视频计数


    def set_callback(self, callback):
        """设置回调函数"""
        self.callback = callback
        print("回调函数已设置")



    def handle_response(self, response):
            """处理接口响应"""
            if "aweme/v1/web/search/item" in response.url:
                try:
                    data = response.json()
                    if data.get('data'):
                        batch_videos = []
                        for item in data['data']:
                            # print("item=============",item)
                            if item.get('type') == 1:  # 视频类型
                                video_info = {
                                    'title': item.get('aweme_info', {}).get('desc', ''),
                                    'link': f"https://www.douyin.com/video/{item.get('aweme_info', {}).get('aweme_id', '')}",
                                    'author': item.get('aweme_info', {}).get('author', {}).get('nickname', '')  # 添加作者昵称
                                }
                                self.videos.append(video_info)
                                batch_videos.append(video_info)
                        
                        # 如果有新的视频数据，触发回调
                        if self.callback and batch_videos:
                            self.total_videos = len(self.videos)
                            self.callback({
                                'videos': batch_videos,  # 只传递这一批新的视频
                                'current': self.total_videos,
                                'total': max(self.total_videos, 100),  # 设置一个最小目标
                                'need_save': True  # 添加标记，表示需要保存到数据库
                            })
                            print(f"回调触发: 当前批次 {len(batch_videos)} 个视频，总计 {self.total_videos} 个视频")
                            
                except Exception as e:
                    print(f"解析响应数据出错: {str(e)}")
    
    
    def get_douyinlink_list(self, keyword=None,platform_name=None,username=None):
        """获取抖音链接列表"""
        self.user_data_dir=os.path.join(self.data_directory,'Chromes',platform_name,username)
        print("采集的时候用的用户目录，self.user_data_dir",self.user_data_dir)
            
        with sync_playwright() as p:
            print("开始获取抖音链接列表",self.user_data_dir)
            
           
            
            # 配置浏览器启动参数
            browser = p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
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

            try:
                # 创建新页面
                page = browser.new_page()
                
                
                # 监听网络请求
                page.on("response", self.handle_response)

               
                # 访问搜索页面
                search_url = f"https://www.douyin.com/discover/search/{keyword}?type=video"
                print(f"正在访问: {search_url}")
                page.goto(search_url, wait_until="domcontentloaded")  # 改为只等待DOM加载完成
          
          
                # 使用工具类最大化窗口
                # 窗口最大化也能响应停止请求
                PlaywrightUtil.maximize_browser_window()
                 
     
                
                # 滚动页面以触发更多请求
                print("开始滚动页面加载更多内容...")
                last_height = 0
                retry_count = 0
                max_retries = 3  # 最大重试次数
                scroll_count = 0  # 记录滚动次数

                
                while True:  # 移除了thread_control.is_stopped()检查
                    try:
                        # 获取滚动前的页面高度
                        current_height = page.evaluate("document.documentElement.scrollHeight")
                        
                        # 滚动到页面底部
                        page.evaluate("""() => {
                            window.scrollTo({
                                top: document.documentElement.scrollHeight,
                                behavior: 'smooth'
                            });
                        }""")
                        
                        # 等待加载
                        time.sleep(2)
                        
                        # 检查是否出现"暂时没有更多了"的元素
                        no_more = page.query_selector("div.ECAcoo0p div.shrAJJLa")
                        if no_more:
                            no_more_text = page.evaluate("el => el.textContent", no_more)
                            if "暂时没有更多了" in no_more_text:
                                print("检测到'暂时没有更多了'，停止滚动")
                                break
                        
                        # 获取滚动后的新页面高度
                        new_height = page.evaluate("document.documentElement.scrollHeight")
                        scroll_count += 1
                        
                        print(f"第 {scroll_count} 次滚动，页面高度: {new_height}（之前：{current_height}）")
                        
                        # 检查页面高度是否有变化
                        if new_height <= current_height:
                            retry_count += 1
                            print(f"页面高度未增加，重试次数：{retry_count}/{max_retries}")
                            if retry_count >= max_retries:
                                print("达到最大重试次数，确认已加载全部内容")
                                break
                        else:
                            retry_count = 0  # 如果页面高度有变化，重置重试计数
                            print(f"页面已加载更多内容，当前视频数: {len(self.videos)}")
                        
                        last_height = new_height
                        
                        time.sleep(3)
                        
                    except Exception as e:
                        print(f"滚动过程出错: {str(e)}")
                        if scroll_count == 0:
                            print("首次滚动就发生错误，请检查页面状态")
                        break
                    

                print(f"滚动完成，共执行 {scroll_count} 次滚动，找到 {len(self.videos)} 个视频")
                return self.videos

            except Exception as e:
                print(f"抓取过程出错: {str(e)}")
                return []

            finally:
                browser.close()