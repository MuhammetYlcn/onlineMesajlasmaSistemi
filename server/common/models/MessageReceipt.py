from datetime import datetime

class MessageReceipt:
    def __init__(self, message_id, username, status="SENT", timestamp=None):
        self.message_id = message_id
        self.username = username
        self.status = status
        
        if timestamp is None:
            self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            self.timestamp = timestamp

    def to_dict(self):
        return {
            "message_id": self.message_id,
            "username": self.username,
            "status": self.status,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data):
        if not data:
            return None
            
        return cls(
            message_id=data.get("message_id"),
            username=data.get("username"),
            status=data.get("status"),
            timestamp=data.get("timestamp")
        )

    def __repr__(self):
        return (f"<MessageReceipt(message_id={self.message_id}, "
                f"username='{self.username}', "
                f"status='{self.status}', "
                f"timestamp='{self.timestamp}')>")