from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QMessageBox, QFrame, QColorDialog, QFileDialog)
from PyQt6.QtCore import Qt, QBuffer, QIODevice
from PyQt6.QtGui import QPixmap, QImage
import socket
import base64

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

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

class ProfileDialog(QDialog):
    def __init__(self, current_user_dict):
        super().__init__()
        self.user_data = current_user_dict
        self.setWindowTitle("Kullanıcı Profili")
        self.setFixedSize(400, 750)
        self.setObjectName("MainBackground")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(8)
        
        title_lbl = QLabel("Kullanıcı Profili ve Ayarlar")
        title_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #E9EDEF;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_lbl)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #2A3942;")
        main_layout.addWidget(line)
        
        # Profil Resmi (Avatar)
        avatar_layout = QVBoxLayout()
        self.avatar_lbl = QLabel()
        self.avatar_lbl.setStyleSheet("background-color: #202C33; border-radius: 50px; font-size: 60px;")
        self.avatar_lbl.setFixedSize(100, 100)
        self.avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        set_avatar_on_label(self.avatar_lbl, self.user_data.get("avatar", "👤"))
        
        btn_change_photo = QPushButton("📷 Fotoğraf Değiştir")
        btn_change_photo.setStyleSheet("background-color: #2A3942; border-radius: 12px; padding: 5px; color: #E9EDEF; font-size: 12px;")
        btn_change_photo.clicked.connect(self.change_photo)
        
        avatar_container = QHBoxLayout()
        avatar_container.addStretch()
        avatar_container.addWidget(self.avatar_lbl)
        avatar_container.addStretch()
        avatar_layout.addLayout(avatar_container)
        avatar_layout.addWidget(btn_change_photo, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addLayout(avatar_layout)
        
        # Ad Alanı
        lbl_ad = QLabel("Ad:")
        lbl_ad.setStyleSheet("font-weight: bold; color: #AEBAC1;")
        main_layout.addWidget(lbl_ad)
        self.fname_input = QLineEdit(self.user_data.get("first_name", ""))
        self.fname_input.setStyleSheet("background-color: #2A3942; color: #E9EDEF; border-radius: 8px; padding: 8px;")
        main_layout.addWidget(self.fname_input)
        
        # Soyad Alanı
        lbl_soyad = QLabel("Soyad:")
        lbl_soyad.setStyleSheet("font-weight: bold; color: #AEBAC1;")
        main_layout.addWidget(lbl_soyad)
        self.lname_input = QLineEdit(self.user_data.get("last_name", ""))
        self.lname_input.setStyleSheet("background-color: #2A3942; color: #E9EDEF; border-radius: 8px; padding: 8px;")
        main_layout.addWidget(self.lname_input)
        
        # Kullanıcı Adı
        lbl_user = QLabel("Kullanıcı Adı:")
        lbl_user.setStyleSheet("font-weight: bold; color: #AEBAC1;")
        main_layout.addWidget(lbl_user)
        u_input = QLineEdit(self.user_data.get("username", ""))
        u_input.setReadOnly(True)
        u_input.setStyleSheet("background-color: #111B21; color: #6a7175; border: 1px solid #202C33; border-radius: 8px; padding: 8px;")
        main_layout.addWidget(u_input)
        
        # LAN IP Adresi
        lbl_ip = QLabel("Yerel IP Adresiniz:")
        lbl_ip.setStyleSheet("font-weight: bold; color: #AEBAC1;")
        main_layout.addWidget(lbl_ip)
        ip_input = QLineEdit(get_local_ip())
        ip_input.setReadOnly(True)
        ip_input.setStyleSheet("background-color: #111B21; color: #6a7175; border: 1px solid #202C33; border-radius: 8px; padding: 8px;")
        main_layout.addWidget(ip_input)
        
        # Arkaplan Rengi
        lbl_color = QLabel("Sohbet Arka Planı:")
        lbl_color.setStyleSheet("font-weight: bold; color: #AEBAC1; margin-top: 5px;")
        main_layout.addWidget(lbl_color)
        self.btn_color = QPushButton("🎨 Renk Seç")
        self.btn_color.setStyleSheet("background-color: #2A3942; border-radius: 12px; padding: 10px; color: #E9EDEF;")
        self.btn_color.clicked.connect(self.choose_color)
        main_layout.addWidget(self.btn_color)
        
        main_layout.addStretch()
        btn_save = QPushButton("💾 Güncelle ve Kaydet")
        btn_save.setStyleSheet("background-color: #00A884; border-radius: 12px; padding: 12px; font-weight: bold; color: white;")
        btn_save.clicked.connect(self.save_profile)
        main_layout.addWidget(btn_save)

    def change_photo(self):
        try:
            file_path, _ = QFileDialog.getOpenFileName(self, "Fotoğraf Seç", "", "Resimler (*.png *.jpg *.jpeg *.bmp)")
            if file_path:
                pixmap = QPixmap(file_path)
                if pixmap.isNull():
                    QMessageBox.warning(self, "Hata", "Geçersiz görsel dosyası!")
                    return
                size = min(pixmap.width(), pixmap.height())
                x = (pixmap.width() - size) // 2
                y = (pixmap.height() - size) // 2
                pixmap = pixmap.copy(x, y, size, size).scaled(100, 100, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                
                buffer = QBuffer()
                buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                pixmap.save(buffer, "PNG")
                base64_data = base64.b64encode(buffer.data()).decode('utf-8')
                avatar_str = f"data:image/png;base64,{base64_data}"
                self.user_data["avatar"] = avatar_str
                set_avatar_on_label(self.avatar_lbl, avatar_str)
        except Exception as e:
            print(f"[CLIENT] Profil fotoğrafı değiştirme hatası: {e}")
            QMessageBox.warning(self, "Hata", f"Fotoğraf değiştirilirken hata oluştu: {str(e)}")

    def choose_color(self):
        color = QColorDialog.getColor(initial=Qt.GlobalColor.black, parent=self)
        if color.isValid():
            self.user_data["bg_color"] = color.name()
            self.btn_color.setStyleSheet(f"background-color: {color.name()}; border-radius: 12px; padding: 10px; color: white;")

    def save_profile(self):
        self.user_data["first_name"] = self.fname_input.text()
        self.user_data["last_name"] = self.lname_input.text()
        self.accept()
