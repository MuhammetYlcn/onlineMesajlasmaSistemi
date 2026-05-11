import sqlite3
import threading

class DBConnection:
    """Thread-safe SQLite connection manager for the client cache."""
    def __init__(self, db_path):
        self.db_path = db_path
        self.local = threading.local()

    def get_connection(self):
        if not hasattr(self.local, 'conn'):
            self.local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.local.conn.row_factory = sqlite3.Row
        return self.local.conn

    def execute(self, query, params=()):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor

    def fetch_one(self, query, params=()):
        cursor = self.execute(query, params)
        return cursor.fetchone()

    def fetch_all(self, query, params=()):
        cursor = self.execute(query, params)
        return cursor.fetchall()
