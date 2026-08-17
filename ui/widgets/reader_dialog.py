import httpx
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QProgressBar
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap, QKeySequence, QShortcut
from models import Chapter, Page


class PageFetcherWorker(QThread):
    pages_ready = Signal(list)
    error = Signal(str)

    def __init__(self, scraper, chapter: Chapter):
        super().__init__()
        self.scraper = scraper
        self.chapter = chapter

    def run(self):
        try:
            pages = self.scraper.get_chapter_pages(self.chapter.url)
            if not pages and self.chapter:
                from scrapers.factory import ScraperFactory
                fallback_sources = ["Anime-Sama", "Crunchyscan", "Scan-VF", "MangaDex"]
                for alt_src in fallback_sources:
                    if alt_src == getattr(self.scraper, "source_name", ""):
                        continue
                    try:
                        alt_scraper = ScraperFactory.get_scraper(alt_src)
                        search_res = alt_scraper.search(self.chapter.manga_title)
                        if search_res:
                            alt_chaps = alt_scraper.get_chapters(search_res[0].url)
                            matched = next((c for c in alt_chaps if str(c.number) == str(self.chapter.number)), None)
                            if matched:
                                alt_pages = alt_scraper.get_chapter_pages(matched.url)
                                if alt_pages:
                                    pages = alt_pages
                                    break
                    except Exception:
                        pass
            self.pages_ready.emit(pages or [])
        except Exception as e:
            self.error.emit(str(e))


class PageDownloaderWorker(QThread):
    page_downloaded = Signal(int, bytes)

    def __init__(self, page_number: int, url: str, referer: str = None):
        super().__init__()
        self.page_number = page_number
        self.url = url
        self.referer = referer

    def run(self):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": self.referer or "https://anime-sama.to/",
            }
            with httpx.Client(headers=headers, timeout=12.0, follow_redirects=True) as client:
                r = client.get(self.url)
                if r.status_code == 200 and len(r.content) > 100:
                    self.page_downloaded.emit(self.page_number, r.content)
        except Exception:
            pass


class ReaderDialog(QDialog):
    """Visionneuse de scans / Lecteur de chapitres intégré (100% sécurisé)."""

    def __init__(self, chapter: Chapter, scraper, parent=None):
        super().__init__(parent)
        self.chapter = chapter
        self.scraper = scraper
        self.pages: list[Page] = []
        self.current_page_idx = 0
        self.page_cache: dict[int, bytes] = {}
        self.workers: list[PageDownloaderWorker] = []

        self.is_webtoon_mode = any(w in (chapter.manga_title or "").lower() for w in [
            "tbate", "begining", "beginning", "solo leveling", "tower of god",
            "god of high school", "omniscient", "webtoon", "manhwa", "magic emperor",
            "tomb raider", "nano machine", "mercenary enrollment", "eleceed"
        ])

        self.setWindowTitle(f"📖 Lecteur — {chapter.manga_title} ({chapter.title})")
        self.resize(950, 900)
        self.setMinimumSize(700, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #0b0f19;
                color: #f8fafc;
            }
        """)

        self.init_ui()
        self.load_pages()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header controls
        header = QHBoxLayout()

        self.title_lbl = QLabel(f"📖 {self.chapter.manga_title} — {self.chapter.title}")
        self.title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
        header.addWidget(self.title_lbl)
        header.addStretch()

        self.mode_btn = QPushButton("📜 Mode Webtoon (Vertical)" if self.is_webtoon_mode else "📖 Mode Manga (Page par Page)")
        self.mode_btn.setObjectName("SecondaryButton")
        self.mode_btn.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; border-radius: 6px; padding: 4px 10px;")
        self.mode_btn.clicked.connect(self.toggle_mode)
        header.addWidget(self.mode_btn)

        self.prev_btn = QPushButton("◀ Précédente")
        self.prev_btn.setObjectName("SecondaryButton")
        self.prev_btn.setEnabled(False)
        self.prev_btn.clicked.connect(self.prev_page)
        header.addWidget(self.prev_btn)

        self.page_counter_lbl = QLabel("Page 0 / 0")
        self.page_counter_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #f8fafc;")
        header.addWidget(self.page_counter_lbl)

        self.next_btn = QPushButton("Suivante ▶")
        self.next_btn.setObjectName("SecondaryButton")
        self.next_btn.setEnabled(False)
        self.next_btn.clicked.connect(self.next_page)
        header.addWidget(self.next_btn)

        close_btn = QPushButton("✕ Fermer")
        close_btn.setStyleSheet("background-color: #ef4444; color: white; font-weight: bold; border-radius: 6px; padding: 4px 10px;")
        close_btn.clicked.connect(self.close)
        header.addWidget(close_btn)

        layout.addLayout(header)

        # Loading bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        # Image view area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #05070d; }")

        self.img_label = QLabel("Chargement des pages du chapitre...")
        self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setStyleSheet("color: #94a3b8; font-size: 15px;")

        self.scroll_area.setWidget(self.img_label)
        layout.addWidget(self.scroll_area)

        # Shortcuts (Flèches Gauche / Droite)
        QShortcut(QKeySequence(Qt.Key_Left), self, self.prev_page)
        QShortcut(QKeySequence(Qt.Key_Right), self, self.next_page)

    def load_pages(self):
        self.fetcher = PageFetcherWorker(self.scraper, self.chapter)
        self.fetcher.pages_ready.connect(self.on_pages_ready)
        self.fetcher.error.connect(self.on_error)
        self.fetcher.start()

    def toggle_mode(self):
        self.is_webtoon_mode = not self.is_webtoon_mode
        self.mode_btn.setText("📜 Mode Webtoon (Vertical)" if self.is_webtoon_mode else "📖 Mode Manga (Page par Page)")
        if self.pages:
            if self.is_webtoon_mode:
                self.render_webtoon_view()
            else:
                self.scroll_area.setWidget(self.img_label)
                self.load_page_image(self.current_page_idx)

    def render_webtoon_view(self):
        """Affiche toutes les pages bout à bout verticalement sans espace (Mode Webtoon)."""
        container = QWidget()
        v_layout = QVBoxLayout(container)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(0)
        v_layout.setAlignment(Qt.AlignCenter)

        target_w = max(600, self.scroll_area.width() - 40)

        for idx in range(len(self.pages)):
            lbl = QLabel(f"Chargement page {idx+1}...")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #64748b; padding: 10px;")
            v_layout.addWidget(lbl)

            if idx in self.page_cache:
                pix = QPixmap()
                if pix.loadFromData(self.page_cache[idx]) and not pix.isNull():
                    lbl.setPixmap(pix.scaledToWidth(target_w, Qt.SmoothTransformation))
            else:
                def make_cb(target_label=lbl):
                    def cb(page_idx, data):
                        p = QPixmap()
                        if p.loadFromData(data) and not p.isNull():
                            target_label.setPixmap(p.scaledToWidth(target_w, Qt.SmoothTransformation))
                    return cb
                page = self.pages[idx]
                w = PageDownloaderWorker(idx, page.url, page.referer)
                w.page_downloaded.connect(make_cb())
                self.workers.append(w)
                w.start()

        self.scroll_area.setWidget(container)

    def on_pages_ready(self, pages: list[Page]):
        self.progress_bar.hide()
        self.pages = pages or []
        if not pages:
            self.img_label.setText("❌ Impossible de charger les pages de ce chapitre.")
            return

        self.current_page_idx = 0
        self.update_page_counter()

        if self.is_webtoon_mode:
            self.render_webtoon_view()
        else:
            self.load_page_image(0)

        # Preload next page
        if len(pages) > 1 and not self.is_webtoon_mode:
            self.preload_page(1)

    def on_error(self, err_msg: str):
        self.progress_bar.hide()
        self.img_label.setText(f"❌ Erreur de chargement: {err_msg}")

    def load_page_image(self, idx: int):
        if idx < 0 or idx >= len(self.pages):
            return

        self.current_page_idx = idx
        self.update_page_counter()
        page = self.pages[idx]

        if idx in self.page_cache:
            self.display_image_data(self.page_cache[idx])
        else:
            self.img_label.setText(f"Chargement de la page {idx + 1}...")
            self.downloader = PageDownloaderWorker(idx, page.url, page.referer)
            self.downloader.page_downloaded.connect(self.on_page_downloaded)
            self.downloader.start()

    def on_page_downloaded(self, idx: int, data: bytes):
        self.page_cache[idx] = data
        if idx == self.current_page_idx:
            self.display_image_data(data)
        
        # Preload adjacent pages
        if idx + 1 < len(self.pages) and (idx + 1) not in self.page_cache:
            self.preload_page(idx + 1)

    def preload_page(self, idx: int):
        if 0 <= idx < len(self.pages) and idx not in self.page_cache:
            page = self.pages[idx]
            worker = PageDownloaderWorker(idx, page.url, page.referer)
            worker.page_downloaded.connect(self.on_preload_downloaded)
            self.workers.append(worker)
            worker.start()

    def on_preload_downloaded(self, idx: int, data: bytes):
        self.page_cache[idx] = data

    def display_image_data(self, data: bytes):
        pix = QPixmap()
        if pix.loadFromData(data) and not pix.isNull():
            target_w = self.scroll_area.width() - 40
            scaled_pix = pix.scaledToWidth(max(600, target_w), Qt.SmoothTransformation)
            self.img_label.setPixmap(scaled_pix)
        else:
            self.img_label.setText("❌ Image corrompue")

    def update_page_counter(self):
        total = len(self.pages)
        curr = self.current_page_idx + 1 if total > 0 else 0
        self.page_counter_lbl.setText(f"Page {curr} / {total}")
        self.prev_btn.setEnabled(self.current_page_idx > 0)
        self.next_btn.setEnabled(self.current_page_idx < total - 1)

    def prev_page(self):
        if self.current_page_idx > 0:
            self.load_page_image(self.current_page_idx - 1)

    def next_page(self):
        if self.current_page_idx < len(self.pages) - 1:
            self.load_page_image(self.current_page_idx + 1)

    def closeEvent(self, event):
        """Nettoyage sécurisé des threads pour éviter tout crash C++ QObject."""
        if hasattr(self, "fetcher") and self.fetcher.isRunning():
            try:
                self.fetcher.disconnect()
                self.fetcher.wait(100)
            except Exception:
                pass
        if hasattr(self, "downloader") and self.downloader.isRunning():
            try:
                self.downloader.disconnect()
                self.downloader.wait(100)
            except Exception:
                pass
        for w in getattr(self, "workers", []):
            if w.isRunning():
                try:
                    w.disconnect()
                    w.wait(100)
                except Exception:
                    pass
        event.accept()
