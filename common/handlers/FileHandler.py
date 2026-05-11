# client/handlers/file_handler.py
import os
import uuid

class FileHandler:
    def __init__(self, cache_dir="cache"):
        self.base_cache = cache_dir
        self.upload_dirs = {
            "AUDIO": os.path.join(self.base_cache, "uploads", "audio"),
            "FILES": os.path.join(self.base_cache, "uploads", "files"),
            "IMAGES": os.path.join(self.base_cache, "uploads", "images")
        }
        self._ensure_dirs()

    def _ensure_dirs(self):
        for path in self.upload_dirs.values():
            os.makedirs(path, exist_ok=True)

    # --- CHUNK YAPISINA UYGUN METOD ---
    def save_chunk(self, chunk_data, file_type, target_filename):
        """
        Sunucudan gelen her bir 128 KB'lık parçayı dosyanın sonuna ekler.
        """
        if file_type not in self.upload_dirs:
            raise ValueError(f"Geçersiz tip: {file_type}")

        target_path = os.path.join(self.upload_dirs[file_type], target_filename)

        # 'ab' modu (Append Binary): Dosya yoksa oluşturur, varsa sonuna ekler.
        with open(target_path, "ab") as f:
            f.write(chunk_data)
        
        return target_path

    def generate_unique_filename(self, original_name):
        """Transfer başlamadan önce çakışmasız bir isim üretir."""
        ext = os.path.splitext(original_name)[1]
        return f"{uuid.uuid4().hex}{ext}"

    # --- ESKİ METOD (Kısa dosyalar veya tek seferlik kayıtlar için kalabilir) ---
    def save_full_file(self, raw_data, file_type, filename):
        target_path = os.path.join(self.upload_dirs[file_type], filename)
        with open(target_path, "wb") as f:
            f.write(raw_data)
        return target_path

    def delete_from_cache(self, file_path):
        if os.path.exists(file_path):
            os.remove(file_path)