class MessageService:
    def __init__(self, server):
        self.server = server

    def is_blocked(self, user1, user2):
        if not user1 or not user2 or user1 == user2:
            return False
        return self.server.block_dao.is_blocked(user1, user2)

    def handle_send_msg(self, sock, payload):
        sender = self.server.client_info.get(sock)
        if not sender: return
        
        # Add sender to payload for forwarding
        payload["sender"] = sender
        gid = payload.get("group_id")
        msg_id = str(payload.get("msg_id"))
        target_ip = payload.get("target_ip")
        message_type = payload.get("message_type", "TEXT")
        
        # Prepare targets and data outside of long-running operations
        target_socks = []
        
        with self.server.lock:
            # Initialize receipt tracking
            self.server.message_receipts[msg_id] = {
                "seen_by": set(),
                "received_by": set(),
                "sender": sender,
                "target": f"group_{gid}" if gid else target_ip
            }
            
            if gid:
                if not self.server.group_member_dao.is_member(gid, sender):
                    self._send_error(sock, msg_id, "Grup üyesi değilsiniz.")
                    return
                
                members = self.server.group_member_dao.get_group_members(gid)
                for member in members:
                    if member.username != sender:
                        t_sock = self.server.clients.get(member.username)
                        if t_sock:
                            target_socks.append(t_sock)
            else:
                if target_ip:
                    if self.is_blocked(sender, target_ip):
                        self._send_error(sock, msg_id, "Mesaj gönderilemedi: Engelleme durumu mevcut.")
                        return
                    
                    t_sock = None
                    for c_name, c_sock in self.server.clients.items():
                        if str(c_name).lower() == str(target_ip).lower():
                            t_sock = c_sock
                            break
                    if t_sock:
                        target_socks.append(t_sock)

        # 1. Forward message to targets (OUTSIDE lock)
        for t_sock in target_socks:
            self.server._send_packet(t_sock, {"action": "RECEIVE_MSG", "payload": payload})
        
        # 2. Save to Database (OUTSIDE lock)
        # For files, we store the data in the content field to make it persistent
        content_to_save = payload.get("content")
        if payload.get("file_data"):
            content_to_save = payload.get("file_data")
            
        from common.models.Message import Message
        msg_obj = Message(
            sender=sender,
            receiver=target_ip if not gid else None,
            group_id=gid,
            message_type=message_type,
            content=content_to_save,
            file_path=payload.get("file_name") or payload.get("file_path"),
            msg_id=msg_id,
            timestamp=payload.get("timestamp"),
            reply_to_id=payload.get("reply_to_id"),
            is_forwarded=payload.get("is_forwarded", 0)
        )
        self.server.message_dao.save_message(msg_obj)
        
        # 3. Send confirmation receipt to sender (OUTSIDE lock)
        resp = {
            "action": "RECEIPT",
            "payload": {
                "msg_id": msg_id, 
                "status": "server_received", 
                "target": target_ip or f"group_{gid}"
            }
        }
        self.server._send_packet(sock, resp)
        print(f"[SERVER] server_received sent for msg_id={msg_id} to {sender}")


    def _send_error(self, sock, msg_id, error_text):
        resp = {
            "action": "ERROR",
            "payload": {"msg_id": msg_id, "message": error_text}
        }
        self.server._send_packet(sock, resp)

    def handle_receipt(self, sock, payload):
        msg_id = str(payload.get("msg_id"))
        status = payload.get("status")
        user_who_sent_receipt = self.server.client_info.get(sock)
        if not user_who_sent_receipt: return
        
        with self.server.lock:
            rec = self.server.message_receipts.get(msg_id)
            if not rec:
                msg_data = self.server.message_dao.get_message_by_msg_id(msg_id)
                if msg_data:
                    rec = {
                        "seen_by": set(),
                        "received_by": set(),
                        "sender": msg_data.sender,
                        "target": f"group_{msg_data.group_id}" if msg_data.group_id else msg_data.receiver
                    }
                    self.server.message_receipts[msg_id] = rec
            
            if rec:
                from security.Hash import Hash
                h_uname = Hash.hash_deterministic(user_who_sent_receipt)
                print(f"[DEBUG] handle_receipt: msg_id={msg_id}, status={status}, user={user_who_sent_receipt}, h_uname={h_uname}")
                
                if status == "peer_received":
                    rec["received_by"].add(h_uname)
                elif status == "seen":
                    rec["seen_by"].add(h_uname)
                
                # Save to database to persist (using hashed username)
                try:
                    import time
                    try:
                        row = self.server.db_manager.fetch_one(
                            "SELECT status FROM MessagesReceipts WHERE msg_id = ? AND username = ?",
                            (msg_id, h_uname)
                        )
                        if row:
                            if row['status'] != 'seen' or status == 'seen':
                                self.server.db_manager.execute(
                                    "UPDATE MessagesReceipts SET status = ?, timestamp = ? WHERE msg_id = ? AND username = ?",
                                    (status, str(time.time()), msg_id, h_uname)
                                )
                                print(f"[DEBUG] Updated DB receipt: {msg_id} for {user_who_sent_receipt} -> {status}")
                        else:
                            self.server.db_manager.execute(
                                "INSERT INTO MessagesReceipts (msg_id, username, status, timestamp) VALUES (?, ?, ?, ?)",
                                (msg_id, h_uname, status, str(time.time()))
                            )
                            print(f"[DEBUG] Inserted DB receipt: {msg_id} for {user_who_sent_receipt} -> {status}")
                    except Exception as e:
                        print(f"[DEBUG] DB fallback check due to: {e}")
                        # Fallback for old schema if exists
                        row = self.server.db_manager.fetch_one(
                            "SELECT status FROM MessagesReceipts WHERE message_id = ? AND username = ?",
                            (msg_id, h_uname)
                        )
                        if row:
                            if row['status'] != 'seen' or status == 'seen':
                                self.server.db_manager.execute(
                                    "UPDATE MessagesReceipts SET status = ?, timestamp = ? WHERE message_id = ? AND username = ?",
                                    (status, str(time.time()), msg_id, h_uname)
                                )
                        else:
                            self.server.db_manager.execute(
                                "INSERT INTO MessagesReceipts (message_id, username, status, timestamp) VALUES (?, ?, ?, ?)",
                                (msg_id, h_uname, status, str(time.time()))
                            )
                except Exception as e:
                    print(f"Receipt DB error: {e}")
                    
                original_sender = rec["sender"]
                target = rec["target"]
                print(f"[DEBUG] Receipt routing: msg_id={msg_id}, sender={original_sender}, target={target}, status={status}")

                # Her durumda gönderene ilet (Grup veya Özel)
                sender_sock = self.server.clients.get(original_sender)
                
                # Grup için 'herkes gördü' mantığını da koruyalım
                if target.startswith("group_"):
                    from security.Hash import Hash
                    gid = int(target.split("_")[1])
                    members = self.server.group_member_dao.get_group_members(gid)
                    
                    other_members_hashes = [Hash.hash_deterministic(m.username) for m in members if m.username != original_sender]
                    has_everyone_received = all(mh in rec["received_by"] or mh in rec["seen_by"] for mh in other_members_hashes)
                    has_everyone_seen = all(mh in rec["seen_by"] for mh in other_members_hashes)
                    
                    if has_everyone_seen:
                        status = "seen"
                    elif has_everyone_received:
                        status = "peer_received"
                    # status remains as is otherwise (the one received from Bob)

        # Send to original sender (OUTSIDE lock)
        if sender_sock:
            print(f"[SERVER] Forwarding receipt to sender: {original_sender}, status={status}")
            self.server._send_packet(sender_sock, {"action": "RECEIPT", "payload": {"msg_id": msg_id, "status": status, "target": target}})
        else:
            print(f"[SERVER] Could not forward receipt: {original_sender} is offline.")



    def handle_delete_msg(self, sock, payload):
        msg_id = payload.get("msg_id")
        target = payload.get("target")
        self.server.message_dao.delete_message(msg_id)
        self.notify_message_update("DELETE_MSG", {"msg_id": msg_id}, target)

    def handle_edit_msg(self, sock, payload):
        msg_id = payload.get("msg_id")
        new_content = payload.get("content")
        target = payload.get("target")
        self.server.message_dao.update_message_content(msg_id, new_content)
        self.notify_message_update("EDIT_MSG", {"msg_id": msg_id, "content": new_content}, target)

    def handle_get_history(self, sock, payload):
        target = payload.get("target")
        after_ts = payload.get("after_timestamp", "1970-01-01 00:00:00")
        username = self.server.client_info.get(sock)
        
        history = []  # Başlangıç değeri: NameError'ı önler
        if target and username:
            if target.startswith("group_"):
                gid = int(target.split("_")[1])
                history = self.server.message_dao.get_group_chat_history(gid, after_timestamp=after_ts)
            else:
                history = self.server.message_dao.get_private_chat_history(username, target, after_timestamp=after_ts)
        
        messages_with_status = []
        for m in history:
            m_dict = m.__dict__.copy()
            if m.group_id:
                members = self.server.group_member_dao.get_group_members(m.group_id)
                other_members = [mem.username for mem in members if mem.username != m.sender]
                
                try:
                    seen_rows = self.server.db_manager.fetch_all(
                        "SELECT username FROM MessagesReceipts WHERE msg_id = ? AND status = 'seen'", (m.msg_id,)
                    )
                except Exception:
                    seen_rows = self.server.db_manager.fetch_all(
                        "SELECT username FROM MessagesReceipts WHERE message_id = ? AND status = 'seen'", (m.msg_id,)
                    )
                
                from security.Hash import Hash
                seen_users_hashes = [r['username'] for r in seen_rows]
                has_everyone_seen = all(Hash.hash_deterministic(mem) in seen_users_hashes for mem in other_members)
                
                try:
                    rec_rows = self.server.db_manager.fetch_all(
                        "SELECT username FROM MessagesReceipts WHERE msg_id = ? AND status IN ('seen', 'peer_received')", (m.msg_id,)
                    )
                except Exception:
                    rec_rows = self.server.db_manager.fetch_all(
                        "SELECT username FROM MessagesReceipts WHERE message_id = ? AND status IN ('seen', 'peer_received')", (m.msg_id,)
                    )
                rec_users_hashes = [r['username'] for r in rec_rows]
                has_everyone_received = all(Hash.hash_deterministic(mem) in rec_users_hashes for mem in other_members)
                
                if has_everyone_seen:
                    m_dict["status"] = "seen"
                elif has_everyone_received:
                    m_dict["status"] = "peer_received"
                else:
                    m_dict["status"] = "server_received"
            else:
                # Özel sohbet için
                try:
                    receipt_rows = self.server.db_manager.fetch_all(
                        "SELECT username, status FROM MessagesReceipts WHERE msg_id = ?", (m.msg_id,)
                    )
                except Exception:
                    receipt_rows = self.server.db_manager.fetch_all(
                        "SELECT username, status FROM MessagesReceipts WHERE message_id = ?", (m.msg_id,)
                    )
                
                # Sadece karşı tarafın (receiver) receipt'ine bakmamız yeterli ama 
                # basitlik için herhangi bir 'seen' varsa seen diyelim.
                statuses = [r['status'] for r in receipt_rows]
                if "seen" in statuses:
                    m_dict["status"] = "seen"
                elif "peer_received" in statuses:
                    m_dict["status"] = "peer_received"
                else:
                    m_dict["status"] = "server_received"
            
            messages_with_status.append(m_dict)

        resp = {
            "action": "HISTORY_RES",
            "payload": {"target": target, "messages": messages_with_status}
        }
        self.server._send_packet(sock, resp)

    def handle_clear_history(self, sock, payload):
        target = payload.get("target")
        username = self.server.client_info.get(sock)
        if not target or not username: return
        
        if target.startswith("group_"):
            gid = int(target.split("_")[1])
            self.server.message_dao.delete_group_history(gid)
        else:
            self.server.message_dao.delete_chat_history(username, target)
        
        # Don't notify others, usually Clear Chat is a local-ish action 
        # but since we store history on server, we delete it there too.
        # We could send a signal to others to clear their UI too if desired.
        pass

    def notify_message_update(self, action, payload, target):
        with self.server.lock:
            if target and target.startswith("group_"):
                group_id = int(target.split("_")[1])
                members = self.server.group_member_dao.get_group_members(group_id)
                for m in members:
                    m_sock = self.server.clients.get(m.username)
                    if m_sock:
                        self.server._send_packet(m_sock, {"action": action, "payload": payload})
            elif target:
                t_sock = self.server.clients.get(target)
                if t_sock:
                    self.server._send_packet(t_sock, {"action": action, "payload": payload})

    def push_pending_messages(self, username):
        """Kullanıcı login olduğunda almadığı mesajları gönderir."""
        pending = self.server.message_dao.get_pending_messages_for_user(username)
        if not pending: return
        
        print(f"[MESSAGE] Pushing {len(pending)} pending messages to {username}")
        sock = self.server.clients.get(username)
        if not sock: return
        
        for msg in pending:
            payload = msg.to_dict()
            
            # Fix for file messages: move data from 'content' back to 'file_data' 
            # and restore original content (filename) if it's a file/voice message.
            if msg.message_type in ["FILE", "VOICE", "IMAGE", "VIDEO"]:
                payload["file_data"] = msg.content
                payload["file_name"] = msg.file_path
                payload["content"] = "" # Usually file messages don't have text content in this project's current state
            
            if msg.group_id:
                # Grup mesajı ise target_ip yerine group_id kullanılır
                payload["target_ip"] = None
            else:
                payload["target_ip"] = username
            
            self.server._send_packet(sock, {"action": "RECEIVE_MSG", "payload": payload})

