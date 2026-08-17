from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QColor, QPen, QLinearGradient, QFont
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, 
                               QProgressBar, QGraphicsDropShadowEffect)

class SplashScreen(QWidget):
    finished = Signal()

    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SplashScreen)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(600, 380)

        # Main Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        
        layout.addStretch(1)

        # Title
        self.title_label = QLabel("MangasDdl", self)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #e2e8f0;
                font-size: 42px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        layout.addWidget(self.title_label)

        # Subtitle
        self.subtitle_label = QLabel("Téléchargeur & Lecteur de Mangas", self)
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        self.subtitle_label.setStyleSheet("""
            QLabel {
                color: #94a3b8;
                font-size: 14px;
                font-family: 'Segoe UI', Arial, sans-serif;
                margin-top: 5px;
            }
        """)
        layout.addWidget(self.subtitle_label)

        layout.addStretch(1)

        # Status text
        self.status_label = QLabel("Initialisation...", self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #64748b;
                font-size: 12px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1e293b;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #0ea5e9,
                    stop: 1 #38bdf8
                );
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Opacity animation
        self.setWindowOpacity(0.0)
        self.fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_anim.setDuration(800)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.setEasingCurve(QEasingCurve.InOutQuad)
        
        # Loading steps
        self.steps = [
            ("Initialisation...", 15, 300),
            ("Chargement des sources...", 45, 1000),
            ("Préparation de l'interface...", 80, 1800),
            ("Prêt !", 100, 2500)
        ]
        self.current_step = 0
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)
        self.time_elapsed = 0
        
    def start(self):
        self.fade_anim.start()
        self.timer.start(50) # 50ms interval

    def update_progress(self):
        self.time_elapsed += 50
        
        if self.current_step < len(self.steps):
            text, target_val, target_time = self.steps[self.current_step]
            
            if self.time_elapsed >= target_time:
                self.progress_bar.setValue(target_val)
                self.status_label.setText(text)
                self.current_step += 1
            else:
                # Interpolate
                prev_val = 0 if self.current_step == 0 else self.steps[self.current_step-1][1]
                prev_time = 0 if self.current_step == 0 else self.steps[self.current_step-1][2]
                
                progress = (self.time_elapsed - prev_time) / (target_time - prev_time)
                current_val = prev_val + int((target_val - prev_val) * progress)
                self.progress_bar.setValue(current_val)
                
        elif self.time_elapsed > 2700: # Wait a bit after 100%
            self.timer.stop()
            
            # Fade out
            self.fade_out = QPropertyAnimation(self, b"windowOpacity")
            self.fade_out.setDuration(500)
            self.fade_out.setStartValue(1.0)
            self.fade_out.setEndValue(0.0)
            self.fade_out.finished.connect(self.finished.emit)
            self.fade_out.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background gradient
        bg_gradient = QLinearGradient(0, 0, self.width(), self.height())
        bg_gradient.setColorAt(0.0, QColor("#0a0e1a"))
        bg_gradient.setColorAt(1.0, QColor("#0f172a"))

        # Draw rounded rect with border
        rect = self.rect().adjusted(2, 2, -2, -2)
        painter.setBrush(bg_gradient)
        painter.setPen(QPen(QColor("#38bdf8"), 1.5))
        painter.drawRoundedRect(rect, 16, 16)
