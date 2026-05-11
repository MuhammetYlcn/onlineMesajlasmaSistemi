# client/handlers/packet_handler.py
import json
import struct
import os

class PacketHandler:
    # ">I": Big-endian, 4 byte unsigned integer. 
    # Mesajın boyutunu en başa 4 byte olarak yazar.
    HEADER_FORMAT = ">I" 
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    
    # 128 KB: Telefon Hotspot ağında akıcı ve hızlı bir sunum için ideal boyut.
    CHUNK_SIZE = 128 * 1024  

    @staticmethod
    def to_bytes(packet_dict):
        """Common'dan gelen dict'i soket için Header + Body formatına çevirir."""
        try:
            json_bytes = json.dumps(packet_dict).encode('utf-8')
            header = struct.pack(PacketHandler.HEADER_FORMAT, len(json_bytes))
            return header + json_bytes
        except Exception as e:
            print(f"Paketleme hatası: {e}")
            return None

    @staticmethod
    def get_file_chunks(file_path):
        """
        Dosyayı 128 KB'lık parçalara böler. 
        Her parçanın başına kendi boyutunu ekler.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Dosya bulunamadı: {file_path}")
            
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(PacketHandler.CHUNK_SIZE)
                if not chunk:
                    break
                header = struct.pack(PacketHandler.HEADER_FORMAT, len(chunk))
                yield header + chunk

    @staticmethod
    def from_bytes(raw_bytes):
        """Gelen ham byte'ları tekrar JSON/Dict formatına çevirir."""
        try:
            return json.loads(raw_bytes.decode('utf-8'))
        except Exception as e:
            print(f"Paket çözme hatası: {e}")
            return None