from datetime import datetime

class Message:
    def __init__(self, sender, content, message_type="TEXT", timestamp=None, receiver=None, group_id=None, message_id=None, file_path=None, msg_id=None, reply_to_id=None, is_forwarded=0, is_edited=0):
        self.sender = sender
        self.content = content
        self.receiver = receiver
        self.group_id = group_id        
        self.message_id = message_id
        self.reply_to_id = reply_to_id
        self.is_forwarded = is_forwarded
        self.is_edited = is_edited
        
        if timestamp is None:
            self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            self.timestamp = timestamp
        
        self.message_type = message_type
        self.file_path = file_path
        self.msg_id = msg_id
            
    def to_dict(self):
        return {
            "message_id": self.message_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "group_id": self.group_id,
            "message_type": self.message_type,
            "content": self.content,
            "timestamp": self.timestamp,
            "file_path": self.file_path,
            "msg_id": self.msg_id,
            "reply_to_id": self.reply_to_id,
            "is_forwarded": self.is_forwarded,
            "is_edited": self.is_edited
        }

    @classmethod
    def from_dict(cls, data):
        if not data:
            return None
            
        return cls(
            sender=data.get("sender"),
            message_type=data.get("message_type"),
            content=data.get("content"),
            timestamp=data.get("timestamp"),
            receiver=data.get("receiver"),
            group_id=data.get("group_id"),
            message_id=data.get("message_id"),
            file_path=data.get("file_path") or data.get("file_name"),
            msg_id=data.get("msg_id"),
            reply_to_id=data.get("reply_to_id"),
            is_forwarded=data.get("is_forwarded", 0),
            is_edited=data.get("is_edited", 0)
        )

    def __repr__(self):
        target = f"Group:{self.group_id}" if self.group_id else f"User:{self.receiver}"
        return (f"<Message(id={self.message_id}, "
                f"sender={self.sender}, "
                f"target=[{target}], "
                f"type='{self.message_type}', "
                f"is_edited={self.is_edited})>")