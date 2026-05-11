from common.models.User import User 

class UserDAO:
    def __init__(self, db_manager):
        self.db = db_manager
        self.enc_manager = None
        self._ensure_avatar_column()

    def _ensure_avatar_column(self):
        """Users tablosunda gerekli şifreli kolonları kontrol eder."""
        try:
            self.db.execute("ALTER TABLE Users ADD COLUMN avatar TEXT DEFAULT ''")
        except: pass
        try:
            self.db.execute("ALTER TABLE Users ADD COLUMN display_name TEXT")
        except: pass
        try:
            self.db.execute("ALTER TABLE Users ADD COLUMN first_name TEXT")
        except: pass
        try:
            self.db.execute("ALTER TABLE Users ADD COLUMN last_name TEXT")
        except: pass

    def register_user(self, user_obj: User):
        from security.Hash import Hash
        try:
            # Username'i hem hashleyip (arama için) hem de şifreleyip (görüntüleme için) saklıyoruz
            username_val = getattr(user_obj, "username", "")
            if not username_val:
                print("[SERVER] Kayıt hatası: Kullanıcı adı boş")
                return False

            hashed_username = Hash.hash_deterministic(username_val)
            enc_username = self.enc_manager.encrypt(username_val) if self.enc_manager else username_val
            
            avatar_val = getattr(user_obj, "avatar", "👤")
            avatar = self.enc_manager.encrypt(avatar_val) if self.enc_manager else avatar_val
            
            first_name_val = getattr(user_obj, "first_name", "")
            first_name = self.enc_manager.encrypt(first_name_val) if (self.enc_manager and first_name_val) else first_name_val
            
            last_name_val = getattr(user_obj, "last_name", "")
            last_name = self.enc_manager.encrypt(last_name_val) if (self.enc_manager and last_name_val) else last_name_val

            query = """
                INSERT INTO Users (username, passwordhash, lastseen, avatar, display_name, first_name, last_name) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            params = (hashed_username, user_obj.passwordhash, user_obj.lastseen, avatar, enc_username, first_name, last_name)
            self.db.execute(query, params)
            return True
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                print(f"[SERVER] Kayıt başarısız: Kullanıcı zaten mevcut ({user_obj.username})")
            else:
                print(f"[SERVER] Kayıt başarısız: {e}")
                import traceback
                traceback.print_exc()
            return False

    def validate_login(self, username, passwordhash):
        from security.Hash import Hash
        hashed_username = Hash.hash_deterministic(username)
        query = "SELECT * FROM Users WHERE username = ? AND passwordhash = ?"
        row = self.db.fetch_one(query, (hashed_username, passwordhash))
        if row:
            return self._decrypt_user_row(row)
        return None

    def _decrypt_user_row(self, row):
        if not row: return None
        row = dict(row)
        if self.enc_manager:
            # Display name'den gerçek username'i geri alıyoruz
            if row.get('display_name'):
                row['username'] = self.enc_manager.decrypt(row['display_name'])
            
            if row.get('avatar'): row['avatar'] = self.enc_manager.decrypt(row['avatar'])
            if row.get('first_name'): row['first_name'] = self.enc_manager.decrypt(row['first_name'])
            if row.get('last_name'): row['last_name'] = self.enc_manager.decrypt(row['last_name'])
        return User.from_dict(row)

    def delete_user(self, user_id):
        query = "DELETE FROM Users WHERE user_id = ?"
        return self.db.execute(query, (user_id,))

    def update_lastseen(self, username, time_str):
        from security.Hash import Hash
        hashed_username = Hash.hash_deterministic(username)
        query = "UPDATE Users SET lastseen = ? WHERE username = ?"
        return self.db.execute(query, (time_str, hashed_username))

    def get_all_users_info(self):
        query = "SELECT * FROM Users"
        rows = self.db.fetch_all(query)
        decrypted = []
        for r in rows:
            u = self._decrypt_user_row(r)
            if u:
                decrypted.append({
                    "username": u.username,
                    "avatar": u.avatar,
                    "lastseen": u.lastseen
                })
        return decrypted

    def get_user_by_username(self, username):
        from security.Hash import Hash
        hashed_username = Hash.hash_deterministic(username)
        query = "SELECT * FROM Users WHERE username = ?"
        row = self.db.fetch_one(query, (hashed_username,))
        return self._decrypt_user_row(row)

    def get_user_by_id(self, user_id):
        query = "SELECT * FROM Users WHERE user_id = ?"
        row = self.db.fetch_one(query, (user_id,))
        return self._decrypt_user_row(row)