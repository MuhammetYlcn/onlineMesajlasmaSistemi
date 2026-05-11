class PendingMessage:
    def __init__(self, temp_id, sender, content, receiver=None, group_id=None, message_type='TEXT'):
        self.temp_id = temp_id
        self.sender = sender
        self.receiver = receiver
        self.group_id = group_id
        self.message_type = message_type
        self.content = content

    @classmethod
    def from_row(cls, row):
        if not row: return None
        return cls(
            temp_id=row['temp_id'],
            sender=row['sender'],
            receiver=row['receiver'],
            group_id=row['group_id'],
            message_type=row['message_type'],
            content=row['content']
        )

    def to_dict(self):
        return {
            "temp_id": self.temp_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "group_id": self.group_id,
            "message_type": self.message_type,
            "content": self.content
        }

    def __repr__(self):
        target = f"Group:{self.group_id}" if self.group_id else f"User:{self.receiver}"
        return f"<PendingMessage | TempID:{self.temp_id} | To:{target} | Type:{self.message_type}>"