class CachedReceipt:
    def __init__(self, message_id, username, status='SENT', timestamp=None):
        self.message_id = message_id
        self.username = username
        self.status = status
        self.timestamp = timestamp

    @classmethod
    def from_row(cls, row):
        """SQLite satırını (row) CachedReceipt nesnesine dönüştürür."""
        if not row:
            return None
        return cls(
            message_id=row['message_id'],
            username=row['username'],
            status=row['status'],
            timestamp=row['timestamp']
        )

    def to_dict(self):
        return {
            "message_id": self.message_id,
            "username": self.username,
            "status": self.status,
            "timestamp": self.timestamp
        }

    def __repr__(self):
        icons = {
            "SENT": "✓",           # Sunucuya ulaştı
            "DELIVERED": "✓✓",     # Karşı cihazda
            "READ": "blue✓✓"       # Okundu
        }
        icon = icons.get(self.status, "❓")
        
        return (f"<CachedReceipt | {icon} {self.status:9} | "
                f"MsgID:{self.message_id} | "
                f"User:{self.username} | "
                f"Time:{self.timestamp}>")