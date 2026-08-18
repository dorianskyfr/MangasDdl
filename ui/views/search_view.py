from __future__ import annotations
import uuid
from typing import Optional, List, Dict, Tuple, Any
import httpx
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QComboBox, QListWidget, QListWidgetItem, QLabel, QSplitter,
    QTableWidget, QTableWidgetItem, QCheckBox, QHeaderView, QFrame,
    QProgressBar, QMessageBox, QScrollArea, QSizePolicy, QCompleter
)
from PySide6.QtCore import Qt, QThread, Signal, QSize, QStringListModel
from PySide6.QtGui import QPixmap, QImage, QFont, QColor

from models import Manga, Chapter, DownloadJob
from scrapers.factory import ScraperFactory
from config import config_manager
from downloader.mangadex_volume import MultiSourceVolumeProvider, MangaDexVolumeProvider
from search_history import search_history
from reading_history import reading_history


KNOWN_MAIN_CHAPTERS = {
    "the beginning after the end": 245,
    "tbate": 245,
    "naruto": 700,
    "bleach": 686,
    "demon slayer": 205,
    "kimetsu no yaiba": 205,
    "attack on titan": 139,
    "shingeki no kyojin": 139,
    "death note": 108,
    "solo leveling": 200,
    "dragon ball": 519,
    "fairy tail": 545,
    "fairy-tail": 545,
    "hunter x hunter": 400,
    "haikyuu": 402,
    "haikyu": 402,
    "slam dunk": 276,
    "fullmetal alchemist": 108,
}

def get_official_main_limit(manga_title: str, total_meta: Optional[int] = None) -> Optional[int]:
    t_clean = manga_title.lower().strip()
    if "tbate" in t_clean or ("begin" in t_clean and "after" in t_clean):
        return 245
    for key, count in KNOWN_MAIN_CHAPTERS.items():
        if key in t_clean:
            return count
    if total_meta and total_meta > 0:
        return total_meta
    return None

def is_bonus_chapter(c: Chapter, max_main: Optional[int] = None) -> bool:
    num_str = str(c.number).strip()
    title_lower = (c.title or "").lower()

    if max_main and max_main > 0:
        try:
            val = float(num_str)
            if val > max_main:
                return True
        except ValueError:
            pass

    if "." in num_str:
        parts = num_str.split(".")
        if len(parts) >= 2 and parts[1] not in ("0", ""):
            return True

    bonus_keywords = [
        "bonus", "extra", "special", "spécial", "hors-série", "hs", "omake",
        "sidestory", "side story", "gaiden", "ex", "sp", "prologue", "epilogue",
        "épilogue", "one-shot", "oneshot", "side"
    ]
    if any(k in title_lower for k in bonus_keywords) or any(k in num_str.lower() for k in bonus_keywords):
        return True

    return False


class FetchWorker(QThread):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            res = self.func(*self.args, **self.kwargs)
            self.finished.emit(res)
        except Exception as e:
            self.error.emit(str(e))


class ImageLoaderWorker(QThread):
    loaded = Signal(str, bytes)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                "Accept": "image/webp,image/avif,image/*,*/*;q=0.8",
                "Referer": "https://anime-sama.to/",
            }
            with httpx.Client(headers=headers, timeout=15.0, follow_redirects=True) as client:
                r = client.get(self.url)
                if r.status_code == 200 and len(r.content) > 500:
                    self.loaded.emit(self.url, r.content)
        except Exception:
            pass


class MangaResultCard(QWidget):
    """Widget personnalisé pour chaque résultat de recherche dans la liste."""

    def __init__(self, manga: Manga, parent=None):
        super().__init__(parent)
        self.manga = manga
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(10)

        # Miniature de couverture
        self.cover_lbl = QLabel()
        self.cover_lbl.setFixedSize(40, 54)
        self.cover_lbl.setStyleSheet("background-color: #1a2030; border-radius: 6px; border: 1px solid #28344d;")
        self.cover_lbl.setAlignment(Qt.AlignCenter)
        self.cover_lbl.setText("📖")
        layout.addWidget(self.cover_lbl)

        # Infos
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        title_lbl = QLabel(self.manga.title)
        title_lbl.setStyleSheet("font-weight: bold; font-size: 12px; color: #f8fafc;")
        title_lbl.setWordWrap(True)
        info_layout.addWidget(title_lbl)

        badge_lbl = QLabel(self.manga.source)
        src_name = self.manga.source.lower()
        if "anime" in src_name:
            src_color = "#0284c7"  # Bleu Anime-Sama
        elif "jap" in src_name:
            src_color = "#10b981"  # Vert JapScan
        else:
            src_color = "#ea580c"  # Orange Crunchyscan

        badge_lbl.setStyleSheet(f"""
            background-color: {src_color};
            color: #ffffff;
            font-size: 9px;
            font-weight: bold;
            padding: 2px 8px;
            border-radius: 4px;
        """)
        badge_lbl.setFixedHeight(18)
        info_layout.addWidget(badge_lbl)

        layout.addLayout(info_layout)

        # Charger la miniature en arrière-plan
        if self.manga.cover_url:
            self.img_worker = ImageLoaderWorker(self.manga.cover_url)
            self.img_worker.loaded.connect(self._on_cover_loaded)
            self.img_worker.start()

    def _on_cover_loaded(self, url: str, data: bytes):
        pixmap = QPixmap()
        loaded = pixmap.loadFromData(data)
        if not loaded:
            try:
                from PIL import Image
                import io
                img = Image.open(io.BytesIO(data)).convert("RGB")
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                pixmap.loadFromData(buf.getvalue())
                loaded = True
            except Exception:
                pass
        if loaded and not pixmap.isNull():
            self.cover_lbl.setPixmap(
                pixmap.scaled(40, 54, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            )


class SearchView(QWidget):
    download_requested = Signal(list)
    log_signal = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_manga = None
        self.current_chapters = []
        self.current_vmap = None
        self.current_vsrc = ""
        self.current_volume_jobs = []
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # 1. Barre de recherche et sélecteur de source
        search_bar_layout = QHBoxLayout()
        search_bar_layout.setSpacing(10)

        self.source_combo = QComboBox()
        self.source_combo.addItems(["🌐 Toutes les sources"] + ScraperFactory.list_sources())
        self.source_combo.setFixedWidth(160)
        search_bar_layout.addWidget(self.source_combo)


        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔎 Rechercher un manga (ex: One Piece, Naruto, Solo Leveling)...")
        self.search_input.returnPressed.connect(self.start_search)
        
        # Search history completer
        self._completer_model = QStringListModel(search_history.get_suggestions())
        self._completer = QCompleter(self._completer_model, self)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchContains)
        self._completer.setMaxVisibleItems(8)
        self.search_input.setCompleter(self._completer)
        self.search_input.textChanged.connect(self._update_search_completer)
        search_bar_layout.addWidget(self.search_input)

        self.search_btn = QPushButton("Rechercher")
        self.search_btn.setMinimumWidth(120)
        self.search_btn.clicked.connect(self.start_search)
        search_bar_layout.addWidget(self.search_btn)

        main_layout.addLayout(search_bar_layout)

        # Barre de progression de recherche
        self.loading_bar = QProgressBar()
        self.loading_bar.setRange(0, 0)
        self.loading_bar.setFixedHeight(4)
        self.loading_bar.setTextVisible(False)
        self.loading_bar.hide()
        main_layout.addWidget(self.loading_bar)

        # 2. Zone de contenu séparée en 2 colonnes (Résultats | Détails & Chapitres)
        splitter = QSplitter(Qt.Horizontal)

        # Panneau de gauche : Liste des résultats
        left_panel = QFrame()
        left_panel.setObjectName("Card")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)

        results_label = QLabel("Résultats de recherche")
        results_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #94a3b8;")
        left_layout.addWidget(results_label)

        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self.on_manga_selected)
        left_layout.addWidget(self.results_list)

        splitter.addWidget(left_panel)

        # Panneau de droite : Détails du manga & Chapitres
        right_panel = QFrame()
        right_panel.setObjectName("Card")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(12)

        # Header détails manga (Couverture + Infos)
        manga_header_layout = QHBoxLayout()
        manga_header_layout.setSpacing(16)

        self.cover_label = QLabel()
        self.cover_label.setFixedSize(120, 165)
        self.cover_label.setStyleSheet("background-color: #111420; border-radius: 8px; border: 1px solid #263147;")
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setText("📖")
        manga_header_layout.addWidget(self.cover_label)

        manga_info_layout = QVBoxLayout()
        manga_info_layout.setSpacing(6)

        self.manga_title_label = QLabel("Sélectionnez un manga")
        self.manga_title_label.setStyleSheet("font-size: 19px; font-weight: bold; color: #38bdf8;")
        self.manga_title_label.setWordWrap(True)
        manga_info_layout.addWidget(self.manga_title_label)

        self.manga_genres_label = QLabel("Genres: -")
        self.manga_genres_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        manga_info_layout.addWidget(self.manga_genres_label)

        # Label statut + nombre de tomes
        self.manga_status_label = QLabel("")
        self.manga_status_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self.manga_status_label.setWordWrap(True)
        manga_info_layout.addWidget(self.manga_status_label)

        self.manga_synopsis_label = QLabel("Sélectionnez un manga dans la liste à gauche pour voir les détails et les chapitres disponibles.")
        self.manga_synopsis_label.setWordWrap(True)
        self.manga_synopsis_label.setMaximumHeight(65)
        self.manga_synopsis_label.setStyleSheet("color: #cbd5e1; font-size: 12px; line-height: 1.4;")
        manga_info_layout.addWidget(self.manga_synopsis_label)


        # Bouton Favoris
        self.fav_btn = QPushButton("⭐ Ajouter aux favoris")
        self.fav_btn.setObjectName("SecondaryButton")
        self.fav_btn.setFixedWidth(170)
        self.fav_btn.clicked.connect(self.toggle_favorite_current_manga)
        manga_info_layout.addWidget(self.fav_btn)

        manga_info_layout.addStretch()

        manga_header_layout.addLayout(manga_info_layout)
        right_layout.addLayout(manga_header_layout)


        # Bannière d'alerte pour source plus récente / plus complète
        self.cross_source_card = QFrame()
        self.cross_source_card.setObjectName("CrossSourceCard")
        self.cross_source_card.setStyleSheet("""
            QFrame#CrossSourceCard {
                background-color: #0f172a;
                border: 1px solid #0284c7;
                border-radius: 8px;
                padding: 6px 12px;
                margin-top: 4px;
            }
        """)
        cross_layout = QHBoxLayout(self.cross_source_card)
        cross_layout.setContentsMargins(8, 4, 8, 4)

        self.cross_source_lbl = QLabel("")
        self.cross_source_lbl.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 12px;")
        cross_layout.addWidget(self.cross_source_lbl)
        cross_layout.addStretch()

        self.switch_source_btn = QPushButton("⚡ Basculer")
        self.switch_source_btn.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                font-weight: bold;
                font-size: 11px;
                padding: 4px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
        """)
        self.switch_source_btn.clicked.connect(self.on_switch_source_clicked)
        cross_layout.addWidget(self.switch_source_btn)
        self.cross_source_card.hide()
        right_layout.addWidget(self.cross_source_card)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #1e2538; margin: 4px 0;")
        right_layout.addWidget(sep)

        # Filtres d'onglets (Chapitres Principaux / Chapitres Bonus / Tous)
        filter_bar_layout = QHBoxLayout()
        filter_bar_layout.setSpacing(6)

        self.btn_filter_main = QPushButton("📖 Chapitres principaux")
        self.btn_filter_bonus = QPushButton("🎁 Chapitres bonus")
        self.btn_filter_all = QPushButton("📚 Tous")

        for btn in (self.btn_filter_main, self.btn_filter_bonus, self.btn_filter_all):
            btn.setCheckable(True)
            btn.setFixedHeight(28)

        self.btn_filter_main.setChecked(True)
        self.current_chapter_filter = "main"

        self.btn_filter_main.clicked.connect(lambda checked=False: self.set_chapter_filter("main"))
        self.btn_filter_bonus.clicked.connect(lambda checked=False: self.set_chapter_filter("bonus"))
        self.btn_filter_all.clicked.connect(lambda checked=False: self.set_chapter_filter("all"))

        filter_bar_layout.addWidget(self.btn_filter_main)
        filter_bar_layout.addWidget(self.btn_filter_bonus)
        filter_bar_layout.addWidget(self.btn_filter_all)
        filter_bar_layout.addStretch()

        right_layout.addLayout(filter_bar_layout)

        # Contrôles de sélection de chapitres & Regroupement en Tomes (Ligne 1)
        chap_controls_row1 = QHBoxLayout()
        chap_controls_row1.setSpacing(12)

        self.select_all_cb = QCheckBox("Tout sélectionner")
        self.select_all_cb.stateChanged.connect(self.toggle_select_all)
        chap_controls_row1.addWidget(self.select_all_cb)

        self.btn_select_range = QPushButton("🔢 Sélectionner plage")
        self.btn_select_range.setObjectName("SecondaryButton")
        self.btn_select_range.setFixedHeight(30)
        self.btn_select_range.clicked.connect(self.open_select_range_dialog)
        chap_controls_row1.addWidget(self.btn_select_range)

        self.group_tomes_cb = QCheckBox("Regrouper en Tomes Officiels")
        self.group_tomes_cb.setChecked(config_manager.get("group_by_volume", False))
        self.group_tomes_cb.stateChanged.connect(self.on_tomes_mode_toggled)
        chap_controls_row1.addWidget(self.group_tomes_cb)

        self.tome_status_lbl = QLabel("")
        self.tome_status_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #38bdf8;")
        chap_controls_row1.addWidget(self.tome_status_lbl)

        chap_controls_row1.addStretch()
        right_layout.addLayout(chap_controls_row1)

        # Ligne 2 : Barre de filtrage des chapitres + Bouton Télécharger
        chap_controls_row2 = QHBoxLayout()
        chap_controls_row2.setSpacing(10)

        self.chapter_filter_input = QLineEdit()
        self.chapter_filter_input.setPlaceholderText("🔍 Filtrer les chapitres par numéro ou nom (ex: 105, bonus, arc)...")
        self.chapter_filter_input.setFixedHeight(34)
        self.chapter_filter_input.textChanged.connect(self.on_chapter_filter_text_changed)
        chap_controls_row2.addWidget(self.chapter_filter_input)

        self.download_btn = QPushButton("🚀 Télécharger la sélection")
        self.download_btn.setFixedHeight(34)
        self.download_btn.setMinimumWidth(200)
        self.download_btn.clicked.connect(self.on_download_clicked)
        self.download_btn.setEnabled(False)
        chap_controls_row2.addWidget(self.download_btn)

        right_layout.addLayout(chap_controls_row2)

        # Tableau des chapitres / tomes avec menu contextuel
        self.chapters_table = QTableWidget(0, 3)
        self.chapters_table.setHorizontalHeaderLabels(["", "CHAPITRE / TOME", "ACTION"])
        self.chapters_table.verticalHeader().setVisible(False)
        self.chapters_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.chapters_table.setColumnWidth(0, 50)
        self.chapters_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.chapters_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.chapters_table.setColumnWidth(2, 200)
        self.chapters_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.chapters_table.customContextMenuRequested.connect(self.on_table_context_menu)

        right_layout.addWidget(self.chapters_table)

        splitter.addWidget(right_panel)
        splitter.setSizes([340, 660])
        main_layout.addWidget(splitter)


    def _search_all_sources_worker(self, query: str) -> list:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        all_results = []
        sources = ScraperFactory.list_sources()

        def fetch_one(src_name):
            try:
                scr = ScraperFactory.get_scraper(src_name)
                return scr.search(query)
            except Exception as e:
                print(f"[MultiSourceSearch] Erreur sur {src_name}: {e}")
                return []

        with ThreadPoolExecutor(max_workers=len(sources)) as executor:
            futures = {executor.submit(fetch_one, s): s for s in sources}
            for future in as_completed(futures):
                res = future.result()
                if res:
                    all_results.extend(res)
        return all_results

    def _update_search_completer(self, text):
        suggestions = search_history.get_suggestions(text)
        self._completer_model.setStringList(suggestions)

    def start_search(self):
        query = self.search_input.text().strip()
        source = self.source_combo.currentText()
        if not query:
            return
            
        search_history.add(query)

        self.loading_bar.show()
        self.results_list.clear()
        self.search_btn.setEnabled(False)

        if source == "🌐 Toutes les sources":
            self.search_worker = FetchWorker(self._search_all_sources_worker, query)
            self.log_signal.emit("INFO", f"Recherche simultanée de '{query}' sur TOUTES les 6 sources...")
        else:
            scraper = ScraperFactory.get_scraper(source)
            self.search_worker = FetchWorker(scraper.search, query)
            self.log_signal.emit("INFO", f"Recherche '{query}' sur {source}...")

        self.search_worker.finished.connect(self.display_search_results)
        self.search_worker.error.connect(self.on_search_error)
        self.search_worker.start()


    def display_search_results(self, results: list):
        self.loading_bar.hide()
        self.search_btn.setEnabled(True)
        self.log_signal.emit("INFO", f"{len(results)} manga(s) trouvé(s).")

        if not results:
            item = QListWidgetItem("Aucun résultat trouvé.")
            self.results_list.addItem(item)
            return

        for manga in results:
            item = QListWidgetItem(self.results_list)
            card = MangaResultCard(manga)
            item.setSizeHint(QSize(280, 68))
            item.setData(Qt.UserRole, manga)
            self.results_list.setItemWidget(item, card)

    def on_search_error(self, err_msg: str):
        self.loading_bar.hide()
        self.search_btn.setEnabled(True)
        self.log_signal.emit("ERROR", f"Erreur de recherche : {err_msg}")

    def on_manga_selected(self, item: QListWidgetItem):
        manga = item.data(Qt.UserRole)
        if not manga:
            return

        self.current_manga = manga
        self.manga_title_label.setText(manga.title)
        self.manga_synopsis_label.setText("Chargement des détails et des chapitres...")
        self.manga_genres_label.setText("Genres: -")
        self.manga_status_label.setText("")

        from favorites import favorites_manager
        if favorites_manager.is_favorite(manga.title):
            self.fav_btn.setText("★ Dans la bibliothèque")
            self.fav_btn.setStyleSheet("background-color: #f59e0b; color: #ffffff; font-weight: bold; border-radius: 6px; padding: 4px 10px;")
        else:
            self.fav_btn.setText("⭐ Ajouter aux favoris")
            self.fav_btn.setStyleSheet("")

        self.tome_status_lbl.setText("⏳ Vérification des tomes...")
        self.tome_status_lbl.setStyleSheet("color: #fbbf24; font-size: 11px; font-weight: bold; margin-right: 8px;")
        self.cover_label.setText("Chargement...")
        self.chapters_table.setRowCount(0)
        self.download_btn.setEnabled(False)


        # Charger la couverture si présente
        if manga.cover_url:
            self.img_worker = ImageLoaderWorker(manga.cover_url)
            self.img_worker.loaded.connect(self.display_cover)
            self.img_worker.start()

        # Charger les détails et les chapitres
        scraper = ScraperFactory.get_scraper(manga.source)
        if hasattr(self, "details_worker") and self.details_worker.isRunning():
            try:
                self.details_worker.wait(200)  # Attente non-bloquante au lieu de terminate()
            except Exception:
                pass

        self.details_worker = FetchWorker(self._load_manga_full_details, scraper, manga.url)
        self.details_worker.finished.connect(self.display_manga_details)
        self.details_worker.error.connect(self.on_details_error)
        self.details_worker.start()

    def on_details_error(self, err_msg: str):
        self.log_signal.emit("ERROR", f"Erreur lors du chargement des détails: {err_msg}")
        self.manga_synopsis_label.setText(f"❌ Erreur de chargement : {err_msg}")
        self.tome_status_lbl.setText("🔴 Erreur de chargement")
        self.tome_status_lbl.setStyleSheet("color: #f87171; font-size: 11px; font-weight: bold; margin-right: 8px;")

    def display_cover(self, url: str, data: bytes):
        pixmap = QPixmap()
        loaded = pixmap.loadFromData(data)
        if not loaded:
            try:
                from PIL import Image
                import io
                img = Image.open(io.BytesIO(data)).convert("RGB")
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                pixmap.loadFromData(buf.getvalue())
                loaded = True
            except Exception:
                pass
        if loaded and not pixmap.isNull():
            self.cover_label.setPixmap(
                pixmap.scaled(120, 165, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            )
        else:
            self.cover_label.setText("📖")

    def _load_manga_full_details(self, scraper, manga_url):
        details = scraper.get_manga_details(manga_url)
        chapters = scraper.get_chapters(manga_url)
        title_for_vmap = details.title or (self.current_manga.title if self.current_manga else manga_url.rstrip("/").split("/")[-1].replace("-", " "))
        alt_titles = getattr(details, "alt_titles", []) or getattr(self.current_manga, "alt_titles", [])
        
        max_main = get_official_main_limit(title_for_vmap)
        main_chapters = [c for c in chapters if not is_bonus_chapter(c, max_main)]
        c_nums = [c.number for c in main_chapters] if main_chapters else [c.number for c in chapters]
        try:
            src_name, vmap = MultiSourceVolumeProvider.get_official_volumes_for_chapters(title_for_vmap, c_nums, alt_titles=alt_titles)
            manga_meta = MultiSourceVolumeProvider.get_manga_meta(title_for_vmap)
        except Exception as e:
            print(f"[SearchView] Error fetching volume map: {e}")
            src_name, vmap = "Indisponible", {}
            manga_meta = {}

        # Compléter le synopsis et les genres depuis les métadonnées officielles si absents de la source
        if (not details.synopsis or details.synopsis == "Aucun synopsis disponible.") and manga_meta.get("synopsis"):
            details.synopsis = manga_meta["synopsis"]
        if (not details.genres or len(details.genres) == 0) and manga_meta.get("genres"):
            details.genres = manga_meta["genres"]
        if not details.cover_url and manga_meta.get("cover_url"):
            details.cover_url = manga_meta["cover_url"]
        elif not details.cover_url and (not self.current_manga or not self.current_manga.cover_url):
            from downloader.volume_cover_provider import VolumeCoverProvider
            fallback_cover = VolumeCoverProvider.get_main_cover_url(title_for_vmap)
            if fallback_cover:
                details.cover_url = fallback_cover

        return details, chapters, src_name, vmap, manga_meta

    def display_manga_details(self, data):
        details, chapters, src_name, vmap, manga_meta = data
        if details.synopsis:
            self.manga_synopsis_label.setText(details.synopsis)
        if details.genres:
            self.manga_genres_label.setText(f"Genres: {', '.join(details.genres)}")

        if details.cover_url:
            self.img_worker = ImageLoaderWorker(details.cover_url)
            self.img_worker.loaded.connect(self.display_cover)
            self.img_worker.start()

        # Afficher le statut et le nombre de tomes
        status_parts = []
        raw_status = manga_meta.get("status", "")
        total_vols = manga_meta.get("total_volumes") or (len(vmap) if vmap else None)
        total_chaps = manga_meta.get("total_chapters") or len(chapters)

        # Traduction du statut AniList / Kitsu
        status_map = {
            "FINISHED": ("✅ Terminé", "#4ade80"),
            "RELEASING": ("🟢 En cours", "#38bdf8"),
            "NOT_YET_RELEASED": ("⏳ Pas encore sorti", "#fbbf24"),
            "CANCELLED": ("❌ Annulé", "#f87171"),
            "HIATUS": ("⏸️ En pause", "#fbbf24"),
            # Kitsu
            "finished": ("✅ Terminé", "#4ade80"),
            "current": ("🟢 En cours", "#38bdf8"),
            "tba": ("⏳ À venir", "#fbbf24"),
            "unreleased": ("⏳ Pas encore sorti", "#fbbf24"),
            "upcoming": ("⏳ À venir", "#fbbf24"),
        }

        status_text, status_color = status_map.get(raw_status, ("🟢 Statut indisponible", "#94a3b8"))

        if total_vols:
            status_parts.append(f"📚 {total_vols} tome(s)")
        
        last_num = chapters[-1].number if chapters else None
        if last_num and (last_num.isdigit() or re.match(r'^\d+$', last_num)):
            status_parts.append(f"📖 Chapitres 1 à {last_num}")
        elif total_chaps:
            status_parts.append(f"📖 {total_chaps} chapitres")

        if status_text:
            status_parts.append(status_text)

        if status_parts:
            self.manga_status_label.setText("  ·  ".join(status_parts))
            self.manga_status_label.setStyleSheet(f"color: {status_color}; font-size: 12px; font-weight: bold;")
        else:
            self.manga_status_label.setText(f"📚 {len(chapters)} chapitres disponibles")
            self.manga_status_label.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: bold;")

        is_already_volume = len(chapters) > 0 and all(
            c.title.lower().startswith("volume") or c.title.lower().startswith("tome")
            for c in chapters
        )

        self.current_chapters = chapters
        self.current_vmap = vmap
        self.current_vsrc = src_name
        self.current_volume_jobs = self._build_volume_jobs()

        max_main = get_official_main_limit(details.title or (self.current_manga.title if self.current_manga else ""), total_chaps)
        self.current_max_main = max_main

        # Calcul des chapitres principaux vs bonus pour les onglets avec la sécurité max_main
        mains = [c for c in chapters if not is_bonus_chapter(c, max_main)]
        bonuses = [c for c in chapters if is_bonus_chapter(c, max_main)]

        self.btn_filter_main.setText(f"📖 Chapitres principaux ({len(mains)})")
        self.btn_filter_bonus.setText(f"🎁 Chapitres bonus ({len(bonuses)})")
        self.btn_filter_all.setText(f"📚 Tous ({len(chapters)})")

        if is_already_volume:
            self.tome_status_lbl.setText("ℹ️ Publié directement en Tomes")
            self.tome_status_lbl.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: bold; margin-right: 8px;")
            self.group_tomes_cb.setChecked(False)
            self.group_tomes_cb.setEnabled(False)
            self.group_tomes_cb.setToolTip("Cette œuvre contient déjà des volumes complets sur la source.")
        elif vmap and len(vmap) > 0:
            self.tome_status_lbl.setText(f"🟢 {src_name}")
            self.tome_status_lbl.setStyleSheet("color: #4ade80; font-size: 11px; font-weight: bold; margin-right: 8px;")
            self.group_tomes_cb.setEnabled(True)
            self.group_tomes_cb.setToolTip(f"Découpage exact par Tome basé sur {src_name}")
        else:
            self.tome_status_lbl.setText("🔴 Tomes officiels indisponibles")
            self.tome_status_lbl.setStyleSheet("color: #f87171; font-size: 11px; font-weight: bold; margin-right: 8px;")
            self.group_tomes_cb.setChecked(False)
            self.group_tomes_cb.setEnabled(False)

        # Afficher le tableau selon l'état actuel de la case "Regrouper en Tomes"
        if self.group_tomes_cb.isChecked() and self.current_vmap:
            self.render_volumes_table()
        else:
            self.render_chapters_table()

        self.download_btn.setEnabled(len(chapters) > 0)
        self.log_signal.emit("INFO", f"{len(chapters)} chapitres chargés pour {details.title or self.current_manga.title}.")

        # ── Vérification en arrière-plan d'une meilleure source ────
        self.cross_source_card.hide()
        self.better_source_target = None
        current_src = self.current_manga.source if self.current_manga else self.source_combo.currentText()
        title_for_check = details.title or (self.current_manga.title if self.current_manga else "")

        if hasattr(self, "cross_worker") and self.cross_worker.isRunning():
            try:
                self.cross_worker.wait(100)
            except Exception:
                pass

        self.cross_worker = FetchWorker(self._check_better_sources_worker, title_for_check, current_src, len(chapters))
        self.cross_worker.finished.connect(self.on_better_source_found)
        self.cross_worker.start()

    def _check_better_sources_worker(self, manga_title: str, current_source: str, current_chap_count: int):
        for src_name in ScraperFactory.list_sources():
            if src_name == current_source:
                continue
            try:
                scr = ScraperFactory.get_scraper(src_name)
                results = scr.search(manga_title)
                if results:
                    top = results[0]
                    chaps = scr.get_chapters(top.url)
                    if len(chaps) > current_chap_count + 5:
                        return (src_name, len(chaps), manga_title)
            except Exception:
                pass
        return None

    def on_better_source_found(self, data):
        if data:
            better_src, better_count, target_title = data
            current_count = len(self.current_chapters)
            diff = better_count - current_count
            if diff > 0:
                self.better_source_target = (better_src, target_title)
                self.cross_source_lbl.setText(
                    f"💡 {diff} chapitres plus récents sont disponibles sur {better_src} ! ({better_count} chapitres contre {current_count} ici)"
                )
                self.switch_source_btn.setText(f"⚡ Basculer sur {better_src}")
                self.cross_source_card.show()

    def on_switch_source_clicked(self):
        if hasattr(self, "better_source_target") and self.better_source_target:
            target_src, target_title = self.better_source_target
            self.source_combo.setCurrentText(target_src)
            self.search_input.setText(target_title)
            self.start_search()

    def on_chapter_filter_text_changed(self, text: str):
        q = text.strip().lower()
        for row in range(self.chapters_table.rowCount()):
            item = self.chapters_table.item(row, 1)
            if not item:
                continue
            title = item.text().lower()
            if not q or q in title:
                self.chapters_table.setRowHidden(row, False)
            else:
                self.chapters_table.setRowHidden(row, True)

    def set_chapter_filter(self, filter_type: str):
        self.current_chapter_filter = filter_type
        self.btn_filter_main.setChecked(filter_type == "main")
        self.btn_filter_bonus.setChecked(filter_type == "bonus")
        self.btn_filter_all.setChecked(filter_type == "all")

        # Décocher le mode tomes si un filtre par type de chapitre est cliqué
        if self.group_tomes_cb.isChecked():
            self.group_tomes_cb.blockSignals(True)
            self.group_tomes_cb.setChecked(False)
            self.group_tomes_cb.blockSignals(False)

        self.render_chapters_table()
        self.update_download_btn_text()

    def _build_volume_jobs(self) -> list[DownloadJob]:
        """Construit la liste des jobs de téléchargement par Tome à partir de vmap."""
        if not self.current_chapters or not self.current_vmap:
            return []

        vmap = self.current_vmap
        grouped_tomes: list[tuple[int, list[Chapter]]] = []

        assigned_chaps = set()
        for vol_num, official_cnums in vmap.items():
            chunk = [
                c for c in self.current_chapters
                if c.number in official_cnums or (c.number.isdigit() and str(c.number) in official_cnums)
            ]
            if chunk:
                grouped_tomes.append((vol_num, chunk))
                for c in chunk:
                    assigned_chaps.add(c.number)

        remaining = [c for c in self.current_chapters if c.number not in assigned_chaps]
        if remaining:
            max_vol = max(vmap.keys(), default=0)
            chunk_size = 9
            for i in range(0, len(remaining), chunk_size):
                chunk = remaining[i : i + chunk_size]
                grouped_tomes.append((max_vol + 1 + (i // chunk_size), chunk))

        volume_jobs = []
        for vol_num, chunk in grouped_tomes:
            first_num = chunk[0].number
            last_num = chunk[-1].number
            range_str = f"Chapitres {first_num} à {last_num}" if len(chunk) > 1 else f"Chapitre {first_num}"

            job = DownloadJob(
                job_id=str(uuid.uuid4()),
                manga_title=chunk[0].manga_title,
                chapter_number=range_str,
                chapter_title=f"Tome {vol_num:02d}",
                chapter_url=chunk[0].url,
                source=chunk[0].source,
                is_volume=True,
                volume_number=vol_num,
                chapters_list=chunk,
            )
            volume_jobs.append(job)

        return volume_jobs

    def on_tomes_mode_toggled(self, state):
        if self.group_tomes_cb.isChecked() and self.current_vmap:
            self.render_volumes_table()
        else:
            self.render_chapters_table()
        self.update_download_btn_text()

    def render_chapters_table(self):
        """Affiche les chapitres individuels dans le tableau selon le filtre sélectionné (main, bonus, all)."""
        filt = getattr(self, "current_chapter_filter", "main")
        max_main = getattr(self, "current_max_main", None)

        if filt == "bonus":
            displayed_chapters = [c for c in self.current_chapters if is_bonus_chapter(c, max_main)]
        elif filt == "main":
            displayed_chapters = [c for c in self.current_chapters if not is_bonus_chapter(c, max_main)]
        else:
            displayed_chapters = self.current_chapters

        self.chapters_table.setHorizontalHeaderLabels(["", "CHAPITRE", "ACTION"])
        self.chapters_table.setRowCount(len(displayed_chapters))

        manga_title = self.current_manga.title if self.current_manga else ""

        for row, chap in enumerate(displayed_chapters):
            self.chapters_table.setRowHeight(row, 38)

            cb = QCheckBox()
            cb.stateChanged.connect(self.update_download_btn_text)
            cb_item = QWidget()
            cb_layout = QHBoxLayout(cb_item)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self.chapters_table.setCellWidget(row, 0, cb_item)

            # Indicateur Lu / Non-lu
            is_read = reading_history.is_read(manga_title, chap.number)
            if is_read:
                title_text = f"✓ {chap.title}"
            else:
                title_text = chap.title

            title_item = QTableWidgetItem(title_text)
            title_item.setData(Qt.UserRole, chap)
            if is_read:
                title_item.setForeground(QColor("#4ade80"))
                title_item.setToolTip(f"Chapitre déjà lu")
            self.chapters_table.setItem(row, 1, title_item)

            dl_btn = QPushButton("⬇ Télécharger")
            dl_btn.setObjectName("SecondaryButton")
            dl_btn.setFixedSize(110, 28)
            dl_btn.clicked.connect(lambda _, c=chap: self.download_single_chapter(c))

            read_btn = QPushButton("✓ Lu" if is_read else "👁️ Lire")
            read_btn.setFixedSize(65, 28)
            if is_read:
                read_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #166534;
                        color: #4ade80;
                        font-weight: bold;
                        font-size: 11px;
                        border-radius: 6px;
                    }
                    QPushButton:hover {
                        background-color: #15803d;
                    }
                """)
            else:
                read_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #0284c7;
                        color: #ffffff;
                        font-weight: bold;
                        font-size: 11px;
                        border-radius: 6px;
                    }
                    QPushButton:hover {
                        background-color: #0369a1;
                    }
                """)
            read_btn.clicked.connect(lambda _, c=chap: self.open_reader_dialog(c))

            dl_w = QWidget()
            dl_l = QHBoxLayout(dl_w)
            dl_l.setContentsMargins(2, 2, 2, 2)
            dl_l.setSpacing(6)
            dl_l.setAlignment(Qt.AlignCenter)
            dl_l.addWidget(read_btn)
            dl_l.addWidget(dl_btn)
            self.chapters_table.setCellWidget(row, 2, dl_w)


        self.select_all_cb.setChecked(False)

    def open_reader_dialog(self, chapter: Chapter):
        """Ouvre la visionneuse de scans intégrée pour lire ce chapitre."""
        from ui.widgets.reader_dialog import ReaderDialog
        try:
            scraper = ScraperFactory.get_scraper(chapter.source)
            dialog = ReaderDialog(chapter, scraper, self)
            dialog.exec()
            # Marquer le chapitre comme lu après fermeture du lecteur
            reading_history.mark_as_read(
                chapter.manga_title, chapter.number, chapter.source
            )
            # Rafraîchir le tableau pour mettre à jour l'indicateur
            if self.group_tomes_cb.isChecked() and self.current_vmap:
                self.render_volumes_table()
            else:
                self.render_chapters_table()
            self.log_signal.emit("INFO", f"Chapitre {chapter.number} marqué comme lu.")
        except Exception as e:
            QMessageBox.warning(self, "Erreur du lecteur", f"Impossible d'ouvrir le chapitre : {e}")

    def open_select_range_dialog(self):
        """Affiche une boîte de dialogue pour sélectionner rapidement une plage de chapitres."""
        from PySide6.QtWidgets import QInputDialog
        if not self.current_chapters:
            return

        text, ok = QInputDialog.getText(
            self,
            "Sélectionner une plage de chapitres",
            "Entrez la plage de chapitres à télécharger (ex: 1-50 ou 10 à 25) :"
        )
        if ok and text:
            import re
            numbers = [int(n) for n in re.findall(r'\d+', text)]
            if len(numbers) >= 2:
                start_c, end_c = sorted(numbers[:2])
                count = 0
                for row in range(self.chapters_table.rowCount()):
                    item = self.chapters_table.item(row, 1)
                    if not item:
                        continue
                    chap = item.data(Qt.UserRole)
                    if chap:
                        try:
                            num = float(chap.number)
                            if start_c <= num <= end_c:
                                cb_widget = self.chapters_table.cellWidget(row, 0)
                                if cb_widget:
                                    cb = cb_widget.findChild(QCheckBox)
                                    if cb:
                                        cb.setChecked(True)
                                        count += 1
                        except ValueError:
                            pass
                self.log_signal.emit("INFO", f"{count} chapitre(s) sélectionné(s) de {start_c} à {end_c}.")
                self.update_download_btn_text()

    def toggle_favorite_current_manga(self):

        """Ajoute ou retire le manga actuel de la bibliothèque de favoris."""
        from favorites import favorites_manager
        if not self.current_manga:
            return
        is_fav = favorites_manager.toggle_favorite(self.current_manga)
        if is_fav:
            self.fav_btn.setText("★ Dans la bibliothèque")
            self.fav_btn.setStyleSheet("background-color: #f59e0b; color: #ffffff; font-weight: bold; border-radius: 6px; padding: 4px 10px;")
            self.log_signal.emit("SUCCESS", f"'{self.current_manga.title}' ajouté à votre bibliothèque de favoris !")
        else:
            self.fav_btn.setText("⭐ Ajouter aux favoris")
            self.fav_btn.setStyleSheet("")
            self.log_signal.emit("INFO", f"'{self.current_manga.title}' retiré des favoris.")


    def render_volumes_table(self):
        """Affiche directement les Tomes/Volumes officiels dans le tableau à la place des chapitres."""
        self.chapters_table.setHorizontalHeaderLabels(["", "TOME OFFICIEL", "ACTION"])
        vol_jobs = self.current_volume_jobs
        self.chapters_table.setRowCount(len(vol_jobs))

        manga_title = self.current_manga.title if self.current_manga else ""
        meta = MultiSourceVolumeProvider.get_manga_meta(manga_title)
        is_series_finished = (meta.get("status") in ["FINISHED", "finished", "completed"])

        for row, job in enumerate(vol_jobs):
            self.chapters_table.setRowHeight(row, 40)

            cb = QCheckBox()
            cb.stateChanged.connect(self.update_download_btn_text)
            cb_item = QWidget()
            cb_layout = QHBoxLayout(cb_item)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self.chapters_table.setCellWidget(row, 0, cb_item)

            chap_count = len(job.chapters_list)
            is_last_vol = (row == len(vol_jobs) - 1)

            if is_last_vol:
                if is_series_finished:
                    title_text = f"{job.chapter_title} ({job.chapter_number}) — {chap_count} chapitres 🏁 (Tome Final)"
                    title_item = QTableWidgetItem(title_text)
                    title_item.setForeground(QColor("#4ade80"))
                    title_item.setToolTip("✅ Ce tome clôture la série officielle (Série terminée).")
                else:
                    title_text = f"{job.chapter_title} ({job.chapter_number}) — {chap_count} chapitres ⏳ (En cours de parution)"
                    title_item = QTableWidgetItem(title_text)
                    title_item.setForeground(QColor("#fbbf24"))
                    title_item.setToolTip("⏳ Ce tome est en cours de parution.")
            else:
                title_text = f"{job.chapter_title} ({job.chapter_number}) — {chap_count} chapitres"
                title_item = QTableWidgetItem(title_text)

            title_item.setData(Qt.UserRole, job)
            self.chapters_table.setItem(row, 1, title_item)

            dl_btn = QPushButton(f"⬇ {job.chapter_title}")
            dl_btn.setObjectName("SecondaryButton")
            dl_btn.setFixedSize(120, 28)
            dl_btn.clicked.connect(lambda _, j=job: self.download_requested.emit([j]))

            dl_w = QWidget()
            dl_l = QHBoxLayout(dl_w)
            dl_l.setContentsMargins(2, 2, 2, 2)
            dl_l.setAlignment(Qt.AlignCenter)
            dl_l.addWidget(dl_btn)
            self.chapters_table.setCellWidget(row, 2, dl_w)

        self.select_all_cb.setChecked(False)

    def toggle_select_all(self, state):
        checked = state == Qt.Checked or state == 2
        for row in range(self.chapters_table.rowCount()):
            cb_widget = self.chapters_table.cellWidget(row, 0)
            if cb_widget:
                cb = cb_widget.findChild(QCheckBox)
                if cb:
                    cb.setChecked(checked)
        self.update_download_btn_text()

    def update_download_btn_text(self):
        count = 0
        for row in range(self.chapters_table.rowCount()):
            cb_widget = self.chapters_table.cellWidget(row, 0)
            if cb_widget:
                cb = cb_widget.findChild(QCheckBox)
                if cb and cb.isChecked():
                    count += 1

        if count == 0:
            unit = "Tome(s)" if (self.group_tomes_cb.isChecked() and self.current_vmap) else "chapitre(s)"
            self.download_btn.setText(f"🚀 Télécharger les {unit} sélectionnés")
        else:
            if self.group_tomes_cb.isChecked() and self.current_vmap:
                self.download_btn.setText(f"🚀 Télécharger ({count} Tome(s) Officiel(s))")
            else:
                self.download_btn.setText(f"🚀 Télécharger ({count} chapitre(s))")

    def download_single_chapter(self, chapter: Chapter):
        job = DownloadJob(
            job_id=str(uuid.uuid4()),
            manga_title=chapter.manga_title,
            chapter_number=chapter.number,
            chapter_title=chapter.title,
            chapter_url=chapter.url,
            source=chapter.source
        )
        self.download_requested.emit([job])

    def on_download_clicked(self):
        selected_jobs: list = []
        for row in range(self.chapters_table.rowCount()):
            cb_widget = self.chapters_table.cellWidget(row, 0)
            if cb_widget:
                cb = cb_widget.findChild(QCheckBox)
                if cb and cb.isChecked():
                    item = self.chapters_table.item(row, 1)
                    if item:
                        obj = item.data(Qt.UserRole)
                        if obj:
                            selected_jobs.append(obj)

        if not selected_jobs:
            unit = "Tome" if (self.group_tomes_cb.isChecked() and self.current_vmap) else "chapitre"
            QMessageBox.warning(self, "Sélection vide", f"Veuillez cocher au moins un {unit} à télécharger.")
            return

        if self.group_tomes_cb.isChecked() and self.current_vmap:
            # selected_jobs contient directement les DownloadJob des Tomes
            self.download_requested.emit(selected_jobs)
            total_chaps = sum(len(j.chapters_list) for j in selected_jobs)
            QMessageBox.information(
                self, "Téléchargement par Tomes Officiels lancé",
                f"{len(selected_jobs)} Tome(s) Officiel(s) ({total_chaps} chapitres) ajouté(s) à la file.\nSource: {self.current_vsrc}"
            )
        else:
            # selected_jobs contient des objets Chapter
            final_jobs = []
            for chap in selected_jobs:
                job = DownloadJob(
                    job_id=str(uuid.uuid4()),
                    manga_title=chap.manga_title,
                    chapter_number=chap.number,
                    chapter_title=chap.title,
                    chapter_url=chap.url,
                    source=chap.source,
                )
                final_jobs.append(job)

            self.download_requested.emit(final_jobs)
            QMessageBox.information(
                self, "Téléchargement lancé",
                f"{len(final_jobs)} chapitre(s) ajouté(s) à la file de téléchargement."
            )

    def on_table_context_menu(self, pos):
        """Menu contextuel clic-droit sur les chapitres/tomes."""
        row = self.chapters_table.rowAt(pos.y())
        if row < 0 or row >= self.chapters_table.rowCount():
            return

        title_item = self.chapters_table.item(row, 1)
        if not title_item:
            return

        obj = title_item.data(Qt.UserRole)
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction, QGuiApplication

        menu = QMenu(self)
        if isinstance(obj, Chapter):
            act_read = menu.addAction("👁️ Lire ce chapitre")
            act_dl = menu.addAction("⬇️ Télécharger ce chapitre")
            menu.addSeparator()
            act_copy = menu.addAction("📋 Copier le nom")
            menu.addSeparator()
            act_sel_all = menu.addAction("✅ Tout sélectionner")
            act_desel_all = menu.addAction("❌ Tout désélectionner")

            action = menu.exec(self.chapters_table.viewport().mapToGlobal(pos))
            if action == act_read:
                self.open_reader_dialog(obj)
            elif action == act_dl:
                self.download_single_chapter(obj)
            elif action == act_copy:
                QGuiApplication.clipboard().setText(title_item.text())
            elif action == act_sel_all:
                self.toggle_select_all(Qt.Checked)
            elif action == act_desel_all:
                self.toggle_select_all(Qt.Unchecked)
        elif isinstance(obj, DownloadJob):
            act_dl_tome = menu.addAction(f"⬇️ Télécharger {title_item.text()}")
            menu.addSeparator()
            act_sel_all = menu.addAction("✅ Tout sélectionner")
            act_desel_all = menu.addAction("❌ Tout désélectionner")

            action = menu.exec(self.chapters_table.viewport().mapToGlobal(pos))
            if action == act_dl_tome:
                self.download_requested.emit([obj])
            elif action == act_sel_all:
                self.toggle_select_all(Qt.Checked)
            elif action == act_desel_all:
                self.toggle_select_all(Qt.Unchecked)

