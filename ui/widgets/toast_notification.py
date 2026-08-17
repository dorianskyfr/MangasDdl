"""
Toast Notification Widget v2.0
=============================

Widget de notifications toast pour l'application.
- Support des notifications de succes, erreur, info, avertissement
- Animation d'apparition/disparition fluide
- Positionnement flexible
- Auto-destruction apres timeout
- Gestion de multiples notifications en pile

Utilisation :
    from ui.widgets.toast_notification import ToastNotification, ToastManager
    
    # Creer une notification simple
    ToastNotification.show("Telechargement termine", "Le chapitre a ete telecharge avec succes", "success")
    
    # Avec duree personnalisee (en secondes)
    ToastNotification.show("Info", "Nouvelle mise a jour disponible", "info", duration=5)
"""

from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QFrame, QApplication
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, Signal
from PySide6.QtGui import QColor


class ToastNotification(QFrame):
    """
    Widget de notification toast unique avec animations.
    
    Args:
        title: Titre de la notification
        message: Message de la notification
        toast_type: Type ("info", "success", "warning", "error")
        duration: Duree en secondes (0 = jamais)
        parent: Widget parent
    """
    
    closed = Signal()
    
    LEVEL_COLORS = {
        "info": "#3b82f6",
        "success": "#22c55e",
        "warning": "#f59e0b",
        "error": "#ef4444",
    }
    
    LEVEL_ICONS = {
        "info": "i",
        "success": "OK",
        "warning": "!",
        "error": "X",
    }
    
    BG_COLORS = {
        "dark": "#1e293b",
        "light": "#e2e8f0",
    }
    
    def __init__(self, title: str, message: str, toast_type: str = "info", 
                 duration: int = 3, parent: QWidget = None):
        super().__init__(parent)
        self._title = title
        self._message = message
        self._type = (toast_type or "info").lower()
        self._duration = duration
        self._timer = None
        self._animation = None
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.ToolTip)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.init_ui()
        self.apply_style()
        
        self.start_show_animation()
        
        if duration > 0:
            self._timer = QTimer(self)
            self._timer.timeout.connect(self.close)
            self._timer.start(duration * 1000)
    
    def init_ui(self):
        self.setFixedWidth(360)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)
        
        icon_label = QLabel(self.LEVEL_ICONS.get(self._type, "i"))
        icon_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(icon_label)
        
        content_layout = QVBoxLayout()
        content_layout.setSpacing(2)
        
        title_label = QLabel(self._title)
        level_color = self.LEVEL_COLORS.get(self._type, "#3b82f6")
        title_label.setStyleSheet(f"color: {level_color}; font-weight: bold; font-size: 13px;")
        content_layout.addWidget(title_label)
        
        message_label = QLabel(self._message)
        message_label.setStyleSheet("color: #f8fafc; font-size: 13px;")
        message_label.setWordWrap(True)
        content_layout.addWidget(message_label)
        
        layout.addLayout(content_layout)
        layout.addStretch()
    
    def apply_style(self):
        try:
            from ui.theme import theme_manager
            is_dark = theme_manager.is_dark if hasattr(theme_manager, 'is_dark') else True
        except:
            is_dark = True
        
        bg_color = self.BG_COLORS.get("dark" if is_dark else "light", "#1e293b")
        border_color = "#1e293b" if is_dark else "#cbd5e1"
        level_color = self.LEVEL_COLORS.get(self._type, "#3b82f6")
        
        self.setStyleSheet(f"""
            ToastNotification {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
                border-left: 4px solid {level_color};
            }}
        """)
    
    def start_show_animation(self):
        self.setOpacity(0)
        self.show()
        
        self._animation = QPropertyAnimation(self, b"opacity")
        self._animation.setDuration(300)
        self._animation.setStartValue(0)
        self._animation.setEndValue(1)
        self._animation.setEasingCurve(QEasingCurve.OutQuad)
        self._animation.start()
    
    def start_hide_animation(self):
        if self._timer:
            self._timer.stop()
        
        self._animation = QPropertyAnimation(self, b"opacity")
        self._animation.setDuration(250)
        self._animation.setStartValue(1)
        self._animation.setEndValue(0)
        self._animation.setEasingCurve(QEasingCurve.InQuad)
        self._animation.finished.connect(self.deleteLater)
        self._animation.start()
    
    def closeEvent(self, event):
        self.start_hide_animation()
        self.closed.emit()
        event.accept()
    
    def mousePressEvent(self, event):
        self.close()
        event.accept()
    
    @staticmethod
    def show(title: str, message: str, toast_type: str = "info", 
             duration: int = 3, parent: QWidget = None):
        toast = ToastNotification(title, message, toast_type, duration, parent)
        
        if parent:
            parent_pos = parent.mapToGlobal(parent.rect().bottomRight())
            toast.move(
                parent_pos.x() - toast.width() - 20,
                parent_pos.y() - toast.height() - 20
            )
        else:
            from PySide6.QtGui import QScreen, QGuiApplication
            screen = QGuiApplication.primaryScreen()
            screen_geom = screen.geometry()
            toast.move(
                screen_geom.width() - toast.width() - 20,
                screen_geom.height() - toast.height() - 20
            )
        
        return toast


class ToastManager(QWidget):
    """Gestionnaire de notifications toast en pile."""
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._toasts = []
        self._parent = parent
        self._spacing = 12
        self._max_toasts = 5
    
    def show(self, title: str, message: str, toast_type: str = "info", 
             duration: int = 3):
        toast = ToastNotification(title, message, toast_type, duration, self._parent)
        self._toasts.append(toast)
        toast.closed.connect(lambda: self._on_toast_closed(toast))
        self._reposition_toasts()
        
        if len(self._toasts) > self._max_toasts:
            oldest = self._toasts.pop(0)
            oldest.close()
        
        return toast
    
    def _on_toast_closed(self, toast):
        if toast in self._toasts:
            self._toasts.remove(toast)
            self._reposition_toasts()
    
    def _reposition_toasts(self):
        if not self._parent:
            return
        
        parent_pos = self._parent.mapToGlobal(self._parent.rect().bottomRight())
        y_offset = 20
        for toast in reversed(self._toasts):
            if toast.isVisible():
                toast.move(
                    parent_pos.x() - toast.width() - 20,
                    parent_pos.y() - y_offset - toast.height()
                )
                y_offset += toast.height() + self._spacing
    
    def clear_all(self):
        for toast in self._toasts[:]:
            toast.close()
        self._toasts.clear()
    
    def info(self, title: str, message: str, duration: int = 3):
        return self.show(title, message, "info", duration)
    
    def success(self, title: str, message: str, duration: int = 3):
        return self.show(title, message, "success", duration)
    
    def warning(self, title: str, message: str, duration: int = 3):
        return self.show(title, message, "warning", duration)
    
    def error(self, title: str, message: str, duration: int = 3):
        return self.show(title, message, "error", duration)


_toast_manager = None


def get_toast_manager(parent: QWidget = None) -> ToastManager:
    global _toast_manager
    if _toast_manager is None:
        _toast_manager = ToastManager(parent)
    return _toast_manager


def show_toast(title: str, message: str, toast_type: str = "info", 
               duration: int = 3, parent: QWidget = None):
    ToastNotification.show(title, message, toast_type, duration, parent)


def toast_info(title: str, message: str, duration: int = 3):
    manager = get_toast_manager()
    manager.info(title, message, duration)


def toast_success(title: str, message: str, duration: int = 3):
    manager = get_toast_manager()
    manager.success(title, message, duration)


def toast_warning(title: str, message: str, duration: int = 3):
    manager = get_toast_manager()
    manager.warning(title, message, duration)


def toast_error(title: str, message: str, duration: int = 3):
    manager = get_toast_manager()
    manager.error(title, message, duration)
