import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization

class EncryptionManager:
    def __init__(self, key_path=None):
        self.fernet_key = None
        self.fernet = None
        self.private_key = None
        self.public_key = None
        self.key_path = key_path

    def generate_rsa_keys(self):
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()
        return self.public_key

    def get_public_key_bytes(self):
        if not self.public_key: return None
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

    def load_public_key(self, pem_bytes):
        self.public_key = serialization.load_pem_public_key(pem_bytes)

    def decrypt_fernet_key(self, encrypted_key):
        if not self.private_key: return None
        self.fernet_key = self.private_key.decrypt(
            encrypted_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        self.fernet = Fernet(self.fernet_key)
        return self.fernet_key

    def encrypt_fernet_key(self, fernet_key, public_key_obj=None):
        target_pub = public_key_obj or self.public_key
        if not target_pub: return None
        return target_pub.encrypt(
            fernet_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

    def set_fernet_key(self, key):
        self.fernet_key = key
        self.fernet = Fernet(key)

    def encrypt(self, data: str) -> str:
        if not self.fernet or not data: return data
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data: str) -> str:
        if not self.fernet or not encrypted_data: return encrypted_data
        try:
            return self.fernet.decrypt(encrypted_data.encode()).decode()
        except:
            return encrypted_data # Fallback if not encrypted or wrong key
