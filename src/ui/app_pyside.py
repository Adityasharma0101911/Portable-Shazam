"""
Modern PySide6 UI for Portable Shazam
Responsive, glassmorphism design with smooth animations
"""
import sys
import os
import threading
import webbrowser
from io import BytesIO

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QProgressBar, QFrame, QGraphicsDropShadowEffect,
    QGraphicsBlurEffect, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPixmap, QFont, QColor, QPalette, QLinearGradient, QBrush, QPainter, QImage

import requests
from PIL import Image, ImageFilter

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.audio_capture import AudioCapture, AudioCaptureError
from src.api_client import create_client, APIError
from src.models.song import SongMatch

try:
    import config
except ImportError:
    config = None


# Global song history
song_history = []


class SignalEmitter(QObject):
    """Thread-safe signal emitter for UI updates"""
    update_status = Signal(str)
    update_progress = Signal(float)
    update_level = Signal(float)
    update_results = Signal(list)
    show_error = Signal(str)
    finish_listening = Signal()  # Signal to trigger finish on main thread


class GlassCard(QFrame):
    """Glassmorphism card component"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("glassCard")
        self.setStyleSheet("""
            #glassCard {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 16px;
            }
        """)
        
        # Add shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)


class ModernButton(QPushButton):
    """Modern styled button with hover effects"""
    def __init__(self, text, primary=True, parent=None):
        super().__init__(text, parent)
        self.primary = primary
        self.setMinimumHeight(50)
        self.setCursor(Qt.PointingHandCursor)
        self._update_style()
    
    def _update_style(self):
        if self.primary:
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #8b5cf6, stop:1 #ec4899);
                    color: white;
                    border: none;
                    border-radius: 12px;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 12px 32px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #7c3aed, stop:1 #db2777);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #6d28d9, stop:1 #be185d);
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.1);
                    color: white;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    border-radius: 12px;
                    font-size: 14px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.2);
                }
            """)


class SongCard(GlassCard):
    """Song result card with album art and action buttons"""
    def __init__(self, song: SongMatch, rank: int, parent=None):
        super().__init__(parent)
        self.song = song
        
        # Add to history
        self._add_to_history(song)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)
        
        # Top row: album art + song info
        top_row = QHBoxLayout()
        top_row.setSpacing(16)
        
        # Album art
        self.album_art = QLabel()
        self.album_art.setFixedSize(80, 80)
        self.album_art.setStyleSheet("""
            background-color: rgba(139, 92, 246, 0.3);
            border-radius: 8px;
        """)
        self.album_art.setAlignment(Qt.AlignCenter)
        self.album_art.setText("🎵")
        self.album_art.setFont(QFont("Segoe UI", 24))
        top_row.addWidget(self.album_art)
        
        # Load album art in background
        if song.album_art_url:
            threading.Thread(target=self._load_album_art, daemon=True).start()
        
        # Song info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        # Rank and title
        title_layout = QHBoxLayout()
        rank_label = QLabel(f"#{rank}")
        rank_label.setStyleSheet("color: #8b5cf6; font-weight: bold; font-size: 14px;")
        title_layout.addWidget(rank_label)
        
        title_label = QLabel(song.title)
        title_label.setStyleSheet("color: white; font-weight: bold; font-size: 16px;")
        title_label.setWordWrap(True)
        title_layout.addWidget(title_label, 1)
        info_layout.addLayout(title_layout)
        
        # Artist
        artist_label = QLabel(f"🎤 {song.artist}")
        artist_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); font-size: 14px;")
        info_layout.addWidget(artist_label)
        
        # Album
        if song.album and song.album != "Unknown":
            album_label = QLabel(f"💿 {song.album}")
            album_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 12px;")
            info_layout.addWidget(album_label)
        
        # Confidence
        conf_label = QLabel(f"✓ {song.confidence:.0f}% match")
        conf_label.setStyleSheet("color: #10b981; font-size: 12px;")
        info_layout.addWidget(conf_label)
        
        top_row.addLayout(info_layout, 1)
        main_layout.addLayout(top_row)
        
        # Bottom row: action buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        
        if song.youtube_url:
            yt_btn = QPushButton("▶ YouTube")
            yt_btn.setCursor(Qt.PointingHandCursor)
            yt_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ff0000;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: 12px;
                    font-weight: bold;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #cc0000;
                }
            """)
            yt_btn.clicked.connect(lambda: webbrowser.open(song.youtube_url))
            buttons_layout.addWidget(yt_btn)
        
        if song.spotify_url:
            sp_btn = QPushButton("♪ Spotify")
            sp_btn.setCursor(Qt.PointingHandCursor)
            sp_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1db954;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: 12px;
                    font-weight: bold;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #1aa34a;
                }
            """)
            sp_btn.clicked.connect(lambda: webbrowser.open(song.spotify_url))
            buttons_layout.addWidget(sp_btn)
        
        buttons_layout.addStretch()
        main_layout.addLayout(buttons_layout)
    
    def _add_to_history(self, song):
        """Add song to global history"""
        global song_history
        # Avoid duplicates
        for s in song_history:
            if s.title == song.title and s.artist == song.artist:
                return
        song_history.insert(0, song)
        if len(song_history) > 10:
            song_history.pop()
    
    def _load_album_art(self):
        try:
            response = requests.get(self.song.album_art_url, timeout=5)
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                img = img.resize((80, 80), Image.Resampling.LANCZOS)
                img = img.convert("RGBA")
                
                # Create QImage from PIL image
                data = img.tobytes("raw", "RGBA")
                qimg = QImage(data, 80, 80, 80 * 4, QImage.Format_RGBA8888)
                # Make a copy so it doesn't depend on the data buffer
                qimg = qimg.copy()
                pixmap = QPixmap.fromImage(qimg)
                
                # Store reference to prevent garbage collection
                self._pixmap_ref = pixmap
                
                # Update on main thread
                QTimer.singleShot(0, lambda p=pixmap: self._set_album_art(p))
        except Exception as e:
            print(f"Album art error: {e}")
    
    def _set_album_art(self, pixmap):
        """Set the album art pixmap (called on main thread)"""
        self.album_art.setPixmap(pixmap)
        self.album_art.setText("")


class PortableShazamWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Portable Shazam")
        self.setMinimumSize(500, 700)
        self.resize(550, 800)
        
        # Dark gradient background
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0f0f1a, stop:0.5 #1a1a2e, stop:1 #0f0f1a);
            }
            QLabel {
                color: white;
            }
            QComboBox {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
                min-height: 20px;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox QAbstractItemView {
                background-color: #1a1a2e;
                color: white;
                selection-background-color: #8b5cf6;
            }
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.1);
                border: none;
                border-radius: 4px;
                height: 8px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #8b5cf6, stop:1 #ec4899);
                border-radius: 4px;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.1);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #8b5cf6;
                border-radius: 4px;
            }
        """)
        
        # Initialize components
        self.audio_capture = AudioCapture()
        self.api_client = create_client()
        self._is_listening = False
        self._is_continuous = False
        self._bg_pixmap = None
        
        # Signal emitter for thread-safe UI updates
        self.signals = SignalEmitter()
        self.signals.update_status.connect(self._on_status_update)
        self.signals.update_progress.connect(self._on_progress_update)
        self.signals.update_level.connect(self._on_level_update)
        self.signals.update_results.connect(self._on_results_update)
        self.signals.show_error.connect(self._on_error)
        self.signals.finish_listening.connect(self._finish_listening)
        
        self._setup_ui()
        self._update_audio_devices()
    
    def _setup_ui(self):
        """Create the UI layout"""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)
        
        # Header
        header = QVBoxLayout()
        header.setAlignment(Qt.AlignCenter)
        
        icon = QLabel("🎵")
        icon.setFont(QFont("Segoe UI", 48))
        icon.setAlignment(Qt.AlignCenter)
        header.addWidget(icon)
        
        title = QLabel("Portable Shazam")
        title.setFont(QFont("Segoe UI", 28, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        header.addWidget(title)
        
        subtitle = QLabel("Identify any song in seconds")
        subtitle.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 14px;")
        subtitle.setAlignment(Qt.AlignCenter)
        header.addWidget(subtitle)
        
        main_layout.addLayout(header)
        
        # Audio source card
        source_card = GlassCard()
        source_layout = QVBoxLayout(source_card)
        source_layout.setContentsMargins(16, 16, 16, 16)
        source_layout.setSpacing(12)
        
        source_title = QLabel("🔊 Audio Source")
        source_title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        source_layout.addWidget(source_title)
        
        # Device row with dropdown and refresh button
        device_row = QHBoxLayout()
        device_row.setSpacing(8)
        
        self.device_combo = QComboBox()
        self.device_combo.addItem("Loading...")
        self.device_combo.currentTextChanged.connect(self._on_device_changed)
        device_row.addWidget(self.device_combo, 1)
        
        refresh_btn = QPushButton("↻")
        refresh_btn.setFixedSize(40, 40)
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        refresh_btn.setToolTip("Refresh audio devices")
        refresh_btn.clicked.connect(self._update_audio_devices)
        device_row.addWidget(refresh_btn)
        
        source_layout.addLayout(device_row)
        
        main_layout.addWidget(source_card)
        
        # Listen section
        listen_card = GlassCard()
        listen_layout = QVBoxLayout(listen_card)
        listen_layout.setContentsMargins(24, 24, 24, 24)
        listen_layout.setSpacing(16)
        listen_layout.setAlignment(Qt.AlignCenter)
        
        # Audio level
        self.level_bar = QProgressBar()
        self.level_bar.setMaximum(100)
        self.level_bar.setValue(0)
        self.level_bar.setTextVisible(False)
        self.level_bar.setFixedHeight(12)
        listen_layout.addWidget(self.level_bar)
        
        level_label = QLabel("Audio Level")
        level_label.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 12px;")
        level_label.setAlignment(Qt.AlignCenter)
        listen_layout.addWidget(level_label)
        
        # Buttons row
        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(12)
        
        # Listen button
        self.listen_btn = ModernButton("🎤  LISTEN")
        self.listen_btn.setMinimumWidth(160)
        self.listen_btn.setMinimumHeight(60)
        self.listen_btn.clicked.connect(self._toggle_listening)
        buttons_row.addWidget(self.listen_btn)
        
        # Continuous scan button
        self.continuous_btn = QPushButton("🔁 AUTO")
        self.continuous_btn.setMinimumWidth(100)
        self.continuous_btn.setMinimumHeight(60)
        self.continuous_btn.setCursor(Qt.PointingHandCursor)
        self.continuous_btn.setCheckable(True)
        self.continuous_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 12px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
            QPushButton:checked {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10b981, stop:1 #059669);
                border: none;
            }
        """)
        self.continuous_btn.setToolTip("Toggle continuous scanning")
        self.continuous_btn.clicked.connect(self._toggle_continuous)
        buttons_row.addWidget(self.continuous_btn)
        
        listen_layout.addLayout(buttons_row)
        
        # Status
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 14px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        listen_layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.hide()
        listen_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(listen_card)
        
        # Results section
        results_label = QLabel("📋 Results")
        results_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        main_layout.addWidget(results_label)
        
        # Scroll area for results
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(12)
        self.results_layout.addStretch()
        
        scroll.setWidget(self.results_container)
        main_layout.addWidget(scroll, 1)
        
        # Footer
        footer = QHBoxLayout()
        
        credits = QLabel("Created by Aditya Sharma")
        credits.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 11px;")
        footer.addWidget(credits)
        
        # Links
        github_btn = QPushButton("GitHub")
        github_btn.setCursor(Qt.PointingHandCursor)
        github_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8b5cf6;
                border: none;
                font-size: 11px;
            }
            QPushButton:hover {
                color: #a78bfa;
            }
        """)
        github_btn.clicked.connect(lambda: webbrowser.open("https://github.com/Adityasharma0101911/Portable-Shazam"))
        footer.addWidget(github_btn)
        
        portfolio_btn = QPushButton("Portfolio")
        portfolio_btn.setCursor(Qt.PointingHandCursor)
        portfolio_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8b5cf6;
                border: none;
                font-size: 11px;
            }
            QPushButton:hover {
                color: #a78bfa;
            }
        """)
        portfolio_btn.clicked.connect(lambda: webbrowser.open("https://adityasharma0101.vercel.app"))
        footer.addWidget(portfolio_btn)
        
        footer.addStretch()
        
        version = QLabel("v2.0.0")
        version.setStyleSheet("color: rgba(255, 255, 255, 0.3); font-size: 11px;")
        footer.addWidget(version)
        
        main_layout.addLayout(footer)
        
        # Initial state message
        self._show_initial_state()
    
    def _show_initial_state(self):
        """Show initial state"""
        # Clear results
        while self.results_layout.count() > 1:
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add initial message
        initial = QLabel("🎧\n\nReady to identify music\nPlay some music and click LISTEN")
        initial.setAlignment(Qt.AlignCenter)
        initial.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 16px;")
        initial.setWordWrap(True)
        self.results_layout.insertWidget(0, initial)
    
    def _update_audio_devices(self):
        """Update audio device list"""
        import platform
        devices = []
        has_loopback = False
        
        try:
            import soundcard as sc
            default = sc.default_speaker()
            if default:
                name = default.name.encode('ascii', 'replace').decode()
                devices.append(f"{name} (Default)")
            for speaker in sc.all_speakers():
                if default and speaker.name == default.name:
                    continue
                name = speaker.name.encode('ascii', 'replace').decode()
                devices.append(name)
            
            # Check if loopback is available
            all_mics = sc.all_microphones(include_loopback=True)
            loopback_keywords = ['loopback', 'monitor', 'blackhole', 'soundflower', 'multi-output']
            for mic in all_mics:
                name_lower = mic.name.lower()
                if getattr(mic, 'isloopback', False) or any(kw in name_lower for kw in loopback_keywords):
                    has_loopback = True
                    break
        except Exception as e:
            print(f"Error detecting audio devices: {e}")
            devices.append("System Audio")
        
        self.device_combo.clear()
        self.device_combo.addItems(devices)
        if devices:
            self.audio_capture.set_selected_device(devices[0])
        
        # Show warning on macOS if no loopback device
        if platform.system() == "Darwin" and not has_loopback:
            self.status_label.setText("⚠️ BlackHole required for macOS")
            self.status_label.setStyleSheet("color: #f59e0b; font-size: 14px;")
    
    def _on_device_changed(self, device):
        if device and device != "Loading...":
            self.audio_capture.set_selected_device(device)
    
    def _toggle_listening(self):
        if self._is_listening:
            self._stop_listening()
        else:
            self._start_listening()
    
    def _start_listening(self):
        self._is_listening = True
        self.listen_btn.setText("🛑  STOP")
        self.status_label.setText("Listening...")
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        
        self.audio_capture.set_level_callback(
            lambda level: self.signals.update_level.emit(level)
        )
        
        threading.Thread(target=self._record_and_identify, daemon=True).start()
    
    def _stop_listening(self):
        self._is_listening = False
        self._is_continuous = False
        self.continuous_btn.setChecked(False)
        self.audio_capture.stop_recording()
        self.listen_btn.setText("🎤  LISTEN")
        self.status_label.setText("Stopped")
        self.progress_bar.hide()
        self.level_bar.setValue(0)
    
    def _toggle_continuous(self):
        """Toggle continuous scanning mode"""
        self._is_continuous = self.continuous_btn.isChecked()
        if self._is_continuous:
            self.status_label.setText("Auto-scan enabled")
            # Start listening if not already
            if not self._is_listening:
                self._start_listening()
        else:
            self.status_label.setText("Auto-scan disabled")
    
    def _record_and_identify(self):
        try:
            duration = getattr(config, 'RECORDING_DURATION', 5) if config else 5
            
            audio_data = self.audio_capture.capture_audio(
                duration=duration,
                progress_callback=lambda p: self.signals.update_progress.emit(p)
            )
            
            if not self._is_listening:
                return
            
            self.signals.update_status.emit("Identifying...")
            
            results = self.api_client.identify(audio_data)
            self.signals.update_results.emit(results)
            
        except AudioCaptureError as e:
            self.signals.show_error.emit(f"Audio error: {e}")
        except APIError as e:
            self.signals.show_error.emit(f"API error: {e}")
        except Exception as e:
            self.signals.show_error.emit(f"Error: {e}")
        finally:
            # Use signal to call finish_listening on main thread
            # QTimer.singleShot from background thread doesn't work!
            self.signals.finish_listening.emit()
    
    def _finish_listening(self):
        print(f"[DEBUG] _finish_listening called")
        print(f"[DEBUG] _is_continuous = {self._is_continuous}")
        print(f"[DEBUG] continuous_btn.isChecked() = {self.continuous_btn.isChecked()}")
        
        was_continuous = self._is_continuous
        self._is_listening = False
        self.listen_btn.setText("🎤  LISTEN")
        self.progress_bar.hide()
        # Don't reset level bar to 0, let it decay naturally
        
        # If continuous mode is on, restart listening after a short delay
        if was_continuous:
            print("[DEBUG] was_continuous is True, scheduling restart...")
            self.status_label.setText("Auto-scan: restarting in 2s...")
            QTimer.singleShot(2000, self._auto_restart_listening)
        else:
            print("[DEBUG] was_continuous is False, NOT restarting")
    
    def _auto_restart_listening(self):
        """Auto-restart listening in continuous mode"""
        print(f"[DEBUG] _auto_restart_listening called")
        print(f"[DEBUG] continuous_btn.isChecked() = {self.continuous_btn.isChecked()}")
        print(f"[DEBUG] _is_listening = {self._is_listening}")
        
        # Check button state directly to ensure it's still enabled
        if self.continuous_btn.isChecked() and not self._is_listening:
            print("[DEBUG] Conditions met, restarting...")
            self._is_continuous = True  # Ensure flag is synced
            self._start_listening()
        else:
            print("[DEBUG] Conditions NOT met, not restarting")
    
    def _on_status_update(self, status):
        self.status_label.setText(status)
    
    def _on_progress_update(self, progress):
        self.progress_bar.setValue(int(progress * 100))
    
    def _on_level_update(self, level):
        self.level_bar.setValue(int(level * 100))
    
    def _on_results_update(self, results):
        # Clear old results
        while self.results_layout.count() > 1:
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not results:
            self.status_label.setText("No matches found")
            self._show_initial_state()
            return
        
        # Show found message, but add auto-scan indicator if in continuous mode
        found_msg = f"Found {len(results)} match(es)"
        if self._is_continuous:
            found_msg += " • Auto-scan active"
        self.status_label.setText(found_msg)
        self.status_label.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 14px;")
        
        for i, song in enumerate(results, 1):
            card = SongCard(song, i)
            self.results_layout.insertWidget(self.results_layout.count() - 1, card)
    
    def _on_error(self, message):
        self.status_label.setText(message)
        self.status_label.setStyleSheet("color: #ef4444; font-size: 14px;")


def run_app():
    """Entry point"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = PortableShazamWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
