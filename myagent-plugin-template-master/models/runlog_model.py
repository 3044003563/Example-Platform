import os
import sqlite3
from pathlib import Path
from datetime import datetime

class RunlogModel:
    def __init__(self, plugin_name: str,data_directory:str):
        self.plugin_name = plugin_name
        self.data_directory = data_directory
        self.db_path = self.get_db_path()
        self.table_name = 'task_runlog'
        
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
            'task_id': 'INTEGER',
            'result': 'TEXT',
            'log': 'TEXT',
            'run_time': 'DATETIME DEFAULT CURRENT_TIMESTAMP'
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
                
                
    def get_logs(self):
        """获取所有运行日志，关联任务名称"""
        try:
            query = """
            SELECT 
                l.*,
                t.name as task_name
            FROM task_runlog l
            LEFT JOIN tasks t ON l.task_id = t.id
            ORDER BY l.created_at DESC
            """
            return self.fetch_all(query)
        except Exception as e:
            print(f"获取运行日志失败: {str(e)}")
            return []    

    
    
    def add_log(self, log_data: dict):
        """
        添加任务运行日志
        参数:
            log_data: 字典格式，包含:
                - task_id: 任务ID
                - result: 执行结果
                - log: 详细日志
                - run_time: 运行时间
        """
        try:
            # 获取当前时间
            current_time = self.get_current_time()
            
            # 构建插入语句
            query = """
            INSERT INTO task_runlog (
                task_id,
                result,
                log,
                run_time,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """
            
            # 准备参数
            params = (
                log_data.get('task_id'),
                log_data.get('result'),
                log_data.get('log'),
                log_data.get('run_time', current_time),
                current_time,
                current_time
            )
            
            # 执行插入
            log_id = self.execute(query, params)
            print(f"成功添加运行日志，ID: {log_id}")
            return log_id
            
        except Exception as e:
            print(f"添加运行日志失败: {str(e)}")
            raise e
        
    
    def get_current_time(self):
        """获取当前北京时间"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')