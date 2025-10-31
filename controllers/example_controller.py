from models.example_model import ExampleModel
from utils.example_util import ExampleUtil
from utils.task_progress_manager import TaskProgressManager
from models.accountmanage_model import AccountmanageModel
from utils.enhanced_control import with_enhanced_control


class ExampleController():
    def __init__(self,plugin_name,data_directory):
        self.plugin_name=plugin_name
        self.data_directory=data_directory
        self.model = ExampleModel(plugin_name,data_directory)
        self.account_model = AccountmanageModel(plugin_name,data_directory)
        self.initialize()
       
    def initialize(self):
        pass
        

    def add_item(self, *args, **kwargs):
        print("add_item===============")
        print(args)
        title=kwargs.get('title')
        link=kwargs.get('link')
        author=kwargs.get('author')
        self.model.add_item(title,link,author)
        return {'success': True, 'data': '新项目创建成功'}

    def get_items(self, *args, **kwargs):
        print("get_items===============")
        page = int(kwargs.get('page', 1))
        page_size = int(kwargs.get('page_size', 10))
        keyword = kwargs.get('keyword', '')
        
        result = self.model.get_items(page, page_size, keyword)
        
        return {'success': True, 'data': result}
    
    
    def update_item(self, *args, **kwargs):
        print("update_item===============")
        id = kwargs.get('id')
        title = kwargs.get('title')
        link = kwargs.get('link')
        self.model.update_item(id, title, link)
        return {'success': True, 'data': '修改成功'}


    def delete_item(self, *args, **kwargs):
        print("delete_item===============")
        id = kwargs.get('id')
        self.model.delete_item(id)
        return {'success': True, 'data': '删除成功'}

    def batch_delete_items(self, *args, **kwargs):
        print("batch_delete_items===============")
        ids = kwargs.get('ids', [])
        if not ids:
            return {'success': False, 'data': '请选择要删除的项目'}
        
        self.model.batch_delete_items(ids)
        return {'success': True, 'data': '批量删除成功'}
    
    
    
    def collect_links(self, *args, **kwargs):
        """
        采集链接
        :param kwargs: 包含 keyword 参数
        :return: 返回采集结果
        """
        try:
            keyword = kwargs.get('keyword', '')
            account_id = kwargs.get('account_id', '')
            
            if not keyword:
                return {'success': False, 'data': '关键词不能为空'}
                
            
            if not account_id:
                return {'success': False, 'data': '账号ID不能为空'}
            
            
             # 获取账号信息
            account = self.account_model.get_account_by_id(account_id)
            platform_name = account.get('platform_name')
            username = account.get('username')
            
            # 🚀 创建任务进度管理器
            task_progress = TaskProgressManager()
            
            # 使用装饰器处理批量采集 - 整个批量操作使用一次装饰器
            def process_collection_batch(keyword, platform_name, username):
                collected_count = 0
                
                # 🚀 简化：只初始化任务类型
                task_progress.init_task("批量采集")
                
                # 🚀 更新初始状态
                task_progress.update_status(f"正在初始化采集: {keyword}...")
                
                # 简化的回调函数
                def collection_callback(data):
                    nonlocal collected_count
                    if 'videos' in data and data['videos']:
                        try:
                            batch_videos = data['videos']
                            for video in batch_videos:
                                self.add_item(title=video['title'], link=video['link'], author=video['author'])
                                collected_count += 1
                                
                                # 🚀 实时更新采集进度
                                task_progress.update_status(f"已采集 {collected_count} 个视频: {video['title'][:20]}...")
                                
                            print(f"已采集 {collected_count} 个视频")
                        except Exception as e:
                            print(f"处理采集回调时出错: {str(e)}")
                            # 🚀 显示错误状态
                            task_progress.update_status(f"⚠️ 处理出错: {str(e)[:20]}...")
                    return True
                
                # 初始化抖音链接工具
                example_util = ExampleUtil(self.data_directory)
                example_util.set_callback(collection_callback)
                
                # 🚀 更新开始采集状态
                task_progress.update_status(f"开始采集关键词: {keyword}...")
                print(f"开始采集关键词: {keyword}")
                
                try:
                    # 调用采集方法（这里不再使用装饰器，因为已经在外层使用了）
                    videos = example_util.get_douyinlink_list(
                        keyword, 
                        platform_name, 
                        username
                    )
                    
                    # 🚀 任务完成 - 简化显示
                    final_message = f'🎉 采集完成！共采集 {collected_count} 个视频'
                    print(final_message)
                    
                    task_progress.complete_task(final_message)
                    
                    return {
                        'success': True, 
                        'collected_count': collected_count,
                        'message': f'采集完成，共采集 {collected_count} 个视频'
                    }
                    
                except Exception as e:
                    # 🚀 采集失败状态
                    error_message = f'❌ 采集失败: {str(e)[:50]}...'
                    print(f"采集失败: {str(e)}")
                    
                    task_progress.update_status(error_message)
                    task_progress.complete_task(error_message)
                    
                    return {
                        'success': False,
                        'collected_count': collected_count,
                        'error': str(e)
                    }
            
            # 使用装饰器执行整个批量任务
            result = with_enhanced_control(process_collection_batch)(keyword, platform_name, username)
            
            
            
            return {'success': True, 'data': '采集任务已开始'}
            
        except Exception as e:
            print(f"collect_links error: {str(e)}")
            return {'success': False, 'data': f'采集失败: {str(e)}'}
            
    