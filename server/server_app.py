import sys
import os

# Ana dizini sys.path'e eklerek common ve server modüllerine erişim sağlayalım
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from server.SocketServer import SocketServer

def main():
    print("--- LAN Chat Sadece Sunucu Modu ---")
    server = SocketServer()
    if server.start():
        print("Sunucu başarıyla başlatıldı. Durdurmak için Ctrl+C tuşuna basın.")
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nSunucu durduruluyor...")
            server.stop()
    else:
        print("Hata: Sunucu başlatılamadı. Port kullanımda olabilir.")

if __name__ == "__main__":
    main()
