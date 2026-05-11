from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QSplitter
from PyQt6.QtCore import Qt

from .SidebarWidget import SidebarWidget
from .ChatWidget import ChatWidget
from .ProfileDialog import ProfileDialog

class MainWindow(QMainWindow):
    def __init__(self, user_data, local_enc=None, message_dao=None):
        super().__init__()
        self.current_user = user_data # Kullanıcının adı, soyadı falan
        self.local_enc = local_enc
        self.message_dao = message_dao
        
        # Arayüz isminde kullanıcının adı yazsın
        self.setWindowTitle(f"LAN Sohbet - {self.current_user.get('first_name', '')}")
        self.resize(1100, 750)

        central_widget = QWidget()
        central_widget.setObjectName("MainBackground")
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.sidebar = SidebarWidget()
        self.sidebar.set_my_avatar(self.current_user.get('avatar', '👤'))
        self.chat_view = ChatWidget(local_enc=self.local_enc, message_dao=getattr(self, 'message_dao', None))

        self.splitter.addWidget(self.sidebar)
        self.splitter.addWidget(self.chat_view)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 7)
        main_layout.addWidget(self.splitter)

        # Arkaplan Rengini Uygula (Kayıtlıysa, değilse varsayılan saydam siyah)
        default_color = self.current_user.get("bg_color", "transparent")
        self.chat_view.set_custom_background(default_color)

        # --------------------- ARAYÜZ SİNYALLERİ ---------------------
        self.sidebar.contact_selected.connect(self.on_contact_selected)
        self.sidebar.profile_clicked.connect(self.open_profile_settings)

    def open_profile_settings(self, lan_service=None):
        """Profil ikonuna basıldığında ayarlar dialogunu açar"""
        old_avatar = self.current_user.get("avatar")
        dialog = ProfileDialog(self.current_user)
        if dialog.exec():
            # Profil güncellendikten sonra
            new_avatar = self.current_user.get("avatar")
            if new_avatar != old_avatar and lan_service:
                lan_service.update_avatar(new_avatar)
                self.sidebar.set_my_avatar(new_avatar)
                # "Siz" satırını güncelle
                self.sidebar.add_lan_contact("Siz", self.current_user['username'], new_avatar)
            
            new_color = self.current_user.get("bg_color", "transparent")
            self.chat_view.set_custom_background(new_color)
            self.setWindowTitle(f"LAN Sohbet - {self.current_user.get('first_name', '')}")

    def on_contact_selected(self, contact_name, contact_avatar, contact_ip):
        """Sol taraftan biri seçildiğinde sohbeti ona yöneltir"""
        is_blocked = False
        if hasattr(self, 'lan_service') and contact_ip in getattr(self.lan_service, 'blocked_users', []):
            is_blocked = True
            
        is_kicked = False
        member_list = None
        if contact_ip.startswith("group_"):
            if hasattr(self, 'current_groups'):
                gid = int(contact_ip.split("_")[1])
                g_info = self.current_groups.get(gid)
                if g_info:
                    member_list = g_info.get('members')
                else:
                    is_kicked = True
                    
        for i in range(self.sidebar.contact_list.count()):
            item = self.sidebar.contact_list.item(i)
            data = item.data(Qt.ItemDataRole.UserRole)
            if data and data[2] == contact_ip:
                is_online = data[3] if len(data) > 3 else False
                lastseen = data[4] if len(data) > 4 else None
                self.chat_view.set_chat_target(contact_name, contact_avatar, contact_ip, is_online, lastseen, member_list, is_kicked, is_blocked)
                return
        
        self.chat_view.set_chat_target(contact_name, contact_avatar, contact_ip, False, None, member_list, is_kicked, is_blocked)
