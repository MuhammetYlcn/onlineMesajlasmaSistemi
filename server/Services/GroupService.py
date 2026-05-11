class GroupService:
    def __init__(self, server):
        self.server = server

    def handle_create_group(self, sock, payload):
        group_data = payload.get("group")
        members = payload.get("members")
        sender = self.server.client_info.get(sock)
        
        from common.models.Group import Group
        from common.models.GroupMember import GroupMember
        
        new_group = Group(group_name=group_data.get("group_name"), created_by=sender, avatar=group_data.get("avatar"))
        self.server.group_dao.create_group(new_group)
        
        res = self.server.db_manager.fetch_one("SELECT MAX(group_id) as last_id FROM Groups")
        group_id = res['last_id']
        
        all_members = list(set(members + [sender]))
        for m in all_members:
            is_admin = 1 if m == sender else 0
            self.server.group_member_dao.add_member(GroupMember(group_id=group_id, username=m, is_admin=is_admin))
        
        for m in all_members:
            m_sock = self.server.clients.get(m)
            if m_sock:
                self.broadcast_group_list(m, m_sock)

    def handle_update_group_avatar(self, sock, payload):
        group_id = payload.get("group_id")
        avatar = payload.get("avatar")
        self.server.group_dao.update_group_avatar(group_id, avatar)
        self.broadcast_group_info_to_members(group_id)

    def handle_add_group_member(self, sock, payload):
        group_id = payload.get("group_id")
        username = payload.get("username")
        from common.models.GroupMember import GroupMember
        self.server.group_member_dao.add_member(GroupMember(group_id=group_id, username=username, is_admin=0))
        self.broadcast_group_info_to_members(group_id)

    def handle_remove_group_member(self, sock, payload):
        group_id = payload.get("group_id")
        username = payload.get("username")
        all_members = self.server.group_member_dao.get_group_members(group_id)
        self.server.group_member_dao.remove_member(group_id, username)
        
        m_sock = self.server.clients.get(username)
        if m_sock: self.broadcast_group_list(username, m_sock)
        
        for m in all_members:
            if m.username != username:
                m_sock = self.server.clients.get(m.username)
                if m_sock: self.broadcast_group_list(m.username, m_sock)

    def handle_make_admin(self, sock, payload):
        group_id = payload.get("group_id")
        username = payload.get("username")
        self.server.group_member_dao.update_admin_status(group_id, username, 1)
        self.broadcast_group_info_to_members(group_id)

    def handle_delete_group(self, sock, payload):
        group_id = payload.get("group_id")
        sender = self.server.client_info.get(sock)
        if self.server.group_member_dao.is_user_admin(group_id, sender):
            members = self.server.group_member_dao.get_group_members(group_id)
            self.server.db_manager.execute("DELETE FROM Group_Members WHERE group_id = ?", (group_id,))
            self.server.group_dao.delete_group(group_id)
            for m in members:
                m_sock = self.server.clients.get(m.username)
                if m_sock:
                    self.broadcast_group_list(m.username, m_sock)

    def broadcast_group_list(self, username, sock):
        with self.server.lock:
            group_ids = self.server.group_member_dao.get_user_groups(username)
            groups = []
            for gid in group_ids:
                g = self.server.group_dao.get_group_by_id(gid)
                if g:
                    members = self.server.group_member_dao.get_group_members(gid)
                    g_dict = g.to_dict() if hasattr(g, 'to_dict') else g.__dict__.copy()
                    m_list = []
                    # Create a copy of clients to avoid dict modification errors
                    current_clients = list(self.server.clients.keys())
                    for m in members:
                        m_dict = m.to_dict() if hasattr(m, 'to_dict') else m.__dict__.copy()
                        m_dict['is_online'] = any(m.username.lower() == c.lower() for c in current_clients)
                        m_list.append(m_dict)
                    g_dict['members'] = m_list
                    groups.append(g_dict)
            
            packet = {"action": "GROUP_LIST_UPDATE", "payload": groups}
            self.server._send_packet(sock, packet)

    def broadcast_group_info_to_members(self, group_id):
        members = self.server.group_member_dao.get_group_members(group_id)
        for m in members:
            m_sock = self.server.clients.get(m.username)
            if m_sock:
                self.broadcast_group_list(m.username, m_sock)
