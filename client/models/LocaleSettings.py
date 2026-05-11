class LocaleSettings:
    def __init__(self, encryption_key=None, remember_me=0, saved_username=None, setting_id=1):
        """
        Yerel cihaz ayarlarini temsil eden model. 
        Veritabaninda tek bir satir (setting_id=1) olarak tutulur.
        """
        self.setting_id = setting_id
        self.encryption_key = encryption_key  # Fernet anahtarı (TEXT)
        self.remember_me = remember_me        # 0 veya 1
        self.saved_username = saved_username  # Hatırlanacak kullanıcı adı

    @classmethod
    def from_row(cls, row, enc_manager=None):
        """SQLite satirini LocaleSettings nesnesine dönüştürür."""
        if not row:
            return None
        saved_user = enc_manager.decrypt(row["saved_username"]) if enc_manager else row["saved_username"]
        return cls(
            setting_id=row["setting_id"],
            encryption_key=row["encryption_key"],
            remember_me=row["remember_me"],
            saved_username=saved_user
        )

    def to_dict(self):
        """Veritabanina kaydederken kolaylik sağlar."""
        return {
            "setting_id": self.setting_id,
            "encryption_key": self.encryption_key,
            "remember_me": self.remember_me,
            "saved_username": self.saved_username
        }
        
    def __repr__(self):
        return (f"<LocaleSettings(id={self.setting_id}, "
                f"remember_me={self.remember_me}, "
                f"saved_user='{self.saved_username}', "
                f"encryption_key={self.encryption_key}>")