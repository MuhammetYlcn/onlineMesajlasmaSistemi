import socket
import json
import threading
import time
from PyQt6.QtCore import QObject, pyqtSignal
from models.CachedMessage import CachedMessage
from models.CachedUser import CachedUser
from models.CachedGroup import CachedGroup
from models.CachedBlock import CachedBlock
from models.CachedReceipt import CachedReceipt
from models.PendingMessage import PendingMessage

class LANService(QObject):
    """Merkezi Sunucuya Bağlanan İstemci Servisi"""
    peer_found = pyqtSignal(dict) # { 'ip': '...', 'username': '...', 'first_name': '...', 'avatar': '👤' }
    message_received = pyqtSignal(str, str, str, str, str, dict) # target, text, file_path, msg_id, message_type, extra_data
    message_deleted = pyqtSignal(str) # msg_id
    server_lost = pyqtSignal(str) # Error message (optional)
    error_received = pyqtSignal(str) # message
    login_response = pyqtSignal(bool, str, dict) # success, message, user_data
    register_response = pyqtSignal(bool, str) # success, message
    receipt_received = pyqtSignal(str, str, str) # msg_id, status, target
    history_received = pyqtSignal(str, list) # target, messages
    group_list_updated = pyqtSignal(list) # List of groups
    blocked_list_updated = pyqtSignal(list) # List of blocked usernames
    message_edited = pyqtSignal(str, str) # msg_id, new_content
    typing_status_received = pyqtSignal(str, str, str) # sender, target, status
    
    def __init__(self, user_data=None, message_dao=None, group_dao=None, local_enc=None):
        super().__init__()
        self.user_data = user_data
        self.message_dao = message_dao
        self.group_dao = group_dao
        self.local_enc = local_enc
        self.server_ip = None
        self.server_port = 50005
        self.udp_port = 50006
        self.sock = None
        self.running = False
        self.blocked_users = []
        self.send_lock = threading.Lock()
        self.discovery_running = False
        
        from security.EncryptionManager import EncryptionManager
        self.enc_manager = EncryptionManager()  # Sunucu ile şifreli iletişim için
        self.enc_manager.generate_rsa_keys()
        # NOT: message_dao'nun enc_manager'i local_enc olmalı (sunucu anahtarı değil)
        # main.py zaten bunu ayarlıyor: message_dao.enc_manager = local_enc
        
    def start_discovery(self, callback):
        """Sunucuyu bulmak için UDP dinler"""
        self.discovery_running = True
        threading.Thread(target=self._discovery_loop, args=(callback,), daemon=True).start()

    def _discovery_loop(self, callback):
        import concurrent.futures
        
        print("[CLIENT] Sunucu aranıyor (UDP Dinleme ve TCP Tarama)...")
        
        # UDP Dinleyici Başlat
        def listen_udp():
            try:
                udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                udp_sock.bind(('', self.udp_port))
                udp_sock.settimeout(2.0)
                
                while self.discovery_running:
                    try:
                        data, addr = udp_sock.recvfrom(2048)
                        if not self.discovery_running: break
                        
                        packet = json.loads(data.decode('utf-8'))
                        if packet.get("action") == "SERVER_DISCOVERY":
                            server_ip = addr[0]
                            print(f"[CLIENT] Sunucu UDP ile bulundu: {server_ip}")
                            self.server_ip = server_ip
                            self.discovery_running = False
                            callback(server_ip)
                            break
                    except socket.timeout:
                        continue
                    except:
                        continue
                udp_sock.close()
            except:
                pass

        threading.Thread(target=listen_udp, daemon=True).start()

        while self.discovery_running:
            try:
                def get_all_local_ips():
                    ips = []
                    try:
                        hostname = socket.gethostname()
                        for ip in socket.gethostbyname_ex(hostname)[2]:
                            if not ip.startswith("127."):
                                ips.append(ip)
                        
                        # Radmin/Hamachi gibi VPN'ler için ek kontrol
                        import subprocess
                        output = subprocess.check_output("ipconfig", shell=True).decode('cp850')
                        for line in output.split('\n'):
                            if "IPv4 Address" in line or "IPv4 Adresi" in line:
                                parts = line.split(':')
                                if len(parts) > 1:
                                    ip = parts[1].strip()
                                    if ip not in ips and not ip.startswith("127."):
                                        ips.append(ip)
                    except:
                        pass
                    return list(set(ips))
                
                ips = get_all_local_ips()
                
                def check_port(ip):
                    try:
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            s.settimeout(0.3)
                            if s.connect_ex((ip, self.server_port)) == 0:
                                s.sendall(json.dumps({"action": "PING", "payload": {}}).encode('utf-8'))
                                response_data = s.recv(1024)
                                if b'"action": "PONG"' in response_data:
                                    return ip
                    except:
                        pass
                    return None

                # Taramayı yap
                for local_ip in ips + ["127.0.0.1"]:
                    if not self.discovery_running: break
                    
                    if local_ip == "127.0.0.1":
                        targets = ["127.0.0.1"]
                    else:
                        base_ip = ".".join(local_ip.split(".")[:-1])
                        targets = [f"{base_ip}.{i}" for i in range(1, 255)]
                    
                    with concurrent.futures.ThreadPoolExecutor(max_workers=60) as executor:
                        future_to_ip = {executor.submit(check_port, ip): ip for ip in targets if self.discovery_running}
                        for future in concurrent.futures.as_completed(future_to_ip):
                            if not self.discovery_running: break
                            res = future.result()
                            if res:
                                self.server_ip = res
                                self.discovery_running = False
                                print(f"[CLIENT] Sunucu TCP tarama ile bulundu: {self.server_ip}")
                                callback(self.server_ip)
                                return
            except Exception as e:
                print(f"[CLIENT] Tarama hatası: {e}")
            
            if self.discovery_running:
                time.sleep(2)

    def connect_to_server(self, ip):
        self.server_ip = ip
        print(f"[CLIENT] Sunucuya bağlanılıyor: {ip}:{self.server_port}...")
        try:
            self.discovery_running = False # Taramayı durdur
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((self.server_ip, self.server_port))
            self.sock.setblocking(True) # Kesin olarak bloklayan moda geç
            self.running = True
            
            # Alım döngüsünü başlat
            threading.Thread(target=self._receive_loop, daemon=True).start()
            
            # Keep-alive (Bağlantıyı canlı tutma) döngüsünü başlat
            threading.Thread(target=self._keep_alive_loop, daemon=True).start()
            
            # Şifreleme Anahtarını İste
            pub_key = self.enc_manager.get_public_key_bytes().decode()
            self._send_safe({"action": "GET_KEY", "payload": {"public_key": pub_key}})
            
            print(f"[CLIENT] Sunucuya başarıyla bağlanıldı: {ip}")
            return True
        except Exception as e:
            print(f"[CLIENT] Sunucuya bağlanılamadı ({ip}): {e}")
            return False

    def _keep_alive_loop(self):
        """Bağlantının kopmasını önlemek için periyodik PING gönderir"""
        while self.running:
            time.sleep(2) # Her 2 saniyede bir
            if self.running:
                self._send_safe({"action": "PING", "payload": {}})

    def _send_safe(self, packet):
        if not self.sock: return False
        try:
            data = json.dumps(packet).encode('utf-8')
            with self.send_lock:
                self.sock.sendall(data)
            return True
        except Exception as e:
            if self.running:
                print(f"[CLIENT] Paket gönderme hatası: {e}")
                self.running = False
                self.server_lost.emit(str(e))
            return False

    def login(self, username, password_hash):
        packet = {
            "action": "LOGIN",
            "payload": {"username": username, "password_hash": password_hash}
        }
        self._send_safe(packet)

    def register(self, username, password_hash):
        packet = {
            "action": "REGISTER",
            "payload": {"username": username, "passwordhash": password_hash}
        }
        self._send_safe(packet)
        # Yanıt bekleme (Basitlik için senkron bekleyelim veya sinyalle dönelim)
        # Not: _receive_loop bunu yakalayacak. UI tarafında login_successful sinyali LANService üzerinden de yönetilebilir.

    def update_avatar(self, new_avatar):
        packet = {
            "action": "UPDATE_AVATAR",
            "payload": {"avatar": new_avatar}
        }
        self._send_safe(packet)

    def send_typing_status(self, target, status):
        packet = {
            "action": "TYPING_STATUS",
            "payload": {"target": target, "status": status}
        }
        self._send_safe(packet)

    def block_user(self, blocked_username):
        if blocked_username not in self.blocked_users:
            self.blocked_users.append(blocked_username)
        
        # Yerel veritabanına kaydet
        if hasattr(self, 'block_dao') and self.block_dao:
            my_username = self.user_data.get("username") if self.user_data else "me"
            self.block_dao.save(CachedBlock(blocker=my_username, blocked=blocked_username))
            
        packet = {"action": "BLOCK_USER", "payload": {"blocked_username": blocked_username}}
        self._send_safe(packet)

    def delete_message(self, msg_id, target):
        packet = {"action": "DELETE_MSG", "payload": {"msg_id": msg_id, "target": target}}
        self._send_safe(packet)

    def get_history(self, target):
        last_time = "1970-01-01 00:00:00"
        if self.message_dao:
            last_time = self.message_dao.get_latest_timestamp(target)
            
        packet = {"action": "GET_HISTORY", "payload": {"target": target, "after_timestamp": last_time}}
        self._send_safe(packet)

    def clear_history(self, target):
        # Sunucuya silme komutu göndermiyoruz (Kişisel temizlik için)
        # packet = {"action": "CLEAR_HISTORY", "payload": {"target": target}}
        # self._send_safe(packet)
        
        # Sadece yerelde temizle
        if self.message_dao:
            if target.startswith("group_"):
                try:
                    gid = int(target.split("_")[1])
                    self.message_dao.delete_chat(group_id=gid)
                except: pass
            else:
                self.message_dao.delete_chat(chat_partner=target)

    def edit_message(self, msg_id, target, new_content):
        packet = {"action": "EDIT_MSG", "payload": {"msg_id": msg_id, "target": target, "content": new_content}}
        self._send_safe(packet)

    def create_group(self, group_name, members, avatar=None):
        packet = {
            "action": "CREATE_GROUP",
            "payload": {
                "group": {"group_name": group_name, "avatar": avatar},
                "members": members
            }
        }
        self._send_safe(packet)

    def update_group_avatar(self, group_id, avatar_str):
        packet = {"action": "UPDATE_GROUP_AVATAR", "payload": {"group_id": group_id, "avatar": avatar_str}}
        self._send_safe(packet)

    def delete_group(self, group_id):
        packet = {"action": "DELETE_GROUP", "payload": {"group_id": group_id}}
        self._send_safe(packet)

    def add_group_member(self, group_id, username):
        packet = {"action": "ADD_GROUP_MEMBER", "payload": {"group_id": group_id, "username": username}}
        self._send_safe(packet)

    def remove_group_member(self, group_id, username):
        packet = {"action": "REMOVE_GROUP_MEMBER", "payload": {"group_id": group_id, "username": username}}
        self._send_safe(packet)

    def make_group_admin(self, group_id, username):
        packet = {"action": "MAKE_ADMIN", "payload": {"group_id": group_id, "username": username}}
        self._send_safe(packet)

    def send_receipt(self, target_username, msg_id, status):
        packet = {
            "action": "RECEIPT",
            "payload": {"msg_id": msg_id, "status": status, "target": target_username}
        }
        self._send_safe(packet)

    def send_message(self, target_username, text, file_path="", msg_id=None, message_type="TEXT", extra_data=None):
        import os, base64
        packet = {
            "action": "SEND_MSG",
            "payload": {
                "target_ip": target_username,
                "content": text,
                "msg_id": msg_id or str(time.time()),
                "message_type": message_type,
                "reply_to_id": extra_data.get("reply_to_id") if isinstance(extra_data, dict) else None,
                "is_forwarded": extra_data.get("is_forwarded", 0) if isinstance(extra_data, dict) else 0
            }
        }
        
        # Eğer target_username group_ ile başlıyorsa group_id set et
        if target_username and target_username.startswith("group_"):
            packet["payload"]["group_id"] = int(target_username.split("_")[1])
            packet["payload"]["target_ip"] = None
        
        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, "rb") as f:
                    file_data = f.read()
                
                # Eğer dosya yerel olarak şifrelenmişse (indirilenler klasöründeyse), gönderirken şifresini çöz
                if self.local_enc and "downloads" in file_path.lower():
                    try:
                        file_data = self.local_enc.decrypt(file_data)
                    except:
                        pass # Şifreli değilse veya hata olursa orijinali gönder
                        
                packet["payload"]["file_data"] = base64.b64encode(file_data).decode('utf-8')
                packet["payload"]["file_name"] = os.path.basename(file_path)
            except Exception as e:
                print(f"[CLIENT] Dosya okuma/çözme hatası: {e}")

        # Mesajı gönder
        success = self._send_safe(packet)
        
        # Önbelleğe kaydet (Local-First için kritik)
        if self.message_dao:
            try:
                # Grup mu yoksa özel mesaj mı kesinleştirelim
                payload = packet["payload"]
                m_id = str(payload.get("msg_id"))
                
                # target_username 'group_123' formatındaysa g_id al, değilse r_user al
                if target_username and target_username.startswith("group_"):
                    try:
                        g_id = int(target_username.split("_")[1])
                    except: g_id = None
                    r_user = None
                else:
                    g_id = None
                    r_user = target_username

                cached_msg = CachedMessage(
                    message_id=m_id,
                    sender=self.user_data.get("username") if self.user_data else "Siz",
                    receiver=r_user,
                    group_id=g_id,
                    message_type=message_type,
                    content=text,
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                    is_me=1,
                    local_path=file_path,
                    is_sent=1 if success else 0,
                    status="server_received" if success else "pending",
                    reply_to_id=payload.get("reply_to_id")
                )
                self.message_dao.save(cached_msg)
            except Exception as e:
                print(f"[CACHE] send_message kayit hatasi: {e}")
            
        if not success:
            print(f"[CLIENT] Mesaj gönderilemedi, çevrimdışı önbelleğe alındı: {packet['payload']['msg_id']}")
            # PendingMessages tablosuna da ekle (Kullanıcı isteği: her tablo dolsun)
            if hasattr(self, 'pending_dao') and self.pending_dao:
                p_msg = PendingMessage(
                    temp_id=None,
                    sender=self.user_data.get("username") if self.user_data else "me",
                    receiver=target_username if not (target_username and target_username.startswith("group_")) else None,
                    group_id=packet["payload"].get("group_id"),
                    message_type=message_type,
                    content=text
                )
                self.pending_dao.save(p_msg)

    def resend_pending_messages(self):
        """Çevrimdışıyken gönderilemeyen mesajları tekrar göndermeyi dener."""
        if not self.running or not self.message_dao: return
        
        pending = self.message_dao.get_pending_messages()
        if not pending: return
        
        print(f"[CLIENT] {len(pending)} adet bekleyen mesaj gönderiliyor...")
        for msg in pending:
            # Her mesaj için uygun target belirle
            target = msg.receiver if msg.receiver else f"group_{msg.group_id}"
            
            # send_message'ı tekrar çağırmak yerine direkt paketi hazırlayıp gönderelim
            # çünkü send_message zaten save() çağırıyor (sonsuz döngü olmasın)
            import base64, os
            packet = {
                "action": "SEND_MSG",
                "payload": {
                    "target_ip": msg.receiver,
                    "content": msg.content,
                    "msg_id": msg.message_id,
                    "message_type": msg.message_type,
                    "timestamp": msg.timestamp,
                    "group_id": msg.group_id
                }
            }
            
            if msg.local_path and os.path.exists(msg.local_path):
                try:
                    with open(msg.local_path, "rb") as f:
                        packet["payload"]["file_data"] = base64.b64encode(f.read()).decode('utf-8')
                        packet["payload"]["file_name"] = os.path.basename(msg.local_path)
                except: pass
                
            if self._send_safe(packet):
                self.message_dao.mark_as_sent(msg.message_id)
                # Eğer başarıyla gönderildiyse PendingMessages tablosundan da temizle
                if hasattr(self, 'pending_dao') and self.pending_dao:
                    # Not: PendingMessages tablosunda mesaj_id yerine temp_id var, 
                    # eşleştirmek için içeriğe bakabiliriz veya basitlik için tümünü temizleyebiliriz.
                    # Şimdilik ana mantık is_sent üzerinden yürüdüğü için burayı opsiyonel bırakıyoruz.
                    pass
                target = msg.receiver if msg.receiver else f"group_{msg.group_id}"
                self.receipt_received.emit(msg.message_id, "server_received", target)
                time.sleep(0.1)  # Sunucuyu yormayalim

    def unblock_user(self, username):
        if username in self.blocked_users:
            self.blocked_users.remove(username)
            
        # Yerel veritabanından sil
        if hasattr(self, 'block_dao') and self.block_dao:
            my_username = self.user_data.get("username") if self.user_data else "me"
            self.block_dao.delete(my_username, username)
            
        packet = {"action": "UNBLOCK_USER", "payload": {"blocked_username": username}}
        self._send_safe(packet)

    def _receive_loop(self):
        import codecs
        decoder = codecs.getincrementaldecoder('utf-8')(errors='ignore')
        buffer = ""
        while self.running:
            try:
                raw_data = self.sock.recv(65536)
                if not raw_data: break
                
                buffer += decoder.decode(raw_data)
                while True:
                    buffer = buffer.lstrip()
                    if not buffer: break
                    try:
                        packet, index = json.JSONDecoder().raw_decode(buffer)
                        buffer = buffer[index:].lstrip()
                        self._handle_packet(packet)
                    except json.JSONDecodeError:
                        break
                    except Exception as e:
                        print(f"[CLIENT] Paket işleme hatası: {e}")
                        break
            except Exception as e:
                print(f"[CLIENT] Alım hatası: {e}")
                break
        
        self.running = False
        self.server_lost.emit("Bağlantı koptu veya sunucu yanıt vermiyor.")

    def _handle_packet(self, packet):
        action = packet.get("action")
        payload = packet.get("payload")
        if action != "PONG":
            print(f"[CLIENT] Paket işleniyor: {action}")

        if action == "USER_LIST_UPDATE":
            # İstemciye tüm kullanıcı bilgilerini (online/offline, lastseen) ilet
            self.known_users = payload
            for user_info in payload:
                username = user_info.get("username")
                if self.user_data and str(username).strip().lower() == str(self.user_data.get('username', '')).strip().lower(): 
                    continue
                
                self.peer_found.emit({
                    "username": username,
                    "first_name": username,
                    "ip": username,
                    "avatar": user_info.get("avatar", "👤"),
                    "is_online": user_info.get("is_online"),
                    "lastseen": user_info.get("lastseen")
                })
                
                # Yerel veritabanına kaydet
                if hasattr(self, 'user_dao') and self.user_dao:
                    self.user_dao.save(CachedUser(
                        username=username, 
                        last_seen=user_info.get("lastseen"),
                        avatar=user_info.get("avatar", "👤")
                    ))

        elif action == "KEY_RESPONSE":
            import base64
            encrypted_key = base64.b64decode(payload.get("encrypted_key"))
            self.enc_manager.decrypt_fernet_key(encrypted_key)
            print("[CLIENT] Şifreleme anahtarı başarıyla kuruldu.")
            return

        elif action == "RESPONSE":
            status = payload.get("status")
            message = payload.get("message") or ""
            data = payload.get("data")
            # 'data' alan\u0131 sadece login'de dolu gelir; Kay\u0131t yan\u0131t\u0131nda None/bo\u015f gelir
            if data is not None or "Giriş" in message:
                self.login_response.emit(status == "SUCCESS", message, data or {})
            else:
                self.register_response.emit(status == "SUCCESS", message)

        elif action == "BLOCKED_LIST":
            self.blocked_users = payload
            self.blocked_list_updated.emit(self.blocked_users)
            # Yerel veritabanına kaydet
            if hasattr(self, 'block_dao') and self.block_dao:
                # Önce listeyi temizle (sunucudan gelen tam liste olduğu varsayımıyla)
                # Not: CachedBlockDAO'da clear_all yoksa eklememiz gerekebilir veya tek tek silebiliriz.
                # Basitlik için sadece ekliyoruz.
                my_username = self.user_data.get("username") if self.user_data else "me"
                for blocked in payload:
                    self.block_dao.save(CachedBlock(blocker=my_username, blocked=blocked))

        elif action == "ERROR":
            message = payload.get("message")
            self.error_received.emit(message)

        elif action == "RECEIVE_MSG":
            sender = payload.get("sender")
            content = payload.get("content")
            msg_id = str(payload.get("msg_id"))
            message_type = payload.get("message_type", "TEXT")
            file_name = payload.get("file_name")
            file_data = payload.get("file_data")
            save_path = ""
            
            if file_data:
                import base64, os
                download_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "downloads")
                
                try:
                    os.makedirs(download_dir, exist_ok=True)
                    
                    # Basit boyut kontrolü (~50MB)
                    estimated_size = len(file_data) * 0.75
                    if estimated_size > 50 * 1024 * 1024:
                        print(f"[CLIENT] Dosya çok büyük ({estimated_size/1024/1024:.2f} MB). Kaydedilmedi.")
                        save_path = ""
                    else:
                        save_path = os.path.join(download_dir, file_name)
                        if os.path.exists(save_path):
                            name, ext = os.path.splitext(file_name)
                            save_path = os.path.join(download_dir, f"{name}_{int(time.time())}{ext}")
                            
                        raw_bytes = base64.b64decode(file_data)
                        # DOSYAYI ŞİFRELEYEREK KAYDET
                        if self.local_enc:
                            raw_bytes = self.local_enc.encrypt(raw_bytes)
                            
                        with open(save_path, "wb") as f:
                            f.write(raw_bytes)
                            
                        if not os.path.exists(save_path) or os.path.getsize(save_path) == 0:
                            raise IOError("Dosya sıfır bayt olarak kaydedildi.")
                            
                        print(f"[CLIENT] Dosya başarıyla kaydedildi: {save_path}")
                except IOError as e:
                    print(f"[CLIENT] Dosya diske yazılamadı: {e}")
                    save_path = ""
                except Exception as e:
                    print(f"[CLIENT] Beklenmeyen dosya kaydetme hatası: {e}")
                    save_path = ""
            
            # Target determines where the message will be displayed in the UI
            target = f"group_{payload.get('group_id')}" if payload.get('group_id') else sender
            
            extra_data = {
                "reply_to_id": payload.get("reply_to_id"),
                "is_forwarded": payload.get("is_forwarded"),
                "is_edited": payload.get("is_edited"),
                "sender": sender
            }
            
            self.message_received.emit(target, content, save_path, msg_id, message_type, extra_data)
            
            # Önbelleğe kaydet
            if self.message_dao:
                try:
                    my_username = self.user_data.get("username") if self.user_data else None
                    # group_id'yi mutlaka integer'a çevir (DB tutarlılığı için)
                    g_id = payload.get("group_id")
                    if g_id:
                        try: g_id = int(g_id)
                        except: pass
                    
                    cached_msg = CachedMessage(
                        message_id=msg_id,
                        sender=sender,
                        receiver=my_username if not g_id else None,
                        group_id=g_id,
                        message_type=message_type,
                        content=content,
                        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                        is_me=0,
                        local_path=save_path if save_path else None,
                        reply_to_id=payload.get("reply_to_id")
                    )
                    self.message_dao.save(cached_msg)
                except Exception as e:
                    print(f"[CLIENT] Alınan mesaj önbelleğe yazılamadı: {e}")
            
            # Alındı onayı gönder (2 Tik için)
            ack = {
                "action": "RECEIPT",
                "payload": {"msg_id": msg_id, "status": "peer_received", "target": sender}
            }
            self._send_safe(ack)

        elif action == "RECEIPT":
            msg_id = str(payload.get("msg_id"))
            status = payload.get("status")
            target = payload.get("target")
            print(f"[CLIENT] Receipt Received: msg_id={msg_id}, status={status}, target={target}")
            self.receipt_received.emit(msg_id, status, target)
            if self.message_dao:
                self.message_dao.update_status(msg_id, status)
            if hasattr(self, 'receipt_dao') and self.receipt_dao:
                import time
                self.receipt_dao.save(CachedReceipt(message_id=msg_id, username=target, status=status, timestamp=time.strftime("%Y-%m-%d %H:%M:%S")))
        elif action == "DELETE_MSG":
            msg_id = payload.get("msg_id")
            self.message_deleted.emit(msg_id)
            if self.message_dao:
                self.message_dao.delete_message(msg_id)
        elif action == "EDIT_MSG":
            msg_id = payload.get("msg_id")
            content = payload.get("content")
            self.message_edited.emit(msg_id, content)
            if self.message_dao:
                self.message_dao.update_message_content(msg_id, content)
        elif action == "GROUP_LIST_UPDATE":
            self.known_groups = payload
            self.group_list_updated.emit(payload)
            # Yerel veritabanına kaydet
            if self.group_dao:
                for g in payload:
                    cached_g = CachedGroup(
                        group_id=g['group_id'],
                        group_name=g['group_name'],
                        created_by=g.get('created_by'),
                        created_at=g.get('created_at'),
                        is_admin=1 if g.get('is_admin') else 0,
                        avatar=g.get('avatar', '👥')
                    )
                    self.group_dao.save(cached_g)
        elif action == "TYPING_STATUS":
            self.typing_status_received.emit(payload.get("sender"), payload.get("target"), payload.get("status"))

        elif action == "HISTORY_RES":
            target = payload.get("target")
            messages = payload.get("messages", [])
            self.history_received.emit(target, messages)
            
            # Geçmişi önbelleğe kaydet/güncelle
            if self.message_dao:
                my_username = self.user_data.get("username") if self.user_data else None
                for m in messages:
                    is_me = 1 if m.get('sender') == my_username else 0
                    g_id = m.get('group_id')
                    if g_id:
                        try: g_id = int(g_id)
                        except: pass
                    
                    cached_msg = CachedMessage(
                        message_id=str(m.get('msg_id')),
                        sender=m.get('sender'),
                        receiver=m.get('receiver') if not g_id else None,
                        group_id=g_id,
                        message_type=m.get('message_type', 'TEXT'),
                        content=m.get('content'),
                        timestamp=m.get('timestamp'),
                        is_me=is_me,
                        local_path=m.get('file_path'),
                        status=m.get('status'),
                        reply_to_id=m.get('reply_to_id')
                    )
                    self.message_dao.save(cached_msg)

        elif action == "SHUTDOWN":
            print("[CLIENT] Sunucu kapandı!")
            self.running = False
            self.server_lost.emit("Sunucu yöneticisi tarafından kapatıldı.")

    def stop(self):
        self.running = False
        if self.sock:
            try: self.sock.close()
            except: pass
