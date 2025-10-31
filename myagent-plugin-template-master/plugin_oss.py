from packaging.version import Version
import os
import oss2
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class PluginOss:
    def __init__(self):
        


        # 阿里云 OSS 配置
        self.access_key_id = 'LTAI5tHk3ttc1MXKUawfDo4e'
        self.access_key_secret = 'hogXPtQ4gducA9Mk2VeZInndxmxltD'
        self.endpoint = 'oss-cn-shenzhen.aliyuncs.com'  # 例如: 'http://oss-cn-hangzhou.aliyuncs.com'
        self.bucket_name = 'myrpa'
        
      
        # 获取当前文件所在目录
        current_dir = Path(__file__).parent  # utils目录
        
        # 构建插件目录路径 (上一级的plugins/installed)
        self.plugin_dir = current_dir.parent / 'plugins' / 'installed'
        
        # 确保插件目录存在
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        
        
        # 初始化 OSS 客户端
        self.bucket = self._init_oss_client()

    def _init_oss_client(self):
        """初始化 OSS 客户端"""
        try:
            auth = oss2.Auth(self.access_key_id, self.access_key_secret)
            return oss2.Bucket(auth, self.endpoint, self.bucket_name)
        except Exception as e:
            logger.error(f"初始化 OSS 客户端失败: {e}")
            raise

    def download_plugin(self, plugin_name, version):
        """
        下载指定插件的指定版本
        :param plugin_name: 插件名称
        :param version: 插件版本
        :return: 本地插件路径
        """
        try:
            # OSS 上的插件路径
            oss_path = f'plugins/{plugin_name}/{version}/{plugin_name}.zip'
            
            # 本地保存路径
            local_dir = self.plugin_dir / plugin_name / version
            local_dir.mkdir(parents=True, exist_ok=True)
            local_path = local_dir / f'{plugin_name}.zip'
            
            print(local_path)

            # 检查文件是否存在
            if not self.bucket.object_exists(oss_path):
                raise FileNotFoundError(f"插件文件不存在: {oss_path}")

            # 下载文件
            logger.info(f"开始下载插件: {plugin_name} v{version}")
            self.bucket.get_object_to_file(oss_path, str(local_path))
            logger.info(f"插件下载完成: {local_path}")

            return local_path

        except oss2.exceptions.NoSuchKey:
            logger.error(f"插件文件不存在: {oss_path}")
            raise FileNotFoundError(f"插件文件不存在: {oss_path}")
        except Exception as e:
            logger.error(f"下载插件失败: {e}")
            raise

    def list_available_plugins(self):
        """
        列出 OSS 上可用的所有插件
        :return: 插件列表 [{'name': 'plugin1', 'versions': ['1.0', '1.1']}, ...]
        """
        try:
            plugins = {}
            prefix = 'plugins/'
            
            # 列出所有插件文件
            for obj in oss2.ObjectIterator(self.bucket, prefix=prefix):
                # 解析路径: plugins/plugin_name/version/plugin_name.zip
                parts = obj.key.split('/')
                if len(parts) == 4 and parts[3].endswith('.zip'):
                    plugin_name = parts[1]
                    version = parts[2]
                    
                    if plugin_name not in plugins:
                        plugins[plugin_name] = {'name': plugin_name, 'versions': set()}
                    plugins[plugin_name]['versions'].add(version)

            # 转换版本集合为列表
            return [
                {'name': info['name'], 'versions': sorted(list(info['versions']))}
                for info in plugins.values()
            ]

        except Exception as e:
            logger.error(f"获取插件列表失败: {e}")
            raise

    def get_latest_version(self, plugin_name):
        """
        获取指定插件的最新版本
        :param plugin_name: 插件名称
        :return: 最新版本号
        """
        try:
            plugins = self.list_available_plugins()
            for plugin in plugins:
                if plugin['name'] == plugin_name:
                    versions = sorted(plugin['versions'], key=lambda x: Version(x))
                    return versions[-1] if versions else None
            return None
        except Exception as e:
            logger.error(f"获取插件最新版本失败: {e}")
            raise
        
        
    
    def upload_plugin(self, plugin_name, version, local_path):
        """
        上传插件到 OSS
        :param plugin_name: 插件名称
        :param version: 插件版本
        :param local_path: 本地插件路径
        """
        try:
            # OSS 上的插件路径
            oss_path = f'plugins/{plugin_name}/{version}/{plugin_name}.zip'
            
            # 上传文件
            logger.info(f"开始上传插件: {plugin_name} v{version} 到 OSS")
            self.bucket.put_object_from_file(oss_path, local_path)
            logger.info(f"插件上传完成: {oss_path}")

        except Exception as e:
            logger.error(f"上传插件失败: {e}")
            raise
        
    
    def delete_plugin_version(self, plugin_name, version):
        """
        删除指定插件的指定版本
        :param plugin_name: 插件名称
        :param version: 插件版本
        """
        try:
            # OSS 上的插件路径
            oss_path = f'plugins/{plugin_name}/{version}/{plugin_name}.zip'
            
            # 检查文件是否存在
            if self.bucket.object_exists(oss_path):
                # 删除文件
                logger.info(f"开始删除插件: {plugin_name} v{version}")
                self.bucket.delete_object(oss_path)
                logger.info(f"插件删除完成: {oss_path}")
            else:
                logger.warning(f"要删除的插件版本不存在: {oss_path}")

        except Exception as e:
            logger.error(f"删除插件失败: {e}")
            raise
        


if __name__ == "__main__":
    
    downloader = PluginOss()
    
    try:
        # 列出所有可用插件
        available_plugins = downloader.list_available_plugins()
        print("可用插件:", available_plugins)

        # 下载特定插件
        # plugin_name = "example_plugin"
        # version = "1.0.0"
        # local_path = downloader.download_plugin(plugin_name, version)
        # print(f"插件已下载到: {local_path}")

        # 获取最新版本
        plugin_name="example_plugin"
        latest_version = downloader.get_latest_version(plugin_name)
        print(f"最新版本: {latest_version}")
        
        
        # plugin_name = "example_plugin"
        # version = "1.0.0"
        local_path = downloader.download_plugin(plugin_name, latest_version)
        print(f"插件已下载到: {local_path}")
        

    except Exception as e:
        print(f"错误: {e}")