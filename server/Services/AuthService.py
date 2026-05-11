class AuthService:
    def __init__(self, server):
        self.server = server

    def handle_login(self, sock, payload):
        from common.packet_models import make_response_packet
        username = payload.get("username")
        password = payload.get("password_hash")
        print(f"[AUTH] Login attempt: {username}")
        
        try:
            user = self.server.user_dao.validate_login(username, password)
            if user:
                print(f"[AUTH] Login successful for: {username}")
                
                # Önemli: Eğer bu kullanıcı adı ile başka bir bağlantı varsa, onu temizleyelim
                # (Zombi bağlantıları önlemek için)
                with self.server.lock:
                    old_sock = self.server.clients.get(username)
                    if old_sock and old_sock != sock:
                        print(f"[AUTH] {username} için eski bağlantı (sock {id(old_sock)}) temizleniyor.")
                        # Eski socket'i client_info'dan da silelim ki remove_client tetiklendiğinde 
                        # yanlışlıkla yeni bağlantıyı etkilemesin
                        self.server.client_info.pop(old_sock, None)
                        try: old_sock.close()
                        except: pass
                    
                    self.server.clients[user.username] = sock
                    self.server.client_info[sock] = user.username
                
                resp = make_response_packet("SUCCESS", "Giriş başarılı", user.to_dict())
                self.server._send_packet(sock, resp)
                print(f"[AUTH] Response sent to: {username}")
                
                self.server.user_service.broadcast_user_list()
                print(f"[AUTH] User list broadcasted after login: {username}")
                
                self.server.user_service.send_blocked_list(sock, username)
                print(f"[AUTH] Blocked list sent to: {username}")
                
                # Çevrimdışı mesajları gönder
                self.server.message_service.push_pending_messages(username)
                print(f"[AUTH] Pending messages pushed for: {username}")
            else:

                print(f"[AUTH] Login failed (wrong credentials): {username}")
                resp = make_response_packet("ERROR", "Giriş başarısız: Hatalı kullanıcı adı veya şifre")
                self.server._send_packet(sock, resp)
        except Exception as e:
            print(f"[AUTH] Login error for {username}: {e}")
            import traceback
            traceback.print_exc()
            resp = make_response_packet("ERROR", f"Sunucu hatası: {str(e)}")
            self.server._send_packet(sock, resp)

    def handle_register(self, sock, payload):
        from common.packet_models import make_response_packet
        from common.models.User import User
        username = payload.get("username")
        print(f"[AUTH] Registration attempt: {username}")
        new_user = User(username=username, passwordhash=payload.get("passwordhash"))
        success = self.server.user_dao.register_user(new_user)
        if success:
            print(f"[AUTH] Registration successful for: {username}")
            resp = make_response_packet("SUCCESS", "Kayıt başarılı")
        else:
            print(f"[AUTH] Registration failed for: {username}")
            resp = make_response_packet("ERROR", "Kullanıcı zaten mevcut veya sunucu hatası")
        self.server._send_packet(sock, resp)

    def handle_ping(self, sock, payload):
        resp = {"action": "PONG", "payload": {"message": "ALIVE"}}
        self.server._send_packet(sock, resp)

