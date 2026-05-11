class GroupMember:
    def __init__(self, group_id, username, is_admin=False, is_kicked=0):
        self.group_id = group_id
        self.username = username
        self.is_admin = is_admin
        self.is_kicked = is_kicked

    def to_dict(self):
        return {
            "group_id": self.group_id,
            "username": self.username,
            "is_admin": self.is_admin,
            "is_kicked": self.is_kicked
        }

    @classmethod
    def from_dict(cls, data):
        if not data:
            return None
            
        return cls(
            group_id=data.get("group_id"),
            username=data.get("username"),
            is_admin=data.get("is_admin", 0),
            is_kicked=data.get("is_kicked", 0)
        )

    def __repr__(self):
        role_label = "ADMIN" if self.is_admin else "MEMBER"
        return (f"<GroupMember(group_id={self.group_id}, "
                f"username='{self.username}', "
                f"status='{role_label}')>")