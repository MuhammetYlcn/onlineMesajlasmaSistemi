# common/db_manager/DBConnection.py
import sqlite3
import os

class DBConnection:
    def __init__(self, db_path):
        """
        Her iki taraf da kendi db_path bilgisini vererek bu sınıfı başlatır.
        """
        self.db_path = db_path
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """Veritabanı klasörü yoksa oluşturur."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        # Row_factory: row['column_name'] şeklinde erişim sağlar
        conn.row_factory = sqlite3.Row
        return conn

    def execute(self, query, params=(), commit=True):
        """INSERT, UPDATE, DELETE işlemleri için."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if commit:
                conn.commit()
            return cursor

    def fetch_one(self, query, params=()):
        """Tek bir satır çekmek için."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone()
        conn.close()
        # Row objesini sözlüğe çeviriyoruz ki .get() kullanılabilsin
        return dict(result) if result else None 

    def fetch_all(self, query, params=()):
        """Çoklu satır çekmek için."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        # Tüm liste elemanlarını sözlüğe çeviriyoruz
        return [dict(row) for row in results]