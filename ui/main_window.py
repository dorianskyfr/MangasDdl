from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QStackedWidget, QLabel, QFrame, QSplitter, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap

from ui.theme import theme_manager, DARK_THEME_QSS
from ui.views.search_view import SearchView
from ui.views.downloads_view import DownloadsView
from ui.views.settings_view import SettingsView
from ui.views.stats_view import StatsView
from ui.views.library_view import LibraryView
from ui.widgets.log_viewer import LogViewerWidget
from ui.widgets.toast_notification import ToastManager, show_toast, toast_success, toast_error




class MainWindow(QMainWindow):
    """Fenêtre principale de l'application avec UI moderne v3.0."""
    
    theme_changed = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Antigravity Manga Scraper & Downloader")
        self.resize(1300, 900)
        self.setMinimumSize(1000, 700)
        
        # Configuration de la fenêtre
        self.setWindowIcon(self._create_icon())
        
        # Appliquer le thème
        self.apply_theme()
        
        # Initialiser le gestionnaire de toasts
        self.toast_manager = ToastManager(self)
        
        self.init_ui()
        self.update_status_bar()
        
        # Connexion du theme manager
        self.theme_changed.connect(self.apply_theme)

    def _create_icon(self):
        """Crée une icône pour la fenêtre."""
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        return QIcon(pixmap)

    def apply_theme(self, theme_name: str = None):
        """Applique le thème actuel à la fenêtre."""
        if theme_name:
            theme_manager.set_theme(theme_name)
        
        theme_css = theme_manager.get_theme()
        self.setStyleSheet(theme_css)
        
        # Mettre à jour les styles spécifiques
        self._update_custom_styles()

    def _update_custom_styles(self):
        """Met à jour les styles personnalisés en fonction du thème."""
        is_dark = theme_manager.is_dark
        
        # Status bar
        status_color = "#64748b"
        status_bg = "#0f1420" if is_dark else "#e2e8f0"
        self.statusBar().setStyleSheet(f"""
            color: {status_color};
            font-size: 11px;
            padding: 4px 8px;
            background-color: {status_bg};
        """)

    def update_status_bar(self):
        """Met à jour la barre de status."""
        theme_status = "Sombre" if theme_manager.is_dark else "Clair"
        self.statusBar().showMessage(f"Prêt • Theme: {theme_status} • Antigravity Manga Downloader v3.0.0")

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # =====================================================================
        # 1. SIDEBAR NAVIGATION
        # =====================================================================
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(260)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 20, 12, 20)
        sidebar_layout.setSpacing(12)

        # --- Header Sidebar (Logo + Title) ---
        header_frame = QFrame()
        header_layout = QVBoxLayout(header_frame)
        header_layout.setSpacing(6)
        header_layout.setContentsMargins(0, 0, 0, 0)

        app_title = QLabel("MangaScraper")
        app_title.setObjectName("AppLogo")
        header_layout.addWidget(app_title)

        subtitle = QLabel("Anime-Sama • JapScan • SushiScan • UNekoScans • Scan-VF • MangaDex")
        subtitle.setObjectName("AppSubtitle")
        header_layout.addWidget(subtitle)

        sidebar_layout.addWidget(header_frame)

        # --- Status Badge ---
        status_card = QFrame()
        status_card.setObjectName("Card")
        status_card.setFixedHeight(48)
        status_card_layout = QHBoxLayout(status_card)
        status_card_layout.setContentsMargins(12, 0, 12, 0)

        status_icon = QLabel("🟢")
        status_icon.setStyleSheet("font-size: 16px;")
        status_card_layout.addWidget(status_icon)

        status_text = QLabel("6 Sources actives")
        status_text.setStyleSheet("font-weight: bold; font-size: 12px;")
        status_card_layout.addWidget(status_text)
        status_card_layout.addStretch()

        sidebar_layout.addWidget(status_card)

        # --- Separateur ---
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setStyleSheet("background-color: #1e293b; margin: 4px 0;")
        sidebar_layout.addWidget(sep1)

        # --- Navigation Buttons ---
        nav_buttons = [
            ("🔍", "Recherche", 0, "nav_search_btn"),
            ("⬇️", "Téléchargements", 1, "nav_dl_btn"),
            ("⭐", "Bibliothèque", 4, "nav_lib_btn"),
            ("⚙️", "Paramètres", 2, "nav_settings_btn"),
            ("📊", "Statistiques", 3, "nav_stats_btn"),
        ]

        self.nav_buttons = {}
        for icon, text, index, obj_name in nav_buttons:
            btn = QPushButton(f"{icon}  {text}")
            btn.setObjectName(obj_name)
            btn.setProperty("active", "false")
            btn.clicked.connect(lambda _, i=index: self.switch_view(i))
            btn.setFixedHeight(44)
            sidebar_layout.addWidget(btn)
            self.nav_buttons[obj_name] = btn
            if index == 0:
                btn.setProperty("active", "true")

        # --- Separateur ---
        sidebar_layout.addStretch()

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("background-color: #1e293b; margin: 4px 0;")
        sidebar_layout.addWidget(sep2)

        # --- Theme Toggle Button ---
        self.theme_toggle_btn = QPushButton()
        self.theme_toggle_btn.setObjectName("themeToggleBtn")
        self.theme_toggle_btn.setFixedSize(40, 40)
        self.theme_toggle_btn.setStyleSheet(self._get_theme_toggle_style())
        self.theme_toggle_btn.clicked.connect(self.toggle_theme)
        self.theme_toggle_btn.setToolTip("Basculer entre theme sombre et clair")
        sidebar_layout.addWidget(self.theme_toggle_btn, alignment=Qt.AlignCenter)

        # --- Version ---
        version_label = QLabel("v3.0.0 Pro")
        version_label.setStyleSheet("color: #64748b; font-size: 11px; text-align: center;")
        sidebar_layout.addWidget(version_label)

        main_layout.addWidget(sidebar)

        # =====================================================================
        # 2. MAIN CONTENT AREA
        # =====================================================================
        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.setHandleWidth(6)

        self.stacked_widget = QStackedWidget()

        # Initialize views
        self.search_view = SearchView()
        self.downloads_view = DownloadsView()
        self.settings_view = SettingsView()
        self.stats_view = StatsView()
        self.library_view = LibraryView()
        self.log_viewer = LogViewerWidget()

        self.stacked_widget.addWidget(self.search_view)      # 0
        self.stacked_widget.addWidget(self.downloads_view)   # 1
        self.stacked_widget.addWidget(self.settings_view)    # 2
        self.stacked_widget.addWidget(self.stats_view)       # 3
        self.stacked_widget.addWidget(self.library_view)     # 4

        main_splitter.addWidget(self.stacked_widget)
        main_splitter.addWidget(self.log_viewer)
        main_splitter.setSizes([700, 200])

        main_layout.addWidget(main_splitter)

        # =====================================================================
        # SIGNAL CONNECTIONS
        # =====================================================================
        self.search_view.download_requested.connect(self.on_download_requested)
        self.search_view.log_signal.connect(self.log_viewer.log)
        self.downloads_view.log_signal.connect(self.log_viewer.log)
        self.settings_view.log_signal.connect(self.log_viewer.log)
        self.stats_view.log_signal.connect(self.log_viewer.log)
        self.library_view.log_signal.connect(self.log_viewer.log)
        self.library_view.open_manga_requested.connect(self.open_manga_from_library)



        # Theme change from settings
        self.settings_view.theme_changed.connect(self.on_theme_changed_from_settings)

        self.log_viewer.log("INFO", "Application demarree avec succes.")

    def _get_theme_toggle_style(self) -> str:
        """Return the style of the theme toggle button."""
        is_dark = theme_manager.is_dark
        bg_color = "#161e30" if is_dark else "#e2e8f0"
        border_color = "#334155" if is_dark else "#cbd5e1"
        text_color = "#f8fafc" if is_dark else "#0f172a"
        hover_bg = "#1a2234" if is_dark else "#f1f5f9"
        hover_border = "#38bdf8"
        
        icon = "☀️" if is_dark else "🌙"
        
        return f"""
            QPushButton {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 10px;
                font-size: 16px;
                color: {text_color};
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
                border-color: {hover_border};
            }}
            QPushButton:pressed {{
                background-color: {'#0f1420' if is_dark else '#f8fafc'};
            }}
        """

    def toggle_theme(self):
        """Toggle between dark and light theme."""
        new_theme = theme_manager.toggle_theme()
        self.theme_changed.emit(new_theme)
        self.theme_toggle_btn.setStyleSheet(self._get_theme_toggle_style())
        self.update_status_bar()
        self.statusBar().showMessage(f"Theme: {'Sombre' if theme_manager.is_dark else 'Clair'}", 3000)

    def on_theme_changed_from_settings(self, theme_name: str):
        """Handle theme change from settings."""
        theme_manager.set_theme(theme_name)
        self.apply_theme(theme_name)
        self.theme_toggle_btn.setStyleSheet(self._get_theme_toggle_style())
        self.update_status_bar()

    def on_download_requested(self, jobs: list):
        """Transfer jobs to downloader and switch to downloads view."""
        self.downloads_view.add_jobs(jobs)
        self.switch_view(1)
        self.statusBar().showMessage(f"{len(jobs)} telechargement(s) ajoute(s)", 3000)

    def open_manga_from_library(self, manga):
        """Redirige vers l'onglet Recherche et effectue la recherche du manga favori."""
        self.switch_view(0)
        self.search_view.source_combo.setCurrentText(manga.source)
        self.search_view.search_input.setText(manga.title)
        self.search_view.start_search()

    def switch_view(self, index: int):
        """Switch to the specified view."""
        self.stacked_widget.setCurrentIndex(index)
        
        if index == 3:
            self.stats_view.refresh_stats()
        elif index == 4:
            self.library_view.refresh_library()

        # Update navigation buttons state
        nav_obj_names = ["nav_search_btn", "nav_dl_btn", "nav_settings_btn", "nav_stats_btn", "nav_lib_btn"]
        for idx, obj_name in enumerate(nav_obj_names):
            if obj_name in self.nav_buttons:
                btn_idx = 4 if obj_name == "nav_lib_btn" else (3 if obj_name == "nav_stats_btn" else (2 if obj_name == "nav_settings_btn" else (1 if obj_name == "nav_dl_btn" else 0)))
                self.nav_buttons[obj_name].setProperty("active", "true" if btn_idx == index else "false")
                self.nav_buttons[obj_name].style().unpolish(self.nav_buttons[obj_name])
                self.nav_buttons[obj_name].style().polish(self.nav_buttons[obj_name])


    
    def show_toast(self, title: str, message: str, toast_type: str = "info", duration: int = 3):
        """Affiche une notification toast."""
        self.toast_manager.show(title, message, toast_type, duration)
    
    def closeEvent(self, event):
        """Handle window close."""
        event.accept()
