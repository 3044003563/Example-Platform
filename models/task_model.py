import os
import sqlite3
from pathlib import Path
from datetime import datetime

class TaskModel:
    def __init__(self, plugin_name: str,data_directory:str):
        self.plugin_name = plugin_name
        self.data_directory = data_directory
        self.db_path = self.get_db_path()
        self.table_name = 'tasks'
        
        # 确保数据库目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        
        # 创建数据库连接时设置时区
        with self.get_connection() as conn:
            conn.execute("PRAGMA timezone='+08:00'")
        
        self.create_tables()

    def get_db_path(self) -> Path:
        # 使用 Path 对象处理路径
        db_dir = Path(self.data_directory) / 'Tables'
        # 确保目录存在
        if not db_dir.exists():
           db_dir.mkdir(parents=True, exist_ok=True)
        
        return db_dir / f'{self.plugin_name}.db'
    
    def get_connection(self):
        print("self.db_path:=============", self.db_path)
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
        """创建基础表结构并动态管理字段"""
        # 1. 创建基础表(只包含基本字段)
        base_table_query = f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        self.execute(base_table_query)
        
        # 2. 定义需要的字段配置
        required_columns = {
            'name': 'TEXT',
            'app': 'VARCHAR(255)',
            'freq_type': 'TEXT',
            'freq_value': 'TEXT',
            'freq_desc': 'TEXT',
            'start_time': 'DATETIME DEFAULT CURRENT_TIMESTAMP',
            'end_time': 'DATETIME DEFAULT CURRENT_TIMESTAMP',
            'queue': 'INTEGER DEFAULT 0',
            'timeout': 'INTEGER DEFAULT 0',
            'enabled': 'INTEGER DEFAULT 0',
            'status': 'INTEGER DEFAULT 0',
            'last_run_time': 'DATETIME DEFAULT CURRENT_TIMESTAMP',
            'next_run_time': 'DATETIME DEFAULT CURRENT_TIMESTAMP',
            'controller_name':'TEXT',
            'method_name':'TEXT',
            'params': 'TEXT'
        }
        
        # 3. 获取当前表中已存在的字段
        existing_columns = self.get_existing_columns()
        
        # 4. 动态添加或修改字段
        for column_name, column_type in required_columns.items():
            if column_name not in existing_columns:
                # 新增字段
                alter_query = f"ALTER TABLE {self.table_name} ADD COLUMN {column_name} {column_type}"
                try:
                    self.execute(alter_query)
                    print(f"添加新字段: {column_name}")
                except Exception as e:
                    print(f"添加字段 {column_name} 失败: {str(e)}")
            else:
                # 检查字段类型是否需要修改
                current_type = existing_columns[column_name].upper()
                required_type = column_type.upper()
                if current_type != required_type:
                    print(f"字段 {column_name} 类型需要从 {current_type} 更新为 {required_type}")
                    self.modify_column_type(column_name, required_type)
        
        
         
    def get_existing_columns(self):
        """获取表中现有的字段及其类型"""
        query = f"PRAGMA table_info({self.table_name})"
        columns = {}
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                results = cursor.fetchall()
                for row in results:
                    # row的结构: (cid, name, type, notnull, dflt_value, pk)
                    columns[row[1]] = row[2]
                return columns
        except Exception as e:
            print(f"获取表结构失败: {str(e)}")
            return {}



    def modify_column_type(self, column_name, new_type):
        """修改字段类型（通过创建临时表实现）"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 1. 获取所有现有字段
            cursor.execute(f"PRAGMA table_info({self.table_name})")
            columns = {row[1]: row[2] for row in cursor.fetchall()}
            
            # 2. 创建临时表
            column_definitions = [f"id INTEGER PRIMARY KEY AUTOINCREMENT"]
            for col, type_ in columns.items():
                if col != 'id':
                    if col == column_name:
                        column_definitions.append(f"{col} {new_type}")
                    else:
                        column_definitions.append(f"{col} {type_}")
            
            cursor.execute("BEGIN TRANSACTION")
            
            # 3. 创建临时表
            temp_table = f"{self.table_name}_temp"
            create_temp_table = f"""
            CREATE TABLE {temp_table} (
                {', '.join(column_definitions)}
            )
            """
            cursor.execute(create_temp_table)
            
            # 4. 复制数据
            cursor.execute(f"INSERT INTO {temp_table} SELECT * FROM {self.table_name}")
            
            # 5. 删除原表
            cursor.execute(f"DROP TABLE {self.table_name}")
            
            # 6. 重命名临时表
            cursor.execute(f"ALTER TABLE {temp_table} RENAME TO {self.table_name}")
            
            conn.commit()
            print(f"成功修改字段 {column_name} 的类型为 {new_type}")
            
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            print(f"修改字段类型失败: {str(e)}")
            
        finally:
            if conn:
                conn.close()         

    
    def get_tasks(self):
        """获取所有任务"""
        query = """
        SELECT * FROM tasks
        ORDER BY created_at DESC
        """
        return self.fetch_all(query)
    
    
    
    def save_task(self, task_data: dict):
        """保存任务"""
        try:
            # 如果有额外数据，将其序列化为JSON
            if 'params' in task_data:
                import json
                task_data['params'] = json.dumps(task_data['params'])
                
            # 构建插入语句
            columns = ', '.join(task_data.keys())
            placeholders = ', '.join(['?' for _ in task_data])
            values = tuple(task_data.values())
            
            query = f"""
            INSERT INTO {self.table_name} ({columns})
            VALUES ({placeholders})
            """
            
            task_id = self.execute(query, values)
            return task_id
            
        except Exception as e:
            print(f"保存任务失败: {str(e)}")
            raise e
        
        
    def get_enabled_tasks(self):
        """获取所有启用中的任务（enabled=1）"""
        query = """
        SELECT * FROM tasks 
        WHERE enabled = 1 
        ORDER BY created_at DESC
        """
        try:
            return self.fetch_all(query)
        except Exception as e:
            print(f"获取启用中的任务失败: {str(e)}")
            return []
        
        
    
    def toggle_task_status(self, task_id: int, enabled: int):
        """切换任务的启用状态"""
        try:
            query = """
            UPDATE tasks 
            SET enabled = ?, 
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """
            self.execute(query, (enabled, task_id))
            return True
        except Exception as e:
            print(f"更新任务状态失败: {str(e)}")
            raise e
        
    
    def delete_task(self, task_id: int):
        """删除指定任务"""
        try:
            query = """
            DELETE FROM tasks 
            WHERE id = ?
            """
            self.execute(query, (task_id,))
            return True
        except Exception as e:
            print(f"删除任务失败: {str(e)}")
            raise e
        
    
    def get_task_by_id(self, task_id: int):
        """根据ID获取任务详情"""
        query = "SELECT * FROM tasks WHERE id = ?"
        result = self.fetch_all(query, (task_id,))
        return result[0] if result else None
        
    
    
    def get_current_time(self):
        """获取当前北京时间"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')