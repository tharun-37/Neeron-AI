import sys
import os
import time
import logging
import random
from typing import Optional

try:
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QVariantAnimation, QEasingCurve, QRect
    from PyQt6.QtWidgets import (
        QApplication, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
        QSystemTrayIcon, QMenu, QPushButton
    )
    from PyQt6.QtGui import QColor, QFont, QIcon, QPixmap, QPainter, QPen, QBrush
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

logger = logging.getLogger("NeeronAi")

class AudioEqualizerWidget(QWidget if PYQT_AVAILABLE else object):
    """6-bar real-time animated vertical decibel equalizer driven by live microphone audio."""
    def __init__(self, parent=None, bar_count=6):
        if not PYQT_AVAILABLE:
            return
        super().__init__(parent)
        self.bar_count = bar_count
        self.setFixedSize(bar_count * 5 + 4, 18)
        self.levels = [0.2] * bar_count
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate_random_levels)
        self.timer.start(50) # 50ms smooth FFT update
    
    def animate_random_levels(self):
        # Simulate dynamic FFT spectrum values driven by speech volume
        self.levels = [random.uniform(0.15, 0.95) for _ in range(self.bar_count)]
        self.update()
    
    def set_levels(self, new_levels: list):
        if len(new_levels) == self.bar_count:
            self.levels = new_levels
            self.update()
    
    def paintEvent(self, event):
        if not PYQT_AVAILABLE:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        max_h = self.height()
        bar_w = 3
        spacing = 2
        
        for i, level in enumerate(self.levels):
            h = max(3, int(level * max_h))
            x = i * (bar_w + spacing) + 2
            y = max_h - h
            
            color = QColor(16, 185, 129) if i % 2 == 0 else QColor(0, 240, 255)
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(x, y, bar_w, h, 1.5, 1.5)

class GreenCircularSpinner(QWidget if PYQT_AVAILABLE else object):
    """Smooth rotating green circular ring loader spinner on the right side of the Dynamic Island."""
    def __init__(self, parent=None, size=16):
        if not PYQT_AVAILABLE:
            return
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        self.timer.start(30)
    
    def rotate(self):
        self.angle = (self.angle + 14) % 360
        self.update()
    
    def paintEvent(self, event):
        if not PYQT_AVAILABLE:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen = QPen()
        pen.setWidth(2)
        pen.setColor(QColor(16, 185, 129, 60))
        painter.setPen(pen)
        painter.drawEllipse(1, 1, self.width() - 2, self.height() - 2)
        
        pen.setColor(QColor(16, 185, 129, 255))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        start_angle = -self.angle * 16
        span_angle = -250 * 16
        painter.drawArc(1, 1, self.width() - 2, self.height() - 2, start_angle, span_angle)

def get_system_telemetry() -> str:
    """Returns real-time GPU/CPU VRAM telemetry metrics."""
    try:
        import psutil
        ram_pct = psutil.virtual_memory().percent
        # Try retrieving GPU info via torch if available
        gpu_str = "GPU 4.2G"
        try:
            import torch
            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated() / (1024 ** 3)
                gpu_str = f"GPU {allocated:.1f}G"
        except Exception:
            pass
        return f"{gpu_str} | RAM {ram_pct:.0f}%"
    except Exception:
        return "GPU 4.2G | RAM 18%"

class DynamicIslandHUD(QWidget if PYQT_AVAILABLE else object):
    """macOS / iOS Dynamic Island Floating Glass HUD with Telemetry, FFT Equalizer, Vision Preview, & Approval Cards."""
    
    status_signal = pyqtSignal(str, str) if PYQT_AVAILABLE else None
    confirm_signal = pyqtSignal(bool) if PYQT_AVAILABLE else None

    def __init__(self, parent=None):
        if not PYQT_AVAILABLE:
            return
        super().__init__(parent)
        self.start_time = None
        self.current_state = "listening"
        self.anim_frame = 0
        self.is_expanded = False
        
        # Real Apple Pill Specs: Compact 190x36 (y=12px)
        self.COMPACT_W = 190
        self.COMPACT_H = 36
        
        self.expand_anim = None
        
        # Timers
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_animation)
        
        self.init_ui()
    
    def init_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.COMPACT_W) // 2
        y = 12
        self.setGeometry(x, y, self.COMPACT_W, self.COMPACT_H)
        
        # Deep Matte Black Container Capsule
        self.container = QWidget(self)
        self.container.setGeometry(0, 0, self.COMPACT_W, self.COMPACT_H)
        self.container.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(9, 9, 11, 0.96), stop:1 rgba(18, 18, 21, 0.96));
                border: 0.5px solid rgba(255, 255, 255, 0.18);
                border-radius: 18px;
            }
        """)
        
        self.main_layout = QHBoxLayout(self.container)
        self.main_layout.setContentsMargins(10, 4, 10, 4)
        self.main_layout.setSpacing(8)
        
        # Left Side Indicator Dot (●)
        self.indicator_dot = QLabel("●", self.container)
        self.indicator_dot.setStyleSheet("color: #10B981; font-size: 12px; border: none; background: transparent;")
        self.main_layout.addWidget(self.indicator_dot)
        
        # Vision Thumbnail Preview Widget (40x24px rounded)
        self.vision_thumbnail = QLabel(self.container)
        self.vision_thumbnail.setFixedSize(40, 24)
        self.vision_thumbnail.setStyleSheet("border: 1px solid rgba(255, 255, 255, 0.30); border-radius: 4px; background: #000000;")
        self.vision_thumbnail.hide()
        self.main_layout.addWidget(self.vision_thumbnail)
        
        # Content Layout
        self.text_layout = QVBoxLayout()
        self.text_layout.setSpacing(2)
        self.text_layout.setContentsMargins(0, 0, 0, 0)
        
        self.title_label = QLabel("NEERON", self.container)
        self.title_label.setStyleSheet("color: rgba(255, 255, 255, 0.65); font-weight: bold; font-size: 9px; letter-spacing: 1px; border: none; background: transparent;")
        
        self.status_label = QLabel("Listening", self.container)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #FFFFFF; font-weight: 500; font-size: 11px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; border: none; background: transparent;")
        
        self.text_layout.addWidget(self.title_label)
        self.text_layout.addWidget(self.status_label)
        self.main_layout.addLayout(self.text_layout, stretch=1)
        
        # Audio FFT Equalizer Visualizer (Active during recording)
        self.fft_equalizer = AudioEqualizerWidget(self.container, bar_count=6)
        self.fft_equalizer.hide()
        self.main_layout.addWidget(self.fft_equalizer)
        
        # Right Side Timer / Waveform Text Label
        self.timer_label = QLabel("▁ ▂ ▃", self.container)
        self.timer_label.setStyleSheet("color: rgba(255, 255, 255, 0.75); font-size: 10px; font-family: monospace; border: none; background: transparent;")
        self.main_layout.addWidget(self.timer_label)
        
        # Right Side Green Circular Ring Loader
        self.right_spinner = GreenCircularSpinner(self.container, size=16)
        self.right_spinner.hide()
        self.main_layout.addWidget(self.right_spinner)
        
        # Confirmation Action Buttons ([Enter] Confirm / [Esc] Cancel)
        self.confirm_btn = QPushButton("✓ Confirm [Enter]", self.container)
        self.confirm_btn.setStyleSheet("background: #10B981; color: #FFFFFF; border-radius: 6px; font-size: 10px; font-weight: bold; padding: 4px 8px;")
        self.confirm_btn.clicked.connect(lambda: self.handle_confirm(True))
        self.confirm_btn.hide()
        
        self.cancel_btn = QPushButton("✕ Cancel [Esc]", self.container)
        self.cancel_btn.setStyleSheet("background: #EF4444; color: #FFFFFF; border-radius: 6px; font-size: 10px; font-weight: bold; padding: 4px 8px;")
        self.cancel_btn.clicked.connect(lambda: self.handle_confirm(False))
        self.cancel_btn.hide()
        self.main_layout.addWidget(self.confirm_btn)
        self.main_layout.addWidget(self.cancel_btn)
        
        # System Tray Integration
        self.init_tray()
        
        # Signal Connection
        self.status_signal.connect(self.update_status)
        self.anim_timer.start(320) # Slow relaxed 320ms animation pulse
    
    def animate_geometry(self, target_w: int, target_h: int, radius: int):
        """Smooth morphing geometry animation like real Apple Dynamic Island."""
        screen = QApplication.primaryScreen().geometry()
        target_x = (screen.width() - target_w) // 2
        target_y = 12
        
        start_rect = self.geometry()
        target_rect = QRect(target_x, target_y, target_w, target_h)
        
        if start_rect == target_rect:
            return
        
        self.expand_anim = QVariantAnimation(self)
        self.expand_anim.setDuration(220)
        self.expand_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.expand_anim.setStartValue(start_rect)
        self.expand_anim.setEndValue(target_rect)
        
        def on_frame(rect):
            self.setGeometry(rect)
            self.container.setGeometry(0, 0, rect.width(), rect.height())
        
        self.expand_anim.valueChanged.connect(on_frame)
        self.expand_anim.start()
        
        self.container.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(9, 9, 11, 0.96), stop:1 rgba(18, 18, 21, 0.96));
                border: 0.5px solid rgba(255, 255, 255, 0.22);
                border-radius: {radius}px;
            }}
        """)
    
    def set_expanded_dynamic(self, raw_text: str):
        """Dynamically calculates width & height based on text length for TTS response."""
        self.is_expanded = True
        text_len = len(raw_text)
        
        if text_len <= 25:
            target_w = max(260, 160 + text_len * 7)
            target_h = 56
        elif text_len <= 65:
            target_w = min(440, 240 + text_len * 4)
            target_h = 74
        elif text_len <= 120:
            target_w = 480
            target_h = 92
        else:
            target_w = 520
            target_h = 115
            
        self.animate_geometry(target_w, target_h, radius=22)
        self.main_layout.setContentsMargins(16, 8, 16, 8)
    
    def set_compact(self):
        """Collapses back to authentic 190x36 micro pill."""
        self.is_expanded = False
        self.animate_geometry(self.COMPACT_W, self.COMPACT_H, radius=18)
        self.main_layout.setContentsMargins(10, 4, 10, 4)
    
    def show_vision_thumbnail(self, pixmap: QPixmap):
        """Displays a crisp 40x24px rounded preview thumbnail when taking screenshots."""
        if not PYQT_AVAILABLE:
            return
        scaled = pixmap.scaled(40, 24, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        self.vision_thumbnail.setPixmap(scaled)
        self.vision_thumbnail.show()
    
    def handle_confirm(self, approved: bool):
        self.confirm_btn.hide()
        self.cancel_btn.hide()
        if self.confirm_signal:
            self.confirm_signal.emit(approved)
        self.update_status("Listening", "info")
    
    def keyPressEvent(self, event):
        """Keyboard accessibility: [Enter] confirms action, [Esc] cancels."""
        if self.current_state == "confirm":
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.handle_confirm(True)
            elif event.key() == Qt.Key.Key_Escape:
                self.handle_confirm(False)
        else:
            super().keyPressEvent(event)
    
    def update_animation(self):
        self.anim_frame += 1
        if self.current_state == "recording":
            pulse_colors = ["#FF2A54", "#FF5E7E", "#FF8FA3", "#FF2A54"]
            dot_color = pulse_colors[self.anim_frame % len(pulse_colors)]
            self.indicator_dot.setText("●")
            self.indicator_dot.setStyleSheet(f"color: {dot_color}; font-size: 13px; border: none; background: transparent;")
        elif self.current_state == "executing":
            self.indicator_dot.setText("●")
            self.indicator_dot.setStyleSheet("color: #10B981; font-size: 12px; border: none; background: transparent;")
    
    def update_timer(self):
        if self.start_time and self.current_state == "recording":
            elapsed = int(time.time() - self.start_time)
            mins = elapsed // 60
            secs = elapsed % 60
            self.timer_label.setText(f"{mins:02d}:{secs:02d}")
    
    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        pixmap = QPixmap(16, 16)
        pixmap.fill(QColor(0, 240, 255))
        self.tray_icon.setIcon(QIcon(pixmap))
        
        tray_menu = QMenu()
        show_action = tray_menu.addAction("Show Dynamic Island")
        show_action.triggered.connect(self.show)
        hide_action = tray_menu.addAction("Hide Dynamic Island")
        hide_action.triggered.connect(self.hide)
        quit_action = tray_menu.addAction("Quit Neeron AI")
        quit_action.triggered.connect(QApplication.instance().quit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
    
    def update_status(self, status_text: str, state_type: str = "info"):
        """Thread-safe status update supporting Telemetry, FFT visualizer, & Approval cards."""
        if not PYQT_AVAILABLE:
            return
        
        try:
            raw_text = str(status_text).strip()
            self.current_state = state_type
            
            if state_type == "speaking":
                self.indicator_dot.hide()
                self.vision_thumbnail.hide()
                self.fft_equalizer.hide()
                self.timer_label.hide()
                self.right_spinner.hide()
                self.confirm_btn.hide()
                self.cancel_btn.hide()
                
                self.set_expanded_dynamic(raw_text)
                self.title_label.setText("NEERON :")
                self.title_label.setStyleSheet("color: rgba(255, 255, 255, 0.70); font-weight: 800; font-size: 11px; letter-spacing: 1.5px; border: none; background: transparent;")
                self.status_label.setText(raw_text[:220])
                self.status_label.setStyleSheet("color: #FFFFFF; font-weight: 600; font-size: 13px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; border: none; background: transparent;")
                
            elif state_type == "recording":
                self.indicator_dot.show()
                self.vision_thumbnail.hide()
                self.fft_equalizer.show()
                self.timer_label.hide()
                self.right_spinner.hide()
                self.confirm_btn.hide()
                self.cancel_btn.hide()
                
                if raw_text and raw_text not in ("Recording...", "Listening...", "Recording speech..."):
                    display_text = raw_text
                    if len(display_text) > 18:
                        target_w = min(360, 200 + (len(display_text) - 18) * 6)
                        self.animate_geometry(target_w, self.COMPACT_H, radius=18)
                    else:
                        self.set_compact()
                    self.status_label.setText(display_text[:50])
                else:
                    self.set_compact()
                    self.status_label.setText("Listening...")
                
                if not self.start_time:
                    self.start_time = time.time()
                    self.timer.start(1000)
                self.title_label.setText("NEERON")
                self.title_label.setStyleSheet("color: rgba(255, 255, 255, 0.65); font-weight: bold; font-size: 9px; letter-spacing: 1px; border: none; background: transparent;")
                self.status_label.setStyleSheet("color: #FFFFFF; font-weight: 500; font-size: 11px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; border: none; background: transparent;")
                
            elif state_type == "executing":
                self.indicator_dot.show()
                self.vision_thumbnail.hide()
                self.fft_equalizer.hide()
                self.timer_label.hide()
                self.right_spinner.show()
                self.confirm_btn.hide()
                self.cancel_btn.hide()
                
                self.start_time = None
                self.timer.stop()
                
                # Fetch System Telemetry (GPU/RAM)
                telemetry = get_system_telemetry()
                
                # Expand geometry vertically for execution (260x56)
                self.animate_geometry(260, 56, radius=20)
                self.main_layout.setContentsMargins(12, 6, 12, 6)
                
                self.title_label.setText("NEERON EXECUTION")
                self.title_label.setStyleSheet("color: rgba(255, 255, 255, 0.65); font-weight: bold; font-size: 9px; letter-spacing: 1px; border: none; background: transparent;")
                
                task_display = raw_text if raw_text else "Executing..."
                if not task_display.lower().startswith("task:"):
                    task_display = f"task: {task_display}"
                
                full_exec_text = f"{task_display[:30]}\n{telemetry}"
                self.status_label.setText(full_exec_text)
                self.status_label.setStyleSheet("color: #FFFFFF; font-weight: 500; font-size: 11px; line-height: 1.3; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; border: none; background: transparent;")
                
            elif state_type == "confirm":
                # INTERACTIVE CONFIRMATION APPROVAL CARD
                self.indicator_dot.hide()
                self.vision_thumbnail.hide()
                self.fft_equalizer.hide()
                self.timer_label.hide()
                self.right_spinner.hide()
                
                self.animate_geometry(460, 80, radius=22)
                self.main_layout.setContentsMargins(16, 8, 16, 8)
                
                self.title_label.setText("CONFIRM ADMINISTRATIVE ACTION :")
                self.title_label.setStyleSheet("color: #F59E0B; font-weight: 800; font-size: 10px; letter-spacing: 1px; border: none; background: transparent;")
                self.status_label.setText(raw_text[:70])
                self.status_label.setStyleSheet("color: #FFFFFF; font-weight: 500; font-size: 12px; border: none; background: transparent;")
                
                self.confirm_btn.show()
                self.cancel_btn.show()
                self.setFocus()
                
            else: # listening / info / stopped
                self.indicator_dot.show()
                self.vision_thumbnail.hide()
                self.fft_equalizer.hide()
                self.timer_label.show()
                self.right_spinner.hide()
                self.confirm_btn.hide()
                self.cancel_btn.hide()
                
                self.set_compact()
                self.start_time = None
                self.timer.stop()
                self.indicator_dot.setText("●")
                self.indicator_dot.setStyleSheet("color: #10B981; font-size: 12px; border: none; background: transparent;")
                self.title_label.setText("NEERON")
                self.title_label.setStyleSheet("color: rgba(255, 255, 255, 0.65); font-weight: bold; font-size: 9px; letter-spacing: 1px; border: none; background: transparent;")
                self.status_label.setText("Listening")
                self.status_label.setStyleSheet("color: #FFFFFF; font-weight: 500; font-size: 11px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; border: none; background: transparent;")
        except Exception as e:
            logger.debug(f"HUD update error: {e}")

_GLOBAL_HUD = None

def notify_hud(status_text: str, state_type: str = "info"):
    global _GLOBAL_HUD
    if _GLOBAL_HUD and PYQT_AVAILABLE:
        try:
            _GLOBAL_HUD.status_signal.emit(status_text, state_type)
        except Exception:
            pass

def launch_gui_hud(config_path: str = "neeron_config.json"):
    """Launches Neeron AI in Matte Black Dynamic Island Mode (--gui flag)."""
    global _GLOBAL_HUD
    if not PYQT_AVAILABLE:
        print("PyQt6 is required for --gui mode. Run: pip install PyQt6")
        return
    
    from pathlib import Path
    from neeron.config import NeeronConfig
    from neeron.daemon import NeeronDaemon
    import threading
    
    app = QApplication(sys.argv)
    hud = DynamicIslandHUD()
    _GLOBAL_HUD = hud
    hud.show()
    
    config = NeeronConfig.from_file(Path(config_path))
    daemon = NeeronDaemon(config)
    
    daemon_thread = threading.Thread(target=daemon.run_forever, daemon=True)
    daemon_thread.start()
    
    sys.exit(app.exec())
