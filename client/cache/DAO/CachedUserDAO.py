from models.CachedUser import CachedUser

class CachedUserDAO:
    def __init__(self, db_conn):
        self.db = db_conn

    # CREATE & UPDATE (Upsert)
    def save(self, user: CachedUser):
        query = "INSERT OR REPLACE INTO CachedUsers (username, last_seen, avatar) VALUES (?, ?, ?)"
        self.db.execute(query, (user.username, user.last_seen, user.avatar))

    # READ
    def get_by_username(self, username):
        query = "SELECT * FROM CachedUsers WHERE username = ?"
        row = self.db.fetch_one(query, (username,))
        return CachedUser.from_row(row)

    def get_all(self):
        rows = self.db.fetch_all("SELECT * FROM CachedUsers")
        return [CachedUser.from_row(row) for row in rows]

    # DELETE
    def delete(self, username):
        query = "DELETE FROM CachedUsers WHERE username = ?"
        self.db.execute(query, (username,))

    def clear_all(self):
        query = "DELETE FROM CachedUsers"
        self.db.execute(query)