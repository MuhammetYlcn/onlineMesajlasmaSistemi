class CachedUser:
    def __init__(self, username, last_seen, avatar="👤"):
        self.username = username
        self.last_seen = last_seen
        self.avatar = avatar

    @classmethod
    def from_row(cls, row):
        if not row: return None
        row = dict(row)
        return cls(
            username=row['username'],
            last_seen=row['last_seen'],
            avatar=row.get('avatar', "👤")
        )

    def to_dict(self):
        return {
            "username": self.username,
            "last_seen": self.last_seen,
            "avatar": self.avatar
        }

    def __repr__(self):
        """Geliştirici dostu çıktı (Debug için)."""
        return f"<CachedUser(username='{self.username}', last_seen='{self.last_seen}')>"