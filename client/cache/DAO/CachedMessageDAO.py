# client/cache/cached_message_dao.py
from models.CachedMessage import CachedMessage

class CachedMessageDAO:
    def __init__(self, db_conn):
        self.db = db_conn
        self.enc_manager = None

    # CREATE
    def save(self, msg: CachedMessage):
        try:
            query = """INSERT OR REPLACE INTO CachedMessages 
                       (message_id, sender, receiver, group_id, message_type, content, 
                        timestamp, is_me, local_path, is_read, is_sent, status, reply_to_id) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
            content_val = str(msg.content) if msg.content is not None else ""
            content = self.enc_manager.encrypt(content_val) if self.enc_manager else content_val
            local_path_val = str(msg.local_path) if msg.local_path else None
            local_path = self.enc_manager.encrypt(local_path_val) if (self.enc_manager and local_path_val) else local_path_val
            
            self.db.execute(query, (
                msg.message_id, msg.sender, msg.receiver, msg.group_id,
                msg.message_type, content, msg.timestamp, msg.is_me,
                local_path, msg.is_read, msg.is_sent, msg.status, msg.reply_to_id
            ))
        except Exception as e:
            print(f"[CACHE] CachedMessageDAO.save() hatası: {e}")
            import traceback; traceback.print_exc()

    def _decrypt_row(self, row):
        if not row: return None
        row = dict(row)
        if self.enc_manager:
            try:
                row['content'] = self.enc_manager.decrypt(row['content'])
            except Exception:
                pass  # Şifresi çözülemeyen içerik orijinal bırakılır
            if row.get('local_path'):
                try:
                    row['local_path'] = self.enc_manager.decrypt(row['local_path'])
                except Exception:
                    pass
        return CachedMessage.from_row(row)

    # READ - Sohbet Listesi Sıralama 
    def get_recent_chats(self):
        query = """
            SELECT *, MAX(timestamp) as last_msg_time 
            FROM CachedMessages 
            GROUP BY COALESCE(group_id, CASE WHEN is_me = 1 THEN receiver ELSE sender END)
            ORDER BY last_msg_time DESC
        """
        rows = self.db.fetch_all(query)
        return [self._decrypt_row(row) for row in rows]

    # READ - Spesifik Mesajlaşma Geçmişi
    def get_chat_history(self, chat_partner, limit=50):
        # Sadece is_me=1 ve alıcının partner olduğu (giden) 
        # veya is_me=0 ve gönderenin partner olduğu (gelen) mesajları getir.
        # Bu sayede 'Sen' (kendine mesaj) alanı diğer sohbetlerle karışmaz.
        query = """SELECT * FROM CachedMessages 
                   WHERE ((is_me = 1 AND receiver = ?) OR (is_me = 0 AND sender = ?)) 
                   AND group_id IS NULL 
                   ORDER BY timestamp ASC LIMIT ?"""
        rows = self.db.fetch_all(query, (chat_partner, chat_partner, limit))
        return [self._decrypt_row(row) for row in rows]

    def get_group_history(self, group_id, limit=50):
        query = "SELECT * FROM CachedMessages WHERE group_id = ? ORDER BY timestamp ASC LIMIT ?"
        rows = self.db.fetch_all(query, (group_id, limit))
        return [self._decrypt_row(row) for row in rows]

    # UPDATE
    def mark_as_read(self, message_id):
        query = "UPDATE CachedMessages SET is_read = 1 WHERE message_id = ?"
        self.db.execute(query, (message_id,))

    def mark_as_sent(self, message_id):
        query = "UPDATE CachedMessages SET is_sent = 1 WHERE message_id = ?"
        self.db.execute(query, (message_id,))

    def update_status(self, message_id, status):
        try:
            if not message_id or not status:
                return
            query = "UPDATE CachedMessages SET status = ? WHERE message_id = ?"
            self.db.execute(query, (status, message_id))
        except Exception as e:
            print(f"[CACHE] update_status hatası: {e}")

    def get_pending_messages(self):
        query = "SELECT * FROM CachedMessages WHERE is_me = 1 AND is_sent = 0 ORDER BY timestamp ASC"
        rows = self.db.fetch_all(query)
        return [self._decrypt_row(row) for row in rows]

    def get_latest_timestamp(self, target_id):
        """Belirli bir sohbet için en son mesajın zaman damgasını döner."""
        # Grup kontrolü
        gid = None
        if target_id.startswith("group_"):
            try: gid = int(target_id.split("_")[1])
            except: pass
            query = "SELECT MAX(timestamp) as last_time FROM CachedMessages WHERE group_id = ?"
            row = self.db.fetch_one(query, (gid,))
        else:
            # Özel sohbet kontrolü (is_me mantığı ile)
            query = """SELECT MAX(timestamp) as last_time FROM CachedMessages 
                       WHERE ((is_me = 1 AND receiver = ?) OR (is_me = 0 AND sender = ?)) 
                       AND group_id IS NULL"""
            row = self.db.fetch_one(query, (target_id, target_id))
            
        return row['last_time'] if row and row['last_time'] else "1970-01-01 00:00:00"

    def delete_message(self, message_id):
        query = "DELETE FROM CachedMessages WHERE message_id = ?"
        self.db.execute(query, (message_id,))

    def update_message_content(self, message_id, new_content):
        try:
            content = self.enc_manager.encrypt(new_content) if self.enc_manager else new_content
            query = "UPDATE CachedMessages SET content = ? WHERE message_id = ?"
            self.db.execute(query, (content, message_id))
        except Exception as e:
            print(f"[CACHE] update_message_content hatası: {e}")

    # DELETE
    def delete_chat(self, chat_partner=None, group_id=None):
        if group_id:
            query = "DELETE FROM CachedMessages WHERE group_id = ?"
            self.db.execute(query, (group_id,))
        else:
            query = """DELETE FROM CachedMessages 
                       WHERE ((is_me = 1 AND receiver = ?) OR (is_me = 0 AND sender = ?)) 
                       AND group_id IS NULL"""
            self.db.execute(query, (chat_partner, chat_partner))