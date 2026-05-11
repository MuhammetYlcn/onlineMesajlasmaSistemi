import hashlib
import secrets

class Hash:
    @staticmethod
    def hash_password(password):
        salt = secrets.token_hex(16) # 32 karakterlik rastgele hex salt
        salted_password = password + salt
        hashed = hashlib.sha256(salted_password.encode('utf-8')).hexdigest()
        
        # Veritabanında bu formatta saklanacak
        return f"{salt}:{hashed}"

    @staticmethod
    def verify_password(stored_combined_hash, provided_password):
        if not stored_combined_hash or ":" not in stored_combined_hash:
            return False
            
        # Parçalarına ayırıyoruz
        salt, stored_hash = stored_combined_hash.split(":")
        
        # Kullanıcının girdiği şifreyi aynı tuz ile hashle
        new_hash = hashlib.sha256((provided_password + salt).encode('utf-8')).hexdigest()
        
        return new_hash == stored_hash

    @staticmethod
    def hash_deterministic(data, salt="FIXED_SERVER_SALT_DO_NOT_CHANGE"):
        """Veritabanında arama yapılabilecek (WHERE username=?) ama şifreli görünen hash üretir."""
        if not data: return data
        return hashlib.sha256((data + salt).encode('utf-8')).hexdigest()