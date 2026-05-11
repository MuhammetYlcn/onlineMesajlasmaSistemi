# server/database/message_dao.py
from common.models.Message import Message

class MessageDAO:
    def __init__(self, db_manager):
        self.db = db_manager
        self.enc_manager = None

    def save_message(self, msg_obj: Message):
        from security.Hash import Hash
        query = """
            INSERT INTO Messages (sender, receiver, group_id, message_type, content, file_path, msg_id, timestamp, reply_to_id, is_forwarded, is_edited) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        content = self.enc_manager.encrypt(msg_obj.content) if self.enc_manager else msg_obj.content
        hashed_sender = Hash.hash_deterministic(msg_obj.sender)
        hashed_receiver = Hash.hash_deterministic(msg_obj.receiver) if msg_obj.receiver else None
        
        params = (
            hashed_sender, 
            hashed_receiver, 
            msg_obj.group_id, 
            msg_obj.message_type, 
            content,
            msg_obj.file_path,
            msg_obj.msg_id,
            msg_obj.timestamp,
            getattr(msg_obj, 'reply_to_id', None),
            getattr(msg_obj, 'is_forwarded', 0),
            getattr(msg_obj, 'is_edited', 0)
        )
        return self.db.execute(query, params)

    def _decrypt_message_row(self, row):
        if not row: return None
        row = dict(row)
        if self.enc_manager:
            try:
                row['content'] = self.enc_manager.decrypt(row['content'])
            except: pass
            
            # Join ile gelen gerçek isimleri (şifreli display_name) çözüyoruz
            if row.get('sender_name'):
                try:
                    row['sender'] = self.enc_manager.decrypt(row['sender_name'])
                except: pass
            if row.get('receiver_name'):
                try:
                    row['receiver'] = self.enc_manager.decrypt(row['receiver_name'])
                except: pass
        
        return Message.from_dict(row)

    def update_message_content(self, msg_id, new_content):
        enc_content = self.enc_manager.encrypt(new_content) if self.enc_manager else new_content
        query = "UPDATE Messages SET content = ?, is_edited = 1 WHERE msg_id = ?"
        return self.db.execute(query, (enc_content, msg_id))

    def get_group_chat_history(self, group_id, limit=100, after_timestamp="1970-01-01 00:00:00"):
        query = """
            SELECT m.*, u1.display_name as sender_name, u2.display_name as receiver_name
            FROM Messages m
            LEFT JOIN Users u1 ON m.sender = u1.username
            LEFT JOIN Users u2 ON m.receiver = u2.username
            WHERE m.group_id = ? AND m.timestamp > ?
            ORDER BY m.timestamp ASC LIMIT ?
        """
        rows = self.db.fetch_all(query, (group_id, after_timestamp, limit))
        return [self._decrypt_message_row(r) for r in rows]

    def get_private_chat_history(self, user1, user2, limit=100, after_timestamp="1970-01-01 00:00:00"):
        from security.Hash import Hash
        h1, h2 = Hash.hash_deterministic(user1), Hash.hash_deterministic(user2)
        query = """
            SELECT m.*, u1.display_name as sender_name, u2.display_name as receiver_name
            FROM Messages m
            LEFT JOIN Users u1 ON m.sender = u1.username
            LEFT JOIN Users u2 ON m.receiver = u2.username
            WHERE ((m.sender = ? AND m.receiver = ?) OR (m.sender = ? AND m.receiver = ?))
            AND m.timestamp > ?
            ORDER BY m.timestamp ASC LIMIT ?
        """
        rows = self.db.fetch_all(query, (h1, h2, h2, h1, after_timestamp, limit))
        return [self._decrypt_message_row(r) for r in rows]

    def get_message_by_msg_id(self, msg_id):
        query = """
            SELECT m.*, u1.display_name as sender_name, u2.display_name as receiver_name
            FROM Messages m
            LEFT JOIN Users u1 ON m.sender = u1.username
            LEFT JOIN Users u2 ON m.receiver = u2.username
            WHERE m.msg_id = ?
        """
        row = self.db.fetch_one(query, (msg_id,))
        return self._decrypt_message_row(row)

    def delete_message(self, msg_id):
        query = "DELETE FROM Messages WHERE msg_id = ?"
        return self.db.execute(query, (msg_id,))

    def get_messages_paginated(self, username, offset=0, limit=50):
        from security.Hash import Hash
        h_uname = Hash.hash_deterministic(username)
        query = """
            SELECT m.*, u1.display_name as sender_name, u2.display_name as receiver_name
            FROM Messages m
            LEFT JOIN Users u1 ON m.sender = u1.username
            LEFT JOIN Users u2 ON m.receiver = u2.username
            WHERE m.sender = ? OR m.receiver = ? OR m.group_id IN (
                SELECT group_id FROM Group_Members WHERE username = ?
            )
            ORDER BY m.timestamp DESC 
            LIMIT ? OFFSET ?
        """
        rows = self.db.fetch_all(query, (h_uname, h_uname, h_uname, limit, offset))
        return [self._decrypt_message_row(r) for r in rows]

    def delete_chat_history(self, user1, user2):
        from security.Hash import Hash
        h1, h2 = Hash.hash_deterministic(user1), Hash.hash_deterministic(user2)
        # Önce bu mesajların ID'lerini bulalım ki receipt'leri de silelim
        self.db.execute("DELETE FROM MessagesReceipts WHERE msg_id IN (SELECT msg_id FROM Messages WHERE (sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?))", (h1, h2, h2, h1))
        query = "DELETE FROM Messages WHERE (sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?)"
        return self.db.execute(query, (h1, h2, h2, h1))

    def delete_group_history(self, group_id):
        self.db.execute("DELETE FROM MessagesReceipts WHERE msg_id IN (SELECT msg_id FROM Messages WHERE group_id = ?)", (group_id,))
        query = "DELETE FROM Messages WHERE group_id = ?"
        return self.db.execute(query, (group_id,))

    def get_pending_messages_for_user(self, username):
        """Kullanıcının henüz almadığı (receipt gönderilmemiş) mesajları döner."""
        from security.Hash import Hash
        h_uname = Hash.hash_deterministic(username)
        # Sadece özel mesajları veya üyesi olduğu gruplardaki mesajları bul
        # ve MessagesReceipts tablosunda bu kullanıcı için bir kayıt olmayanları getir.
        query = """
            SELECT m.*, u1.display_name as sender_name, u2.display_name as receiver_name
            FROM Messages m
            LEFT JOIN Users u1 ON m.sender = u1.username
            LEFT JOIN Users u2 ON m.receiver = u2.username
            WHERE (m.receiver = ? OR (m.group_id IS NOT NULL AND m.group_id IN (SELECT group_id FROM Group_Members WHERE username = ?)))
            AND m.sender != ?
            AND NOT EXISTS (
                SELECT 1 FROM MessagesReceipts mr 
                WHERE mr.msg_id = m.msg_id AND mr.username = ?
            )
            ORDER BY m.timestamp ASC
        """
        rows = self.db.fetch_all(query, (h_uname, h_uname, h_uname, h_uname))
        return [self._decrypt_message_row(r) for r in rows]