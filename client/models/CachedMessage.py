class CachedMessage:
    def __init__(self, message_id, sender, content, timestamp, 
                 receiver=None, group_id=None, message_type='TEXT', 
                 is_me=1, local_path=None, is_read=0, is_sent=1, status=None, reply_to_id=None):
        self.message_id = message_id
        self.sender = sender
        self.content = content
        self.timestamp = timestamp
        self.receiver = receiver
        self.group_id = group_id
        self.message_type = message_type
        self.is_me = is_me
        self.local_path = local_path
        self.is_read = is_read
        self.is_sent = is_sent
        self.status = status
        self.reply_to_id = reply_to_id

    @classmethod
    def from_row(cls, row, enc_manager=None):
        if not row: return None
        content = enc_manager.decrypt(row['content']) if enc_manager else row['content']
        return cls(
            message_id=row['message_id'],
            sender=row['sender'],
            receiver=row['receiver'],
            group_id=row['group_id'],
            message_type=row['message_type'],
            content=content,
            timestamp=row['timestamp'],
            is_me=row['is_me'],
            local_path=row['local_path'],
            is_read=row['is_read'],
            is_sent=row.get('is_sent', 1),
            status=row.get('status'),
            reply_to_id=row.get('reply_to_id')
        )

    def to_dict(self):
        return {
            "message_id": self.message_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "group_id": self.group_id,
            "message_type": self.message_type,
            "content": self.content,
            "timestamp": self.timestamp,
            "is_me": self.is_me,
            "local_path": self.local_path,
            "is_read": self.is_read,
            "status": self.status,
            "reply_to_id": self.reply_to_id
        }

    def __repr__(self):
        # Mesajın yönünü belirleyelim
        direction = "OUTGOING ↗" if self.is_me else "INCOMING ↙"
        target = f"GroupID:{self.group_id}" if self.group_id else f"User:{self.receiver}"
        
        # İçerik çok uzunsa keselim
        display_content = (str(self.content)[:30] + '...') if len(str(self.content)) > 30 else self.content
        
        # Okundu durumu (Sadece gelen mesajlar için anlamlı olabilir)
        read_status = "READ" if self.is_read else "UNREAD"

        return (f"<CachedMessage | {direction} | ID:{self.message_id} | "
                f"From:{self.sender} | To:{target} | Type:{self.message_type} | "
                f"Status:{read_status} | Content:'{display_content}' | Time:{self.timestamp}>")