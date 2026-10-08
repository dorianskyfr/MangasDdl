from __future__ import annotations
from ui.tasks import ManagedThread

import sys
import httpx
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QProgressBar, QStackedWidget, QFrame
)
from PySide6.QtGui import QPixmap, QKeySequence, QShortcut, QWheelEvent
from PySide6.QtCore import Qt, QThread, Signal, QTimer

from models import Chapter, Page, matching_manga
from scrapers.factory import ScraperFactory


class PageFetcherWorker(ManagedThread):
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
                if self.isInterruptionRequested():
                    return
                if alt_src == current_src:
                    continue
                try:
                    alt_scraper = ScraperFactory.get_scraper(alt_src)
                    search_res = alt_scraper.search(self.chapter.manga_title)
                    candidate = matching_manga(search_res, self.chapter.manga_title)
                    if candidate:
                        alt_chaps = alt_scraper.get_chapters(candidate.url)
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


class PageDownloaderWorker(ManagedThread):
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
            if self.isInterruptionRequested():
                return
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
    """Reader with bounded image requests and persistent manga/webtoon widgets."""

    def __init__(self, chapter, scraper, parent=None):
        super().__init__(parent)
        self.chapter = chapter
        self.scraper = scraper
        self.pages = []
        self.page_cache = {}
        self.workers = []
        self._inflight = {}
        self._pending = []
        self._closing = False
        self._labels = []
        self.current_page_idx = 0
        self.zoom_factor = 1.0
        self.completed_reading = False
        self.is_webtoon_mode = any(word in chapter.manga_title.lower() for word in ("webtoon", "manhwa", "solo leveling", "beginning"))
        self.setWindowTitle(f"Lecteur — {chapter.manga_title} · {chapter.title}")
        self.resize(1100, 850)
        self.setMinimumSize(800, 580)
        self.init_ui()
        for key, callback in (("Left", self.prev_page), ("Right", self.next_page), ("Space", self.next_page), ("F", self.toggle_fullscreen), ("F11", self.toggle_fullscreen), ("Ctrl++", self.zoom_in), ("Ctrl+-", self.zoom_out), ("Ctrl+0", self.reset_zoom)):
            QShortcut(QKeySequence(key), self, callback)
        self.fetcher = PageFetcherWorker(scraper, chapter)
        self.fetcher.pages_ready.connect(self.on_pages_ready)
        self.fetcher.error.connect(self.on_error)
        self.fetcher.start()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        title = QLabel(self.chapter.manga_title)
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        header = QHBoxLayout()
        self.page_counter_lbl = QLabel("Chargement…")
        header.addWidget(self.page_counter_lbl)
        header.addStretch()
        self.zoom_lbl = QLabel("100%")
        self.prev_btn = self._button("←", self.prev_page, header)
        self.prev_btn.setToolTip("Page précédente (←)")
        self.next_btn = self._button("→", self.next_page, header)
        self.next_btn.setToolTip("Page suivante (→ / Espace)")
        self._button("−", self.zoom_out, header)
        header.addWidget(self.zoom_lbl)
        self._button("+", self.zoom_in, header)
        self.mode_btn = self._button("Mode manga" if self.is_webtoon_mode else "Mode webtoon", self.toggle_mode, header)
        self.fs_btn = self._button("Plein écran", self.toggle_fullscreen, header)
        self._button("Fermer", self.close, header)
        layout.addLayout(header)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)
        self.stack = QStackedWidget()
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.img_label = QLabel("Chargement des pages du chapitre…")
        self.img_label.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidget(self.img_label)
        self.webtoon_area = QScrollArea()
        self.webtoon_area.setWidgetResizable(True)
        self.webtoon_container = QWidget()
        self.webtoon_layout = QVBoxLayout(self.webtoon_container)
        self.webtoon_layout.setContentsMargins(0, 0, 0, 0)
        self.webtoon_layout.setSpacing(0)
        self.webtoon_area.setWidget(self.webtoon_container)
        self.webtoon_area.verticalScrollBar().valueChanged.connect(self._on_scroll)
        self.stack.addWidget(self.scroll_area)
        self.stack.addWidget(self.webtoon_area)
        layout.addWidget(self.stack)
        self.update_page_counter()

    def _button(self, text, callback, layout):
        button = QPushButton(text)
        button.setObjectName("SecondaryButton")
        button.clicked.connect(callback)
        layout.addWidget(button)
        return button

    def on_pages_ready(self, pages):
        if self._closing:
            return
        self.progress_bar.hide()
        self.pages = pages or []
        if not self.pages:
            self.on_error("Aucune page disponible pour ce chapitre.")
            return
        for idx in range(len(self.pages)):
            label = QLabel(f"Page {idx + 1} · chargement…")
            label.setAlignment(Qt.AlignCenter)
            label.setMinimumHeight(120)
            self.webtoon_layout.addWidget(label)
            self._labels.append(label)
        self.update_page_counter()
        self._show_mode()

    def on_error(self, message):
        if not self._closing:
            self.progress_bar.hide()
            self.img_label.setText(f"Impossible de charger le chapitre.\n{message}")
            self.stack.setCurrentIndex(0)

    def _queue(self, indices):
        for idx in indices:
            if 0 <= idx < len(self.pages) and idx not in self.page_cache and idx not in self._inflight and idx not in self._pending:
                self._pending.append(idx)
        self._pump()

    def _pump(self):
        if self._closing:
            return
        while self._pending and len(self._inflight) < 4:
            idx = self._pending.pop(0)
            page = self.pages[idx]
            worker = PageDownloaderWorker(idx, page.url, page.referer)
            self._inflight[idx] = worker
            self.workers.append(worker)
            worker.page_downloaded.connect(self.on_page_downloaded)
            worker.finished.connect(self._worker_finished)
            worker.start()

    def _worker_finished(self):
        worker = self.sender()
        self._inflight.pop(worker.idx, None)
        self._pump()

    def on_page_downloaded(self, idx, data):
        if self._closing:
            return
        pix = QPixmap()
        if not data or not pix.loadFromData(data) or pix.isNull():
            self._labels[idx].setText(f"Page {idx + 1} indisponible. Rouvrez le chapitre pour réessayer.")
            if idx == self.current_page_idx:
                self.img_label.setText("Page indisponible. Rouvrez le chapitre pour réessayer.")
            return
        self.page_cache[idx] = data
        self._render_webtoon_page(idx)
        if idx == self.current_page_idx and not self.is_webtoon_mode:
            self.display_image_data(data)
            if idx == len(self.pages) - 1:
                self.completed_reading = True
        if self.is_webtoon_mode:
            QTimer.singleShot(0, self._on_scroll)

    def load_page_image(self, idx):
        if not 0 <= idx < len(self.pages):
            return
        self.current_page_idx = idx
        self.update_page_counter()
        if idx in self.page_cache:
            self.display_image_data(self.page_cache[idx])
            if idx == len(self.pages) - 1:
                self.completed_reading = True
        else:
            self.img_label.setText(f"Chargement de la page {idx + 1}…")
            # Prioritize the requested page ahead of preloads.
            if idx in self._pending:
                self._pending.remove(idx)
            self._pending.insert(0, idx) if idx not in self._inflight else None
            self._pump()
        self._queue([idx + 1])
        self.scroll_area.verticalScrollBar().setValue(0)

    def display_image_data(self, data):
        pix = QPixmap()
        if pix.loadFromData(data):
            width = int(max(200, self.scroll_area.viewport().width() - 24) * self.zoom_factor)
            self.img_label.setPixmap(pix.scaledToWidth(width, Qt.SmoothTransformation))

    def _render_webtoon_page(self, idx):
        if idx in self.page_cache:
            pix = QPixmap()
            if pix.loadFromData(self.page_cache[idx]):
                width = int(max(200, self.webtoon_area.viewport().width() - 24) * self.zoom_factor)
                self._labels[idx].setPixmap(pix.scaledToWidth(width, Qt.SmoothTransformation))

    def _show_mode(self):
        self.stack.setCurrentIndex(1 if self.is_webtoon_mode else 0)
        self.prev_btn.setVisible(not self.is_webtoon_mode)
        self.next_btn.setVisible(not self.is_webtoon_mode)
        if self.is_webtoon_mode:
            self._queue(range(len(self.pages)))
            for idx in self.page_cache:
                self._render_webtoon_page(idx)
        else:
            self._pending.clear()
            self.load_page_image(self.current_page_idx)

    def toggle_mode(self):
        self.is_webtoon_mode = not self.is_webtoon_mode
        self.mode_btn.setText("Mode manga" if self.is_webtoon_mode else "Mode webtoon")
        self._show_mode()

    def _on_scroll(self, value=None):
        bar = self.webtoon_area.verticalScrollBar()
        if self.is_webtoon_mode and self.pages and len(self.page_cache) == len(self.pages) and bar.value() >= bar.maximum() - 5:
            self.completed_reading = True

    def update_page_counter(self):
        self.page_counter_lbl.setText(f"Page {self.current_page_idx + 1 if self.pages else 0} / {len(self.pages)}")
        self.prev_btn.setEnabled(self.current_page_idx > 0)
        self.next_btn.setEnabled(self.current_page_idx < len(self.pages) - 1)

    def prev_page(self):
        self.load_page_image(self.current_page_idx - 1)

    def next_page(self):
        self.load_page_image(self.current_page_idx + 1)

    def toggle_fullscreen(self):
        self.showNormal() if self.isFullScreen() else self.showFullScreen()
        self.fs_btn.setText("Quitter plein écran" if self.isFullScreen() else "Plein écran")

    def zoom_in(self):
        self.zoom_factor = min(2.5, self.zoom_factor + 0.15)
        self.apply_zoom()

    def zoom_out(self):
        self.zoom_factor = max(0.4, self.zoom_factor - 0.15)
        self.apply_zoom()

    def reset_zoom(self):
        self.zoom_factor = 1.0
        self.apply_zoom()

    def apply_zoom(self):
        self.zoom_lbl.setText(f"{self.zoom_factor:.0%}")
        for idx in self.page_cache:
            self._render_webtoon_page(idx)
        if self.current_page_idx in self.page_cache:
            self.display_image_data(self.page_cache[self.current_page_idx])

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "stack"):
            self.apply_zoom()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            self.zoom_in() if event.angleDelta().y() > 0 else self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    def done(self, result):
        self._closing = True
        self._pending.clear()
        for worker in [self.fetcher, *self.workers]:
            worker.requestInterruption()
        super().done(result)
