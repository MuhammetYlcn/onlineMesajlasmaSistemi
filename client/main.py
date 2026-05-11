import sys
import os
import ctypes
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("LANChat.v1")
except:
    pass
import time

# İstemci kendi dizinindeki modülleri kullanır
client_root = os.path.dirname(os.path.abspath(__file__))
if client_root not in sys.path:
    sys.path.insert(0, client_root)

from PyQt6.QtWidgets import QApplication, QMessageBox, QLineEdit, QInputDialog
from PyQt6.QtCore import Qt
from ui.LoginWindow import LoginWindow
from ui.MainWindow import MainWindow
from services.LANService import LANService
from cache.db_connection import DBConnection
from cache.DAO.LocaleSettingsDAO import LocaleSettingsDAO
from cache.DAO.CachedMessageDAO import CachedMessageDAO
from cache.DAO.CachedUserDAO import CachedUserDAO
from cache.DAO.CachedGroupDAO import CachedGroupDAO
from cache.DAO.CachedBlockDAO import CachedBlockDAO
from cache.DAO.CachedReceiptDAO import CachedReceiptDAO
from cache.DAO.PendingMessageDAO import PendingMessageDAO
from models.CachedUser import CachedUser
from models.CachedGroup import CachedGroup
from models.CachedBlock import CachedBlock
from models.CachedReceipt import CachedReceipt

def load_stylesheet(app_instance):
    style_path = os.path.join(os.path.dirname(__file__), "resources", "StyleSheet.qss")
    if os.path.exists(style_path):
        with open(style_path, "r", encoding="utf-8") as f:
            app_instance.setStyleSheet(f.read())

def main():
    app = QApplication(sys.argv)
    load_stylesheet(app)

    # Veritabanı Hazırlığı
    cache_dir = os.path.join(os.path.dirname(__file__), "cache", "localdata")
    os.makedirs(cache_dir, exist_ok=True)
    db_path = os.path.join(cache_dir, "cache.db")
    db_conn = DBConnection(db_path)
    
    # Şema Düzeltme (message_id INTEGER -> TEXT)
    try:
        # Önce tablonun olup olmadığını kontrol edelim
        table_exists = db_conn.fetch_one("SELECT name FROM sqlite_master WHERE type='table' AND name='CachedMessages'")
        if table_exists:
            # Sütunları tek tek kontrol et ve eksikse ekle (Daha sağlam yöntem)
            cols = [c['name'] for c in db_conn.fetch_all("PRAGMA table_info(CachedMessages)")]
            if 'status' not in cols:
                db_conn.execute("ALTER TABLE CachedMessages ADD COLUMN status TEXT")
                print("[CLIENT] CachedMessages tablosuna status sütunu eklendi.")
            if 'reply_to_id' not in cols:
                db_conn.execute("ALTER TABLE CachedMessages ADD COLUMN reply_to_id TEXT")
                print("[CLIENT] CachedMessages tablosuna reply_to_id sütunu eklendi.")
        else:
            # Tablo hiç yoksa direkt oluştur (Typo düzeltilmiş şema)
            db_conn.execute("CREATE TABLE IF NOT EXISTS CachedMessages (message_id TEXT PRIMARY KEY, sender TEXT, receiver TEXT, group_id INTEGER, message_type TEXT, content TEXT, timestamp TEXT, is_me INTEGER, local_path TEXT, is_read INTEGER DEFAULT 0, is_sent INTEGER DEFAULT 1, status TEXT, reply_to_id TEXT)")
    except Exception as e:
        print(f"[CLIENT] Veritabanı şema güncelleme hatası: {e}")

    # Veritabanı Tablolarını Başlatma
    db_conn.execute("""
        CREATE TABLE IF NOT EXISTS LocaleSettings (
            setting_id INTEGER PRIMARY KEY,
            encryption_key TEXT,
            remember_me INTEGER,
            saved_username TEXT
        )
    """)
    db_conn.execute("""
        CREATE TABLE IF NOT EXISTS CachedBlocks (
            blocker TEXT,
            blocked TEXT,
            PRIMARY KEY (blocker, blocked)
        )
    """)
    db_conn.execute("""
        CREATE TABLE IF NOT EXISTS CachedGroups (
            group_id INTEGER PRIMARY KEY,
            group_name TEXT,
            created_by TEXT,
            created_at TEXT,
            is_admin INTEGER,
            avatar TEXT
        )
    """)
    try:
        db_conn.execute("ALTER TABLE CachedGroups ADD COLUMN avatar TEXT")
    except: pass
    db_conn.execute("""
        CREATE TABLE IF NOT EXISTS CachedUsers (
            username TEXT PRIMARY KEY,
            last_seen TEXT,
            avatar TEXT
        )
    """)
    try:
        db_conn.execute("ALTER TABLE CachedUsers ADD COLUMN avatar TEXT")
    except: pass
    db_conn.execute("""
        CREATE TABLE IF NOT EXISTS CachedReceipts (
            message_id TEXT,
            username TEXT,
            status TEXT,
            timestamp TEXT,
            PRIMARY KEY (message_id, username)
        )
    """)
    db_conn.execute("""
        CREATE TABLE IF NOT EXISTS PendingMessages (
            temp_id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            receiver TEXT,
            group_id INTEGER,
            message_type TEXT,
            content TEXT
        )
    """)

    # Yerel Şifreleme (Cache için)
    from security.LocalEncryption import LocalEncryption
    local_enc = LocalEncryption()
    
    settings_dao = LocaleSettingsDAO(db_conn)
    message_dao = CachedMessageDAO(db_conn)
    user_dao = CachedUserDAO(db_conn)
    group_dao = CachedGroupDAO(db_conn)
    block_dao = CachedBlockDAO(db_conn)
    receipt_dao = CachedReceiptDAO(db_conn)
    pending_dao = PendingMessageDAO(db_conn)
    
    # DAO'lara yerel şifreleyiciyi verelim
    settings_dao.enc_manager = local_enc
    message_dao.enc_manager = local_enc
    group_dao.enc_manager = local_enc
    
    lan_service = LANService(
        message_dao=message_dao, 
        group_dao=group_dao,
        local_enc=local_enc
    )
    # LANService içinde diğer DAO'ları da manuel ekleyelim (init'te hepsi yoksa)
    lan_service.user_dao = user_dao
    lan_service.block_dao = block_dao
    lan_service.receipt_dao = receipt_dao
    lan_service.pending_dao = pending_dao

    # 1. Sunucuyu bul
    from PyQt6.QtCore import QEventLoop, QTimer
    loop = QEventLoop()
    found_ip = []
    def on_server_found(ip):
        found_ip.append(ip)
        loop.quit()
        
    lan_service.start_discovery(on_server_found)
    # 10 saniye sonra loop'u kapat
    QTimer.singleShot(10000, loop.quit)
    loop.exec()
    
    if not found_ip:
        # Manuel IP Girişi Fallback
        ip, ok = QInputDialog.getText(None, "Sunucu Bulunamadı", "Sunucu otomatik bulunamadı.\nLütfen Sunucu IP adresini girin:", QLineEdit.EchoMode.Normal, "127.0.0.1")
        if ok and ip:
            if not lan_service.connect_to_server(ip):
                QMessageBox.critical(None, "Hata", f"Sunucuya ({ip}) bağlanılamadı!")
                sys.exit(1)
        else:
            sys.exit(0)
    else:
        import time
        time.sleep(0.5)
        if not lan_service.connect_to_server(found_ip[0]):
            QMessageBox.critical(None, "Hata", f"Sunucuya ({found_ip[0]}) bağlanılamadı!")
            sys.exit(1)

    # 2. Giriş Ekranı
    login_screen = LoginWindow(lan_service, settings_dao)
    current_user_data = None
    
    def on_login_success(user_dict):
        nonlocal current_user_data
        current_user_data = user_dict
        lan_service.user_data = user_dict
        if block_dao:
            blocked = block_dao.get_all()
            lan_service.blocked_users = [b.blocked for b in blocked]
        # Girişten kısa süre sonra bekleyen mesajları gönder
        QTimer.singleShot(2000, lan_service.resend_pending_messages)
        
    login_screen.login_successful.connect(on_login_success)
    
    if login_screen.exec() == 0 or current_user_data is None:
        sys.exit(0)
    
    from PyQt6.QtWidgets import QSystemTrayIcon
    
    # 3. Ana Pencere
    window = MainWindow(current_user_data, local_enc=local_enc, message_dao=message_dao)
    window.lan_service = lan_service

    window.tray_icon = QSystemTrayIcon(window)
    window.tray_icon.setIcon(window.style().standardIcon(window.style().StandardPixmap.SP_MessageBoxInformation))
    window.tray_icon.show()
    
    # Kendine mesaj atabilmek için sidebar'a "Siz" ekle
    window.sidebar.add_lan_contact("Siz", current_user_data['username'], current_user_data.get('avatar', "👤"))

    # Sinyalleri Bağla
    def on_peer_found(peer_info):
        if not peer_info or not isinstance(peer_info, dict): return
        username = peer_info.get("username")
        if not username: return
        
        is_online = peer_info.get("is_online", False)
        lastseen = peer_info.get("lastseen")
        
        # Kendimiz ise ismini "Siz" yap ve durumu gizle
        is_me = (username == current_user_data['username'])
        display_name = "Siz" if is_me else username
        
        window.sidebar.add_lan_contact(
            display_name,
            username, 
            peer_info.get("avatar", "👤"),
            is_online=is_online if not is_me else False,
            lastseen=lastseen if not is_me else None
        )
        
        # Eğer şu an bu kişiyle konuşuyorsak, tepedeki barı da güncelle
        current_chat = str(window.chat_view._current_chat_ip or "").strip().lower()
        if current_chat == str(username).strip().lower():
            if is_me:
                status = ""
            else:
                status = "çevrimiçi" if is_online else f"son görülme: {lastseen}" if lastseen else "çevrimdışı"
                
            window.chat_view.chat_status.setText(status)
            
            # Profil fotoğrafını da güncelle
            from ui.ChatWidget import set_avatar_on_label
            set_avatar_on_label(window.chat_view.target_avatar, peer_info.get("avatar", "👤"))
            window.chat_view.chat_title.setText(display_name)
    
    lan_service.peer_found.connect(on_peer_found)
    
    # Kaçırılmış olabilecek (Login esnasında gelmiş) kullanıcıları ekle
    if hasattr(lan_service, "known_users"):
        for user_info in lan_service.known_users:
            on_peer_found(user_info)
    
    try:
        window.sidebar.profile_clicked.disconnect() 
    except:
        pass
    window.sidebar.profile_clicked.connect(lambda: window.open_profile_settings(lan_service))
    
    # Bloklama İsteği
    def on_block_requested(username):
        reply = QMessageBox.question(window, "Kullanıcıyı Engelle", f"{username} kullanıcısını engellemek istediğinize emin misiniz?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            lan_service.block_user(username)
            QMessageBox.information(window, "Başarılı", f"{username} engellendi.")
    
    window.sidebar.block_requested.connect(on_block_requested)
    
    def on_unblock_requested(username):
        reply = QMessageBox.question(window, "Engeli Kaldır", f"{username} kullanıcısının engelini kaldırmak istediğinize emin misiniz?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            lan_service.unblock_user(username)
            QMessageBox.information(window, "Başarılı", f"{username} engeli kaldırıldı.")

    # chat_view'in engellemesini de buna bağlamıştık ama toggle etmek için chat_view de değiştirilebilir
    window.chat_view.block_requested.connect(on_block_requested)
    window.chat_view.unblock_requested.connect(on_unblock_requested)

    # Grup İşlemleri
    def on_create_group():
        if hasattr(lan_service, "known_users") and isinstance(lan_service.known_users, list):
            all_users = [u['username'] for u in lan_service.known_users if isinstance(u, dict) and 'username' in u]
        else:
            all_users = []
            for i in range(window.sidebar.contact_list.count()):
                data = window.sidebar.contact_list.item(i).data(Qt.ItemDataRole.UserRole)
                if data and not data[2].startswith("group_") and data[2] != "Siz":
                    all_users.append(data[2])
        
        from ui.GroupDialog import GroupDialog
        dialog = GroupDialog(all_users, current_user_data['username'], lan_service=lan_service)
        if dialog.exec():
            data = dialog.get_data()
            lan_service.create_group(data['group_name'], data['members'], data.get('avatar'))

    window.sidebar.create_group_requested.connect(on_create_group)

    # Grup Listesi Güncelleme
    window.current_groups = {} # {group_id: group_dict}
    def on_groups_updated(groups):
        window.current_groups = {g['group_id']: g for g in groups}
        window.sidebar.update_groups(groups)
        
        # Eğer aktif sohbet bir grupsa ve güncellendiyse başlığı güncelle
        curr = window.chat_view._current_chat_ip
        if curr and curr.startswith("group_"):
            gid = int(curr.split("_")[1])
            if gid in window.current_groups:
                g_info = window.current_groups[gid]
                window.chat_view.chat_title.setText(g_info['group_name'])
                window.chat_view.chat_status.setText(f"{len(g_info['members'])} üye, {sum(1 for m in g_info['members'] if m.get('is_online'))} çevrimiçi")
                
                from ui.ChatWidget import set_avatar_on_label
                set_avatar_on_label(window.chat_view.target_avatar, g_info.get('avatar', '👥'))
            else:
                # Grup silinmiş veya çıkarılmışız
                window.chat_view.chat_status.setText("Gruptan çıkarıldınız veya grup silindi")
                window.chat_view.input_area.setEnabled(False)

    lan_service.group_list_updated.connect(on_groups_updated)

    # YEREL VERİTABANINDAN YÜKLE (Local-First)
    if user_dao:
        cached_users = user_dao.get_all()
        for u in cached_users:
            on_peer_found({
                "username": u.username,
                "first_name": u.username,
                "ip": u.username,
                "avatar": u.avatar or "👤",
                "is_online": False,
                "lastseen": u.last_seen
            })
            
    if group_dao:
        cached_groups = group_dao.get_all_my_groups()
        groups_payload = []
        for g in cached_groups:
            groups_payload.append({
                "group_id": g.group_id,
                "group_name": g.group_name,
                "avatar": g.avatar or "👥",
                "created_by": g.created_by,
                "created_at": g.created_at,
                "is_admin": g.is_admin,
                "members": [] # Üyeler sunucudan gelecek
            })
        if groups_payload:
            on_groups_updated(groups_payload)

    def on_typing_status_received(sender, target, status):
        curr_chat = str(window.chat_view._current_chat_ip or "").strip().lower()
        if curr_chat == str(target).strip().lower():
            if status:
                text = f"{sender} {status}" if target.startswith("group_") else status
                window.chat_view.chat_status.setText(text)
            else:
                if target.startswith("group_"):
                    gid = int(target.split("_")[1])
                    if gid in window.current_groups:
                        g_info = window.current_groups[gid]
                        window.chat_view.chat_status.setText(f"{len(g_info['members'])} üye, {sum(1 for m in g_info['members'] if m.get('is_online'))} çevrimiçi")
                else:
                    for i in range(window.sidebar.contact_list.count()):
                        data = window.sidebar.contact_list.item(i).data(Qt.ItemDataRole.UserRole)
                        if data and str(data[2]).strip().lower() == str(target).strip().lower():
                            is_online = data[3] if len(data) > 3 else False
                            lastseen = data[4] if len(data) > 4 else None
                            if data[0] == "Siz":
                                status_text = ""
                            else:
                                status_text = "çevrimiçi" if is_online else f"son görülme: {lastseen}" if lastseen else "çevrimdışı"
                            window.chat_view.chat_status.setText(status_text)
                            break

    lan_service.typing_status_received.connect(on_typing_status_received)

    if hasattr(lan_service, "known_groups"):
        on_groups_updated(lan_service.known_groups)

    # Mesaj Düzenleme (UI -> Servis)
    def on_ui_message_edit(msg_id, new_content, target):
        lan_service.edit_message(msg_id, target, new_content)

    window.chat_view.message_edited.connect(on_ui_message_edit)

    # Mesaj Düzenleme (Servis -> UI)
    def on_remote_message_edited(msg_id, content):
        if msg_id in window.chat_view.bubbles:
            window.chat_view.bubbles[msg_id].update_text(content)

    lan_service.message_edited.connect(on_remote_message_edited)

    # Mesaj İletme (Forward)
    def on_forward_requested(msg_id, source_target):
        # Mesajı bul
        if msg_id not in window.chat_view.last_msgs_map: return
        sender, text, file_path, msg_type = window.chat_view.last_msgs_map[msg_id]
        
        # Eğer file_path sadece bir isimse (indirilenler klasöründeyse), tam yolu oluştur
        if file_path and not os.path.isabs(file_path):
            download_dir = os.path.join(os.getcwd(), "resources", "downloads")
            file_path = os.path.join(download_dir, file_path)
        
        # Hedef seç
        all_contacts = []
        for i in range(window.sidebar.contact_list.count()):
            data = window.sidebar.contact_list.item(i).data(Qt.ItemDataRole.UserRole)
            if data: 
                all_contacts.append(data)
            
        from PyQt6.QtWidgets import QDialog, QListWidget, QVBoxLayout, QPushButton
        f_dialog = QDialog(window)
        f_dialog.setWindowTitle("Mesajı İlet")
        f_dialog.setMinimumWidth(300)
        f_layout = QVBoxLayout(f_dialog)
        list_w = QListWidget()
        for c in all_contacts:
            list_w.addItem(f"{c[0]}") # Etiketleri kaldırdık
        f_layout.addWidget(list_w)
        btn_f = QPushButton("İlet")
        btn_f.setStyleSheet("background-color: #00a884; color: white; padding: 10px; font-weight: bold;")
        f_layout.addWidget(btn_f)
        
        def do_forward():
            sel = list_w.currentRow()
            if sel >= 0:
                target_data = all_contacts[sel]
                target_id = target_data[2] # username veya group_123 formatı
                new_msg_id = str(time.time())
                extra = {"is_forwarded": 1}
                
                # Eğer hedefe iletilen bir grupsa, extra içine group_id'yi ekle
                if isinstance(target_id, str) and target_id.startswith("group_"):
                    try:
                        extra["group_id"] = int(target_id.split("_")[1])
                    except: pass
                
                # 1. Mesajı Sunucuya Gönder
                lan_service.send_message(target_id, text, file_path, new_msg_id, msg_type, extra)
                
                # 2. Arayüzü Güncelle
                if window.chat_view._current_chat_ip == target_id:
                    window.chat_view.add_message(
                        text=text,
                        is_sender=True,
                        file_path=file_path,
                        msg_id=new_msg_id,
                        sender_username=current_user_data['username'],
                        message_type=msg_type,
                        extra_data=extra
                    )
                
                f_dialog.accept()
        
        btn_f.clicked.connect(do_forward)
        f_dialog.exec()

    window.chat_view.forward_requested.connect(on_forward_requested)

    # Mesaj Silme İsteği (Arayüzden tetiklenen)
    def on_ui_message_delete(msg_id, target):
        lan_service.delete_message(msg_id, target)
        window.chat_view.remove_single_message(msg_id)

    window.chat_view.message_deleted.connect(on_ui_message_delete)

    # Mesaj Silme Bilgisi (Sunucudan gelen)
    def on_remote_message_deleted(msg_id):
        window.chat_view.remove_single_message(msg_id)

    lan_service.message_deleted.connect(on_remote_message_deleted)

    def on_message_received(target, text, file_path, msg_id, message_type, extra_data):
        # Eğer bu mesajı zaten biz gönderdiysek tekrar ekleme
        if msg_id in window.chat_view.bubbles:
            return
            
        import winsound
        try: winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
        except: pass
        
        # Sadece aktif sohbete aitse ekle
        curr_chat = str(window.chat_view._current_chat_ip or "").strip().lower()
        if curr_chat == str(target).strip().lower():
            # Grupta gönderen kişinin adını gösterelim, target (group_1) değil
            real_sender = (extra_data or {}).get("sender") or target
            window.chat_view.add_message(text, is_sender=False, file_path=file_path, msg_id=msg_id, sender_username=real_sender, message_type=message_type, extra_data=extra_data)
            
            # Aktif sohbet ise 'seen' gönder
            if msg_id:
                lan_service.send_receipt(target, msg_id, "seen")
        else:
            # Aktif sohbet değilse peer_received gönder (kişiye ulaştı)
            if msg_id:
                lan_service.send_receipt(target, msg_id, "peer_received")
            
            sender_name = target
            for i in range(window.sidebar.contact_list.count()):
                data = window.sidebar.contact_list.item(i).data(Qt.ItemDataRole.UserRole)
                if data and str(data[2]).strip().lower() == str(target).strip().lower():
                    sender_name = data[0]
                    break
            
            window.tray_icon.showMessage("Yeni Mesaj", f"{sender_name} size yeni bir mesaj gönderdi.", QSystemTrayIcon.MessageIcon.Information, 3000)
            window.sidebar.increment_unread(target)
            print(f"[CLIENT] Aktif olmayan sohbetten mesaj: {target} -> {text}")

    lan_service.message_received.connect(on_message_received)
    lan_service.receipt_received.connect(window.chat_view.update_message_status)
    lan_service.server_lost.connect(lambda msg: (QMessageBox.warning(window, "Bağlantı Kesildi", f"Sunucu kapandı!\nHata: {msg}"), window.close()))
    lan_service.error_received.connect(lambda msg: QMessageBox.warning(window, "Hata", msg))

    def on_history_received(target, messages):
        curr_chat = str(window.chat_view._current_chat_ip or "").strip().lower()
        if curr_chat == str(target).strip().lower():
            for msg in messages:
                is_me = msg['sender'] == current_user_data['username']
                # Mesajları tek tek ekle
                window.chat_view.add_message(
                    text=msg['content'],
                    is_sender=is_me,
                    file_path=msg.get('file_path'),
                    msg_id=msg.get('msg_id'),
                    sender_username=msg['sender'],
                    message_type=msg.get('message_type', 'TEXT'),
                    extra_data={
                        "reply_to_id": msg.get("reply_to_id"),
                        "is_forwarded": msg.get("is_forwarded"),
                        "is_edited": msg.get("is_edited"),
                        "status": msg.get("status")
                    }
                )
                
                # Geçmişten gelen ve henüz 'seen' olmayan mesajlar için 'seen' gönder
                if not is_me and msg.get('status') != 'seen':
                    msg_id = msg.get('msg_id')
                    if msg_id:
                        lan_service.send_receipt(target, msg_id, "seen")
            
            # Geçmiş yüklendi, progress bar'ı gizle
            window.chat_view.show_progress(False)

    lan_service.history_received.connect(on_history_received)
    window.chat_view.history_requested.connect(lan_service.get_history)

    def on_user_sent_message(text, target_username, file_path="", msg_id=None, message_type="TEXT", extra_data=None):
        if text == "[SEEN]":
            lan_service.send_receipt(target_username, msg_id, "seen")
        else:
            # Medya gönderimi için yükleme göstergesi (Popup yerine Progress Bar)
            is_media = file_path or message_type in ["IMAGE", "VIDEO", "VOICE", "FILE"]
            if is_media:
                window.chat_view.show_progress(True)
                QApplication.processEvents()
                
            try:
                lan_service.send_message(target_username, text, file_path, msg_id, message_type, extra_data)
            finally:
                if is_media:
                    window.chat_view.show_progress(False)

    window.chat_view.message_sent.connect(on_user_sent_message)

    def on_typing_status_changed(target, status):
        lan_service.send_typing_status(target, status)

    window.chat_view.typing_status_changed.connect(on_typing_status_changed)
    window.chat_view.clear_history_requested.connect(lan_service.clear_history)

    # Kapanışta temizlik
    def cleanup():
        lan_service.stop()

    app.aboutToQuit.connect(cleanup)
    
    # Sidebar öğe tıklandığında (Grup yönetimi için ekstra)
    def on_sidebar_item_clicked(name, avatar, target_id):
        window.sidebar.clear_unread(target_id)
        if target_id.startswith("group_"):
            # Sağ üstteki ⋮ butonunu grup yönetimi için kullanabiliriz veya Sidebar'a sağ tık ekleyebiliriz
            # Şimdilik SidebarWidget'a grup için sağ tık ekleyelim (SidebarWidget.py'de zaten var)
            pass

    window.sidebar.contact_selected.connect(on_sidebar_item_clicked)
    
    def on_group_settings_requested(gid):
        group_info = window.current_groups.get(gid)
        if group_info:
            from ui.GroupDialog import GroupDialog
            if hasattr(lan_service, "known_users") and isinstance(lan_service.known_users, list):
                all_users = [u['username'] for u in lan_service.known_users if isinstance(u, dict) and 'username' in u]
            else:
                all_users = [window.sidebar.contact_list.item(i).data(Qt.ItemDataRole.UserRole)[2] for i in range(window.sidebar.contact_list.count()) if not window.sidebar.contact_list.item(i).data(Qt.ItemDataRole.UserRole)[2].startswith("group_")]
            dialog = GroupDialog(all_users, current_user_data['username'], group_info=group_info, lan_service=lan_service)
            dialog.exec()

    window.chat_view.group_settings_requested.connect(on_group_settings_requested)
    
    # Sidebar sağ tık menüsü
    def on_sidebar_context_menu(pos):
        item = window.sidebar.contact_list.itemAt(pos)
        if not item: return
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data: return
        
        target_id = data[2]
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(window)
        menu.setStyleSheet("QMenu { background-color: #202C33; color: white; border: 1px solid #2A3942; } QMenu::item { padding: 8px 25px; } QMenu::item:selected { background-color: #374248; }")
        
        if target_id.startswith("group_"):
            action_clear = menu.addAction("🗑️ Sohbeti Temizle")
            action_manage = menu.addAction("👥 Grup Ayarları")
            action = menu.exec(window.sidebar.contact_list.mapToGlobal(pos))
            
            if action == action_clear:
                window.chat_view.clear_chat()
            elif action == action_manage:
                on_group_settings_requested(int(target_id.split("_")[1]))
        else:
            action_clear = menu.addAction("🗑️ Sohbeti Temizle")
            
            action_block = None
            action_unblock = None
            
            # Kendimizi engelleyemeyiz
            if target_id != current_user_data['username'] and target_id != "Siz":
                is_blocked = target_id in lan_service.blocked_users
                if is_blocked:
                    action_unblock = menu.addAction("🔓 Engeli Kaldır")
                else:
                    action_block = menu.addAction("🚫 Engelle")
                
            action = menu.exec(window.sidebar.contact_list.mapToGlobal(pos))
            
            if action == action_clear:
                window.chat_view.clear_chat()
            elif action_block and action == action_block:
                on_block_requested(target_id)
            elif action_unblock and action == action_unblock:
                on_unblock_requested(target_id)

    window.sidebar.contact_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    window.sidebar.contact_list.customContextMenuRequested.connect(on_sidebar_context_menu)

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
