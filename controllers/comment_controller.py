from models.comment_model import CommentModel
from models.accountmanage_model import AccountmanageModel
from utils.task_progress_manager import TaskProgressManager
from utils.example_util import ExampleUtil


class CommentController:
    def __init__(self, plugin_name, data_directory):
        self.plugin_name = plugin_name
        self.data_directory = data_directory
        self.model = CommentModel(plugin_name, data_directory)
        self.account_model = AccountmanageModel(plugin_name, data_directory)

    def add_comment(self, *args, **kwargs):
        link = kwargs.get('link')
        content = kwargs.get('content')
        comment_time = kwargs.get('comment_time')
        author = kwargs.get('author')
        ip = kwargs.get('ip')
        if not link or not content:
            return {'success': False, 'data': '链接与评论内容必填'}
        self.model.add_comment(link, content, comment_time, author, ip)
        return {'success': True, 'data': '评论添加成功'}

    def get_comments(self, *args, **kwargs):
        page = int(kwargs.get('page', 1))
        page_size = int(kwargs.get('page_size', 10))
        keyword = kwargs.get('keyword', '')
        result = self.model.get_comments(page, page_size, keyword)
        return {'success': True, 'data': result}

    def update_comment(self, *args, **kwargs):
        id = kwargs.get('id')
        link = kwargs.get('link')
        content = kwargs.get('content')
        comment_time = kwargs.get('comment_time')
        author = kwargs.get('author')
        ip = kwargs.get('ip')
        if not id:
            return {'success': False, 'data': '缺少评论ID'}
        self.model.update_comment(id, link, content, comment_time, author, ip)
        return {'success': True, 'data': '评论更新成功'}

    def delete_comment(self, *args, **kwargs):
        id = kwargs.get('id')
        if not id:
            return {'success': False, 'data': '缺少评论ID'}
        self.model.delete_comment(id)
        return {'success': True, 'data': '删除成功'}

    def batch_delete_comments(self, *args, **kwargs):
        ids = kwargs.get('ids', [])
        if not ids:
            return {'success': False, 'data': '请选择要删除的评论'}
        self.model.batch_delete_comments(ids)
        return {'success': True, 'data': '批量删除成功'}

    def collect_comments(self, *args, **kwargs):
        """
        说明：示例采集实现，复用 ExampleUtil 按关键词采集视频列表，
        将采集到的视频信息映射写入评论表（link 写入视频链接，content 简要填充为标题或留空，author 写入作者昵称）。
        前端需传入：keyword、account_id，可选 need_control_window 由上层控制。
        """
        try:
            keyword = kwargs.get('keyword', '').strip()
            account_id = kwargs.get('account_id', '').strip()
            if not keyword:
                return {'success': False, 'data': '关键词不能为空'}
            if not account_id:
                return {'success': False, 'data': '账号ID不能为空'}

            # 获取账号信息（决定浏览器用户目录隔离等）
            account = self.account_model.get_account_by_id(account_id)
            if not account:
                return {'success': False, 'data': '未找到账号信息'}
            platform_name = account.get('platform_name')
            username = account.get('username')

            # 进度管理（可选，用于控制窗口展示）
            task_progress = TaskProgressManager()
            task_progress.init_task('评论采集')
            task_progress.update_status(f'开始按关键词采集：{keyword} ...')

            collected_count = 0

            # 设置采集工具与回调，收到批量数据时写入评论表
            util = ExampleUtil(self.data_directory)

            def on_batch(data):
                nonlocal collected_count
                videos = data.get('videos') or []
                if not videos:
                    return True
                for v in videos:
                    link = v.get('link') or ''
                    title = v.get('title') or ''
                    author = v.get('author') or ''
                    # 将视频信息映射为一条“评论”记录（示例：内容用标题占位）
                    try:
                        self.model.add_comment(link=link, content=title, comment_time=None, author=author, ip=None)
                        collected_count += 1
                        task_progress.update_status(f"已保存 {collected_count} 条: {title[:20]}")
                    except Exception as e:
                        task_progress.update_status(f"保存出错: {str(e)[:30]}")
                return True

            util.set_callback(on_batch)

            # 启动浏览器采集（内部会不断滚动触发接口响应，回调逐批写库）
            util.get_douyinlink_list(keyword, platform_name, username)

            task_progress.complete_task(f'采集完成，共保存 {collected_count} 条')
            return {'success': True, 'data': f'采集任务完成，已保存 {collected_count} 条'}

        except Exception as e:
            return {'success': False, 'data': f'采集失败：{str(e)}'}
