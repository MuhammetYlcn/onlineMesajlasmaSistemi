# server/database/message_receipt_dao.py
from common.models.MessageReceipt import MessageReceipt

class MessageReceiptDAO:
    def __init__(self, db_manager):
        self.db = db_manager

    def add_receipt(self, receipt_obj: MessageReceipt):
        """
        Yeni bir iletim/okundu bilgisi kaydeder.
        status: 'SENT', 'DELIVERED', 'READ' gibi değerler alır.
        """
        query = """
            INSERT INTO MessagesReceipts (message_id, username, status, timestamp) 
            VALUES (?, ?, ?, ?)
        """
        params = (
            receipt_obj.message_id, 
            receipt_obj.username, 
            receipt_obj.status, 
            receipt_obj.timestamp
        )
        try:
            return self.db.execute_query(query, params)
        except Exception as e:
            print(f"Fiş kaydetme hatası: {e}")
            return False

    def update_status(self, message_id, username, new_status, time_str):
        """
        Mevcut bir mesajın durumunu günceller (Örn: SENT -> READ).
        """
        query = """
            UPDATE MessagesReceipts 
            SET status = ?, timestamp = ? 
            WHERE message_id = ? AND username = ? COLLATE NOCASE
        """
        return self.db.execute_query(query, (new_status, time_str, message_id, username))

    def get_receipts_for_message(self, message_id):
        """
        Bir mesajın tüm iletim bilgilerini getirir. 
        Grup mesajlarında kimlerin okuduğunu görmek için kritiktir.
        """
        query = "SELECT * FROM MessagesReceipts WHERE message_id = ?"
        rows = self.db.fetch_all(query, (message_id,))
        return [MessageReceipt.from_dict(row) for row in rows]

    def get_status_count(self, message_id, status):
        """Belirli bir statüdeki (Örn: 'READ') kullanıcı sayısını döner."""
        query = "SELECT COUNT(*) as count FROM MessagesReceipts WHERE message_id = ? AND status = ?"
        row = self.db.fetch_one(query, (message_id, status))
        return row['count'] if row else 0