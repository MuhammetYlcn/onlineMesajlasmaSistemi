from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes

class RSAHandler:
    def __init__(self):
        self.private_key = None
        self.public_key = None
        # Sunucu başlarken anahtarları otomatik üretir
        self._generate_keys()

    def _generate_keys(self):
        """Sunucu için 2048-bit RSA anahtar çifti üretir."""
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        self.public_key = self.private_key.public_key()

    def get_public_key_pem(self):
        """
        İstemciye gönderilmek üzere Açık Anahtarı (Public Key) 
        PEM (String benzeri byte) formatına çevirir.
        """
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()

    def decrypt_fernet_key(self, encrypted_key_b64):
        """
        İstemciden gelen RSA ile şifrelenmiş Fernet anahtarını çözer.
        """
        try:
            # Base64 gelen veriyi byte formatına çevir
            import base64
            encrypted_key = base64.b64decode(encrypted_key_b64)

            # Private Key ile deşifre et
            decrypted_key = self.private_key.decrypt(
                encrypted_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            return decrypted_key # Bu dönen veri CryptoHandler'ın set_key() metoduna verilecek
        except Exception as e:
            print(f"[RSA ERROR] Anahtar çözme başarısız: {e}")
            return None