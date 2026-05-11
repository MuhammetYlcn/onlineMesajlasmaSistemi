from models.LocaleSettings import LocaleSettings

class LocaleSettingsDAO:
    def __init__(self, db_conn):
        self.db = db_conn
        self.enc_manager = None

    def save(self, settings: LocaleSettings):
        """
        setting_id her zaman 1 olarak kalir.
        """
        query = """INSERT OR REPLACE INTO LocaleSettings 
                   (setting_id, encryption_key, remember_me, saved_username) 
                   VALUES (?, ?, ?, ?)"""
        saved_user = self.enc_manager.encrypt(settings.saved_username) if self.enc_manager else settings.saved_username
        self.db.execute(query, (
            settings.setting_id, 
            settings.encryption_key, 
            settings.remember_me, 
            saved_user
        ))

    def get_settings(self):
        query = "SELECT * FROM LocaleSettings WHERE setting_id = 1"
        row = self.db.fetch_one(query)
        return LocaleSettings.from_row(row, self.enc_manager)

    def update_remember_me(self, status: int):
        query = "UPDATE LocaleSettings SET remember_me = ? WHERE setting_id = 1"
        self.db.execute(query, (status,))

    def delete_settings(self):
        query = "DELETE FROM LocaleSettings WHERE setting_id = 1"
        self.db.execute(query)

    def has_saved_session(self):
        settings = self.get_settings()
        return settings is not None and settings.remember_me == 1