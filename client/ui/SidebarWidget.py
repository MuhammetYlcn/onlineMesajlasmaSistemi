from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QListWidget, QListWidgetItem, QLabel, QPushButton, QMenu)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint
from PyQt6.QtGui import QPixmap, QImage
import base64

def set_avatar_on_label(label, avatar_str):
    if avatar_str and avatar_str.startswith("data:image"):
        try:
            header, data = avatar_str.split(',', 1)
            img_data = base64.b64decode(data)
            image = QImage.fromData(img_data)
            pixmap = QPixmap.fromImage(image).scaled(label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            label.setPixmap(pixmap)
            label.setText("")
        except:
            label.setText("👤")
    else:
        label.setPixmap(QPixmap())
        label.setText(avatar_str if avatar_str else "👤")

class ClickableLabel(QLabel):
    clicked = pyqtSignal()
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

class ContactItemWidget(QWidget):
    def __init__(self, name, ip_address, avatar_str="👤", is_online=True, lastseen=None):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(45, 45)
        self.avatar_label.setStyleSheet("background-color: #6a7175; border-radius: 22px; font-size: 24px;")
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        set_avatar_on_label(self.avatar_label, avatar_str)
        layout.addWidget(self.avatar_label)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        name_label = QLabel(name)
        name_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #E9EDEF;")
        
        if name == "Siz":
            status_text = ""
            status_color = "transparent"
        else:
            status_text = "çevrimiçi" if is_online else f"son görülme: {lastseen}" if lastseen else "çevrimdışı"
            status_color = "#00A884" if is_online else "#8696A0"
        
        self.ip_label = QLabel(status_text)
        self.ip_label.setStyleSheet(f"font-size: 13px; color: {status_color};")
        
        info_layout.addWidget(name_label)
        info_layout.addWidget(self.ip_label)
        layout.addLayout(info_layout, stretch=1)
        
        self.unread_badge = QLabel()
        self.unread_badge.setFixedSize(24, 24)
        self.unread_badge.setStyleSheet("background-color: #00A884; color: white; border-radius: 12px; font-weight: bold; font-size: 12px;")
        self.unread_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.unread_badge.setVisible(False)
        layout.addWidget(self.unread_badge)
        
        # Sağ tık menüsünün listeye ulaşması için
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

    def set_unread_count(self, count):
        if count > 0:
            self.unread_badge.setText(str(count))
            self.unread_badge.setVisible(True)
        else:
            self.unread_badge.setVisible(False)

class SidebarWidget(QWidget):
    contact_selected = pyqtSignal(str, str, str) # name, avatar, target_id (ip or group_id)
    profile_clicked = pyqtSignal()
    create_group_requested = pyqtSignal()
    block_requested = pyqtSignal(str) # Username

    def __init__(self):
        super().__init__()
        self.setObjectName("Sidebar")
        self.setFixedWidth(350)
        self.unread_counts = {} # target_id -> count
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Üst Bar
        self.top_bar = QWidget()
        self.top_bar.setObjectName("SidebarHeader")
        self.top_bar.setFixedHeight(60)
        top_layout = QHBoxLayout(self.top_bar)
        
        self.my_avatar = ClickableLabel()
        self.my_avatar.setFixedSize(40, 40)
        self.my_avatar.setStyleSheet("background-color: #6a7175; border-radius: 20px; font-size: 20px;")
        self.my_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.my_avatar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.my_avatar.clicked.connect(self.profile_clicked.emit)
        top_layout.addWidget(self.my_avatar)
        
        hint = QLabel("Profil için tıkla")
        hint.setStyleSheet("color: #8696A0; font-size: 11px;")
        top_layout.addWidget(hint)
        self.btn_new_group = QPushButton("➕")
        self.btn_new_group.setFixedSize(40, 40)
        self.btn_new_group.setToolTip("Yeni Grup Oluştur")
        self.btn_new_group.setStyleSheet("QPushButton { background-color: transparent; border-radius: 20px; color: #8696A0; font-size: 20px; } QPushButton:hover { background-color: #374248; }")
        self.btn_new_group.clicked.connect(self.create_group_requested.emit)
        top_layout.addWidget(self.btn_new_group)
        
        top_layout.addStretch()
        main_layout.addWidget(self.top_bar)

        # Arama
        self.search_input = QLineEdit()
        self.search_input.setObjectName("SearchBar")
        self.search_input.setPlaceholderText("🔍 Kişileri aratın")
        self.search_input.textChanged.connect(self.filter_contacts)
        main_layout.addWidget(self.search_input)

        self.contact_list = QListWidget()
        self.contact_list.itemClicked.connect(self.on_item_clicked)
        main_layout.addWidget(self.contact_list)

    def update_groups(self, groups):
        """Mevcut gruplari guncelle."""
        for g in groups:
            self.add_group_contact(g['group_id'], g['group_name'], g.get('avatar', '👥'))

    def set_my_avatar(self, avatar_str):
        set_avatar_on_label(self.my_avatar, avatar_str)

    def add_lan_contact(self, name, ip, avatar="👤", is_online=True, lastseen=None):
        for i in range(self.contact_list.count()):
            item = self.contact_list.item(i)
            existing_data = item.data(Qt.ItemDataRole.UserRole)
            if existing_data and str(existing_data[2]).strip().lower() == str(ip).strip().lower():
                item.setData(Qt.ItemDataRole.UserRole, (name, avatar, ip, is_online, lastseen))
                custom_widget = ContactItemWidget(name, ip, avatar, is_online, lastseen)
                custom_widget.set_unread_count(self.unread_counts.get(ip, 0))
                self.contact_list.setItemWidget(item, custom_widget)
                return
                
        item = QListWidgetItem(self.contact_list)
        item.setSizeHint(QSize(350, 70))
        item.setData(Qt.ItemDataRole.UserRole, (name, avatar, ip, is_online, lastseen))
        custom_widget = ContactItemWidget(name, ip, avatar, is_online, lastseen)
        custom_widget.set_unread_count(self.unread_counts.get(ip, 0))
        self.contact_list.setItemWidget(item, custom_widget)

    def filter_contacts(self, text):
        for i in range(self.contact_list.count()):
            item = self.contact_list.item(i)
            name = item.data(Qt.ItemDataRole.UserRole)[0]
            item.setHidden(text.lower() not in name.lower())

    def add_group_contact(self, group_id, name, avatar="👥"):
        target_id = f"group_{group_id}"
        self.add_lan_contact(name, target_id, avatar)

    def on_item_clicked(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            self.contact_selected.emit(data[0], data[1], data[2])

    def increment_unread(self, target_id):
        self.unread_counts[target_id] = self.unread_counts.get(target_id, 0) + 1
        self._update_unread_badge(target_id)
        
    def clear_unread(self, target_id):
        if target_id in self.unread_counts and self.unread_counts[target_id] > 0:
            self.unread_counts[target_id] = 0
            self._update_unread_badge(target_id)
            
    def _update_unread_badge(self, target_id):
        for i in range(self.contact_list.count()):
            item = self.contact_list.item(i)
            data = item.data(Qt.ItemDataRole.UserRole)
            if data and data[2] == target_id:
                widget = self.contact_list.itemWidget(item)
                if widget and hasattr(widget, 'set_unread_count'):
                    widget.set_unread_count(self.unread_counts.get(target_id, 0))
                break
