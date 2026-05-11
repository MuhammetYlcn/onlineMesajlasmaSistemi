# server/database/block_dao.py
from common.models.Block import Block

class BlockDAO:
    def __init__(self, db_manager):
        self.db = db_manager

    def block_user(self, block_obj: Block):
        from security.Hash import Hash
        h1, h2 = Hash.hash_deterministic(block_obj.blocker), Hash.hash_deterministic(block_obj.blocked)
        query = "INSERT INTO BlockedUsers (blocker, blocked) VALUES (?, ?)"
        try:
            return self.db.execute(query, (h1, h2))
        except Exception as e:
            print(f"Engelleme başarısız: {e}")
            return False

    def unblock_user(self, blocker, blocked):
        from security.Hash import Hash
        h1, h2 = Hash.hash_deterministic(blocker), Hash.hash_deterministic(blocked)
        query = "DELETE FROM BlockedUsers WHERE blocker = ? AND blocked = ?"
        return self.db.execute(query, (h1, h2))

    def is_blocked(self, blocker, blocked):
        from security.Hash import Hash
        h1, h2 = Hash.hash_deterministic(blocker), Hash.hash_deterministic(blocked)
        query = "SELECT 1 FROM BlockedUsers WHERE (blocker = ? AND blocked = ?) OR (blocker = ? AND blocked = ?)"
        row = self.db.fetch_one(query, (h1, h2, h2, h1))
        return 1 if row else 0

    def get_my_blocked_list(self, username):
        from security.Hash import Hash
        h_uname = Hash.hash_deterministic(username)
        # Not: Engellenen kullanıcıların gerçek isimlerini almak için JOIN lazım
        query = """
            SELECT b.blocked, u.display_name 
            FROM BlockedUsers b
            JOIN Users u ON b.blocked = u.username
            WHERE b.blocker = ?
        """
        rows = self.db.fetch_all(query, (h_uname,))
        blocked_list = []
        for r in rows:
            data = dict(r)
            if hasattr(self, 'enc_manager') and self.enc_manager and data.get('display_name'):
                blocked_list.append(self.enc_manager.decrypt(data['display_name']))
            else:
                blocked_list.append(data['blocked'])
        return blocked_list