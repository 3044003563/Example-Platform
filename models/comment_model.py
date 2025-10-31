import os
import sqlite3
from pathlib import Path
from datetime import datetime


class CommentModel:
    def __init__(self, plugin_name: str, data_directory: str):
        self.plugin_name = plugin_name
        self.data_directory = data_directory
        self.table_name = 'comments'
        self.db_path = self.get_db_path()
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.create_tables()

    def get_db_path(self) -> Path:
        db_dir = Path(self.data_directory) / 'Tables'
        if not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir / f'{self.plugin_name}.db'

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
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def create_tables(self):
        base_query = f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link TEXT,
            content TEXT,
            comment_time TEXT,
            author TEXT,
            ip TEXT,
            created_at DATETIME DEFAULT (datetime('now', 'localtime')),
            updated_at DATETIME DEFAULT (datetime('now', 'localtime'))
        )
        """
        self.execute(base_query)

    def get_current_time(self):
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def add_comment(self, link: str, content: str, comment_time: str = None, author: str = None, ip: str = None):
        query = f"INSERT INTO {self.table_name} (link, content, comment_time, author, ip) VALUES (?, ?, ?, ?, ?)"
        return self.execute(query, (link, content, comment_time, author, ip))

    def update_comment(self, id: int, link: str, content: str, comment_time: str = None, author: str = None, ip: str = None):
        now = self.get_current_time()
        query = f"""
            UPDATE {self.table_name}
            SET link = ?,
                content = ?,
                comment_time = ?,
                author = ?,
                ip = ?,
                updated_at = ?
            WHERE id = ?
        """
        self.execute(query, (link, content, comment_time, author, ip, now, id))

    def delete_comment(self, id: int):
        query = f"DELETE FROM {self.table_name} WHERE id = ?"
        self.execute(query, (id,))

    def batch_delete_comments(self, ids):
        if not ids:
            return
        placeholders = ','.join(['?' for _ in ids])
        query = f"DELETE FROM {self.table_name} WHERE id IN ({placeholders})"
        self.execute(query, ids)

    def get_comments(self, page: int = 1, page_size: int = 10, keyword: str = None):
        base_query = f"FROM {self.table_name} WHERE 1=1"
        params = []
        if keyword:
            base_query += " AND (link LIKE ? OR content LIKE ? OR author LIKE ? OR ip LIKE ?)"
            like = f"%{keyword}%"
            params.extend([like, like, like, like])

        count_query = f"SELECT COUNT(*) as total {base_query}"
        total = self.fetch_all(count_query, params)[0]['total'] if self.fetch_all(count_query, params) else 0

        offset = (page - 1) * page_size
        data_query = f"""
            SELECT * {base_query}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        data_params = params + [page_size, offset]
        items = self.fetch_all(data_query, data_params)

        return {
            'total': total,
            'items': items,
            'page': page,
            'page_size': page_size
        }


