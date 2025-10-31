#!/usr/bin/env python
"""
依赖安装脚本
"""
import subprocess
import sys
import os

def install_package(package):
    """安装单个包"""
    try:
        print(f"正在安装 {package}...")
        result = subprocess.run([sys.executable, "-m", "pip", "install", package], 
                              capture_output=True, text=True, check=True)
        print(f"✅ {package} 安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {package} 安装失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False

def main():
    """主安装函数"""
    packages = [
        "webview",
        "playwright", 
        "packaging",
        "pillow",
        "numpy",
        "pywin32",
        "apscheduler",
        "psutil",
        "oss2"
    ]
    
    print("🚀 开始安装依赖包...")
    print("=" * 50)
    
    success_count = 0
    for package in packages:
        if install_package(package):
            success_count += 1
        print("-" * 30)
    
    print(f"\n📊 安装结果: {success_count}/{len(packages)} 个包安装成功")
    
    if success_count == len(packages):
        print("🎉 所有依赖包安装完成！")
        
        # 安装 playwright 浏览器
        print("\n🌐 正在安装 Playwright 浏览器...")
        try:
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], 
                          check=True)
            print("✅ Playwright 浏览器安装成功")
        except subprocess.CalledProcessError as e:
            print(f"❌ Playwright 浏览器安装失败: {e}")
        
        # 测试 webview
        print("\n🧪 测试 webview 模块...")
        try:
            import webview
            print("✅ webview 模块测试成功")
        except ImportError as e:
            print(f"❌ webview 模块测试失败: {e}")
    else:
        print("⚠️ 部分依赖包安装失败，请检查错误信息")

if __name__ == "__main__":
    main()
