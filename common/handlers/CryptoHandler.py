from cryptography.fernet import Fernet
import base64

class CryptoHandler:
    def __init__(self):
        self.fernet = None

    def generate_new_key(self):
        """Yeni bir Fernet anahtarı üretir (Bytes döner)."""
        return Fernet.generate_key()

    def set_key(self, key):
        """
        Veritabanından çekilen key'i (string veya bytes) 
        motorun kullanabileceği hale getirir.
        """
        if not key:
            raise ValueError("Geçersiz anahtar! Anahtar boş olamaz.")
            
        if isinstance(key, str):
            key = key.encode()
            
        try:
            self.fernet = Fernet(key)
        except Exception as e:
            raise ValueError(f"Fernet anahtarı yüklenemedi: {e}")

    def encrypt(self, plain_text):
        """Metni şifreler. Anahtar yoksa ValueError fırlatır."""
        if not self.fernet:
            raise RuntimeError("Şifreleme başarısız: Henüz bir anahtar (key) ayarlanmadı!")
        
        if not plain_text:
            return ""

        token = self.fernet.encrypt(plain_text.encode())
        return token.decode()

    def decrypt(self, cipher_text):
        """Şifreli metni çözer. Anahtar yoksa veya deşifre edilemezse hata fırlatır."""
        if not self.fernet:
            raise RuntimeError("Deşifreleme başarısız: Henüz bir anahtar (key) ayarlanmadı!")
        
        if not cipher_text:
            return ""

        try:
            decoded_text = self.fernet.decrypt(cipher_text.encode())
            return decoded_text.decode()
        except Exception as e:
            # Burada hata fırlatıyoruz çünkü yanlış anahtarla veri okumaya çalışıyor olabiliriz
            raise ValueError(f"Deşifreleme işlemi başarısız oldu (Hatalı anahtar veya bozuk veri): {e}")