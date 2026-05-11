# server/database/group_dao.py
from common.models.Group import Group

class GroupDAO:
    def __init__(self, db_manager, enc_manager=None):
        self.db = db_manager
        self.enc_manager = enc_manager

    def create_group(self, group_obj: Group):
        """
        Yeni bir grup oluşturur. group_id AUTOINCREMENT olduğu için eklenmedi.
        """
        group_name = self.enc_manager.encrypt(group_obj.group_name) if self.enc_manager else group_obj.group_name
        avatar = self.enc_manager.encrypt(group_obj.avatar) if (self.enc_manager and group_obj.avatar) else group_obj.avatar
        
        query = """
            INSERT INTO Groups (group_name, created_by, avatar, created_at) 
            VALUES (?, ?, ?, ?)
        """
        params = (group_name, group_obj.created_by, avatar, group_obj.created_at)
        try:
            # execute_query'nin başarılı olması durumunda True dönecektir
            return self.db.execute(query, params)
        except Exception as e:
            print(f"Grup oluşturma hatası: {e}")
            return False

    def update_group_avatar(self, group_id, avatar_str):
        avatar = self.enc_manager.encrypt(avatar_str) if self.enc_manager else avatar_str
        query = "UPDATE Groups SET avatar = ? WHERE group_id = ?"
        return self.db.execute(query, (avatar, group_id))

    def get_group_by_id(self, group_id):
        """ID üzerinden grup bilgilerini getirir."""
        query = "SELECT * FROM Groups WHERE group_id = ?"
        row = self.db.fetch_one(query, (group_id,))
        if row and self.enc_manager:
            row = dict(row)
            row['group_name'] = self.enc_manager.decrypt(row['group_name'])
            if row['avatar']:
                row['avatar'] = self.enc_manager.decrypt(row['avatar'])
        return Group.from_dict(row) if row else None

    def get_groups_by_creator(self, username):
        """Belirli bir kullanıcının kurduğu grupları listeler."""
        query = "SELECT * FROM Groups WHERE created_by = ? COLLATE NOCASE"
        rows = self.db.fetch_all(query, (username,))
        groups = []
        for row in rows:
            group_data = dict(row)
            if self.enc_manager:
                group_data['group_name'] = self.enc_manager.decrypt(group_data['group_name'])
                if group_data['avatar']:
                    group_data['avatar'] = self.enc_manager.decrypt(group_data['avatar'])
            groups.append(Group.from_dict(group_data))
        return groups

    def delete_group(self, group_id):
        """Grubu sistemden tamamen siler."""
        query = "DELETE FROM Groups WHERE group_id = ?"
        try:
            return self.db.execute(query, (group_id,))
        except Exception as e:
            print(f"Grup silme hatası: {e}")
            return False

    def update_group_name(self, group_id, new_name):
        """Grup adını günceller."""
        enc_name = self.enc_manager.encrypt(new_name) if self.enc_manager else new_name
        query = "UPDATE Groups SET group_name = ? WHERE group_id = ?"
        return self.db.execute(query, (enc_name, group_id))