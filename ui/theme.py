"""MangasDdl 1.0 design tokens and Qt stylesheets."""
import re
from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QWidget

DARK = dict(bg='#101018', panel='#181822', input='#20202d', hover='#292938',
            text='#f5f3ff', muted='#aaa7be', border='#323142', accent='#a78bfa',
            primary='#7c3aed', primary_hover='#6d28d9', success='#4ade80', warning='#fbbf24', error='#fb7185')
LIGHT = dict(bg='#f5f4fa', panel='#ffffff', input='#f1eff8', hover='#e9e4f7',
             text='#25213b', muted='#67617a', border='#d9d4e6', accent='#6d28d9',
             primary='#7c3aed', primary_hover='#6d28d9', success='#15803d', warning='#a16207', error='#be123c')


def stylesheet(c):
    return f"""
    QWidget {{ background: {c['bg']}; color: {c['text']}; font-family: 'Segoe UI', 'DejaVu Sans'; font-size: 13px; }}
    QLabel {{ background: transparent; }}
    QFrame#Sidebar {{ background: {c['panel']}; border-right: 1px solid {c['border']}; }}
    QLabel#AppLogo {{ font-size: 25px; font-weight: 800; color: {c['text']}; padding: 8px 0; }}
    QLabel#AppSubtitle, QLabel#Muted {{ color: {c['muted']}; font-size: 12px; }}
    QLabel#PageTitle {{ font-size: 26px; font-weight: 800; }}
    QLabel#Eyebrow {{ color: {c['accent']}; font-size: 11px; font-weight: 700; }}
    QFrame#Card, QFrame#Hero {{ background: {c['panel']}; border: 1px solid {c['border']}; border-radius: 14px; }}
    QFrame#Hero {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {c['panel']},stop:1 {c['hover']}); }}
    QPushButton {{ background: {c['primary']}; color: #ffffff; border: none; border-radius: 8px; padding: 9px 14px; font-weight: 600; }}
    QPushButton:hover {{ background: {c['primary_hover']}; }}
    QPushButton:pressed {{ background: #5b21b6; }}
    QPushButton:disabled {{ background: {c['hover']}; color: {c['muted']}; }}
    QPushButton:focus, QComboBox:focus, QLineEdit:focus, QSpinBox:focus {{ border: 1px solid {c['accent']}; }}
    QPushButton#SecondaryButton, QPushButton#themeToggleBtn {{ background: {c['input']}; color: {c['text']}; border: 1px solid {c['border']}; }}
    QPushButton#SecondaryButton:hover, QPushButton#themeToggleBtn:hover {{ background: {c['hover']}; border-color: {c['accent']}; }}
    #Sidebar QPushButton {{ text-align: left; background: transparent; color: {c['muted']}; padding: 12px 14px; border-radius: 10px; }}
    #Sidebar QPushButton:hover {{ background: {c['hover']}; color: {c['text']}; }}
    #Sidebar QPushButton[active="true"] {{ background: {c['hover']}; color: {c['accent']}; font-weight: 700; border-left: 3px solid {c['accent']}; }}
    QLineEdit, QComboBox, QSpinBox {{ background: {c['input']}; border: 1px solid {c['border']}; border-radius: 8px; padding: 8px 10px; selection-background-color: {c['primary']}; }}
    QComboBox::drop-down {{ border: none; width: 22px; }}
    QComboBox QAbstractItemView {{ background: {c['panel']}; color: {c['text']}; selection-background-color: {c['hover']}; border: 1px solid {c['border']}; }}
    QListWidget, QTableWidget, QTextEdit, QTextBrowser {{ background: {c['panel']}; border: 1px solid {c['border']}; border-radius: 10px; alternate-background-color: {c['input']}; gridline-color: {c['border']}; selection-background-color: {c['hover']}; selection-color: {c['text']}; }}
    QListWidget::item {{ padding: 4px; border-bottom: 1px solid {c['border']}; }}
    QListWidget::item:selected, QListWidget::item:hover {{ background: {c['hover']}; border-radius: 8px; }}
    QHeaderView::section {{ background: {c['input']}; color: {c['muted']}; border: none; padding: 12px 8px; font-size: 11px; font-weight: 700; }}
    QTableWidget::item {{ padding: 6px; }}
    QProgressBar {{ background: {c['input']}; border: none; border-radius: 4px; text-align: center; color: {c['text']}; min-height: 6px; }}
    QProgressBar::chunk {{ background: {c['accent']}; border-radius: 4px; }}
    QScrollArea {{ border: none; background: transparent; }}
    QScrollBar:vertical {{ background: transparent; width: 8px; margin: 0; }}
    QScrollBar:horizontal {{ background: transparent; height: 8px; margin: 0; }}
    QScrollBar::handle {{ background: {c['border']}; border-radius: 4px; min-height: 24px; min-width: 24px; }}
    QScrollBar::handle:hover {{ background: {c['muted']}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
    QCheckBox {{ background: transparent; spacing: 8px; }}
    QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {c['border']}; border-radius: 4px; background: {c['input']}; }}
    QCheckBox::indicator:checked {{ background: {c['primary']}; border-color: {c['accent']}; }}
    QGroupBox {{ background: {c['panel']}; border: 1px solid {c['border']}; border-radius: 12px; margin-top: 18px; padding: 20px 14px 14px; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 14px; color: {c['accent']}; font-weight: 700; }}
    QMenuBar, QMenu {{ background: {c['panel']}; color: {c['text']}; }}
    QMenuBar::item:selected, QMenu::item:selected {{ background: {c['hover']}; }}
    QMenu::item {{ padding: 8px 24px; }}
    QStatusBar {{ background: {c['panel']}; color: {c['muted']}; border-top: 1px solid {c['border']}; font-size: 11px; }}
    QToolTip {{ background: {c['panel']}; color: {c['text']}; border: 1px solid {c['border']}; padding: 8px; }}
    QSplitter::handle {{ background: {c['bg']}; }}
    """


# Translate existing widget-specific accents so dynamic cards also follow the theme.
LEGACY_ROLES = {
    'bg': ['#06080c','#080a0f','#05070d','#0a0e1a'],
    'panel': ['#0f1420','#111726','#111420','#0f172a','#161e30','#1a1d2b'],
    'input': ['#1a2030','#1a243a'], 'hover': ['#1a2234','#1e293b'],
    'border': ['#28344d','#263147','#334155'],
    'text': ['#f8fafc','#e2e8f0','#cbd5e1'], 'muted': ['#94a3b8','#64748b','#475569'],
    'accent': ['#38bdf8','#7dd3fc','#60a5fa','#93c5fd'],
    'primary': ['#0284c7','#0ea5e9'], 'primary_hover': ['#0369a1'],
    'success': ['#4ade80'], 'warning': ['#fbbf24'], 'error': ['#f87171','#ef4444'],
}


class ThemeManager(QObject):
    THEME_DARK = 'dark'
    THEME_LIGHT = 'light'

    def __init__(self):
        super().__init__()
        self.current_theme = 'dark'
        self._updating = False
        self._installed = False

    @property
    def colors(self):
        return DARK if self.is_dark else LIGHT

    def get_theme(self, theme_name=None):
        return stylesheet(LIGHT if (theme_name or self.current_theme) == 'light' else DARK)

    def set_theme(self, theme_name):
        if theme_name in ('dark', 'light'):
            self.current_theme = theme_name

    def toggle_theme(self):
        self.set_theme('light' if self.is_dark else 'dark')
        return self.current_theme

    @property
    def is_dark(self):
        return self.current_theme == 'dark'

    @property
    def is_light(self):
        return not self.is_dark

    def adapt_widget(self, widget):
        source = widget.styleSheet()
        last = widget.property('_theme_output')
        if source != last:
            widget.setProperty('_theme_source', source)
        source = widget.property('_theme_source') or source
        mapping = {old: self.colors[role] for role, olds in LEGACY_ROLES.items() for old in olds}
        output = re.sub(r'#[0-9a-fA-F]{6}(?![0-9a-fA-F])', lambda m: mapping.get(m[0].lower(), m[0]), source)
        self._updating = True
        try:
            widget.setProperty('_theme_output', output)
            if widget.styleSheet() != output:
                widget.setStyleSheet(output)
        finally:
            self._updating = False

    def apply(self, app):
        if not self._installed:
            app.installEventFilter(self)
            self._installed = True
        self._updating = True
        app.setStyleSheet(self.get_theme())
        self._updating = False
        for widget in app.allWidgets():
            self.adapt_widget(widget)

    def eventFilter(self, obj, event):
        if not self._updating and isinstance(obj, QWidget) and event.type() in (QEvent.StyleChange, QEvent.Show):
            self.adapt_widget(obj)
        return False


theme_manager = ThemeManager()
DARK_THEME_QSS = stylesheet(DARK)
LIGHT_THEME_QSS = stylesheet(LIGHT)
