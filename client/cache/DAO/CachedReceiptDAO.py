from models.CachedReceipt import CachedReceipt

class CachedReceiptDAO:
    def __init__(self, db_conn):
        self.db = db_conn

    # CREATE & UPDATE (Upsert)
    def save(self, receipt: CachedReceipt):
        """
        Mesaj durumunu kaydeder veya günceller.
        SENT -> DELIVERED -> READ 
        """
        query = """INSERT OR REPLACE INTO CachedReceipts 
                   (message_id, username, status, timestamp) 
                   VALUES (?, ?, ?, ?)"""
        self.db.execute(query, (
            receipt.message_id, 
            receipt.username, 
            receipt.status, 
            receipt.timestamp
        ))

    # READ
    def get_receipts_for_message(self, message_id):
        query = "SELECT * FROM CachedReceipts WHERE message_id = ?"
        rows = self.db.fetch_all(query, (message_id,))
        return [CachedReceipt.from_row(row) for row in rows]

    def get_status_by_user(self, message_id, username):
        query = "SELECT * FROM CachedReceipts WHERE message_id = ? AND username = ?"
        row = self.db.fetch_one(query, (message_id, username))
        return CachedReceipt.from_row(row)

    # DELETE
    def delete_receipts(self, message_id):
        query = "DELETE FROM CachedReceipts WHERE message_id = ?"
        self.db.execute(query, (message_id,))