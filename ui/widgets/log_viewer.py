import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QLabel, QHBoxLayout, QPushButton, QComboBox, QApplication
)
from PySide6.QtGui import QTextCursor

class LogViewerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._raw_logs = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Console d'activité")
        title.setStyleSheet("font-size: 13px; font-weight: bold; color: #94a3b8;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Tous les logs", "INFO", "SUCCESS", "WARNING", "ERROR"])
        self.filter_combo.setFixedWidth(130)
        self.filter_combo.currentTextChanged.connect(self.apply_filter)
        header_layout.addWidget(self.filter_combo)

        copy_btn = QPushButton("Copier")
        copy_btn.setObjectName("SecondaryButton")
        copy_btn.clicked.connect(self.copy_logs)
        header_layout.addWidget(copy_btn)

        clear_btn = QPushButton("Effacer")
        clear_btn.setObjectName("SecondaryButton")
        clear_btn.clicked.connect(self.clear_logs)
        header_layout.addWidget(clear_btn)

        layout.addLayout(header_layout)

        # Text edit pour les logs
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #0d1017;
                color: #e2e8f0;
                border: 1px solid #1e2436;
                border-radius: 8px;
                font-family: 'Consolas', 'Cascadia Code', monospace;
                font-size: 11px;
                padding: 6px;
            }
        """)
        layout.addWidget(self.log_text)

    def log(self, level: str, message: str):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self._raw_logs.append((timestamp, level, message))
        self._append_formatted(timestamp, level, message)

    def _append_formatted(self, timestamp: str, level: str, message: str):
        color = "#38bdf8"  # INFO (Cyan)

        if level == "SUCCESS":
            color = "#4ade80"  # Vert
        elif level == "WARNING":
            color = "#fbbf24"  # Jaune
        elif level == "ERROR":
            color = "#f87171"  # Rouge

        formatted_msg = f'<span style="color: #64748b;">[{timestamp}]</span> <b style="color: {color};">[{level}]</b> {message}'
        self.log_text.append(formatted_msg)
        self.log_text.moveCursor(QTextCursor.End)

    def apply_filter(self, filter_level: str):
        self.log_text.clear()
        for ts, lvl, msg in self._raw_logs:
            if filter_level == "Tous les logs" or lvl == filter_level:
                self._append_formatted(ts, lvl, msg)

    def copy_logs(self):
        plain_text = self.log_text.toPlainText()
        if plain_text:
            QApplication.clipboard().setText(plain_text)

    def clear_logs(self):
        self._raw_logs.clear()
        self.log_text.clear()
