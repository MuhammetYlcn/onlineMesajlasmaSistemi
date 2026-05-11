# server/database/group_member_dao.py
from common.models.GroupMember import GroupMember

class GroupMemberDAO:
    def __init__(self, db_manager):
        self.db = db_manager

    def add_member(self, member_obj: GroupMember):
        from security.Hash import Hash
        h_uname = Hash.hash_deterministic(member_obj.username)
        row = self.db.fetch_one("SELECT 1 FROM Group_Members WHERE group_id = ? AND username = ?", (member_obj.group_id, h_uname))
        if row:
            query = "UPDATE Group_Members SET is_kicked = 0, is_admin = ? WHERE group_id = ? AND username = ?"
            return self.db.execute(query, (member_obj.is_admin, member_obj.group_id, h_uname))
        else:
            query = "INSERT INTO Group_Members (group_id, username, is_admin, is_kicked) VALUES (?, ?, ?, 0)"
            return self.db.execute(query, (member_obj.group_id, h_uname, member_obj.is_admin))

    def remove_member(self, group_id, username):
        from security.Hash import Hash
        h_uname = Hash.hash_deterministic(username)
        query = "UPDATE Group_Members SET is_kicked = 1 WHERE group_id = ? AND username = ?"
        return self.db.execute(query, (group_id, h_uname))

    def get_group_members(self, group_id):
        # Üyelerin gerçek adlarını almak için Users tablosuyla JOIN yapıyoruz
        query = """
            SELECT m.*, u.display_name 
            FROM Group_Members m
            JOIN Users u ON m.username = u.username
            WHERE m.group_id = ? AND (m.is_kicked = 0 OR m.is_kicked IS NULL)
        """
        rows = self.db.fetch_all(query, (group_id,))
        members = []
        # Not: UserDAO._decrypt_user_row mantığını burada manuel uyguluyoruz veya UserService kullanmalıyız.
        # Basitlik için burada decrypt ediyoruz.
        from SocketServer import SocketServer
        # Not: DAO'lar SocketServer'dan enc_manager almalı. GroupMemberDAO'da enc_manager yok.
        # SocketServer.py'da DAO'lara enc_manager set ediliyor.
        for r in rows:
            data = dict(r)
            if hasattr(self, 'enc_manager') and self.enc_manager and data.get('display_name'):
                data['username'] = self.enc_manager.decrypt(data['display_name'])
            members.append(GroupMember.from_dict(data))
        return members

    def get_user_groups(self, username):
        from security.Hash import Hash
        h_uname = Hash.hash_deterministic(username)
        query = "SELECT group_id FROM Group_Members WHERE username = ? AND (is_kicked = 0 OR is_kicked IS NULL)"
        rows = self.db.fetch_all(query, (h_uname,))
        return [row['group_id'] for row in rows]

    def update_admin_status(self, group_id, username, status):
        from security.Hash import Hash
        h_uname = Hash.hash_deterministic(username)
        query = "UPDATE Group_Members SET is_admin = ? WHERE group_id = ? AND username = ?"
        return self.db.execute(query, (status, group_id, h_uname))

    def is_user_admin(self, group_id, username):
        from security.Hash import Hash
        h_uname = Hash.hash_deterministic(username)
        query = "SELECT is_admin FROM Group_Members WHERE group_id = ? AND username = ?"
        row = self.db.fetch_one(query, (group_id, h_uname))
        return row['is_admin'] if row else 0

    def get_member_count(self, group_id):
        query = "SELECT COUNT(*) as count FROM Group_Members WHERE group_id = ? AND (is_kicked = 0 OR is_kicked IS NULL)"
        row = self.db.fetch_one(query, (group_id,))
        return row['count'] if row else 0

    def is_member(self, group_id, username):
        from security.Hash import Hash
        h_uname = Hash.hash_deterministic(username)
        query = "SELECT 1 FROM Group_Members WHERE group_id = ? AND username = ? AND (is_kicked = 0 OR is_kicked IS NULL)"
        row = self.db.fetch_one(query, (group_id, h_uname))
        return 1 if row else 0