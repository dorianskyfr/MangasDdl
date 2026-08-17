from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout
)
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QPixmap
from models import Manga
from favorites import favorites_manager
from ui.views.search_view import ImageLoaderWorker


class FavoriteCard(QFrame):
    """Carte représentant un manga favori dans la bibliothèque."""

    open_requested = Signal(object)
    remove_requested = Signal(object)

    def __init__(self, manga: Manga, parent=None):
        super().__init__(parent)
        self.manga = manga
        self.init_ui()

    def init_ui(self):
        self.setObjectName("Card")
        self.setStyleSheet("""
            QFrame#Card {
                background-color: #161e30;
                border: 1px solid #28344d;
                border-radius: 12px;
                padding: 10px;
            }
            QFrame#Card:hover {
                border-color: #38bdf8;
                background-color: #1a243a;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Couverture
        self.cover_lbl = QLabel()
        self.cover_lbl.setFixedSize(140, 190)
        self.cover_lbl.setStyleSheet("background-color: #0f1420; border-radius: 8px; border: 1px solid #1e293b;")
        self.cover_lbl.setAlignment(Qt.AlignCenter)
        self.cover_lbl.setText("📖")
        layout.addWidget(self.cover_lbl, alignment=Qt.AlignCenter)

        if self.manga.cover_url:
            self.loader = ImageLoaderWorker(self.manga.cover_url)
            self.loader.loaded.connect(self.display_cover)
            self.loader.start()

        # Titre
        title_lbl = QLabel(self.manga.title)
        title_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #f8fafc;")
        title_lbl.setWordWrap(True)
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setFixedHeight(36)
        layout.addWidget(title_lbl)

        # Source badge
        src_lbl = QLabel(self.manga.source)
        src_lbl.setStyleSheet("""
            background-color: #0284c722;
            color: #38bdf8;
            font-weight: bold;
            font-size: 10px;
            padding: 2px 8px;
            border-radius: 4px;
        """)
        src_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(src_lbl, alignment=Qt.AlignCenter)

        # Actions
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        open_btn = QPushButton("📖 Voir")
        open_btn.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                font-weight: bold;
                font-size: 11px;
                border-radius: 6px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
        """)
        open_btn.clicked.connect(lambda checked=False: self.open_requested.emit(self.manga))
        btn_layout.addWidget(open_btn)

        del_btn = QPushButton("🗑️")
        del_btn.setFixedSize(30, 26)
        del_btn.setObjectName("SecondaryButton")
        del_btn.setToolTip("Retirer des favoris")
        del_btn.clicked.connect(lambda checked=False: self.remove_requested.emit(self.manga))
        btn_layout.addWidget(del_btn)

        layout.addLayout(btn_layout)

    def display_cover(self, url: str, data: bytes):
        pix = QPixmap()
        if pix.loadFromData(data) and not pix.isNull():
            self.cover_lbl.setPixmap(
                pix.scaled(140, 190, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            )


class LibraryView(QWidget):
    """Vue de la bibliothèque de favoris."""
    
    open_manga_requested = Signal(object)
    log_signal = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        scroll_area.setWidget(container)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll_area)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("⭐ Ma Bibliothèque & Mangas Favoris")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #38bdf8;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.setObjectName("SecondaryButton")
        refresh_btn.setFixedSize(110, 36)
        refresh_btn.clicked.connect(self.refresh_library)
        header_layout.addWidget(refresh_btn)

        main_layout.addLayout(header_layout)

        # Subtitle / info
        self.count_label = QLabel("0 manga(s) enregistré(s)")
        self.count_label.setStyleSheet("color: #94a3b8; font-size: 13px;")
        main_layout.addWidget(self.count_label)

        # Grid container
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        main_layout.addWidget(self.grid_widget)
        main_layout.addStretch()

        self.refresh_library()

    def refresh_library(self):
        # Vider la grille
        for i in reversed(range(self.grid_layout.count())):
            w = self.grid_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        favs = favorites_manager.list_favorites()
        self.count_label.setText(f"📚 {len(favs)} manga(s) enregistré(s) dans votre bibliothèque")

        if not favs:
            empty_lbl = QLabel("Aucun manga enregistré dans vos favoris.\nRecherchez un manga et cliquez sur '⭐ Favori' pour l'ajouter ici !")
            empty_lbl.setAlignment(Qt.AlignCenter)
            empty_lbl.setStyleSheet("color: #64748b; font-size: 15px; padding: 60px;")
            self.grid_layout.addWidget(empty_lbl, 0, 0)
            return

        cols = 5
        for idx, manga in enumerate(favs):
            row = idx // cols
            col = idx % cols
            card = FavoriteCard(manga)
            card.open_requested.connect(self.open_manga)
            card.remove_requested.connect(self.remove_favorite)
            self.grid_layout.addWidget(card, row, col)

    def open_manga(self, manga: Manga):
        self.open_manga_requested.emit(manga)

    def remove_favorite(self, manga: Manga):
        favorites_manager.remove_favorite(manga.title)
        self.log_signal.emit("INFO", f"'{manga.title}' retiré des favoris.")
        self.refresh_library()
