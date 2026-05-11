class CachedBlock:
    def __init__(self, blocker, blocked):
        self.blocker = blocker
        self.blocked = blocked

    @classmethod
    def from_row(cls, row):
        if not row: return None
        return cls(blocker=row['blocker'], blocked=row['blocked'])

    def to_dict(self):
        return {"blocker": self.blocker, "blocked": self.blocked}

    def __repr__(self):
        return f"<CachedBlock(Blocker='{self.blocker}', Blocked='{self.blocked}')>"