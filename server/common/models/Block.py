class Block:
    def __init__(self, blocker, blocked):
        self.blocker = blocker
        self.blocked = blocked

    def to_dict(self):
        return {
            "blocker": self.blocker,
            "blocked": self.blocked
        }

    @classmethod
    def from_dict(cls, data):
        if not data:
            return None
            
        return cls(
            blocker=data.get("blocker"),
            blocked=data.get("blocked")
        )

    def __repr__(self):
        return f"<Block(blocker='{self.blocker}', blocked='{self.blocked}')>"