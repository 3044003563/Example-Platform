import os
import sqlite3
from pathlib import Path
from datetime import datetime

class AccountmanageModel:
    def __init__(self, plugin_name: str, data_directory: str):
        self.plugin_name = plugin_name
        self.data_directory = data_directory
        self.db_path = self.get_db_path()
        self.table_name = 'accountmanage'
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.create_tables()

    
    
    def get_db_path(self) -> Path:
        # 使用 Path 对象处理路径
        db_dir = Path(self.data_directory) / 'Tables'
        # 确保目录存在
        if not db_dir.exists():
           db_dir.mkdir(parents=True, exist_ok=True)
        
        return Path(db_dir) / 'account-manage.db'

    def get_connection(self):
        return sqlite3.connect(str(self.db_path))

    def execute(self, query: str, params=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                conn.commit()
                return cursor.lastrowid
            except Exception as e:
                conn.rollback()
                raise e

    def fetch_all(self, query: str, params=None):
        """执行查询并返回字典格式的结果"""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def create_tables(self):
        query = """
        CREATE TABLE IF NOT EXISTS accountmanage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            remark TEXT,
            username TEXT,
            password TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            status INTEGER DEFAULT 1,
            login_status INTEGER DEFAULT 0,
            user_data_dir TEXT,
            platform_name TEXT,
            platform_url TEXT
        )
        """
        self.execute(query)

    def get_available_accounts(self): 
        """获取所有可用的账号（status=1）"""
        query = """
        SELECT *
        FROM accountmanage 
        WHERE status = 1
        and platform_name = '抖音'
        ORDER BY created_at DESC
        """
        return self.fetch_all(query)
    

    def get_account_by_id(self, account_id):
        """根据ID获取账号信息"""
        query = """
        SELECT *
        FROM  accountmanage  
        WHERE id = ?
        """
        results = self.fetch_all(query, (account_id,))
        return results[0] if results else None

    