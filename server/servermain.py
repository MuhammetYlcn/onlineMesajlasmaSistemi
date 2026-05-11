import sys
import os
import time
import socket
import json
import concurrent.futures

# Ana dizini sys.path'e ekleyelim
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from SocketServer import SocketServer

def get_all_ips():
    ips = []
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127."):
                ips.append(ip)
    except:
        pass
    
    # Fallback method
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
        if IP not in ips:
            ips.append(IP)
        s.close()
    except:
        pass
        
    if not ips:
        ips = ['127.0.0.1']
    return ips

def check_server(ip):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            if s.connect_ex((ip, 50005)) == 0:
                s.sendall(json.dumps({"action": "PING", "payload": {}}).encode('utf-8'))
                response_data = s.recv(1024)
                if b'"action": "PONG"' in response_data:
                    return ip
    except:
        pass
    return None

def main():
    print("="*40)
    print(" MESAJLAŞMA SUNUCUSU BAŞLATILIYOR ")
    print("="*40)
    
    all_ips = get_all_ips()
    primary_ip = all_ips[0]
    base_ip = ".".join(primary_ip.split(".")[:-1])
    targets = []
    if primary_ip != "127.0.0.1":
        targets = [f"{base_ip}.{i}" for i in range(1, 255) if f"{base_ip}.{i}" != primary_ip]
    targets.append("127.0.0.1")
        
    print("Ağdaki diğer sunucular kontrol ediliyor...")
    server_found = None
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        results = executor.map(check_server, targets)
        for res in results:
            if res:
                server_found = res
                break

    if server_found:
        print(f"\nHATA: Ağda veya bu bilgisayarda zaten aktif bir sunucu var ({server_found})!")
        print("Sadece bir sunucu açılabilir.")
        input("Çıkmak için Enter'a basın...")
        sys.exit(1)

    server_instance = SocketServer()
    if not server_instance.start():
        print("\nHATA: Sunucu başlatılamadı! Başka bir sunucu zaten çalışıyor olabilir.")
        input("Çıkmak için Enter'a basın...")
        sys.exit(1)
        
    import threading
    stop_event = threading.Event()
    
    print("\n[BAŞARILI] Sunucu başarıyla başlatıldı ve dinleniyor. (Versiyon: 1.1)")
    print(f"Sunucu IP Adresleri: {', '.join(all_ips)}")
    print("Sunucuyu kapatmak için bu pencereyi kapatabilir veya Ctrl+C tuşlarına basabilirsiniz.")
    
    try:
        # Event.wait() Ctrl+C tarafından kesilebilir ama daha stabildir
        while not stop_event.is_set():
            stop_event.wait(timeout=1.0)
    except (KeyboardInterrupt, SystemExit):
        print("\n[SERVER] Sunucu kapatma sinyali alındı (Durduruluyor)...")
    except Exception as e:
        print(f"\n[KRİTİK HATA] Ana sunucu döngüsünde beklenmedik hata: {e}")
        import traceback
        traceback.print_exc()
    finally:
        server_instance.stop()
        print("[SERVER] Sunucu güvenli bir şekilde kapatıldı.")
        sys.exit(0)

if __name__ == "__main__":
    main()
