"""
Systeme de design premium & responsive (UI v0.1)
Inspire par le design moderne Glassmorphism & Obsidian Dark.
Supporte les themes Sombre et Clair avec animations fluides.
"""

# ============================================================================
# COLORS - Dark Theme (Default)
# ============================================================================
DARK_BG_PRIMARY = "#06080c"
DARK_BG_SECONDARY = "#080a0f"
DARK_BG_TERTIARY = "#0f1420"
DARK_BG_CARD = "#111726"
DARK_BG_INPUT = "#161e30"
DARK_BG_HOVER = "#1a2234"

DARK_TEXT_PRIMARY = "#f8fafc"
DARK_TEXT_SECONDARY = "#cbd5e1"
DARK_TEXT_MUTED = "#94a3b8"
DARK_TEXT_DISABLED = "#475569"

DARK_BORDER = "#1e293b"
DARK_BORDER_LIGHT = "#334155"
DARK_BORDER_ACCENT = "#38bdf8"

DARK_ACCENT = "#38bdf8"
DARK_ACCENT_LIGHT = "#7dd3fc"
DARK_ACCENT_DARK = "#0284c7"
DARK_SUCCESS = "#4ade80"
DARK_WARNING = "#fbbf24"
DARK_ERROR = "#f87171"

# ============================================================================
# COLORS - Light Theme
# ============================================================================
LIGHT_BG_PRIMARY = "#f8fafc"
LIGHT_BG_SECONDARY = "#f1f5f9"
LIGHT_BG_TERTIARY = "#e2e8f0"
LIGHT_BG_CARD = "#ffffff"
LIGHT_BG_INPUT = "#f8fafc"
LIGHT_BG_HOVER = "#e2e8f0"

LIGHT_TEXT_PRIMARY = "#0f172a"
LIGHT_TEXT_SECONDARY = "#475569"
LIGHT_TEXT_MUTED = "#64748b"
LIGHT_TEXT_DISABLED = "#94a3b8"

LIGHT_BORDER = "#e2e8f0"
LIGHT_BORDER_LIGHT = "#cbd5e1"
LIGHT_BORDER_ACCENT = "#38bdf8"

LIGHT_ACCENT = "#38bdf8"
LIGHT_ACCENT_LIGHT = "#7dd3fc"
LIGHT_ACCENT_DARK = "#0284c7"
LIGHT_SUCCESS = "#4ade80"
LIGHT_WARNING = "#fbbf24"
LIGHT_ERROR = "#f87171"

# ============================================================================
# ANIMATIONS
# ============================================================================
ANIMATIONS_QSS = """
/* Animations de transition fluides */
QWidget {
    transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

QPushButton {
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

QLineEdit, QComboBox, QSpinBox {
    transition: border-color 0.2s ease, background-color 0.2s ease, box-shadow 0.2s ease;
}

QTableWidget::item, QListWidget::item {
    transition: background-color 0.15s ease, color 0.15s ease;
}

QProgressBar::chunk {
    transition: background-color 0.3s ease;
}

/* Effet de ripple pour les boutons (simule) */
QPushButton:pressed {
    transform: scale(0.98);
}
"""

# ============================================================================
# DARK THEME
# ============================================================================
DARK_THEME_QSS = f"""
/* ========================================================================
   THEME SOMBRE - Antigravity Manga Downloader v3.0
   ======================================================================== */

{ANIMATIONS_QSS}

/* ---------------------------------------------------------------
   Style General & Typographie
   --------------------------------------------------------------- */
QWidget {{
    background-color: {DARK_BG_SECONDARY};
    color: {DARK_TEXT_PRIMARY};
    font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 13px;
}}

QMainWindow {{
    background-color: {DARK_BG_PRIMARY};
}}

/* ---------------------------------------------------------------
   Scrollbars Modernes
   --------------------------------------------------------------- */
QScrollBar:vertical {{
    background: {DARK_BG_PRIMARY};
    width: 10px;
    border-radius: 5px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: {DARK_BG_TERTIARY};
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {DARK_ACCENT};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
    width: 0px;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}

/* ---------------------------------------------------------------
   Barre laterale (Sidebar Navigation)
   --------------------------------------------------------------- */
#Sidebar {{
    background-color: {DARK_BG_TERTIARY};
    border-right: 1px solid {DARK_BORDER};
}}

#Sidebar QLabel#AppLogo {{
    font-size: 24px;
    font-weight: 800;
    color: {DARK_ACCENT};
    padding: 12px 8px 4px 8px;
    letter-spacing: 0.5px;
}}

#Sidebar QLabel#AppSubtitle {{
    font-size: 11px;
    color: {DARK_TEXT_MUTED};
    padding-left: 8px;
    margin-bottom: 16px;
}}

#Sidebar QPushButton {{
    background-color: transparent;
    color: {DARK_TEXT_MUTED};
    border: 1px solid transparent;
    border-radius: 12px;
    padding: 12px 16px;
    text-align: left;
    font-weight: 600;
    font-size: 13px;
}}

#Sidebar QPushButton:hover {{
    background-color: {DARK_BG_HOVER};
    color: {DARK_ACCENT};
    border: 1px solid {DARK_BORDER_LIGHT};
}}

#Sidebar QPushButton:checked, #Sidebar QPushButton[active="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {DARK_ACCENT}, stop:1 {DARK_ACCENT_DARK});
    color: {DARK_TEXT_PRIMARY};
    font-weight: bold;
    border: 1px solid {DARK_ACCENT};
    box-shadow: 0 4px 12px rgba(2, 132, 199, 0.25);
}}

#Sidebar QPushButton:disabled {{
    color: {DARK_TEXT_DISABLED};
    background-color: transparent;
}}

/* ---------------------------------------------------------------
   Champs de saisie & ComboBoxes
   --------------------------------------------------------------- */
QLineEdit, QComboBox, QSpinBox {{
    background-color: {DARK_BG_INPUT};
    border: 1px solid {DARK_BORDER};
    border-radius: 8px;
    padding: 9px 14px;
    color: {DARK_TEXT_PRIMARY};
    selection-background-color: {DARK_ACCENT};
    selection-color: {DARK_TEXT_PRIMARY};
}}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border: 1px solid {DARK_ACCENT};
    background-color: {DARK_BG_TERTIARY};
    outline: none;
}}

QLineEdit:hover:!focus, QComboBox:hover:!focus, QSpinBox:hover:!focus {{
    border: 1px solid {DARK_BORDER_LIGHT};
}}

QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{
    background-color: {DARK_BG_TERTIARY};
    color: {DARK_TEXT_DISABLED};
    border-color: {DARK_BORDER};
}}

QComboBox::drop-down {{
    border: none;
    padding-right: 10px;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background-color: {DARK_BG_TERTIARY};
    border: 1px solid {DARK_BORDER};
    selection-background-color: {DARK_ACCENT};
    color: {DARK_TEXT_PRIMARY};
    padding: 4px;
    outline: none;
}}

/* ---------------------------------------------------------------
   Boutons d'action (Primary, Secondary & Pill Tabs)
   --------------------------------------------------------------- */
QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {DARK_ACCENT}, stop:1 {DARK_ACCENT_DARK});
    color: {DARK_TEXT_PRIMARY};
    border: 1px solid {DARK_ACCENT};
    border-radius: 8px;
    padding: 9px 18px;
    font-weight: 600;
    font-size: 13px;
    min-width: 80px;
}}

QPushButton:hover:!disabled {{
    background: qlinear-gradient(x1:0, y1:0, x2:1, y2:0, stop:0 {DARK_ACCENT_LIGHT}, stop:1 {DARK_ACCENT});
    border-color: {DARK_ACCENT_LIGHT};
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(56, 189, 248, 0.3);
}}

QPushButton:pressed:!disabled {{
    background-color: {DARK_ACCENT_DARK};
    border-color: {DARK_ACCENT_DARK};
    transform: translateY(0px);
}}

QPushButton:disabled {{
    background-color: {DARK_BG_TERTIARY};
    color: {DARK_TEXT_DISABLED};
    border: 1px solid {DARK_BORDER};
    transform: none;
}}

/* Bouton secondaire */
QPushButton#SecondaryButton {{
    background-color: {DARK_BG_TERTIARY};
    color: {DARK_TEXT_SECONDARY};
    border: 1px solid {DARK_BORDER};
}}

QPushButton#SecondaryButton:hover {{
    background-color: {DARK_BG_HOVER};
    color: {DARK_TEXT_PRIMARY};
    border-color: {DARK_BORDER_LIGHT};
}}

QPushButton#SecondaryButton:pressed {{
    background-color: {DARK_BG_INPUT};
    border-color: {DARK_BORDER};
}}

QPushButton#SecondaryButton:disabled {{
    background-color: {DARK_BG_TERTIARY};
    color: {DARK_TEXT_DISABLED};
    border-color: {DARK_BORDER};
}}

/* Bouton danger */
QPushButton#DangerButton {{
    background-color: {DARK_ERROR};
    color: white;
    border: 1px solid {DARK_ERROR};
}}

QPushButton#DangerButton:hover {{
    background-color: #ef4444;
    border-color: #ef4444;
}}

/* Bouton succes */
QPushButton#SuccessButton {{
    background-color: {DARK_SUCCESS};
    color: white;
    border: 1px solid {DARK_SUCCESS};
}}

QPushButton#SuccessButton:hover {{
    background-color: #22c55e;
    border-color: #22c55e;
}}

/* Style des onglets filtres (Checkable buttons) */
QPushButton[checkable="true"] {{
    background-color: {DARK_BG_TERTIARY};
    color: {DARK_TEXT_MUTED};
    border: 1px solid {DARK_BORDER};
    border-radius: 14px;
    padding: 4px 14px;
    font-size: 12px;
}}

QPushButton[checkable="true"]:hover {{
    background-color: {DARK_BG_HOVER};
    color: {DARK_ACCENT};
}}

QPushButton[checkable="true"]:checked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {DARK_ACCENT}, stop:1 {DARK_ACCENT_DARK});
    color: {DARK_TEXT_PRIMARY};
    border: 1px solid {DARK_ACCENT};
    font-weight: bold;
}}

/* ---------------------------------------------------------------
   Cartes & Panneaux (Obsidian Cards)
   --------------------------------------------------------------- */
QFrame#Card {{
    background-color: {DARK_BG_CARD};
    border: 1px solid {DARK_BORDER};
    border-radius: 12px;
}}

QFrame#CrossSourceCard {{
    background-color: {DARK_BG_TERTIARY};
    border: 1px solid {DARK_ACCENT};
    border-radius: 8px;
    padding: 6px 12px;
    margin-top: 4px;
}}

/* ---------------------------------------------------------------
   Tableaux & Listes
   --------------------------------------------------------------- */
QTableWidget, QListWidget {{
    background-color: {DARK_BG_PRIMARY};
    border: 1px solid {DARK_BORDER};
    border-radius: 10px;
    gridline-color: {DARK_BORDER};
    outline: none;
}}

QTableWidget::item, QListWidget::item {{
    padding: 8px 12px;
    border-bottom: 1px solid {DARK_BORDER};
}}

QTableWidget::item:hover, QListWidget::item:hover {{
    background-color: {DARK_BG_HOVER};
}}

QTableWidget::item:selected, QListWidget::item:selected {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {DARK_ACCENT_DARK}, stop:1 {DARK_BG_TERTIARY});
    color: {DARK_TEXT_PRIMARY};
    border-radius: 6px;
    border: none;
}}

QHeaderView::section {{
    background-color: {DARK_BG_INPUT};
    color: {DARK_TEXT_MUTED};
    padding: 10px;
    border: none;
    border-bottom: 2px solid {DARK_BORDER};
    font-weight: bold;
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 0.5px;
}}

QHeaderView::section:horizontal {{
    background-color: {DARK_BG_INPUT};
}}

QHeaderView::section:vertical {{
    background-color: {DARK_BG_PRIMARY};
}}

/* ---------------------------------------------------------------
   Barre de progression
   --------------------------------------------------------------- */
QProgressBar {{
    border: 1px solid {DARK_BORDER};
    border-radius: 8px;
    text-align: center;
    background-color: {DARK_BG_PRIMARY};
    color: {DARK_TEXT_PRIMARY};
    font-weight: bold;
    font-size: 12px;
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {DARK_ACCENT}, stop:0.5 {DARK_ACCENT_LIGHT}, stop:1 {DARK_SUCCESS});
    border-radius: 7px;
}}

/* ---------------------------------------------------------------
   Splitter
   --------------------------------------------------------------- */
QSplitter::handle {{
    background-color: {DARK_BORDER};
    width: 1px;
}}

QSplitter::handle:hover {{
    background-color: {DARK_ACCENT};
    width: 2px;
}}

QSplitter::handle:vertical {{
    height: 1px;
}}

/* ---------------------------------------------------------------
   Checkboxes
   --------------------------------------------------------------- */
QCheckBox {{
    spacing: 8px;
    color: {DARK_TEXT_SECONDARY};
    font-weight: 500;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid {DARK_BORDER_LIGHT};
    background-color: {DARK_BG_INPUT};
}}

QCheckBox::indicator:hover {{
    border-color: {DARK_ACCENT};
    background-color: {DARK_BG_HOVER};
}}

QCheckBox::indicator:checked {{
    background-color: {DARK_ACCENT};
    border-color: {DARK_ACCENT};
}}

QCheckBox:checked {{
    color: {DARK_TEXT_PRIMARY};
}}

QCheckBox:disabled {{
    color: {DARK_TEXT_DISABLED};
}}

QCheckBox::indicator:disabled {{
    border-color: {DARK_BORDER};
    background-color: {DARK_BG_TERTIARY};
}}

/* ---------------------------------------------------------------
   Status Bar
   --------------------------------------------------------------- */
QStatusBar {{
    background-color: {DARK_BG_TERTIARY};
    color: {DARK_TEXT_MUTED};
    font-size: 11px;
    padding: 4px 8px;
    border-top: 1px solid {DARK_BORDER};
}}

/* ---------------------------------------------------------------
   Tooltips
   --------------------------------------------------------------- */
QToolTip {{
    background-color: {DARK_BG_CARD};
    color: {DARK_TEXT_PRIMARY};
    border: 1px solid {DARK_BORDER};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 12px;
}}

/* ---------------------------------------------------------------
   Barre de Menu & Menus Déroulants
   --------------------------------------------------------------- */
QMenuBar {{
    background-color: {DARK_BG_TERTIARY};
    color: {DARK_TEXT_PRIMARY};
    border-bottom: 1px solid {DARK_BORDER};
    padding: 2px 6px;
    font-size: 13px;
}}

QMenuBar::item {{
    background: transparent;
    padding: 5px 10px;
    border-radius: 6px;
    color: {DARK_TEXT_PRIMARY};
}}

QMenuBar::item:selected {{
    background-color: {DARK_BG_HOVER};
    color: {DARK_ACCENT};
}}

QMenuBar::item:pressed {{
    background-color: {DARK_BG_INPUT};
}}

QMenu {{
    background-color: {DARK_BG_CARD};
    color: {DARK_TEXT_PRIMARY};
    border: 1px solid {DARK_BORDER};
    border-radius: 8px;
    padding: 4px;
}}

QMenu::item {{
    padding: 8px 16px;
    border-radius: 6px;
}}

QMenu::item:selected {{
    background-color: {DARK_BG_HOVER};
    color: {DARK_ACCENT};
}}

QMenu::separator {{
    height: 1px;
    background-color: {DARK_BORDER};
    margin: 4px 0;
}}

/* ---------------------------------------------------------------
   GroupBox
   --------------------------------------------------------------- */
QGroupBox {{
    border: 1px solid {DARK_BORDER};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    color: {DARK_TEXT_MUTED};
    font-weight: bold;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
    color: {DARK_ACCENT};
    font-size: 14px;
}}

/* ---------------------------------------------------------------
   TabWidget
   --------------------------------------------------------------- */
QTabWidget::pane {{
    border: 1px solid {DARK_BORDER};
    border-radius: 8px;
    background-color: {DARK_BG_CARD};
}}

QTabWidget::tab-bar {{
    alignment: left;
}}

QTabBar::tab {{
    background-color: {DARK_BG_TERTIARY};
    color: {DARK_TEXT_MUTED};
    border: 1px solid {DARK_BORDER};
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 10px 20px;
    font-weight: 600;
}}

QTabBar::tab:hover {{
    background-color: {DARK_BG_HOVER};
    color: {DARK_TEXT_SECONDARY};
}}

QTabBar::tab:selected {{
    background-color: {DARK_BG_CARD};
    color: {DARK_ACCENT};
    border-color: {DARK_BORDER};
    border-bottom-color: {DARK_BG_CARD};
}}

/* ---------------------------------------------------------------
   SpinBox
   --------------------------------------------------------------- */
QSpinBox::up-button, QSpinBox::down-button {{
    background-color: {DARK_BG_TERTIARY};
    border: 1px solid {DARK_BORDER};
    border-radius: 4px;
    width: 24px;
    height: 24px;
}}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {DARK_BG_HOVER};
}}

QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {{
    background-color: {DARK_BG_INPUT};
}}

QSpinBox::up-arrow, QSpinBox::down-arrow {{
    color: {DARK_TEXT_MUTED};
}}
"""

# ============================================================================
# LIGHT THEME
# ============================================================================
LIGHT_THEME_QSS = f"""
/* ========================================================================
   THEME CLAIR - Antigravity Manga Downloader v3.0
   ======================================================================== */

{ANIMATIONS_QSS}

/* ---------------------------------------------------------------
   Style General & Typographie
   --------------------------------------------------------------- */
QWidget {{
    background-color: {LIGHT_BG_SECONDARY};
    color: {LIGHT_TEXT_PRIMARY};
    font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 13px;
}}

QMainWindow {{
    background-color: {LIGHT_BG_PRIMARY};
}}

/* ---------------------------------------------------------------
   Scrollbars Modernes
   --------------------------------------------------------------- */
QScrollBar:vertical {{
    background: {LIGHT_BG_PRIMARY};
    width: 10px;
    border-radius: 5px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: {LIGHT_BG_TERTIARY};
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {LIGHT_ACCENT};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
    width: 0px;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}

/* ---------------------------------------------------------------
   Barre laterale (Sidebar Navigation)
   --------------------------------------------------------------- */
#Sidebar {{
    background-color: {LIGHT_BG_TERTIARY};
    border-right: 1px solid {LIGHT_BORDER};
}}

#Sidebar QLabel#AppLogo {{
    font-size: 24px;
    font-weight: 800;
    color: {LIGHT_ACCENT};
    padding: 12px 8px 4px 8px;
    letter-spacing: 0.5px;
}}

#Sidebar QLabel#AppSubtitle {{
    font-size: 11px;
    color: {LIGHT_TEXT_MUTED};
    padding-left: 8px;
    margin-bottom: 16px;
}}

#Sidebar QPushButton {{
    background-color: transparent;
    color: {LIGHT_TEXT_MUTED};
    border: 1px solid transparent;
    border-radius: 12px;
    padding: 12px 16px;
    text-align: left;
    font-weight: 600;
    font-size: 13px;
}}

#Sidebar QPushButton:hover {{
    background-color: {LIGHT_BG_HOVER};
    color: {LIGHT_ACCENT};
    border: 1px solid {LIGHT_BORDER_LIGHT};
}}

#Sidebar QPushButton:checked, #Sidebar QPushButton[active="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {LIGHT_ACCENT}, stop:1 {LIGHT_ACCENT_DARK});
    color: {LIGHT_TEXT_PRIMARY};
    font-weight: bold;
    border: 1px solid {LIGHT_ACCENT};
    box-shadow: 0 4px 12px rgba(2, 132, 199, 0.25);
}}

/* ---------------------------------------------------------------
   Champs de saisie & ComboBoxes
   --------------------------------------------------------------- */
QLineEdit, QComboBox, QSpinBox {{
    background-color: {LIGHT_BG_INPUT};
    border: 1px solid {LIGHT_BORDER};
    border-radius: 8px;
    padding: 9px 14px;
    color: {LIGHT_TEXT_PRIMARY};
    selection-background-color: {LIGHT_ACCENT};
    selection-color: {LIGHT_TEXT_PRIMARY};
}}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border: 1px solid {LIGHT_ACCENT};
    background-color: {LIGHT_BG_TERTIARY};
    outline: none;
}}

QLineEdit:hover:!focus, QComboBox:hover:!focus, QSpinBox:hover:!focus {{
    border: 1px solid {LIGHT_BORDER_LIGHT};
}}

QComboBox::drop-down {{
    border: none;
    padding-right: 10px;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background-color: {LIGHT_BG_TERTIARY};
    border: 1px solid {LIGHT_BORDER};
    selection-background-color: {LIGHT_ACCENT};
    color: {LIGHT_TEXT_PRIMARY};
    padding: 4px;
    outline: none;
}}

/* ---------------------------------------------------------------
   Boutons d'action
   --------------------------------------------------------------- */
QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {LIGHT_ACCENT}, stop:1 {LIGHT_ACCENT_DARK});
    color: {LIGHT_TEXT_PRIMARY};
    border: 1px solid {LIGHT_ACCENT};
    border-radius: 8px;
    padding: 9px 18px;
    font-weight: 600;
    font-size: 13px;
    min-width: 80px;
}}

QPushButton:hover:!disabled {{
    background: qlinear-gradient(x1:0, y1:0, x2:1, y2:0, stop:0 {LIGHT_ACCENT_LIGHT}, stop:1 {LIGHT_ACCENT});
    border-color: {LIGHT_ACCENT_LIGHT};
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(56, 189, 248, 0.3);
}}

QPushButton:pressed:!disabled {{
    background-color: {LIGHT_ACCENT_DARK};
    border-color: {LIGHT_ACCENT_DARK};
    transform: translateY(0px);
}}

QPushButton:disabled {{
    background-color: {LIGHT_BG_TERTIARY};
    color: {LIGHT_TEXT_DISABLED};
    border: 1px solid {LIGHT_BORDER};
    transform: none;
}}

/* Bouton secondaire */
QPushButton#SecondaryButton {{
    background-color: {LIGHT_BG_TERTIARY};
    color: {LIGHT_TEXT_SECONDARY};
    border: 1px solid {LIGHT_BORDER};
}}

QPushButton#SecondaryButton:hover {{
    background-color: {LIGHT_BG_HOVER};
    color: {LIGHT_TEXT_PRIMARY};
    border-color: {LIGHT_BORDER_LIGHT};
}}

QPushButton#SecondaryButton:pressed {{
    background-color: {LIGHT_BG_INPUT};
    border-color: {LIGHT_BORDER};
}}

/* Style des onglets filtres */
QPushButton[checkable="true"] {{
    background-color: {LIGHT_BG_TERTIARY};
    color: {LIGHT_TEXT_MUTED};
    border: 1px solid {LIGHT_BORDER};
    border-radius: 14px;
    padding: 4px 14px;
    font-size: 12px;
}}

QPushButton[checkable="true"]:hover {{
    background-color: {LIGHT_BG_HOVER};
    color: {LIGHT_ACCENT};
}}

QPushButton[checkable="true"]:checked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {LIGHT_ACCENT}, stop:1 {LIGHT_ACCENT_DARK});
    color: {LIGHT_TEXT_PRIMARY};
    border: 1px solid {LIGHT_ACCENT};
    font-weight: bold;
}}

/* ---------------------------------------------------------------
   Cartes & Panneaux
   --------------------------------------------------------------- */
QFrame#Card {{
    background-color: {LIGHT_BG_CARD};
    border: 1px solid {LIGHT_BORDER};
    border-radius: 12px;
}}

QFrame#CrossSourceCard {{
    background-color: {LIGHT_BG_TERTIARY};
    border: 1px solid {LIGHT_ACCENT};
    border-radius: 8px;
    padding: 6px 12px;
    margin-top: 4px;
}}

/* ---------------------------------------------------------------
   Tableaux & Listes
   --------------------------------------------------------------- */
QTableWidget, QListWidget {{
    background-color: {LIGHT_BG_CARD};
    border: 1px solid {LIGHT_BORDER};
    border-radius: 10px;
    gridline-color: {LIGHT_BORDER};
    outline: none;
}}

QTableWidget::item, QListWidget::item {{
    padding: 8px 12px;
    border-bottom: 1px solid {LIGHT_BORDER};
}}

QTableWidget::item:hover, QListWidget::item:hover {{
    background-color: {LIGHT_BG_HOVER};
}}

QTableWidget::item:selected, QListWidget::item:selected {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {LIGHT_ACCENT_DARK}, stop:1 {LIGHT_BG_TERTIARY});
    color: {LIGHT_TEXT_PRIMARY};
    border-radius: 6px;
    border: none;
}}

QHeaderView::section {{
    background-color: {LIGHT_BG_INPUT};
    color: {LIGHT_TEXT_MUTED};
    padding: 10px;
    border: none;
    border-bottom: 2px solid {LIGHT_BORDER};
    font-weight: bold;
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 0.5px;
}}

/* ---------------------------------------------------------------
   Barre de progression
   --------------------------------------------------------------- */
QProgressBar {{
    border: 1px solid {LIGHT_BORDER};
    border-radius: 8px;
    text-align: center;
    background-color: {LIGHT_BG_PRIMARY};
    color: {LIGHT_TEXT_PRIMARY};
    font-weight: bold;
    font-size: 12px;
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {LIGHT_ACCENT}, stop:0.5 {LIGHT_ACCENT_LIGHT}, stop:1 {LIGHT_SUCCESS});
    border-radius: 7px;
}}

/* ---------------------------------------------------------------
   Splitter
   --------------------------------------------------------------- */
QSplitter::handle {{
    background-color: {LIGHT_BORDER};
    width: 1px;
}}

QSplitter::handle:hover {{
    background-color: {LIGHT_ACCENT};
    width: 2px;
}}

/* ---------------------------------------------------------------
   Checkboxes
   --------------------------------------------------------------- */
QCheckBox {{
    spacing: 8px;
    color: {LIGHT_TEXT_SECONDARY};
    font-weight: 500;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid {LIGHT_BORDER_LIGHT};
    background-color: {LIGHT_BG_INPUT};
}}

QCheckBox::indicator:hover {{
    border-color: {LIGHT_ACCENT};
    background-color: {LIGHT_BG_HOVER};
}}

QCheckBox::indicator:checked {{
    background-color: {LIGHT_ACCENT};
    border-color: {LIGHT_ACCENT};
}}

QCheckBox:checked {{
    color: {LIGHT_TEXT_PRIMARY};
}}

/* ---------------------------------------------------------------
   Status Bar
   --------------------------------------------------------------- */
QStatusBar {{
    background-color: {LIGHT_BG_TERTIARY};
    color: {LIGHT_TEXT_MUTED};
    font-size: 11px;
    padding: 4px 8px;
    border-top: 1px solid {LIGHT_BORDER};
}}

/* ---------------------------------------------------------------
   Tooltips
   --------------------------------------------------------------- */
QToolTip {{
    background-color: {LIGHT_BG_CARD};
    color: {LIGHT_TEXT_PRIMARY};
    border: 1px solid {LIGHT_BORDER};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 12px;
}}

/* ---------------------------------------------------------------
   SpinBox
   --------------------------------------------------------------- */
QSpinBox::up-button, QSpinBox::down-button {{
    background-color: {LIGHT_BG_TERTIARY};
    border: 1px solid {LIGHT_BORDER};
    border-radius: 4px;
    width: 24px;
    height: 24px;
}}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {LIGHT_BG_HOVER};
}}

QSpinBox::up-arrow, QSpinBox::down-arrow {{
    color: {LIGHT_TEXT_MUTED};
}}
"""

# ============================================================================
# THEME MANAGER
# ============================================================================
class ThemeManager:
    """Gestionnaire de themes avec support sombre/clair."""
    
    THEME_DARK = "dark"
    THEME_LIGHT = "light"
    
    def __init__(self):
        self.current_theme = self.THEME_DARK
        self._themes = {
            self.THEME_DARK: DARK_THEME_QSS,
            self.THEME_LIGHT: LIGHT_THEME_QSS,
        }
    
    def get_theme(self, theme_name: str = None) -> str:
        """Recupere le CSS du theme specifie ou du theme actuel."""
        if theme_name:
            return self._themes.get(theme_name, DARK_THEME_QSS)
        return self._themes.get(self.current_theme, DARK_THEME_QSS)
    
    def set_theme(self, theme_name: str):
        """Change le theme actuel."""
        if theme_name in self._themes:
            self.current_theme = theme_name
    
    def toggle_theme(self) -> str:
        """Basculer entre sombre et clair. Retourne le nouveau theme."""
        new_theme = self.THEME_LIGHT if self.current_theme == self.THEME_DARK else self.THEME_DARK
        self.set_theme(new_theme)
        return new_theme
    
    @property
    def is_dark(self) -> bool:
        return self.current_theme == self.THEME_DARK
    
    @property
    def is_light(self) -> bool:
        return self.current_theme == self.THEME_LIGHT

# Instance globale
theme_manager = ThemeManager()

# Pour la compatibilite ascendante
DARK_THEME_QSS = DARK_THEME_QSS
