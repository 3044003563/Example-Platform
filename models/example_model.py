import os
import sqlite3
from pathlib import Path
from datetime import datetime

class ExampleModel:
    def __init__(self, plugin_name: str,data_directory: str):
        """
        初始化模型
        :param plugin_name: 插件名称，从插件配置中获取
        """
        self.plugin_name = plugin_name
        self.data_directory = data_directory
        self.db_path = self.get_db_path()
        print("self.db_path===============",self.db_path)
        self.table_name = 'example_table'
         # 确保数据库目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.create_tables()  # 初始化时创建表

    
    
    def get_db_path(self) -> Path:
        # 使用 Path 对象处理路径
        db_dir = Path(self.data_directory) / 'Tables'
        # 确保目录存在
        if not db_dir.exists():
           db_dir.mkdir(parents=True, exist_ok=True)
        
        return db_dir / f'{self.plugin_name}.db'
    
    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(str(self.db_path))

   
    def execute(self, query: str, params=None):
        """执行SQL查询"""
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
            conn.row_factory = sqlite3.Row  # 设置返回字典格式
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]  # 将结果转换为字典列表

        
        
    def create_tables(self):
        """创建基础表结构并动态管理字段"""
        # 1. 创建基础表(只包含基本字段)
        base_table_query = f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at DATETIME DEFAULT (datetime('now', 'localtime')),
            updated_at DATETIME DEFAULT (datetime('now', 'localtime'))
        )
        """
        self.execute(base_table_query)
        
        # 2. 定义需要的字段配置
        required_columns = {
            'title': 'TEXT',
            'link': 'TEXT',
            'author': 'TEXT'
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
        table_name = self.table_name
        query = f"PRAGMA table_info({table_name})"
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
        table_name = self.table_name
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 1. 获取所有现有字段
            cursor.execute(f"PRAGMA table_info({table_name})")
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
            temp_table = f"{table_name}_temp"
            create_temp_table = f"""
            CREATE TABLE {temp_table} (
                {', '.join(column_definitions)}
            )
            """
            cursor.execute(create_temp_table)
            
            # 4. 复制数据
            cursor.execute(f"INSERT INTO {temp_table} SELECT * FROM {table_name}")
            
            # 5. 删除原表
            cursor.execute(f"DROP TABLE {table_name}")
            
            # 6. 重命名临时表
            cursor.execute(f"ALTER TABLE {temp_table} RENAME TO {table_name}")
            
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
                
    def get_current_time(self):
        """获取当前北京时间"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')    

    def add_item(self, title, link, author=None):
        """添加数据"""
        print("add_item===============")
        print(title)
        print(link)
        print(author)
        query = "INSERT INTO example_table (title, link,author) VALUES (?, ?,?)"
        return self.execute(query, (title, link,author))

    def get_items(self, page=1, page_size=10, keyword=None):
        """获取分页数据"""
        # 构建基础查询
        base_query = "FROM example_table WHERE 1=1"
        params = []
        
        # 添加搜索条件
        if keyword:
            base_query += " AND (title LIKE ? OR link LIKE ?)"
            params.extend([f'%{keyword}%', f'%{keyword}%'])
        
        # 获取总数
        count_query = f"SELECT COUNT(*) as total {base_query}"
        total = self.fetch_all(count_query, params)[0]['total']
        
        # 计算分页
        offset = (page - 1) * page_size
        
        # 获取分页数据
        data_query = f"""
            SELECT * {base_query}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        items = self.fetch_all(data_query, params)
        
        return {
            'total': total,
            'items': items,
            'page': page,
            'page_size': page_size
        }
    
    
    def update_item(self, id, title, link,author=None):
        """更新项目"""
        now = self.get_current_time()
        query = """
            UPDATE example_table 
            SET title = ?, 
                link = ?,
                author = ?,
                updated_at = ?
            WHERE id = ?
        """
        self.execute(query, (title, link,author, now, id))


    def delete_item(self, id):
        """删除项目"""
        query = "DELETE FROM example_table WHERE id = ?"
        self.execute(query, (id,))
        
    def batch_delete_items(self, ids):
        """批量删除项目"""
        if not ids:
            return
        
        placeholders = ','.join(['?' for _ in ids])
        query = f"DELETE FROM {self.table_name} WHERE id IN ({placeholders})"
        self.execute(query, ids)
        
        
    