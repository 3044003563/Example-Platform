import os
import json
import random
import shutil
from pathlib import Path
from packaging.version import Version
from plugin_oss import PluginOss
import requests

def build_source_package(source_dir, dist_dir):
    """构建源码包"""
    with open('manifest.json', 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    
    plugin_name = manifest.get('plugin_name')
    version = manifest.get('version', '1.0.0')
    
    # 创建临时目录
    temp_dir = os.path.join(dist_dir, 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # 复制需要的文件到临时目录
        for dir_name in ['controllers', 'models', 'views', 'data','utils','config']:
            if os.path.exists(dir_name):
                target_dir = os.path.join(temp_dir, dir_name)
                shutil.copytree(dir_name, target_dir, dirs_exist_ok=True)
        
        # 复制 manifest.json
        shutil.copy2('manifest.json', temp_dir)
        shutil.copy2('setup.py', temp_dir)
        shutil.copy2('requirements.txt', temp_dir)
        
        # 创建源码包
        source_package = os.path.join(dist_dir, f"{plugin_name}-{version}-source.zip")
        shutil.make_archive(
            os.path.splitext(source_package)[0],  # 不包含扩展名的路径
            'zip',
            temp_dir
        )
        
        return source_package
        
    finally:
        # 清理临时目录
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)



def validate_and_prepare_data(manifest):
    """
    验证并准备应用数据
    
    Args:
        manifest: manifest.json的内容
        
    Returns:
        tuple: (bool, dict, str) - (是否验证通过, 处理后的数据, 错误信息)
    """
    try:
        # 验证plugin_name
        plugin_name = manifest.get('plugin_name')
        if not plugin_name:
            return False, None, "验证失败: 插件英文名称（plugin_name）不能为空"
            
        # 组装主应用数据
        data = {
            'plugin_name': plugin_name,
            'name': manifest.get('name'),
            'description': manifest.get('description'),
            'icon': manifest.get('icon'),
            'category': manifest.get('category'),
            'platform': manifest.get('platform'),
            'parent_id': manifest.get('parent_id', 0),
            'route': manifest.get('route'),
            'sort_order': manifest.get('sort_order', 0),
            'status': manifest.get('status', 1),
            'designer_id': manifest.get('designer_id', 0),
            'developer_id': manifest.get('developer_id', 0),
            'monthly_price': manifest.get('monthly_price', 0),
            'half_yearly_price': manifest.get('half_yearly_price', 0),
            'yearly_price': manifest.get('yearly_price', 0),
            'changelog': manifest.get('changelog', '')
        }
        
        # 添加子应用数据
        if 'child_application' in manifest:
            data['child_application'] = [{
                'name': child.get('name'),
                'description': child.get('description'),
                'icon': child.get('icon'),
                'route': child.get('route'),
                'sort_order': child.get('sort_order', 0),
                'status': child.get('status', 1)
            } for child in manifest['child_application']]
            
        # 验证必填字段
        required_fields = {
            'name': '插件名称（name）不能为空',
            'parent_id': '父级应用ID（parent_id）不能为空',
            'route': '应用访问路径（route）不能为空，填写格式为：views/pages/应用名称.html',
            'changelog': '更新日志（changelog）不能为空'
        }
        
        # 检查主应用必填字段
        for field, message in required_fields.items():
            value = data.get(field)
            if not value and value != 0:  # 允许parent_id为0
                return False, None, f"验证失败: {message}"
                
        # 验证主应用route格式
        if not data['route'].startswith('views/pages/') or not data['route'].endswith('.html'):
            return False, None, "验证失败: 主应用的访问路径（route）格式错误，必须以views/pages/开头，以.html结尾"
            
        # 检查子应用信息
        if 'child_application' in data and isinstance(data['child_application'], list):
            for index, child in enumerate(data['child_application']):
                # 检查子应用的name
                if not child.get('name'):
                    return False, None, f"验证失败: 第 {index + 1} 个子应用的名称（name）不能为空"
                # 检查子应用的route
                if not child.get('route'):
                    return False, None, f"验证失败: 第 {index + 1} 个子应用的访问路径（route）不能为空"
                # 验证route格式
                if not child['route'].startswith('views/pages/') or not child['route'].endswith('.html'):
                    return False, None, f"验证失败: 第 {index + 1} 个子应用的访问路径（route）格式错误，必须以views/pages/开头，以.html结尾"
        
        return True, data, None
        
    except Exception as e:
        return False, None, f"数据验证过程中发生错误: {str(e)}"


def update_plugin_info(plugin_name, data, version):
    """更新插件信息到后端API"""
    try:
        API_BASE_URL = os.getenv('API_BASE_URL', 'https://myagent.im/api')
        

        print("发送请求到:", f"{API_BASE_URL}/application/update")

        response = requests.post(
            f"{API_BASE_URL}/application/update",
            json=data,
            headers={'Content-Type': 'application/json'}
        )

        print("响应状态码:", response.status_code)
        print("响应内容:", response.text)

        if response.status_code == 200:
            result = response.json()
            if result.get('code') == 200:
                print("应用发布成功")
                return True
            else:
                print(f"应用发布失败: {result.get('message')}")
                return False
        else:
            print(f"API请求失败，状态码: {response.status_code}")
            return False

    except Exception as e:
        print(f"应用发布时发生错误: {str(e)}")
        if isinstance(e, requests.exceptions.RequestException):
            print(f"请求错误详情: {str(e)}")
        return False



def main():
    try:
        # 创建 dist 目录
        dist_dir = 'dist'
        os.makedirs(dist_dir, exist_ok=True)
        
        # 读取插件信息
        with open('manifest.json', 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        
            # 验证并准备数据
        is_valid, data, error_message = validate_and_prepare_data(manifest)
        if not is_valid:
            print(error_message)
            return False
        
        
        
        plugin_name = data['plugin_name']
        # 获取新版本号
        plugin_oss = PluginOss()
        latest_version = plugin_oss.get_latest_version(plugin_name)
        old_version = latest_version  # 保存旧版本号，用于后续删除
        if latest_version is None:
            latest_version = "1.0.0"
        
        # 计算新版本号
        new_version = Version(latest_version)
        new_version = new_version.base_version
        new_version_parts = list(map(int, new_version.split('.')))
        new_version_parts[-1] += 1
        version = '.'.join(map(str, new_version_parts))
        data['version'] = version
        
        # 构建源码包
        source_package = build_source_package('.', dist_dir)
        
        # 先更新数据库
        response = update_plugin_info(plugin_name, data, version)
        if not response:
            print("更新数据库失败，终止上传源码包")
            return False
            
        # 数据库更新成功后，再上传源码包到 OSS
        plugin_oss.upload_plugin(plugin_name, version, source_package)
        print(f"源码包 {plugin_name} v{version} 上传成功，请在MyAgent测试版本端可以查看")
        print("MyAgent测试版本端下载地址：https://myagent.im/product.html")
        
        
         # 删除旧版本
        if old_version and old_version != version:  # 确保有旧版本且不是当前版本
            try:
                plugin_oss.delete_plugin_version(plugin_name, old_version)
                print(f"已删除旧版本 {plugin_name} v{old_version}")
            except Exception as e:
                print(f"删除旧版本时发生错误: {str(e)}")
        
        # 清理临时文件
        shutil.rmtree(dist_dir)
        return True
        
    except Exception as e:
        print(f"构建插件失败: {str(e)}")
        # 确保清理临时文件
        if os.path.exists(dist_dir):
            shutil.rmtree(dist_dir)
        return False



if __name__ == '__main__':
    success = main()
    if not success:
        print("应用发布失败")
        exit(1)  # 使用非零退出码表示失败
    print("应用发布成功")