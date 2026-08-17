import os
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QStackedWidget, QLabel, QFrame, QSplitter, QMessageBox,
    QMenuBar, QMenu
)
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QIcon, QPixmap, QKeySequence, QDesktopServices, QAction

from config import config_manager
from ui.theme import theme_manager
from ui.views.search_view import SearchView
from ui.views.downloads_view import DownloadsView
from ui.views.settings_view import SettingsView
from ui.views.stats_view import StatsView
from ui.views.library_view import LibraryView
from ui.widgets.log_viewer import LogViewerWidget
from ui.widgets.toast_notification import ToastManager, show_toast, toast_success, toast_error


class MainWindow(QMainWindow):
    """Fenêtre principale de l'application avec UI moderne v3.0 Pro."""
    
    theme_changed = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MangasDdl — Téléchargeur & Lecteur de Mangas")
        self.resize(1300, 900)
        self.setMinimumSize(1000, 700)
        
        # Configuration de la fenêtre
        self.setWindowIcon(self._create_icon())
        
        # Initialiser le gestionnaire de toasts
        self.toast_manager = ToastManager(self)
        
        self.init_ui()
        self._create_menu_bar()
        self.apply_theme()
        self.update_status_bar()
        
        # Connexion du theme manager
        self.theme_changed.connect(self.apply_theme)

    def _create_icon(self):
        """Crée une icône pour la fenêtre."""
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        return QIcon(pixmap)

    def _create_menu_bar(self):
        """Crée la barre de menu native supérieure."""
        menubar = self.menuBar()
        menubar.clear()

        # ── Menu Fichier ──
        file_menu = menubar.addMenu("&Fichier")

        act_search = QAction("🔍 Recherche", self)
        act_search.setShortcut(QKeySequence("Ctrl+F"))
        act_search.triggered.connect(lambda: self.switch_view(0))
        file_menu.addAction(act_search)

        act_dl = QAction("⬇️ Téléchargements", self)
        act_dl.setShortcut(QKeySequence("Ctrl+D"))
        act_dl.triggered.connect(lambda: self.switch_view(1))
        file_menu.addAction(act_dl)

        act_lib = QAction("⭐ Bibliothèque", self)
        act_lib.setShortcut(QKeySequence("Ctrl+B"))
        act_lib.triggered.connect(lambda: self.switch_view(4))
        file_menu.addAction(act_lib)

        act_settings = QAction("⚙️ Paramètres", self)
        act_settings.setShortcut(QKeySequence("Ctrl+,"))
        act_settings.triggered.connect(lambda: self.switch_view(2))
        file_menu.addAction(act_settings)

        act_stats = QAction("📊 Statistiques", self)
        act_stats.setShortcut(QKeySequence("Ctrl+S"))
        act_stats.triggered.connect(lambda: self.switch_view(3))
        file_menu.addAction(act_stats)

        file_menu.addSeparator()

        act_open_folder = QAction("📂 Ouvrir le dossier des téléchargements", self)
        act_open_folder.setShortcut(QKeySequence("Ctrl+O"))
        act_open_folder.triggered.connect(self.open_downloads_folder)
        file_menu.addAction(act_open_folder)

        file_menu.addSeparator()

        act_quit = QAction("🚪 Quitter", self)
        act_quit.setShortcut(QKeySequence("Ctrl+Q"))
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        # ── Menu Affichage ──
        view_menu = menubar.addMenu("&Affichage")

        act_theme = QAction("🌓 Basculer Thème Sombre / Clair", self)
        act_theme.setShortcut(QKeySequence("Ctrl+T"))
        act_theme.triggered.connect(self.toggle_theme)
        view_menu.addAction(act_theme)

        act_fullscreen = QAction("⛶ Plein écran", self)
        act_fullscreen.setShortcut(QKeySequence("F11"))
        act_fullscreen.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(act_fullscreen)

        act_logs = QAction("📜 Afficher / Masquer les Logs", self)
        act_logs.setShortcut(QKeySequence("Ctrl+L"))
        act_logs.triggered.connect(self.toggle_logs_panel)
        view_menu.addAction(act_logs)

        # ── Menu Sources ──
        sources_menu = menubar.addMenu("&Sources")
        sources_list = [
            ("Anime-Sama", "https://anime-sama.to"),
            ("Crunchyscan", "https://sushiscan.fr"),
            ("JapScan", "https://www.japscan.foo"),
            ("Scan-VF", "https://www.scan-vf.net"),
            ("MangaDex", "https://api.mangadex.org"),
        ]
        for s_name, _ in sources_list:
            act_src = QAction(f"📌 Basculer sur {s_name}", self)
            act_src.triggered.connect(lambda _, name=s_name: self.set_search_source(name))
            sources_menu.addAction(act_src)

        # ── Menu Aide ──
        help_menu = menubar.addMenu("&Aide")

        act_shortcuts = QAction("⌨️ Raccourcis clavier", self)
        act_shortcuts.triggered.connect(self.show_shortcuts_dialog)
        help_menu.addAction(act_shortcuts)

        act_about = QAction("ℹ️ À propos de MangasDdl", self)
        act_about.triggered.connect(self.show_about_dialog)
        help_menu.addAction(act_about)

    def set_search_source(self, source_name: str):
        """Active la source choisie dans la vue recherche."""
        self.switch_view(0)
        self.search_view.source_combo.setCurrentText(source_name)

    def open_downloads_folder(self):
        """Ouvre le dossier de téléchargement dans l'explorateur."""
        dl_dir = config_manager.get("download_dir", str(Path.home() / "Downloads" / "MangaDownloader"))
        p = Path(dl_dir)
        p.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))

    def toggle_fullscreen(self):
        """Bascule entre le mode plein écran et la fenêtre normale."""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def toggle_logs_panel(self):
        """Affiche ou masque le panneau inférieur de logs."""
        if self.log_viewer.isVisible():
            self.log_viewer.hide()
        else:
            self.log_viewer.show()

    def show_shortcuts_dialog(self):
        """Affiche la boîte de dialogue des raccourcis."""
        msg = """<h3>⌨️ Raccourcis Clavier</h3>
<ul>
  <li><b>Ctrl + F</b> : Recherche</li>
  <li><b>Ctrl + D</b> : Téléchargements</li>
  <li><b>Ctrl + B</b> : Bibliothèque / Favoris</li>
  <li><b>Ctrl + ,</b> : Paramètres</li>
  <li><b>Ctrl + S</b> : Statistiques</li>
  <li><b>Ctrl + O</b> : Ouvrir le dossier des téléchargements</li>
  <li><b>Ctrl + T</b> : Basculer Thème Sombre / Clair</li>
  <li><b>Ctrl + L</b> : Afficher / Masquer les Logs</li>
  <li><b>F11</b> : Plein écran</li>
  <li><b>Lecteur</b> : Flèches Gauche/Droite, Espace, +, -, F</li>
</ul>"""
        QMessageBox.information(self, "Raccourcis Clavier", msg)

    def show_about_dialog(self):
        """Affiche la boîte À propos."""
        msg = """<h3>📚 MangasDdl v3.0 Pro</h3>
<p>Application de recherche, lecture et téléchargement de mangas & webtoons.</p>
<p><b>Fonctionnalités :</b> Multi-sources, CBZ/PDF/EPUB, Mode Webtoon continu, Tomes officiels AniList HD.</p>
<p>Dépôt GitHub : <a href='https://github.com/dorianskyfr/MangasDdl'>https://github.com/dorianskyfr/MangasDdl</a></p>"""
        QMessageBox.about(self, "À propos de MangasDdl", msg)

    def apply_theme(self, theme_name: str = None):
        """Applique le thème actuel à la fenêtre."""
        if theme_name:
            theme_manager.set_theme(theme_name)
        
        theme_css = theme_manager.get_theme()
        self.setStyleSheet(theme_css)
        self._update_custom_styles()

    def _update_custom_styles(self):
        """Met à jour les styles personnalisés en fonction du thème."""
        is_dark = theme_manager.is_dark
        status_color = "#94a3b8" if is_dark else "#475569"
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
        self.statusBar().showMessage(f"Prêt • Theme: {theme_status} • MangasDdl v3.0.0 Pro")

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
        sidebar_layout.setSpacing(10)

        # --- Header Sidebar (Logo + Title) ---
        header_frame = QFrame()
        header_layout = QVBoxLayout(header_frame)
        header_layout.setSpacing(6)
        header_layout.setContentsMargins(0, 0, 0, 0)

        app_title = QLabel("MangasDdl")
        app_title.setObjectName("AppLogo")
        header_layout.addWidget(app_title)

        subtitle = QLabel("Anime-Sama • JapScan • SushiScan • MangaDex • Scan-VF")
        subtitle.setObjectName("AppSubtitle")
        header_layout.addWidget(subtitle)

        sidebar_layout.addWidget(header_frame)

        # --- Status Badge ---
        status_card = QFrame()
        status_card.setObjectName("Card")
        status_card.setFixedHeight(46)
        status_card_layout = QHBoxLayout(status_card)
        status_card_layout.setContentsMargins(12, 0, 12, 0)

        status_icon = QLabel("🟢")
        status_icon.setStyleSheet("font-size: 14px;")
        status_card_layout.addWidget(status_icon)

        status_text = QLabel("5 Sources Actives")
        status_text.setStyleSheet("font-weight: bold; font-size: 12px; color: #4ade80;")
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
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, i=index: self.switch_view(i))
            btn.setFixedHeight(44)
            sidebar_layout.addWidget(btn)
            self.nav_buttons[obj_name] = btn
            if index == 0:
                btn.setProperty("active", "true")

        sidebar_layout.addStretch()

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("background-color: #1e293b; margin: 4px 0;")
        sidebar_layout.addWidget(sep2)

        # --- Theme Toggle Button ---
        self.theme_toggle_btn = QPushButton()
        self.theme_toggle_btn.setObjectName("themeToggleBtn")
        self.theme_toggle_btn.setFixedSize(40, 40)
        self.theme_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.theme_toggle_btn.setStyleSheet(self._get_theme_toggle_style())
        self.theme_toggle_btn.clicked.connect(self.toggle_theme)
        self.theme_toggle_btn.setToolTip("Basculer entre thème sombre et clair (Ctrl+T)")
        sidebar_layout.addWidget(self.theme_toggle_btn, alignment=Qt.AlignCenter)

        # --- Version ---
        version_label = QLabel("v3.0.0 Pro")
        version_label.setStyleSheet("color: #64748b; font-size: 11px; text-align: center;")
        sidebar_layout.addWidget(version_label, alignment=Qt.AlignCenter)

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
        self.settings_view.theme_changed.connect(self.on_theme_changed_from_settings)

        self.log_viewer.log("INFO", "MangasDdl v3.0 Pro démarré avec succès.")

    def _get_theme_toggle_style(self) -> str:
        """Return the style of the theme toggle button."""
        is_dark = theme_manager.is_dark
        bg_color = "#161e30" if is_dark else "#e2e8f0"
        border_color = "#334155" if is_dark else "#cbd5e1"
        text_color = "#f8fafc" if is_dark else "#0f172a"
        hover_bg = "#1a2234" if is_dark else "#f1f5f9"
        hover_border = "#38bdf8"
        
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
        """

    def toggle_theme(self):
        """Toggle between dark and light theme."""
        new_theme = theme_manager.toggle_theme()
        self.theme_changed.emit(new_theme)
        self.theme_toggle_btn.setStyleSheet(self._get_theme_toggle_style())
        self.update_status_bar()
        self.statusBar().showMessage(f"Thème : {'Sombre' if theme_manager.is_dark else 'Clair'}", 3000)

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
        self.statusBar().showMessage(f"{len(jobs)} téléchargement(s) ajouté(s)", 3000)

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
        _nav_idx = {
            "nav_search_btn": 0, "nav_dl_btn": 1, "nav_settings_btn": 2,
            "nav_stats_btn": 3, "nav_lib_btn": 4,
        }
        for obj_name, btn in self.nav_buttons.items():
            btn_idx = _nav_idx.get(obj_name, -1)
            btn.setProperty("active", "true" if btn_idx == index else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def show_toast(self, title: str, message: str, toast_type: str = "info", duration: int = 3):
        """Affiche une notification toast."""
        self.toast_manager.show(title, message, toast_type, duration)
    
    def closeEvent(self, event):
        """Handle window close."""
        event.accept()
