class UserService:
    def __init__(self, server):
        self.server = server

    def handle_update_avatar(self, sock, payload):
        new_avatar = payload.get("avatar")
        username = self.server.client_info.get(sock)
        if username:
            from security.Hash import Hash
            hashed_username = Hash.hash_deterministic(username)
            enc_avatar = self.server.user_dao.enc_manager.encrypt(new_avatar) if self.server.user_dao.enc_manager else new_avatar
            self.server.db_manager.execute("UPDATE Users SET avatar = ? WHERE username = ?", (enc_avatar, hashed_username))
            print(f"[SERVER] {username} profil fotoğrafını güncelledi.")
            self.broadcast_user_list()

    def handle_block_user(self, sock, payload):
        blocked_user = payload.get("blocked_username")
        blocker = self.server.client_info.get(sock)
        if blocker and blocked_user and blocker != blocked_user:
            from common.models.Block import Block
            self.server.block_dao.block_user(Block(blocker=blocker, blocked=blocked_user))
            print(f"[SERVER] {blocker}, {blocked_user} kullanıcısını engelledi.")
            self.send_blocked_list(sock, blocker)

    def handle_unblock_user(self, sock, payload):
        blocked_user = payload.get("blocked_username")
        blocker = self.server.client_info.get(sock)
        if blocker and blocked_user:
            self.server.block_dao.unblock_user(blocker, blocked_user)
            print(f"[SERVER] {blocker}, {blocked_user} engelini kaldırdı.")
            self.send_blocked_list(sock, blocker)

    def send_blocked_list(self, sock, blocker):
        blocked_rows = self.server.db_manager.fetch_all("SELECT blocked FROM BlockedUsers WHERE blocker = ?", (blocker,))
        blocked_list = [row["blocked"] for row in blocked_rows]
        self.server._send_packet(sock, {"action": "BLOCKED_LIST", "payload": blocked_list})

    def broadcast_user_list(self):
        all_users = self.server.user_dao.get_all_users_info()
        
        with self.server.lock:
            # Username'leri standartlaştırılmış (küçük harf ve temizlenmiş) bir set olarak al
            online_users_set = {str(o).strip().lower() for o in self.server.clients.keys()}
            clients_to_send = list(self.server.clients.items())

        user_list_payload = []
        for user in all_users:
            u_dict = dict(user)
            u_name = str(u_dict.get('username', '')).strip().lower()
            u_dict['is_online'] = u_name in online_users_set
            user_list_payload.append(u_dict)

        packet = {"action": "USER_LIST_UPDATE", "payload": user_list_payload}
        
        # Gönderim işlemini kilit dışında yapalım (performans ve deadlock önleme için)
        for username, sock in clients_to_send:
            try:
                self.server._send_packet(sock, packet)
                self.server.group_service.broadcast_group_list(username, sock)
            except:
                pass

    def remove_client(self, sock):
        username_to_broadcast = None
        with self.server.lock:
            username = self.server.client_info.pop(sock, None)
            if username:
                # Sadece eğer bu socket o kullanıcıya ait olan güncel socket ise sil
                # Karşılaştırmayı daha esnek yapalım (bazı durumlarda username objesi farklı gelebilir)
                current_sock = self.server.clients.get(username)
                if current_sock == sock:
                    self.server.clients.pop(username, None)
                    from datetime import datetime
                    self.server.user_dao.update_lastseen(username, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    print(f"[SERVER] {username} ayrıldı.")
                    username_to_broadcast = username
                else:
                    print(f"[SERVER] {username} için eski/geçersiz bir bağlantı temizlendi.")
            self.server.remove_client_lock(sock)
        
        # Sadece bir kullanıcı gerçekten ayrıldıysa veya login olduysa yayın yapmak daha mantıklı
        # Ancak discovery paketleri de burayı tetiklediği için, username varsa yayın yapalım.
        if username_to_broadcast:
            self.broadcast_user_list()
        
        try: 
            sock.close()
        except: 
            pass
