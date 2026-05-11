import socket
import json
import threading
import time
from common.packet_models import make_response_packet, make_user_list_packet, make_shutdown_packet
from common.db_manager.db_connection import DBConnection
from DAO.UserDAO import UserDAO
from DAO.MessageDAO import MessageDAO
from DAO.GroupDAO import GroupDAO
from DAO.GroupMemberDAO import GroupMemberDAO
from common.models.Group import Group
from common.models.GroupMember import GroupMember
from common.models.Message import Message

class SocketServer:
    def _send_packet(self, sock, packet):
        """Thread-safe packet sending using per-socket locks."""
        try:
            data = json.dumps(packet).encode('utf-8')
            s_lock = None
            with self.lock:
                s_lock = self.client_locks.get(sock)
            
            if s_lock:
                with s_lock:
                    sock.sendall(data)
            else:
                # Fallback if lock doesn't exist for some reason
                sock.sendall(data)
        except Exception as e:
            # print(f"[DEBUG] Send error: {e}")
            pass

    def __init__(self, host='0.0.0.0', tcp_port=50005, udp_port=50006):
        self.host = host
        self.tcp_port = tcp_port
        self.udp_port = udp_port
        self.running = False
        
        # Veritabanı Hazırlığı
        import os
        project_root = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(project_root, "data", "database.db")
        self.db_manager = DBConnection(db_path)
        
        # Sadece kullanıcıları tut, diğer her şeyi temizle (Kullanıcı isteği)
        self._setup_tables()
        
        from DAO.BlockDAO import BlockDAO
        self.user_dao = UserDAO(self.db_manager)
        self.message_dao = MessageDAO(self.db_manager)
        self.group_dao = GroupDAO(self.db_manager)
        self.group_member_dao = GroupMemberDAO(self.db_manager)
        self.block_dao = BlockDAO(self.db_manager)
        
        # Şifreleme Yöneticisi
        from security.EncryptionManager import EncryptionManager
        from cryptography.fernet import Fernet
        self.enc_manager = EncryptionManager()
        master_key_path = os.path.join(project_root, "data", "master.key")
        if os.path.exists(master_key_path):
            with open(master_key_path, "rb") as f:
                self.enc_manager.set_fernet_key(f.read())
        else:
            os.makedirs(os.path.dirname(master_key_path), exist_ok=True)
            key = Fernet.generate_key()
            with open(master_key_path, "wb") as f:
                f.write(key)
            self.enc_manager.set_fernet_key(key)
        
        # DAO'lara enc_manager'ı verelim
        self.user_dao.enc_manager = self.enc_manager
        self.message_dao.enc_manager = self.enc_manager
        self.group_dao.enc_manager = self.enc_manager
        self.group_member_dao.enc_manager = self.enc_manager
        self.block_dao.enc_manager = self.enc_manager
        
        # Initialize Services
        from Services.AuthService import AuthService
        from Services.UserService import UserService
        from Services.MessageService import MessageService
        from Services.GroupService import GroupService
        
        self.auth_service = AuthService(self)
        self.user_service = UserService(self)
        self.message_service = MessageService(self)
        self.group_service = GroupService(self)
        
        self.clients = {} # {username: socket}
        self.client_info = {} # {socket: username}
        self.client_locks = {} # {socket: Lock}
        self.message_receipts = {} # {msg_id: {"seen_by": set(), "received_by": set(), "sender": username, "target": target}}
        try:
            rows = self.db_manager.fetch_all("SELECT * FROM MessagesReceipts")
            for r in rows:
                mid = r.get('msg_id') or r.get('message_id')
                uname = r.get('username')
                status = r.get('status')
                if mid and uname and status:
                    if mid not in self.message_receipts:
                        msg_data = self.message_dao.get_message_by_msg_id(mid)
                        if msg_data:
                            self.message_receipts[mid] = {
                                "seen_by": set(),
                                "received_by": set(),
                                "sender": msg_data.sender,
                                "target": f"group_{msg_data.group_id}" if msg_data.group_id else msg_data.receiver
                            }
                    if mid in self.message_receipts:
                        if status == "peer_received":
                            self.message_receipts[mid]["received_by"].add(uname)
                        elif status == "seen":
                            self.message_receipts[mid]["seen_by"].add(uname)
        except Exception as e:
            print(f"Loading receipts from DB error: {e}")
            
        self.lock = threading.RLock()

    def start(self):
        # 1. TCP Soketi Oluştur ve Bind Et
        try:
            self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_sock.bind((self.host, self.tcp_port))
            self.server_sock.listen(10)
            self.server_sock.settimeout(1.0)
            self.running = True
            print(f"[SERVER] TCP Sunucu {self.tcp_port} portunda başlatıldı.")
        except Exception as e:
            print(f"[SERVER] Başlatılamadı (Port kullanımda olabilir): {e}")
            return False

        # 2. UDP Broadcast (Keşif için)
        self.udp_thread = threading.Thread(target=self._udp_broadcast_loop, daemon=True)
        self.udp_thread.start()

        # 3. Ana Kabul Döngüsü
        self.accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.accept_thread.start()
        
        return True

    def _udp_broadcast_loop(self):
        """İstemcilerin sunucuyu otomatik bulabilmesi için UDP yayını yapar"""
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        broadcast_packet = json.dumps({
            "action": "SERVER_DISCOVERY",
            "payload": {
                "tcp_port": self.tcp_port,
                "server_name": "LAN Sohbet Sunucusu"
            }
        }).encode('utf-8')
        
        print(f"[SERVER] UDP Keşif yayını başlatıldı (Port: {self.udp_port})")
        while self.running:
            try:
                # Broadcast adresine (255.255.255.255) gönder
                udp_sock.sendto(broadcast_packet, ('<broadcast>', self.udp_port))
                time.sleep(2.0) # Her 2 saniyede bir yayınla
            except Exception as e:
                # print(f"[SERVER] UDP Yayın hatası: {e}")
                time.sleep(5.0)
        udp_sock.close()

    def _accept_loop(self):
        while self.running:
            try:
                client_sock, addr = self.server_sock.accept()
                with self.lock:
                    self.client_locks[client_sock] = threading.Lock()
                print(f"[SERVER] Yeni bağlantı: {addr}")
                threading.Thread(target=self._handle_client, args=(client_sock, addr), daemon=True).start()
            except socket.timeout:
                continue
            except:
                break



    def _setup_tables(self):
        # Tabloları oluştur (DROP TABLE kaldırıldı, böylece veriler korunur)
        
        self.db_manager.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                passwordhash TEXT NOT NULL,
                lastseen TEXT,
                avatar TEXT DEFAULT '👤'
            )
        """)
        self.db_manager.execute("""
            CREATE TABLE IF NOT EXISTS Messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT,
                receiver TEXT,
                group_id INTEGER,
                message_type TEXT,
                content TEXT,
                file_path TEXT,
                msg_id TEXT UNIQUE,
                timestamp TEXT,
                reply_to_id TEXT,
                is_forwarded INTEGER DEFAULT 0,
                is_edited INTEGER DEFAULT 0
            )
        """)
        self.db_manager.execute("""
            CREATE TABLE IF NOT EXISTS Groups (
                group_id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name TEXT,
                created_by TEXT,
                avatar TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        try:
            self.db_manager.execute("ALTER TABLE Groups ADD COLUMN avatar TEXT")
        except:
            pass
            
        self.db_manager.execute("""
            CREATE TABLE IF NOT EXISTS Group_Members (
                group_id INTEGER,
                username TEXT,
                is_admin INTEGER DEFAULT 0,
                is_kicked INTEGER DEFAULT 0,
                PRIMARY KEY (group_id, username)
            )
        """)
        try:
            self.db_manager.execute("ALTER TABLE Group_Members ADD COLUMN is_kicked INTEGER DEFAULT 0")
        except:
            pass
        self.db_manager.execute("""
            CREATE TABLE IF NOT EXISTS BlockedUsers (
                blocker TEXT,
                blocked TEXT,
                PRIMARY KEY (blocker, blocked)
            )
        """)
        self.db_manager.execute("""
            CREATE TABLE IF NOT EXISTS MessagesReceipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                msg_id TEXT,
                username TEXT,
                status TEXT,
                timestamp TEXT
            )
        """)
        try:
            self.db_manager.execute("ALTER TABLE MessagesReceipts ADD COLUMN msg_id TEXT")
        except:
            pass

    def _handle_client(self, sock, addr):
        import codecs
        decoder = codecs.getincrementaldecoder('utf-8')(errors='ignore')
        buffer = ""
        while self.running:
            try:
                raw_data = sock.recv(65536)
                if not raw_data:
                    break
                
                buffer += decoder.decode(raw_data)
                while True:
                    buffer = buffer.lstrip()
                    if not buffer: break
                    try:
                        packet, index = json.JSONDecoder().raw_decode(buffer)
                        buffer = buffer[index:].lstrip()
                        try:
                            self._process_packet(sock, packet)
                        except Exception as e:
                            print(f"[SERVER] Paket işleme hatası: {e}")
                            import traceback
                            traceback.print_exc()
                            # Hata olsa bile bağlantıyı koparma, devam et
                    except json.JSONDecodeError:
                        break
                    except Exception as e:
                        print(f"[SERVER] Tampon işleme hatası: {e}")
                        break
            except Exception as e:
                print(f"[SERVER] Bağlantı hatası ({addr}): {e}")
                break
        
        try:
            self.user_service.remove_client(sock)
        except Exception as e:
            print(f"[SERVER] İstemci ayrılma işlemi hatası: {e}")

    def _process_packet(self, sock, packet):
        action = packet.get("action")
        payload = packet.get("payload")
        print(f"[SERVER] Paket Alındı: {action}")

        if action == "GET_KEY":
            public_key_pem = payload.get("public_key")
            if public_key_pem:
                import base64
                encrypted_fernet_key = self.enc_manager.encrypt_fernet_key(self.enc_manager.fernet_key, public_key_pem.encode())
                resp = {
                    "action": "KEY_RESPONSE",
                    "payload": {
                        "encrypted_key": base64.b64encode(encrypted_fernet_key).decode()
                    }
                }
                self._send_packet(sock, resp)
            return

        if action == "PING":
            self.auth_service.handle_ping(sock, payload)
        elif action == "LOGIN":
            self.auth_service.handle_login(sock, payload)
        elif action == "REGISTER":
            self.auth_service.handle_register(sock, payload)
        elif action == "UPDATE_AVATAR":
            self.user_service.handle_update_avatar(sock, payload)
        elif action == "BLOCK_USER":
            self.user_service.handle_block_user(sock, payload)
        elif action == "UNBLOCK_USER":
            self.user_service.handle_unblock_user(sock, payload)
        elif action == "SEND_MSG":
            self.message_service.handle_send_msg(sock, payload)
        elif action == "RECEIPT":
            self.message_service.handle_receipt(sock, payload)
        elif action == "DELETE_MSG":
            self.message_service.handle_delete_msg(sock, payload)
        elif action == "EDIT_MSG":
            self.message_service.handle_edit_msg(sock, payload)
        elif action == "GET_HISTORY":
            self.message_service.handle_get_history(sock, payload)
        elif action == "CLEAR_HISTORY":
            self.message_service.handle_clear_history(sock, payload)
        elif action == "CREATE_GROUP":
            self.group_service.handle_create_group(sock, payload)
        elif action == "UPDATE_GROUP_AVATAR":
            self.group_service.handle_update_group_avatar(sock, payload)
        elif action == "ADD_GROUP_MEMBER":
            self.group_service.handle_add_group_member(sock, payload)
        elif action == "REMOVE_GROUP_MEMBER":
            self.group_service.handle_remove_group_member(sock, payload)
        elif action == "MAKE_ADMIN":
            self.group_service.handle_make_admin(sock, payload)
        elif action == "DELETE_GROUP":
            self.group_service.handle_delete_group(sock, payload)
        elif action == "TYPING_STATUS":
            sender = self.client_info.get(sock)
            target = payload.get("target")
            status_type = payload.get("status")
            if target and status_type is not None:
                if isinstance(target, str) and target.startswith("group_"):
                    try:
                        gid = int(target.split("_")[1])
                        members = self.group_member_dao.get_group_members(gid)
                        for m in members:
                            if m.username != sender:
                                t_sock = self.clients.get(m.username)
                                if t_sock:
                                    self._send_packet(t_sock, {"action": "TYPING_STATUS", "payload": {"sender": sender, "target": target, "status": status_type}})
                    except (ValueError, IndexError):
                        pass
                else:
                    t_sock = self.clients.get(target)
                    if t_sock:
                        self._send_packet(t_sock, {"action": "TYPING_STATUS", "payload": {"sender": sender, "target": sender, "status": status_type}})

    def stop(self):
        packet = make_shutdown_packet()
        with self.lock:
            for sock in list(self.clients.values()):
                self._send_packet(sock, packet)
                try: sock.close()
                except: pass
            self.clients.clear()
            self.client_info.clear()
            self.client_locks.clear()
        
        try:
            self.server_sock.close()
        except: pass

    def remove_client_lock(self, sock):
        with self.lock:
            self.client_locks.pop(sock, None)
