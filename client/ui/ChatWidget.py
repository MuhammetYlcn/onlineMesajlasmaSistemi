from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QPushButton, QScrollArea, QLabel, QFrame, QMenu, QMessageBox, QFileDialog, QGridLayout, QWidgetAction, QApplication)
from PyQt6.QtCore import Qt, pyqtSignal, QDateTime, QPoint, QTimer, QUrl
from PyQt6.QtGui import QPixmap, QImage, QIcon
from PyQt6.QtMultimedia import QMediaRecorder, QAudioInput, QMediaCaptureSession, QMediaPlayer, QAudioOutput
import time
import base64
import os
import tempfile

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

class ChatBubble(QFrame):
    delete_requested = pyqtSignal(str) # msg_id
    block_requested = pyqtSignal(str) # sender_username
    reply_requested = pyqtSignal(str, str) # msg_id, text
    edit_requested = pyqtSignal(str, str) # msg_id, text
    forward_requested = pyqtSignal(str) # msg_id
    
    def __init__(self, text, time_str, is_sender=False, chat_parent=None, file_path=None, msg_id=None, sender_username=None, message_type="TEXT", local_enc=None):
        super().__init__()
        self.bubble_text = text
        self.chat_parent = chat_parent
        self.is_sender = is_sender
        self.msg_id = msg_id
        self.sender_username = sender_username
        self.file_path = file_path
        self.message_type = message_type
        self.local_enc = local_enc
        self.retry_count = 0
        
        self.player = None
        self.audio_output = None
        
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 8, 10, 5)
        self.main_layout.setSpacing(4)
        
        # Gönderen İsmi (Grup Mesajları İçin)
        if sender_username and not is_sender:
            self.sender_label = QLabel(sender_username)
            self.sender_label.setStyleSheet("color: #00A884; font-weight: bold; font-size: 13px; margin-bottom: 2px;")
            self.main_layout.addWidget(self.sender_label)

        # Medya ve Metin İçeriği
        self.load_media()
        
        # Zaman ve Durum Alanı
        self.time_layout = QHBoxLayout()
        self.time_layout.addStretch()
        self.time_label = QLabel(time_str)
        if is_sender:
            self.time_label.setStyleSheet("font-size: 11px; color: #84D2C5;")
            self.tick_label = QLabel("✓")
            self.tick_label.setStyleSheet("font-size: 12px; color: rgba(255, 255, 255, 0.6); font-weight: bold;")
            self.time_layout.addWidget(self.time_label)
            self.time_layout.addWidget(self.tick_label)
        else:
            self.time_label.setStyleSheet("font-size: 11px; color: #8696A0;")
            self.time_layout.addWidget(self.time_label)
        
        self.main_layout.addLayout(self.time_layout)

        if is_sender:
            self.setStyleSheet("QFrame { background-color: #005C4B; border-radius: 12px; border-top-right-radius: 0px; margin: 5px 15px 5px 50px;}")
        else:
            self.setStyleSheet("QFrame { background-color: #202C33; border-radius: 12px; border-top-left-radius: 0px; margin: 5px 50px 5px 15px;}")

    def load_media(self):
        # Dosya yolu varsa ve henüz diske yazılmamışsa/okunamıyorsa tekrar dene
        if self.file_path:
            is_image = self.file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'))
            
            if not os.path.exists(self.file_path) and self.retry_count < 10:
                self.retry_count += 1
                QTimer.singleShot(300, self.load_media)
                return

            if self.message_type == "VOICE":
                self.setup_audio_ui(self.main_layout)
            elif is_image:
                try:
                    with open(self.file_path, "rb") as f:
                        data = f.read()
                    if self.local_enc:
                        try: data = self.local_enc.decrypt(data)
                        except: pass
                    pixmap = QPixmap()
                    pixmap.loadFromData(data)
                    if not pixmap.isNull():
                        img_lbl = QLabel()
                        pix = pixmap.scaled(300, 300, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        img_lbl.setPixmap(pix)
                        self.main_layout.addWidget(img_lbl)
                    else:
                        if self.retry_count < 5:
                            self.retry_count += 1
                            QTimer.singleShot(300, self.load_media)
                            return
                        self.main_layout.addWidget(QLabel("📷 [Görsel Yüklenemedi]"))
                except:
                    if self.retry_count < 5:
                        self.retry_count += 1
                        QTimer.singleShot(300, self.load_media)
            else:
                # Normal dosya
                fname = os.path.basename(self.file_path)
                f_cont = QFrame()
                f_cont.setStyleSheet("background-color: #111B21; border-radius: 6px; padding: 5px;")
                f_layout = QHBoxLayout(f_cont)
                f_lbl = QLabel(f"📁 {fname}")
                f_lbl.setStyleSheet("color: white; font-weight: bold;")
                btn_dl = QPushButton("⬇️")
                btn_dl.setFixedSize(30, 30)
                btn_dl.setStyleSheet("background-color: #2A3942; border-radius: 15px; color: white;")
                btn_dl.clicked.connect(self.download_file)
                f_layout.addWidget(f_lbl)
                f_layout.addStretch()
                f_layout.addWidget(btn_dl)
                self.main_layout.addWidget(f_cont)

        if self.bubble_text and self.bubble_text not in ["[DOSYA]", "[SESLI MESAJ]"]:
            self.content_label = QLabel(self.bubble_text)
            self.content_label.setWordWrap(True)
            self.content_label.setStyleSheet("font-size: 15px; color: #E9EDEF;")
            self.content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.main_layout.addWidget(self.content_label)


    def set_replied_content(self, sender, text):
        """Adds a small preview of the replied message inside this bubble."""
        reply_preview = QFrame()
        reply_preview.setStyleSheet("background-color: rgba(0,0,0,0.1); border-left: 3px solid #00A884; border-radius: 4px; margin-bottom: 5px;")
        rp_layout = QVBoxLayout(reply_preview)
        rp_layout.setContentsMargins(5, 5, 5, 5)
        
        sender_lbl = QLabel(sender or "Bilinmiyor")
        sender_lbl.setStyleSheet("font-weight: bold; color: #00A884; font-size: 12px;")
        text = text or ""
        text_lbl = QLabel(text[:50] + ("..." if len(text) > 50 else ""))
        text_lbl.setStyleSheet("color: #8696A0; font-size: 12px;")
        
        rp_layout.addWidget(sender_lbl)
        rp_layout.addWidget(text_lbl)
        
        self.layout().insertWidget(0, reply_preview)

    def set_edited(self):
        """Adds an '(düzenlendi)' tag to the time label."""
        if "(düzenlendi)" not in self.time_label.text():
            self.time_label.setText(f"(düzenlendi) {self.time_label.text()}")

    def update_text(self, new_text):
        if hasattr(self, 'content_label'):
            self.content_label.setText(new_text)
            self.bubble_text = new_text
            self.set_edited()

    def setup_audio_ui(self, layout):
        audio_layout = QHBoxLayout()
        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(30, 30)
        self.play_btn.setStyleSheet("background-color: transparent; color: white; font-size: 18px; border: none;")
        self.play_btn.clicked.connect(self.toggle_audio)
        
        from PyQt6.QtWidgets import QSlider
        self.progress = QSlider(Qt.Orientation.Horizontal)
        self.progress.setStyleSheet("QSlider::groove:horizontal { background: #2A3942; height: 4px; } QSlider::handle:horizontal { background: #00A884; width: 10px; margin: -3px 0; }")
        
        self.duration_label = QLabel("00:00 / 00:00")
        self.duration_label.setStyleSheet("font-size: 10px; color: #8696A0;")
        
        audio_layout.addWidget(self.play_btn)
        audio_layout.addWidget(self.progress)
        audio_layout.addWidget(self.duration_label)
        layout.addLayout(audio_layout)

    def format_time(self, ms):
        if ms < 0: ms = 0
        s = ms // 1000
        m = s // 60
        s = s % 60
        return f"{m:02d}:{s:02d}"

    def toggle_audio(self):
        if not self.file_path or not os.path.exists(self.file_path):
            QMessageBox.warning(self, "Hata", f"Ses dosyası bulunamadı!\nYol: {self.file_path}")
            return
            
        if not self.player:
            self.player = QMediaPlayer(self)
            self.audio_output = QAudioOutput(self)
            self.player.setAudioOutput(self.audio_output)
            self.audio_output.setVolume(1.0)
            
            self.player.positionChanged.connect(self.update_progress)
            self.player.durationChanged.connect(self.on_duration_changed)
            self.player.playbackStateChanged.connect(self.on_state_changed)
            self.player.errorOccurred.connect(self.on_audio_error)
            
            # ŞİFRELİ SES DOSYASINI GEÇİCİ OLARAK ÇÖZ VE OYNAT
            play_path = self.file_path
            if self.local_enc:
                try:
                    with open(self.file_path, "rb") as f:
                        dec_data = self.local_enc.decrypt(f.read())
                    temp_f = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                    temp_f.write(dec_data)
                    temp_f.close()
                    play_path = temp_f.name
                except Exception as e:
                    print(f"Audio decryption error: {e}")

            self.player.setSource(QUrl.fromLocalFile(play_path))
        
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            if self.player.playbackState() == QMediaPlayer.PlaybackState.StoppedState:
                self.player.setPosition(0)
            self.player.play()

    def on_audio_error(self):
        err = self.player.errorString()
        QMessageBox.critical(self, "Ses Hatası", f"Ses oynatılamadı: {err}\nDosya: {self.file_path}")

    def on_duration_changed(self, d):
        self.progress.setRange(0, d)
        self.update_time_label()

    def update_progress(self, pos):
        self.progress.setValue(pos)
        self.update_time_label()

    def update_time_label(self):
        curr = self.format_time(self.player.position())
        total = self.format_time(self.player.duration())
        self.duration_label.setText(f"{curr} / {total}")

    def on_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_btn.setText("⏸")
        else:
            self.play_btn.setText("▶")

    def download_file(self):
        if not self.file_path or not os.path.exists(self.file_path):
            QMessageBox.warning(self, "Hata", "Dosya bulunamadı!")
            return
            
        save_path, _ = QFileDialog.getSaveFileName(self, "Dosyayı Kaydet", os.path.basename(self.file_path), "Tüm Dosyalar (*)")
        if save_path:
            try:
                with open(self.file_path, "rb") as f:
                    data = f.read()
                
                # ŞİFREYİ ÇÖZÜP KAYDET
                if self.local_enc:
                    data = self.local_enc.decrypt(data)
                
                with open(save_path, "wb") as f:
                    f.write(data)
                QMessageBox.information(self, "Başarılı", "Dosya çözülerek kaydedildi.")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Dosya kaydedilemedi: {e}")

    def show_context_menu(self, position):
        menu = QMenu()
        menu.setStyleSheet("QMenu { background-color: #202C33; color: white; border: 1px solid #2A3942; } QMenu::item:selected { background-color: #374248; }")
        
        action_copy = menu.addAction("📋 Kopyala")
        action_reply = menu.addAction("↩️ Yanıtla")
        action_forward = menu.addAction("➡️ İlet")
        
        action_edit = None
        if self.is_sender and self.message_type == "TEXT":
            action_edit = menu.addAction("✏️ Düzenle")
            
        action_delete = menu.addAction("🗑️ Mesajı Sil")
        
        action_block = None
        if not self.is_sender and self.sender_username:
            menu.addSeparator()
            action_block = menu.addAction("🚫 Kullanıcıyı Engelle")

        action = menu.exec(self.mapToGlobal(position))
        
        if action == action_copy:
            QApplication.clipboard().setText(self.bubble_text)
        elif action == action_reply:
            self.reply_requested.emit(self.msg_id, self.bubble_text)
        elif action == action_edit:
            self.edit_requested.emit(self.msg_id, self.bubble_text)
        elif action == action_forward:
            self.forward_requested.emit(self.msg_id)
        elif action == action_delete:
            self.delete_requested.emit(self.msg_id)
        elif action_block and action == action_block:
            self.block_requested.emit(self.sender_username)

    def set_status(self, status):
        if not self.is_sender: return
        if status == "server_received":
            self.tick_label.setText("✓")
            self.tick_label.setStyleSheet("font-size: 12px; color: rgba(255, 255, 255, 0.6); font-family: 'Segoe UI', 'Arial'; font-weight: bold; margin-left: 3px;")
        elif status == "peer_received":
            self.tick_label.setText("✓✓")
            self.tick_label.setStyleSheet("font-size: 12px; color: rgba(255, 255, 255, 0.6); font-family: 'Segoe UI', 'Arial'; font-weight: bold; margin-left: 3px;")
        elif status == "seen":
            self.tick_label.setText("✓✓")
            self.tick_label.setStyleSheet("font-size: 12px; color: #34B7F1; font-family: 'Segoe UI', 'Arial'; font-weight: bold; margin-left: 3px;")

class ChatWidget(QWidget):
    message_sent = pyqtSignal(str, str, str, str, str, dict) # text, target, file, msg_id, type, extra_data
    message_deleted = pyqtSignal(str, str) # msg_id, target
    message_edited = pyqtSignal(str, str, str) # msg_id, new_text, target
    block_requested = pyqtSignal(str) # username
    unblock_requested = pyqtSignal(str) # username
    history_requested = pyqtSignal(str) # target
    forward_requested = pyqtSignal(str, str) # msg_id, target_to_forward_to
    group_settings_requested = pyqtSignal(int) # group_id
    typing_status_changed = pyqtSignal(str, str) # target_ip, status
    clear_history_requested = pyqtSignal(str) # target_ip

    def __init__(self, local_enc=None, message_dao=None):
        super().__init__()
        self.setObjectName("ChatArea")
        self.local_enc = local_enc
        self.message_dao = message_dao
        self._current_chat_target = None
        self._current_chat_ip = None
        self.bubbles = {}
        self.reply_msg_id = None
        self.edit_msg_id = None
        self.last_msgs_map = {} # {msg_id: (sender, text)}
        
        # Audio Recording
        self.recorder = QMediaRecorder()
        self.capture_session = QMediaCaptureSession()
        self.audio_input = QAudioInput()
        self.capture_session.setAudioInput(self.audio_input)
        self.capture_session.setRecorder(self.recorder)
        self.recording_file = ""
        
        self.record_timer = QTimer()
        self.record_timer.timeout.connect(self.update_record_time)
        self.record_seconds = 0
        
        self.typing_timer = QTimer()
        self.typing_timer.setSingleShot(True)
        self.typing_timer.timeout.connect(self.reset_typing_status)
        self._is_typing = False
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Üst Bar
        self.top_bar = QWidget()
        self.top_bar.setObjectName("ChatHeader")
        self.top_bar.setFixedHeight(60)
        self.top_bar.setStyleSheet("background-color: #202C33; border-bottom: 1px solid #2A3942;")
        top_layout = QHBoxLayout(self.top_bar)
        
        self.target_avatar = QLabel()
        self.target_avatar.setFixedSize(40, 40)
        self.target_avatar.setStyleSheet("background-color: #6a7175; border-radius: 20px;")
        self.target_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title_layout = QVBoxLayout()
        self.chat_title = QLabel("Sohbet Seçin")
        self.chat_title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        self.chat_status = QLabel("")
        self.chat_status.setStyleSheet("font-size: 12px; color: #8696A0;")
        title_layout.addWidget(self.chat_title)
        title_layout.addWidget(self.chat_status)
        
        self.record_label = QLabel("")
        self.record_label.setStyleSheet("color: #ff4d4d; font-weight: bold; font-size: 14px; margin-right: 10px;")
        top_layout.addWidget(self.record_label)
        
        top_layout.addWidget(self.target_avatar)
        top_layout.addLayout(title_layout)
        top_layout.addStretch() 
        
        self.btn_options = QPushButton("⋮")
        self.btn_options.setFixedSize(40, 40)
        self.btn_options.setStyleSheet("QPushButton { background-color: transparent; border-radius: 20px; color: #8696A0; font-size: 20px; }")
        self.btn_options.clicked.connect(self.show_chat_options)
        top_layout.addWidget(self.btn_options)

        main_layout.addWidget(self.top_bar)

        # Mesaj Listesi
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { background-color: #0b141a; border: none; }")
        self.messages_container = QWidget()
        self.messages_container.setObjectName("MessagesContainer")
        self.messages_container.setStyleSheet("background-color: #0b141a;")
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.addStretch()
        self.scroll_area.setWidget(self.messages_container)
        main_layout.addWidget(self.scroll_area, stretch=1)

        # Yanıt Önizleme Alanı (Yeni)
        self.reply_preview = QWidget()
        self.reply_preview.setVisible(False)
        self.reply_preview.setStyleSheet("background-color: #111B21; border-left: 4px solid #00A884; margin: 0px 10px; border-top-left-radius: 10px; border-top-right-radius: 10px;")
        reply_preview_layout = QVBoxLayout(self.reply_preview)
        
        self.reply_header_label = QLabel("Yanıtlanıyor")
        self.reply_header_label.setStyleSheet("color: #00A884; font-weight: bold; font-size: 12px;")
        
        content_row = QHBoxLayout()
        self.reply_text_label = QLabel("")
        self.reply_text_label.setStyleSheet("color: #E9EDEF; font-size: 13px;")
        self.btn_cancel_reply = QPushButton("✕")
        self.btn_cancel_reply.setFixedSize(20, 20)
        self.btn_cancel_reply.setStyleSheet("color: #8696A0; border: none; font-size: 14px; background: transparent;")
        self.btn_cancel_reply.clicked.connect(self.cancel_reply_or_edit)
        content_row.addWidget(self.reply_text_label, stretch=1)
        content_row.addWidget(self.btn_cancel_reply)
        
        reply_preview_layout.addWidget(self.reply_header_label)
        reply_preview_layout.addLayout(content_row)
        
        main_layout.addWidget(self.reply_preview)

        # İlerleme Çubuğu (Yeni)
        from PyQt6.QtWidgets import QProgressBar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #111B21; border: none; }
            QProgressBar::chunk { background-color: #00A884; }
        """)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # Giriş Alanı
        self.input_area = QWidget()
        self.input_area.setObjectName("ChatInputArea")
        self.input_area.setStyleSheet("background-color: #202C33; border-top: 1px solid #2A3942;")
        input_layout = QHBoxLayout(self.input_area)
        input_layout.setContentsMargins(10, 10, 10, 10)
        
        btn_style = "QPushButton { background-color: transparent; border-radius: 20px; color: #8696A0; font-size: 20px; } QPushButton:hover { background-color: #374248; }"
        self.btn_emoji = QPushButton("😀")
        self.btn_emoji.setFixedSize(40, 40)
        self.btn_emoji.setStyleSheet(btn_style)
        self.btn_emoji.clicked.connect(self.show_emoji_menu)
        
        self.btn_attach = QPushButton("📎")
        self.btn_attach.setFixedSize(40, 40)
        self.btn_attach.setStyleSheet(btn_style)
        self.btn_attach.clicked.connect(self.on_attach_clicked)
        
        self.message_input = QTextEdit()
        self.message_input.setStyleSheet("QTextEdit { background-color: #2A3942; border-radius: 10px; padding: 8px; color: #E9EDEF; font-size: 14px; border: none;}")
        self.message_input.setFixedHeight(40)
        self.message_input.textChanged.connect(self.on_typing)
        
        self.send_btn = QPushButton("➤")
        self.send_btn.setFixedSize(40, 40)
        self.send_btn.setStyleSheet("QPushButton { background-color: #00A884; border-radius: 20px; color: white; font-size: 18px; }")
        self.send_btn.clicked.connect(self.on_send_clicked)
        
        self.mic_btn = QPushButton("🎙️")
        self.mic_btn.setFixedSize(40, 40)
        self.mic_btn.setStyleSheet(btn_style)
        self.mic_btn.clicked.connect(self.on_mic_clicked)
        
        input_layout.addWidget(self.btn_emoji)
        input_layout.addWidget(self.btn_attach)
        input_layout.addWidget(self.message_input, stretch=1)
        input_layout.addWidget(self.mic_btn)
        input_layout.addWidget(self.send_btn)
        main_layout.addWidget(self.input_area)
        
        self.set_chat_target(None, None, None)

    def set_custom_background(self, hex_color):
        if not hex_color or hex_color == "transparent": hex_color = "#0b141a"
        self.scroll_area.setStyleSheet(f"QScrollArea {{ background-color: {hex_color}; background-image: url('resources/doodle.svg'); background-attachment: fixed; }}")
        self.messages_container.setStyleSheet("QWidget#MessagesContainer { background-color: transparent; }")

    def show_progress(self, visible, text=None):
        self.progress_bar.setVisible(visible)
        if visible:
            self.progress_bar.setRange(0, 0) # Indeterminate mode
        else:
            self.progress_bar.setRange(0, 100)

    def set_progress_value(self, value):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(value)

    def show_chat_options(self):
        menu = QMenu(self)
        # Stil tanımlamasını daha sade yapalım ki metinler görünür olsun
        menu.setStyleSheet("""
            QMenu { background-color: #202C33; color: white; border: 1px solid #2A3942; }
            QMenu::item { padding: 8px 25px; }
            QMenu::item:selected { background-color: #374248; }
        """)
        
        action_clear = menu.addAction("🗑️ Sohbeti Temizle")
        
        action_block = None
        action_unblock = None
        if self._current_chat_ip and not self._current_chat_ip.startswith("group_") and self._current_chat_ip != "Siz":
            if getattr(self, 'is_blocked', False):
                action_unblock = menu.addAction("🔓 Engeli Kaldır")
            else:
                action_block = menu.addAction("🚫 Engelle")
        
        action_group_settings = None
        if self._current_chat_ip and self._current_chat_ip.startswith("group_"):
            menu.addSeparator()
            action_group_settings = menu.addAction("👥 Grup Bilgisi / Ayarları")
        
        action = menu.exec(self.btn_options.mapToGlobal(QPoint(0, 40)))
        if action == action_clear:
            self.clear_chat_permanently()
        elif action_block and action == action_block:
            self.block_requested.emit(self._current_chat_ip)
            self.is_blocked = True
        elif action_unblock and action == action_unblock:
            self.unblock_requested.emit(self._current_chat_ip)
            self.is_blocked = False
        elif action_group_settings and action == action_group_settings:
            gid = int(self._current_chat_ip.split("_")[1])
            self.group_settings_requested.emit(gid)

    def show_emoji_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #202C33; border: 1px solid #2A3942; border-radius: 8px; }")
        emoji_widget = QWidget()
        grid = QGridLayout(emoji_widget)
        emojiler = ["😀","😂","😊","😍","😎","👍","🔥","❤️","👏","🙏","🎉","✨"]
        row, col = 0, 0
        for emj in emojiler:
            btn = QPushButton(emj)
            btn.setFixedSize(35, 35)
            btn.setStyleSheet("border: none; font-size: 18px;")
            btn.clicked.connect(lambda checked, e=emj: (self.message_input.insertPlainText(e), menu.close()))
            grid.addWidget(btn, row, col)
            col += 1
            if col > 3: col = 0; row += 1
        w_action = QWidgetAction(self)
        w_action.setDefaultWidget(emoji_widget)
        menu.addAction(w_action)
        menu.exec(self.btn_emoji.mapToGlobal(QPoint(0, -menu.sizeHint().height())))



    def on_reply_requested(self, msg_id, text):
        self.reply_msg_id = msg_id
        self.edit_msg_id = None
        self.reply_header_label.setText("Yanıtlanıyor")
        self.reply_text_label.setText(text[:100])
        self.reply_preview.setVisible(True)
        self.message_input.setFocus()

    def on_edit_requested(self, msg_id, text):
        self.edit_msg_id = msg_id
        self.reply_msg_id = None
        self.reply_header_label.setText("Mesajı Düzenle")
        self.reply_text_label.setText(text[:100])
        self.reply_preview.setVisible(True)
        self.message_input.setText(text)
        self.message_input.setFocus()

    def cancel_reply_or_edit(self):
        self.reply_msg_id = None
        self.edit_msg_id = None
        self.reply_preview.setVisible(False)
        self.message_input.clear()

    def on_typing(self):
        if self._current_chat_ip:
            if not self._is_typing:
                self._is_typing = True
                self.typing_status_changed.emit(self._current_chat_ip, "yazıyor...")
            self.typing_timer.start(3000)

    def reset_typing_status(self):
        if self._is_typing and self._current_chat_ip:
            self._is_typing = False
            self.typing_status_changed.emit(self._current_chat_ip, "")

    def set_chat_target(self, target_name, target_avatar, target_ip, is_online=True, lastseen=None, member_list=None, is_kicked=False, is_blocked=False):
        self.is_blocked = is_blocked
        if not target_name:
            self._current_chat_target = None
            self._current_chat_ip = None
            self.chat_title.setText("Sohbet Seçin")
            self.input_area.setEnabled(False)
            self.chat_status.setText("")
            self.target_avatar.setPixmap(QPixmap())
            self.target_avatar.setText("👤")
            return
        self._current_chat_target = target_name
        self._current_chat_ip = target_ip
        self.chat_title.setText(target_name)
        
        if is_kicked:
            status_text = "Gruptan çıkarıldınız veya grup silindi"
        elif target_ip.startswith("group_") and member_list:
            total = len(member_list)
            online = sum(1 for m in member_list if m.get('is_online'))
            status_text = f"{total} üye, {online} çevrimiçi"
        elif target_name == "Siz":
            status_text = ""
        else:
            status_text = "çevrimiçi" if is_online else f"son görülme: {lastseen}" if lastseen else "çevrimdışı"
            
        self.chat_status.setText(status_text)
        
        set_avatar_on_label(self.target_avatar, target_avatar)
        self.input_area.setEnabled(not is_kicked)
        self.clear_chat()
        
        # Önce yerel belleği yükle
        self.load_local_history(target_ip)
        
        # Sonra sunucudan sadece yeni olanları iste
        self.show_progress(True)
        self.history_requested.emit(target_ip)

    def load_local_history(self, target_id):
        if hasattr(self, 'message_dao') and self.message_dao:
            if target_id.startswith("group_"):
                gid = int(target_id.split("_")[1])
                msgs = self.message_dao.get_group_history(gid)
            else:
                msgs = self.message_dao.get_chat_history(target_id)
            
            for m in msgs:
                self.add_message(
                    text=m.content,
                    is_sender=m.is_me,
                    file_path=m.local_path,
                    msg_id=m.message_id,
                    sender_username=m.sender,
                    message_type=m.message_type,
                    extra_data={"status": m.status, "reply_to_id": m.reply_to_id}
                )

    def clear_chat(self):
        """Sadece arayüzdeki mesaj balonlarını temizler."""
        count = self.messages_layout.count()
        for i in reversed(range(count - 1)):
            item = self.messages_layout.itemAt(i)
            if item and item.widget(): item.widget().deleteLater()
        self.bubbles.clear()

    def clear_chat_permanently(self):
        """Hem arayüzü temizler hem de yerel ve sunucu veritabanından siler."""
        if self._current_chat_ip:
            # Yerel veritabanından sil
            if self.message_dao:
                # Grup ise group_id, değilse chat_partner kullan
                if self._current_chat_ip.startswith("group_"):
                    try:
                        gid = int(self._current_chat_ip.split("_")[1])
                        self.message_dao.delete_chat(group_id=gid)
                    except: pass
                else:
                    self.message_dao.delete_chat(chat_partner=self._current_chat_ip)
            
            # Sunucuya silme isteği gönder
            self.clear_history_requested.emit(self._current_chat_ip)
            
        self.clear_chat()

    def remove_single_message(self, msg_id):
        if msg_id in self.bubbles:
            bubble = self.bubbles.pop(msg_id)
            bubble.parent().deleteLater()

    def on_attach_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Dosya Seç", "", "Tüm Dosyalar (*)")
        if file_path:
            msg_id = str(time.time())
            self.message_sent.emit("[DOSYA]", self._current_chat_ip, file_path, msg_id, "FILE", {})
            self.add_message("[DOSYA]", is_sender=True, file_path=file_path, msg_id=msg_id, message_type="FILE")

    def on_send_clicked(self):
        text = self.message_input.toPlainText().strip()
        if text:
            if self.edit_msg_id:
                # Düzenleme modu
                self.message_edited.emit(self.edit_msg_id, text, self._current_chat_ip)
                if self.edit_msg_id in self.bubbles:
                    self.bubbles[self.edit_msg_id].update_text(text)
                self.cancel_reply_or_edit()
            else:
                # Normal veya Yanıt modu
                msg_id = str(time.time())
                extra = {}
                if self.reply_msg_id:
                    extra["reply_to_id"] = self.reply_msg_id
                
                self.message_sent.emit(text, self._current_chat_ip, "", msg_id, "TEXT", extra)
                self.add_message(text, is_sender=True, msg_id=msg_id, extra_data=extra)
                self.message_input.clear()
                self.reset_typing_status()
                if self.reply_msg_id:
                    self.cancel_reply_or_edit()

    def on_mic_clicked(self):
        if self.recorder.recorderState() == QMediaRecorder.RecorderState.RecordingState:
            self.recorder.stop()
            self.record_timer.stop()
            self.mic_btn.setText("🎙️")
            self.mic_btn.setStyleSheet("color: #8696A0;")
            self.record_label.setText("")
            if self._current_chat_ip:
                self.typing_status_changed.emit(self._current_chat_ip, "")
            
            # Gecikme yerine doğrudan gönderelim, QMediaRecorder.stop() genelde yeterlidir.
            # Eğer hala sorun olursa QMediaRecorder.actualLocation() kontrol edilebilir.
            msg_id = str(time.time())
            self.message_sent.emit("[SESLI MESAJ]", self._current_chat_ip, self.recording_file, msg_id, "VOICE", {})
            self.add_message("[SESLI MESAJ]", is_sender=True, file_path=self.recording_file, msg_id=msg_id, message_type="VOICE")
        else:
            temp_dir = tempfile.gettempdir()
            # WAV formatı daha geniş uyumluluğa sahiptir
            self.recording_file = os.path.join(temp_dir, f"voice_{int(time.time())}.wav")
            
            from PyQt6.QtMultimedia import QMediaFormat
            media_format = QMediaFormat()
            media_format.setFileFormat(QMediaFormat.FileFormat.Wave)
            media_format.setAudioCodec(QMediaFormat.AudioCodec.Wave)
            self.recorder.setMediaFormat(media_format)
            
            self.recorder.setOutputLocation(QUrl.fromLocalFile(self.recording_file))
            self.recorder.record()
            self.record_seconds = 0
            self.record_timer.start(1000)
            self.mic_btn.setText("🛑")
            self.mic_btn.setStyleSheet("color: #ff4d4d; font-weight: bold;")
            if self._current_chat_ip:
                self.typing_status_changed.emit(self._current_chat_ip, "sesli mesaj kaydediyor...")

    def update_record_time(self):
        self.record_seconds += 1
        m = self.record_seconds // 60
        s = self.record_seconds % 60
        self.record_label.setText(f"KAYDEDİLİYOR {m:02d}:{s:02d}")

    def add_message(self, text, is_sender=False, file_path=None, msg_id=None, sender_username=None, message_type="TEXT", extra_data=None):
        # Eğer file_path tam yol değilse (history'den geliyorsa), downloads klasörüne bak
        if file_path and not os.path.isabs(file_path):
            download_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "downloads")
            try:
                os.makedirs(download_dir, exist_ok=True)
            except:
                pass
            file_path = os.path.join(download_dir, file_path)
            
        if file_path:
            file_path = os.path.normpath(file_path)

        if message_type in ["FILE", "VOICE", "IMAGE", "VIDEO"]:
            # Eğer local dosya yoksa ve text base64 data içeriyorsa (sunucudan geldiyse)
            if file_path and not os.path.exists(file_path) and text and text not in ["[DOSYA]", "[SESLI MESAJ]"] and not text.startswith("http") and len(text) > 20:
                try:
                    import base64
                    with open(file_path, "wb") as f:
                        f.write(base64.b64decode(text))
                except Exception as e:
                    print(f"Error restoring file from history: {e}")
            
            # Text her zaman [DOSYA] veya [SESLI MESAJ] olmalı, milyonlarca karakterlik base64 string'i değil
            text = "[SESLI MESAJ]" if message_type == "VOICE" else "[DOSYA]"

        if msg_id and msg_id in self.bubbles:
            # Sadece durumu güncelle ve çık
            new_status = (extra_data or {}).get("status")
            if new_status:
                self.bubbles[msg_id].set_status(new_status)
            return

        try:
            current_time = QDateTime.currentDateTime().toString("HH:mm")
            bubble = ChatBubble(text, current_time, is_sender, self, file_path, msg_id, sender_username, message_type, local_enc=self.local_enc)
            
            status = (extra_data or {}).get("status")
            if not status and is_sender:
                status = "server_received"
            if status:
                bubble.set_status(status)

            # Yanıt Bilgisini İşle
            reply_to = (extra_data or {}).get('reply_to_id')
            if reply_to and reply_to in self.last_msgs_map:
                r_data = self.last_msgs_map[reply_to]
                r_sender = r_data[0]
                r_text = r_data[1]
                bubble.set_replied_content(r_sender, r_text)
            
            # Düzenlendi mi?
            if (extra_data or {}).get('is_edited'):
                bubble.set_edited()

            if msg_id:
                self.bubbles[msg_id] = bubble
                actual_sender = "Siz" if is_sender else ((extra_data.get("sender") if extra_data else None) or sender_username or "Bilinmiyor")
                self.last_msgs_map[msg_id] = (actual_sender, text or "", file_path, message_type)
                bubble.delete_requested.connect(lambda mid: self.message_deleted.emit(mid, self._current_chat_ip))
                bubble.block_requested.connect(self.block_requested.emit)
                bubble.reply_requested.connect(self.on_reply_requested)
                bubble.edit_requested.connect(self.on_edit_requested)
                bubble.forward_requested.connect(lambda mid: self.forward_requested.emit(mid, self._current_chat_ip))
            
            if not is_sender and msg_id and status != "seen":
                # [SEEN] gönderirken target kontrolü
                if self._current_chat_ip:
                    # print(f"[DEBUG] Sending [SEEN] for {msg_id} to {self._current_chat_ip}")
                    self.message_sent.emit("[SEEN]", self._current_chat_ip, "", msg_id, "TEXT", {})
                    # Kendi yerel veritabanımızı da güncelleyelim ki tekrar gönderip durmayalım
                    self.update_message_status(msg_id, "seen", self._current_chat_ip)
            
            wrapper_layout = QHBoxLayout()
            if is_sender: wrapper_layout.addStretch(); wrapper_layout.addWidget(bubble)
            else: wrapper_layout.addWidget(bubble); wrapper_layout.addStretch()
            
            wrapper_widget = QWidget()
            wrapper_widget.setLayout(wrapper_layout)
            self.messages_layout.insertWidget(self.messages_layout.count() - 1, wrapper_widget)
            QTimer.singleShot(50, lambda: self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum()))
        except Exception as e:
            print(f"Mesaj ekleme hatası: {e}")

    def update_message_status(self, msg_id, status, target=None):
        msg_id = str(msg_id)
        
        # Eğer target verilmişse ve şu anki target ile aynı değilse sadece DB'yi güncelle
        curr_chat = str(self._current_chat_ip or "").strip().lower()
        if target and str(target).strip().lower() != curr_chat:
            if self.message_dao:
                self.message_dao.update_status(msg_id, status)
            return

        if msg_id in self.bubbles:
            self.bubbles[msg_id].set_status(status)
        
        # Yerel DB'yi de güncelle
        if self.message_dao:
            self.message_dao.update_status(msg_id, status)
