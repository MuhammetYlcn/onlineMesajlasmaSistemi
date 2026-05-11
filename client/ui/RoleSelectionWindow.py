from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QPushButton, QLabel, QHBoxLayout)
from PyQt6.QtCore import Qt

class RoleSelectionWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LAN Chat - Rol Seçimi")
        self.setFixedSize(350, 200)
        self.role = None # 'server' or 'client'
        
        layout = QVBoxLayout(self)
        
        title = QLabel("Nasıl Başlamak İstersiniz?")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        btn_layout = QHBoxLayout()
        
        self.btn_server = QPushButton("Sunucu Olarak Başlat")
        self.btn_server.setStyleSheet("""
            background-color: #00A884; 
            color: white; 
            padding: 15px; 
            font-weight: bold; 
            border-radius: 8px;
        """)
        self.btn_server.clicked.connect(self.select_server)
        
        self.btn_client = QPushButton("İstemci Olarak Katıl")
        self.btn_client.setStyleSheet("""
            background-color: #2A3942; 
            color: white; 
            padding: 15px; 
            font-weight: bold; 
            border-radius: 8px;
        """)
        self.btn_client.clicked.connect(self.select_client)
        
        btn_layout.addWidget(self.btn_server)
        btn_layout.addWidget(self.btn_client)
        
        layout.addLayout(btn_layout)
        
        info = QLabel("Not: Bir ağda sadece bir sunucu olabilir.")
        info.setStyleSheet("color: #8696A0; font-size: 11px;")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)

    def select_server(self):
        self.role = 'server'
        self.accept()

    def select_client(self):
        self.role = 'client'
        self.accept()
