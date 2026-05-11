# client/cache/pending_message_dao.py
from models.PendingMessage import PendingMessage

class PendingMessageDAO:
    def __init__(self, db_conn):
        self.db = db_conn

    # CREATE (Kuyruğa Ekleme)
    def save(self, msg: PendingMessage):
        """
        Yeni bir mesaji gönderilmek üzere bekleyenler kuyruğuna ekler.
        """
        query = """INSERT INTO PendingMessages 
                   (sender, receiver, group_id, message_type, content) 
                   VALUES (?, ?, ?, ?, ?)"""
        # Kayıttan sonra oluşan temp_id'yi geri döndürdüm (UI takibi için)
        last_id = self.db.execute(query, (
            msg.sender, msg.receiver, msg.group_id, 
            msg.message_type, msg.content
        )).lastrowid
        return last_id

    # READ (Kuyruğu Yönetme)
    def get_next_in_queue(self):
        query = "SELECT * FROM PendingMessages ORDER BY temp_id ASC LIMIT 1"
        row = self.db.fetch_one(query)
        return PendingMessage.from_row(row)

    def get_all_pending(self):
        query = "SELECT * FROM PendingMessages ORDER BY temp_id ASC"
        rows = self.db.fetch_all(query)
        return [PendingMessage.from_row(row) for row in rows]

    # DELETE (Kuyruktan Çıkarma)
    def delete(self, temp_id):
        """
        Mesaj sunucuya başariyla ulaştiginda kuyruktan siler.
        """
        query = "DELETE FROM PendingMessages WHERE temp_id = ?"
        self.db.execute(query, (temp_id,))

    