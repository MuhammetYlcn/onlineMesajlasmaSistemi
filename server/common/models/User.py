from datetime import datetime

class User:
    def __init__(self, username, passwordhash, user_id=None, lastseen=None, avatar="👤", display_name=None, first_name=None, last_name=None):
        # Zorunlu alanlar
        self.username = username
        self.passwordhash = passwordhash
        self.avatar = avatar
        
        # Opsiyonel alanlar (Veritabanı veya Sunucu tarafından doldurulur)
        self.user_id = user_id
        self.display_name = display_name
        self.first_name = first_name
        self.last_name = last_name

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
            "lastseen": self.lastseen,
            "avatar": self.avatar,
            "display_name": self.display_name,
            "first_name": self.first_name,
            "last_name": self.last_name
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
            avatar=data.get("avatar", "👤"),
            display_name=data.get("display_name"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name")
        )

    def __repr__(self):
        return (f"<User(id={self.user_id}, "
                f"username='{self.username}', "
                f"passwordhash='{self.passwordhash}', "
                f"lastseen='{self.lastseen}')>")