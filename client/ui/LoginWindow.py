from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTabWidget, QWidget, QMessageBox, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal
from models.LocaleSettings import LocaleSettings
import hashlib

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

class LoginWindow(QDialog):
    login_successful = pyqtSignal(dict)

    def __init__(self, lan_service, settings_dao=None):
        super().__init__()
        self.lan_service = lan_service
        self.settings_dao = settings_dao
        self.setWindowTitle("LAN Sohbet - Giriş")
        self.setFixedSize(350, 400)
        self.setObjectName("MainBackground")
        
        # Sinyalleri bağla
        self.lan_service.login_response.connect(self.on_login_response)
        self.lan_service.register_response.connect(self.on_register_response)
        self.lan_service.server_lost.connect(self.on_server_lost)
        
        main_layout = QVBoxLayout(self)
        
        title_lbl = QLabel("💬 LAN Sohbet")
        title_lbl.setStyleSheet("font-size: 24px; font-weight: bold; color: #00A884;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_lbl)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: none; }
            QTabBar::tab { background: #202C33; padding: 10px 30px; font-weight: bold; }
            QTabBar::tab:selected { background: #2A3942; border-bottom: 2px solid #00A884; }
        """)
        
        self.tab_login = QWidget()
        self.tab_register = QWidget()
        self.tabs.addTab(self.tab_login, "Giriş Yap")
        self.tabs.addTab(self.tab_register, "Kayıt Ol")
        
        self.setup_login_tab()
        self.setup_register_tab()
        main_layout.addWidget(self.tabs)
        
        self.load_cached_settings()

    def setup_login_tab(self):
        layout = QVBoxLayout(self.tab_login)
        layout.addStretch()
        
        self.log_user = QLineEdit()
        self.log_user.setPlaceholderText("Kullanıcı Adı")
        self.log_user.setObjectName("SearchBar")
        layout.addWidget(self.log_user)
        
        self.log_pass = QLineEdit()
        self.log_pass.setPlaceholderText("Şifre")
        self.log_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.log_pass.setObjectName("SearchBar")
        layout.addWidget(self.log_pass)
        
        self.remember_me = QCheckBox("Kullanıcı Adımı Hatırla")
        self.remember_me.setStyleSheet("color: white; margin-bottom: 10px;")
        layout.addWidget(self.remember_me)
        
        self.btn_login = QPushButton("Giriş Yap")
        self.btn_login.setStyleSheet("background-color: #00A884; border-radius: 8px; padding: 10px; font-weight: bold;")
        self.btn_login.clicked.connect(self.do_login)
        layout.addWidget(self.btn_login)
        layout.addStretch()

    def setup_register_tab(self):
        layout = QVBoxLayout(self.tab_register)
        layout.addStretch()
        
        self.reg_user = QLineEdit()
        self.reg_user.setPlaceholderText("Kullanıcı Adı")
        self.reg_user.setObjectName("SearchBar")
        layout.addWidget(self.reg_user)
        
        self.reg_pass = QLineEdit()
        self.reg_pass.setPlaceholderText("Şifre")
        self.reg_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.reg_pass.setObjectName("SearchBar")
        layout.addWidget(self.reg_pass)
        
        self.btn_reg = QPushButton("Kayıt Ol")
        self.btn_reg.setStyleSheet("background-color: #2A3942; border-radius: 8px; padding: 10px; font-weight: bold;")
        self.btn_reg.clicked.connect(self.do_register)
        layout.addWidget(self.btn_reg)
        layout.addStretch()

    def do_login(self):
        u = self.log_user.text().strip()
        p = self.log_pass.text()
        if not u or not p: return
        
        self.btn_login.setEnabled(False)
        self.btn_login.setText("Giriş Yapılıyor...")
        self.lan_service.login(u, hash_password(p))

    def on_login_response(self, success, message, data):
        print(f"[CLIENT] Login response received: success={success}, message={message}")
        self.btn_login.setEnabled(True)
        self.btn_login.setText("Giriş Yap")
        if success:
            print(f"[CLIENT] Login SUCCESS, preparing user data and switching windows...")
            user_data = data or {}
            user_data.setdefault("username", self.log_user.text())
            user_data.setdefault("first_name", self.log_user.text())
            user_data.setdefault("last_name", "")
            user_data.setdefault("avatar", "👤")
            user_data["password"] = self.log_pass.text()
            
            # Kaydet
            if self.settings_dao:
                settings = LocaleSettings(
                    remember_me=1 if self.remember_me.isChecked() else 0,
                    saved_username=self.log_user.text() if self.remember_me.isChecked() else ""
                )
                self.settings_dao.save(settings)

            self.login_successful.emit(user_data)
            self.accept()
        else:
            QMessageBox.warning(self, "Hata", message)

    def load_cached_settings(self):
        if self.settings_dao:
            settings = self.settings_dao.get_settings()
            if settings and settings.saved_username:
                # Eğer hala şifreli bir metin gibi duruyorsa temizle
                if settings.saved_username.startswith("gAAAA"):
                    self.log_user.setText("")
                else:
                    self.log_user.setText(settings.saved_username)
                self.remember_me.setChecked(settings.remember_me == 1)

    def on_server_lost(self, msg):
        self.btn_login.setEnabled(True)
        self.btn_login.setText("Giriş Yap")
        QMessageBox.critical(self, "Bağlantı Koptu", f"Sunucu ile bağlantı kesildi!\nHata: {msg}")

    def do_register(self):
        u = self.reg_user.text().strip()
        p = self.reg_pass.text()
        if not u or not p: return
        
        self.btn_reg.setEnabled(False)
        self.lan_service.register(u, hash_password(p))

    def on_register_response(self, success, message):
        self.btn_reg.setEnabled(True)
        if success:
            QMessageBox.information(self, "Başarılı", "Kayıt başarılı! Giriş yapabilirsiniz.")
            self.tabs.setCurrentIndex(0)
        else:
            QMessageBox.warning(self, "Hata", message)

def import_json():
    import json
    return json
