from models.CachedGroup import CachedGroup

class CachedGroupDAO:
    def __init__(self, db_conn):
        self.db = db_conn
        self.enc_manager = None

    # CREATE & UPDATE (Upsert)
    def save(self, group: CachedGroup):
        query = """INSERT OR REPLACE INTO CachedGroups 
                   (group_id, group_name, created_by, created_at, is_admin, avatar) 
                   VALUES (?, ?, ?, ?, ?, ?)"""
        name = self.enc_manager.encrypt(group.group_name) if self.enc_manager else group.group_name
        self.db.execute(query, (
            group.group_id, 
            name, 
            group.created_by, 
            group.created_at, 
            group.is_admin,
            group.avatar
        ))

    # READ
    def get_by_id(self, group_id):
        query = "SELECT * FROM CachedGroups WHERE group_id = ?"
        row = self.db.fetch_one(query, (group_id,))
        return CachedGroup.from_row(row, self.enc_manager)

    def get_all_my_groups(self):
        rows = self.db.fetch_all("SELECT * FROM CachedGroups ORDER BY group_name ASC")
        return [CachedGroup.from_row(row, self.enc_manager) for row in rows]

    # UPDATE (Specific)
    def update_admin_status(self, group_id, is_admin: int):
        query = "UPDATE CachedGroups SET is_admin = ? WHERE group_id = ?"
        self.db.execute(query, (is_admin, group_id))

    # DELETE
    def delete(self, group_id):
        query = "DELETE FROM CachedGroups WHERE group_id = ?"
        self.db.execute(query, (group_id,))