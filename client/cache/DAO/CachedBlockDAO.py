from models.CachedBlock import CachedBlock

class CachedBlockDAO:
    def __init__(self, db_conn):
        self.db = db_conn

    # CREATE
    def save(self, block: CachedBlock):
        query = "INSERT OR IGNORE INTO CachedBlocks (blocker, blocked) VALUES (?, ?)"
        self.db.execute(query, (block.blocker, block.blocked))

    # READ
    def is_blocked(self, blocked_username):
        query = "SELECT 1 FROM CachedBlocks WHERE blocked = ? LIMIT 1"
        row = self.db.fetch_one(query, (blocked_username,))
        return row is not None

    def get_all(self):
        query = "SELECT * FROM CachedBlocks"
        rows = self.db.fetch_all(query)
        return [CachedBlock.from_row(row) for row in rows]

    # DELETE
    def delete(self, blocker, blocked):
        query = "DELETE FROM CachedBlocks WHERE blocker = ? AND blocked = ?"
        self.db.execute(query, (blocker, blocked))