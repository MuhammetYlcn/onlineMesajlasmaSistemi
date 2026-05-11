import base64
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QListWidget, QListWidgetItem, QPushButton, QLabel, QMessageBox, QWidget, QFileDialog)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QImage, QPixmap

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
            label.setText("👥")
    else:
        label.setPixmap(QPixmap())
        label.setText("👥")

class MemberItemWidget(QWidget):
    def __init__(self, username, display_name, is_member, is_target_admin, is_me, am_i_admin, on_action):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        
        lbl = QLabel(display_name)
        lbl.setStyleSheet("color: white; font-weight: bold;" if is_member else "color: #8696A0;")
        layout.addWidget(lbl)
        
        layout.addStretch()
        
        if am_i_admin and not is_me:
            if is_member:
                if not is_target_admin:
                    btn_admin = QPushButton("⭐ Yönetici Yap")
                    btn_admin.setFixedSize(110, 28)
                    btn_admin.setStyleSheet("background-color: #005C4B; color: white; border-radius: 4px; font-size: 11px; border: none;")
                    btn_admin.clicked.connect(lambda: on_action("make_admin", username))
                    layout.addWidget(btn_admin)
                
                btn_remove = QPushButton("❌ Çıkar")
                btn_remove.setFixedSize(70, 28)
                btn_remove.setStyleSheet("background-color: #EA0038; color: white; border-radius: 4px; font-size: 11px; border: none;")
                btn_remove.clicked.connect(lambda: on_action("remove", username))
                layout.addWidget(btn_remove)
            else:
                btn_add = QPushButton("➕ Ekle")
                btn_add.setFixedSize(70, 28)
                btn_add.setStyleSheet("background-color: #00A884; color: white; border-radius: 4px; font-size: 11px; border: none;")
                btn_add.clicked.connect(lambda: on_action("add", username))
                layout.addWidget(btn_add)

class GroupDialog(QDialog):
    def __init__(self, all_users, current_user, group_info=None, parent=None, lan_service=None):
        super().__init__(parent)
        self.all_users = all_users # List of usernames
        self.current_user = current_user
        self.group_info = group_info # If editing existing group
        self.lan_service = lan_service
        self.selected_users = []
        self.avatar_str = group_info.get("avatar") if group_info else None
        
        self.setWindowTitle("Grup Oluştur" if not group_info else f"Grup: {group_info['group_name']}")
        self.setMinimumWidth(380)
        self.setStyleSheet("""
            QDialog { background-color: #202C33; color: white; } 
            QLabel { color: #E9EDEF; } 
            QLineEdit { background-color: #2A3942; color: white; border-radius: 5px; padding: 8px; border: 1px solid #3B4A54; } 
            QListWidget { background-color: #111B21; color: white; border: none; border-radius: 5px; padding: 5px; } 
            QPushButton { background-color: #00A884; color: white; border-radius: 5px; padding: 8px; font-weight: bold; border: none; }
            QPushButton:hover { background-color: #008F72; }
            QPushButton#DeleteBtn { background-color: #EA0038; }
            QPushButton#DeleteBtn:hover { background-color: #C30030; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Avatar Seçimi
        avatar_layout = QHBoxLayout()
        self.avatar_preview = QLabel("👥")
        self.avatar_preview.setFixedSize(60, 60)
        self.avatar_preview.setStyleSheet("background-color: #6a7175; border-radius: 30px; font-size: 24px;")
        self.avatar_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.btn_select_avatar = QPushButton("Fotoğraf Seç")
        self.btn_select_avatar.setFixedWidth(120)
        self.btn_select_avatar.clicked.connect(self.on_select_avatar)
        
        avatar_layout.addWidget(self.avatar_preview)
        avatar_layout.addWidget(self.btn_select_avatar)
        avatar_layout.addStretch()
        layout.addLayout(avatar_layout)
        
        if self.avatar_str:
            set_avatar_on_label(self.avatar_preview, self.avatar_str)
            
        # Grup Adı
        name_layout = QVBoxLayout()
        name_layout.addWidget(QLabel("Grup Adı:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Grup adını girin...")
        name_layout.addWidget(self.name_input)
        if group_info:
            self.name_input.setText(group_info['group_name'])
            i_am_admin = any(m['username'] == current_user and m['is_admin'] for m in group_info['members'])
            if not i_am_admin:
                self.name_input.setReadOnly(True)
                self.btn_select_avatar.setEnabled(False)
        layout.addLayout(name_layout)
        
        # Üyeler Listesi
        list_label = QLabel("Üyeler Seçin:" if not group_info else "Grup Üyeleri ve Kişiler:")
        layout.addWidget(list_label)
        
        self.user_list = QListWidget()
        self.refresh_user_list()
        layout.addWidget(self.user_list)

        if group_info:
            i_am_admin = any(m['username'] == current_user and m['is_admin'] for m in group_info['members'])
            if i_am_admin:
                self.btn_delete = QPushButton("🗑 Grubu Sil")
                self.btn_delete.setObjectName("DeleteBtn")
                self.btn_delete.clicked.connect(self.on_delete_group)
                layout.addWidget(self.btn_delete)
        
        self.btn_save = QPushButton("Oluştur" if not group_info else "Kapat")
        self.btn_save.clicked.connect(self.on_save)
        layout.addWidget(self.btn_save)

    def on_select_avatar(self):
        try:
            file_path, _ = QFileDialog.getOpenFileName(self, "Fotoğraf Seç", "", "Resim Dosyaları (*.png *.jpg *.jpeg *.bmp)")
            if file_path:
                from PyQt6.QtGui import QImage
                import base64
                import os
                image = QImage(file_path)
                if image.isNull():
                    QMessageBox.warning(self, "Hata", "Geçersiz görsel dosyası!")
                    return
                # Convert to base64
                with open(file_path, "rb") as f:
                    data = f.read()
                # If file is too large, optionally alert
                if len(data) > 1024 * 1024 * 2:
                    QMessageBox.warning(self, "Hata", "Görsel 2MB'den küçük olmalıdır!")
                    return
                # Get correct MIME type
                ext = os.path.splitext(file_path)[1].lower().replace(".", "")
                if ext not in ["png", "jpg", "jpeg", "bmp"]:
                    ext = "png"
                b64 = base64.b64encode(data).decode("utf-8")
                self.avatar_str = f"data:image/{ext};base64,{b64}"
                set_avatar_on_label(self.avatar_preview, self.avatar_str)
                
                # If editing, directly save to server!
                if self.group_info and self.lan_service:
                    self.lan_service.update_group_avatar(self.group_info['group_id'], self.avatar_str)
        except Exception as e:
            print(f"[CLIENT] Grup avatar seçme hatası: {e}")
            QMessageBox.warning(self, "Hata", f"Görsel yüklenirken bir hata oluştu: {str(e)}")

    def refresh_user_list(self):
        self.user_list.clear()
        if self.group_info:
            member_names = [m['username'] for m in self.group_info['members']]
            am_i_admin = any(m['username'] == self.current_user and m['is_admin'] for m in self.group_info['members'])
            
            for m in self.group_info['members']:
                role = " (Yönetici)" if m['is_admin'] else " (Üye)"
                display_name = f"👤 {m['username']}{role}"
                if m['username'] == self.current_user: display_name += " [Siz]"
                
                item = QListWidgetItem(self.user_list)
                item.setData(Qt.ItemDataRole.UserRole, m['username'])
                item.setSizeHint(QSize(0, 40))
                
                custom_widget = MemberItemWidget(
                    username=m['username'],
                    display_name=display_name,
                    is_member=True,
                    is_target_admin=m['is_admin'],
                    is_me=m['username'] == self.current_user,
                    am_i_admin=am_i_admin,
                    on_action=self.on_member_action
                )
                self.user_list.setItemWidget(item, custom_widget)
                
            for user in self.all_users:
                if user not in member_names and user != self.current_user:
                    item = QListWidgetItem(self.user_list)
                    item.setData(Qt.ItemDataRole.UserRole, user)
                    item.setSizeHint(QSize(0, 40))
                    
                    custom_widget = MemberItemWidget(
                        username=user,
                        display_name=f"➕ {user}",
                        is_member=False,
                        is_target_admin=False,
                        is_me=False,
                        am_i_admin=am_i_admin,
                        on_action=self.on_member_action
                    )
                    self.user_list.setItemWidget(item, custom_widget)
        else:
            for user in self.all_users:
                if user == self.current_user: continue
                item = QListWidgetItem(user)
                item.setData(Qt.ItemDataRole.UserRole, user)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.user_list.addItem(item)

    def on_member_action(self, action_type, username):
        if not self.lan_service: return
        
        if action_type == "make_admin":
            self.lan_service.make_group_admin(self.group_info['group_id'], username)
            self.close()
        elif action_type == "remove":
            self.lan_service.remove_group_member(self.group_info['group_id'], username)
            self.close()
        elif action_type == "add":
            self.lan_service.add_group_member(self.group_info['group_id'], username)
            self.close()

    def on_save(self):
        if not self.group_info:
            self.selected_users = []
            for i in range(self.user_list.count()):
                item = self.user_list.item(i)
                if item.checkState() == Qt.CheckState.Checked:
                    self.selected_users.append(item.data(Qt.ItemDataRole.UserRole))
            if not self.name_input.text().strip():
                QMessageBox.warning(self, "Hata", "Lütfen bir grup adı girin.")
                return
            if not self.selected_users:
                QMessageBox.warning(self, "Hata", "Lütfen en az bir üye seçin.")
                return
            self.accept()
        else:
            self.close()

    def on_delete_group(self):
        reply = QMessageBox.question(self, "Grubu Sil", "Bu grubu tamamen silmek istediğinize emin misiniz?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if self.lan_service:
                self.lan_service.delete_group(self.group_info['group_id'])
                self.accept()

    def get_data(self):
        return {"group_name": self.name_input.text().strip(), "members": self.selected_users, "avatar": getattr(self, "avatar_str", None)}
