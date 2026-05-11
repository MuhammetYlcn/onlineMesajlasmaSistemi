from datetime import datetime

class User:
    def __init__(self, username, passwordhash, user_id=None, lastseen=None, avatar="👤"):
        # Zorunlu alanlar
        self.username = username
        self.passwordhash = passwordhash
        self.avatar = avatar
        
        # Opsiyonel alanlar (Veritabanı veya Sunucu tarafından doldurulur)
        self.user_id = user_id

        if(lastseen is None):
            self.lastseen=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            self.lastseen=lastseen

    def to_dict(self):
        """
        Nesneyi, JSON olarak gönderilmeye uygun bir Python sözlüğüne (dictionary) dönüştürür.
        """
        return {
            "user_id": self.user_id,
            "username": self.username,
            "passwordhash": self.passwordhash,
            "lastseen": self.lastseen,
            "avatar": self.avatar
        }

    @classmethod
    def from_dict(cls, data):
        """
        .get() kullanimi sayesinde eksik anahtarlarda hata firlatmaz.
        """
        if not data:
            return None
            
        return cls(
            username=data.get("username"),
            passwordhash=data.get("passwordhash"),
            user_id=data.get("user_id"),
            lastseen=data.get("lastseen"),
            avatar=data.get("avatar", "👤")
        )

    def __repr__(self):
        return (f"<User(id={self.user_id}, "
                f"username='{self.username}', "
                f"passwordhash='{self.passwordhash}', "
                f"lastseen='{self.lastseen}')>")