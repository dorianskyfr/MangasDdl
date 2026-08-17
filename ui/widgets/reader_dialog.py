from __future__ import annotations
import sys
import httpx
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QProgressBar
)
from PySide6.QtGui import QPixmap, QKeySequence, QShortcut, QWheelEvent
from PySide6.QtCore import Qt, QThread, Signal

from models import Chapter, Page
from scrapers.factory import ScraperFactory


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
            if pages:
                self.pages_ready.emit(pages)
                return

            fallback_sources = ["Anime-Sama", "Crunchyscan", "Scan-VF", "MangaDex"]
            current_src = getattr(self.scraper, "source_name", "")
            c_num = str(self.chapter.number)

            for alt_src in fallback_sources:
                if alt_src == current_src:
                    continue
                try:
                    alt_scraper = ScraperFactory.get_scraper(alt_src)
                    search_res = alt_scraper.search(self.chapter.manga_title)
                    if search_res:
                        alt_chaps = alt_scraper.get_chapters(search_res[0].url)
                        matched = next((c for c in alt_chaps if str(c.number) == c_num), None)
                        if matched:
                            alt_pages = alt_scraper.get_chapter_pages(matched.url)
                            if alt_pages:
                                self.pages_ready.emit(alt_pages)
                                return
                except Exception:
                    pass

            self.pages_ready.emit([])
        except Exception as e:
            self.error.emit(str(e))


class PageDownloaderWorker(QThread):
    page_downloaded = Signal(int, bytes)

    def __init__(self, idx: int, url: str, referer: str = None):
        super().__init__()
        self.idx = idx
        self.url = url
        self.referer = referer

    def run(self):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "image/avif,image/webp,image/*,*/*;q=0.8",
        }
        if self.referer:
            headers["Referer"] = self.referer

        for attempt in range(3):
            try:
                with httpx.Client(headers=headers, timeout=15.0, follow_redirects=True) as client:
                    r = client.get(self.url)
                    if r.status_code == 200 and len(r.content) > 500:
                        self.page_downloaded.emit(self.idx, r.content)
                        return
            except Exception:
                pass
        self.page_downloaded.emit(self.idx, b"")


class ReaderDialog(QDialog):
    """Visionneuse de scans / Lecteur de chapitres intégré haute performance."""

    def __init__(self, chapter: Chapter, scraper, parent=None):
        super().__init__(parent)
        self.chapter = chapter
        self.scraper = scraper
        self.pages: list[Page] = []
        self.current_page_idx = 0
        self.page_cache: dict[int, bytes] = {}
        self.workers: list[PageDownloaderWorker] = []
        self.zoom_factor = 1.0

        self.is_webtoon_mode = any(w in (chapter.manga_title or "").lower() for w in [
            "tbate", "begining", "beginning", "solo leveling", "tower of god",
            "god of high school", "omniscient", "webtoon", "manhwa", "magic emperor",
            "tomb raider", "nano machine", "mercenary enrollment", "eleceed"
        ])

        self.setWindowTitle(f"📖 Lecteur — {chapter.manga_title} ({chapter.title})")
        self.resize(1000, 950)
        self.setMinimumSize(700, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #06080c;
                color: #f8fafc;
            }
        """)

        self.init_ui()
        self.setup_shortcuts()
        self.load_pages()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header controls
        header = QHBoxLayout()

        self.title_lbl = QLabel(f"📖 {self.chapter.manga_title} — {self.chapter.title}")
        self.title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #38bdf8;")
        header.addWidget(self.title_lbl)
        header.addStretch()

        # Zoom controls
        zoom_out_btn = QPushButton("🔍 -")
        zoom_out_btn.setToolTip("Zoom arrière (Ctrl -)")
        zoom_out_btn.setStyleSheet("background-color: #1e293b; color: white; border-radius: 6px; padding: 4px 8px; font-weight: bold;")
        zoom_out_btn.clicked.connect(self.zoom_out)
        header.addWidget(zoom_out_btn)

        self.zoom_lbl = QLabel("100%")
        self.zoom_lbl.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: bold; min-width: 40px;")
        self.zoom_lbl.setAlignment(Qt.AlignCenter)
        header.addWidget(self.zoom_lbl)

        zoom_in_btn = QPushButton("🔍 +")
        zoom_in_btn.setToolTip("Zoom avant (Ctrl +)")
        zoom_in_btn.setStyleSheet("background-color: #1e293b; color: white; border-radius: 6px; padding: 4px 8px; font-weight: bold;")
        zoom_in_btn.clicked.connect(self.zoom_in)
        header.addWidget(zoom_in_btn)

        self.mode_btn = QPushButton("📜 Mode Webtoon" if self.is_webtoon_mode else "📖 Mode Manga")
        self.mode_btn.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; border-radius: 6px; padding: 4px 10px;")
        self.mode_btn.clicked.connect(self.toggle_mode)
        header.addWidget(self.mode_btn)

        self.prev_btn = QPushButton("◀ Précédente")
        self.prev_btn.setEnabled(False)
        self.prev_btn.setStyleSheet("background-color: #1e293b; color: white; border-radius: 6px; padding: 4px 10px;")
        self.prev_btn.clicked.connect(self.prev_page)
        header.addWidget(self.prev_btn)

        self.page_counter_lbl = QLabel("Page 0 / 0")
        self.page_counter_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #f8fafc; min-width: 90px;")
        self.page_counter_lbl.setAlignment(Qt.AlignCenter)
        header.addWidget(self.page_counter_lbl)

        self.next_btn = QPushButton("Suivante ▶")
        self.next_btn.setEnabled(False)
        self.next_btn.setStyleSheet("background-color: #1e293b; color: white; border-radius: 6px; padding: 4px 10px;")
        self.next_btn.clicked.connect(self.next_page)
        header.addWidget(self.next_btn)

        self.fs_btn = QPushButton("⛶ Plein écran")
        self.fs_btn.setStyleSheet("background-color: #334155; color: white; border-radius: 6px; padding: 4px 8px;")
        self.fs_btn.clicked.connect(self.toggle_fullscreen)
        header.addWidget(self.fs_btn)

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
        self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #38bdf8; }")
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

    def setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key_Left), self, self.prev_page)
        QShortcut(QKeySequence(Qt.Key_Right), self, self.next_page)
        QShortcut(QKeySequence(Qt.Key_Space), self, self.next_page)
        QShortcut(QKeySequence(Qt.Key_PageUp), self, self.prev_page)
        QShortcut(QKeySequence(Qt.Key_PageDown), self, self.next_page)
        QShortcut(QKeySequence(Qt.Key_Home), self, lambda: self.load_page_image(0))
        QShortcut(QKeySequence(Qt.Key_End), self, lambda: self.load_page_image(len(self.pages) - 1))
        QShortcut(QKeySequence(Qt.Key_F), self, self.toggle_fullscreen)
        QShortcut(QKeySequence(Qt.Key_F11), self, self.toggle_fullscreen)
        QShortcut(QKeySequence(QKeySequence.ZoomIn), self, self.zoom_in)
        QShortcut(QKeySequence(QKeySequence.ZoomOut), self, self.zoom_out)
        QShortcut(QKeySequence(Qt.CTRL | Qt.Key_0), self, self.reset_zoom)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.fs_btn.setText("⛶ Plein écran")
        else:
            self.showFullScreen()
            self.fs_btn.setText("🗗 Quitter plein écran")

    def zoom_in(self):
        if self.zoom_factor < 2.5:
            self.zoom_factor += 0.15
            self.apply_zoom()

    def zoom_out(self):
        if self.zoom_factor > 0.4:
            self.zoom_factor -= 0.15
            self.apply_zoom()

    def reset_zoom(self):
        self.zoom_factor = 1.0
        self.apply_zoom()

    def apply_zoom(self):
        self.zoom_lbl.setText(f"{int(self.zoom_factor * 100)}%")
        if self.is_webtoon_mode:
            self.render_webtoon_view()
        elif self.current_page_idx in self.page_cache:
            self.display_image_data(self.page_cache[self.current_page_idx])

    def load_pages(self):
        self.fetcher = PageFetcherWorker(self.scraper, self.chapter)
        self.fetcher.pages_ready.connect(self.on_pages_ready)
        self.fetcher.error.connect(self.on_error)
        self.fetcher.start()

    def toggle_mode(self):
        self.is_webtoon_mode = not self.is_webtoon_mode
        self.mode_btn.setText("📜 Mode Webtoon" if self.is_webtoon_mode else "📖 Mode Manga")
        if self.pages:
            if self.is_webtoon_mode:
                self.render_webtoon_view()
            else:
                self.scroll_area.setWidget(self.img_label)
                self.load_page_image(self.current_page_idx)

    def render_webtoon_view(self):
        container = QWidget()
        v_layout = QVBoxLayout(container)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(0)
        v_layout.setAlignment(Qt.AlignCenter)

        target_w = int(max(500, self.scroll_area.width() - 40) * self.zoom_factor)

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
            base_w = self.scroll_area.width() - 40
            target_w = int(max(500, base_w) * self.zoom_factor)
            scaled_pix = pix.scaledToWidth(target_w, Qt.SmoothTransformation)
            self.img_label.setPixmap(scaled_pix)
        else:
            self.img_label.setText("❌ Image corrompue ou introuvable")

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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self.is_webtoon_mode and self.current_page_idx in self.page_cache:
            self.display_image_data(self.page_cache[self.current_page_idx])

    def closeEvent(self, event):
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
