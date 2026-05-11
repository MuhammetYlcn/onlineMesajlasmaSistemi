def create_packet(action, payload=None):
    """Tüm ağ paketlerinin temel iskeleti."""
    return {
        "action": action,
        "payload": payload
    }
def make_login_packet(username, password_hash):
    return create_packet("LOGIN", {"username": username, "password_hash": password_hash})

def make_register_packet(user_dto_dict):
    return create_packet("REGISTER", user_dto_dict)

# --- MESAJLAŞMA ---
def make_send_message_packet(message_dto_dict):
    return create_packet("SEND_MSG", message_dto_dict)

def make_receipt_packet(receipt_dto_dict):
    return create_packet("MSG_RECEIPT", receipt_dto_dict)

# --- GRUP YÖNETİMİ ---
def make_create_group_packet(group_dto_dict, members_list):
    return create_packet("CREATE_GROUP", {"group": group_dto_dict, "members": members_list})

def make_add_member_packet(group_id, username):
    return create_packet("ADD_GROUP_MEMBER", {"group_id": group_id, "username": username})

def make_remove_member_packet(group_id, username):
    return create_packet("REMOVE_GROUP_MEMBER", {"group_id": group_id, "username": username})

def make_update_group_name_packet(group_id, new_name):
    return create_packet("UPDATE_GROUP_NAME", {"group_id": group_id, "new_name": new_name})

# --- LİSTELEME VE SORGULAMA ---
def make_get_all_usernames_packet():
    """Yeni kayit kontrolü veya kullanici keşfi için."""
    return create_packet("GET_ALL_USERNAMES")

def make_get_user_groups_packet(username):
    """Kullanicinin üye olduğu gruplari çekmek için."""
    return create_packet("GET_USER_GROUPS", {"username": username})

def make_get_history_packet(target):
    """Sohbet geçmişini istemek için."""
    return create_packet("GET_HISTORY", {"target": target})


# --- GİZLİLİK VE GÜVENLİK ---

def make_block_user_packet(target_username):
    """Bir kullaniciyi engellemek için."""
    return create_packet("BLOCK_USER", {"target_username": target_username})

def make_unblock_user_packet(target_username):
    """Engeli kaldirmak için."""
    return create_packet("UNBLOCK_USER", {"target_username": target_username})

def make_get_blocked_list_packet():
    """Engellediğim kişilerin listesini görmek için."""
    return create_packet("GET_BLOCKED_LIST")

# --- SUNUCU CEVAP VE DURUM SİSTEMİ ---
def make_response_packet(status, message, data=None):
    """Sunucudan gelen standart yanit: SUCCESS/ERROR"""
    return create_packet("RESPONSE", {
        "status": status,
        "message": message,
        "data": data
    })

def make_shutdown_packet():
    """Sunucu kapandığında istemcilere gönderilir."""
    return create_packet("SHUTDOWN")

def make_user_list_packet(users_list):
    """Aktif kullanıcı listesini güncellemek için."""
    return create_packet("USER_LIST_UPDATE", users_list)