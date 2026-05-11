import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

class LocalEncryption:
    def __init__(self, master_key_path=None):
        if master_key_path is None:
            # client klasörü içinde bir yer seçelim
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            master_key_path = os.path.join(base_dir, "cache", "local.key")
            salt_path = os.path.join(base_dir, "cache", "local.salt")
        
        self.master_key_path = master_key_path
        self.salt_path = salt_path
        self.fernet = None
        self._init_keys()

    def _init_keys(self):
        os.makedirs(os.path.dirname(self.master_key_path), exist_ok=True)
        
        # Salt (tuz) kontrolü/oluşturulması
        if not os.path.exists(self.salt_path):
            salt = os.urandom(16)
            with open(self.salt_path, "wb") as f:
                f.write(salt)
        else:
            with open(self.salt_path, "rb") as f:
                salt = f.read()

        # Anahtar kontrolü/oluşturulması
        if not os.path.exists(self.master_key_path):
            # Rastgele bir şifre gibi davranan anahtar üretelim
            password = base64.urlsafe_b64encode(os.urandom(32))
            with open(self.master_key_path, "wb") as f:
                f.write(password)
        else:
            with open(self.master_key_path, "rb") as f:
                password = f.read()

        # KDF ile Fernet anahtarı türetelim (Tuzlama burada yapılıyor)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        self.fernet = Fernet(key)

    def encrypt(self, data):
        if not data: return data
        if isinstance(data, str):
            return self.fernet.encrypt(data.encode()).decode()
        return self.fernet.encrypt(data) # Binary data

    def decrypt(self, encrypted_data):
        if not encrypted_data: return encrypted_data
        try:
            if isinstance(encrypted_data, str):
                return self.fernet.decrypt(encrypted_data.encode()).decode()
            return self.fernet.decrypt(encrypted_data)
        except Exception:
            # Şifreli gibi görünüyorsa ama deşifre edilemiyorsa (örn. anahtar değişmişse)
            # kullanıcıya çöp göstermek yerine boş dönelim
            if isinstance(encrypted_data, str) and (encrypted_data.startswith("gAAAA") or len(encrypted_data) > 64):
                return ""
            return encrypted_data # Şifreli değilse orjinalini dön
