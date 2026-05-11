from datetime import datetime

class Group:
    def __init__(self, group_name, created_by, created_at=None, group_id=None, avatar=None):
        self.group_name = group_name
        self.created_by = created_by
        self.avatar = avatar
        self.group_id = group_id
        
        if created_at is None:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            self.created_at = created_at
        
    def to_dict(self):
        return {
            "group_id": self.group_id,
            "group_name": self.group_name,
            "created_by": self.created_by,
            "avatar": self.avatar,
            "created_at": self.created_at
        }
        
    @classmethod
    def from_dict(cls, data):
          if not data:
              return None
          
          return cls(
              group_id=data.get("group_id"),
              group_name=data.get("group_name"),
              created_by=data.get("created_by"),
              avatar=data.get("avatar"),
              created_at=data.get("created_at")
          )
    
    def __repr__(self):
        return (f"<Group(id={self.group_id}, "
                f"name='{self.group_name}', "
                f"owner='{self.created_by}', "
                f"created_at='{self.created_at}')>")