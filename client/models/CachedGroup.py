class CachedGroup:
    def __init__(self, group_id, group_name, created_by, created_at, is_admin=0, avatar="👥"):
        self.group_id = group_id
        self.group_name = group_name
        self.created_by = created_by
        self.created_at = created_at
        self.is_admin = is_admin
        self.avatar = avatar

    @classmethod
    def from_row(cls, row, enc_manager=None):
        if not row: return None
        row = dict(row)
        name = enc_manager.decrypt(row['group_name']) if enc_manager else row['group_name']
        return cls(
            group_id=row['group_id'],
            group_name=name,
            created_by=row['created_by'],
            created_at=row['created_at'],
            is_admin=row['is_admin'],
            avatar=row.get('avatar', "👥")
        )

    def to_dict(self):
        data = {
            "group_id": self.group_id,
            "group_name": self.group_name,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "is_admin": self.is_admin,
            "avatar": self.avatar
        }
        return data

    def __repr__(self):
        return (f"<CachedGroup(ID={self.group_id}, Name='{self.group_name}', "
                f"IsAdmin={bool(self.is_admin)})>")