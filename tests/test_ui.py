import gc
import time
from unittest.mock import patch
from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import QLabel
from models import Manga, Chapter, Page, DownloadStatus
from ui.main_window import MainWindow
from ui.theme import theme_manager
from ui.tasks import active_workers
from ui.views.search_view import SearchView, FetchWorker
from ui.views.downloads_view import DownloadsView
from ui.widgets.reader_dialog import ReaderDialog, PageFetcherWorker, PageDownloaderWorker
from tests.test_regressions import image_bytes, make_job


def spin(app, condition, timeout=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if condition():
            return
        time.sleep(0.005)
    assert condition(), 'Qt operation timed out'


def test_all_views_and_themes(qapp, monkeypatch):
    monkeypatch.setattr(MainWindow, 'check_for_updates', lambda *args, **kwargs: None)
    window = MainWindow()
    window.show()
    for index in range(5):
        window.switch_view(index)
        assert window.stacked_widget.currentIndex() == index
    window.toggle_theme()
    assert window.settings_view.theme_combo.currentText() == ('Sombre' if theme_manager.is_dark else 'Clair')
    window.toggle_theme()
    window.close()


def test_search_ignores_old_details_response(qapp, monkeypatch):
    def load(self, scraper, manga):
        time.sleep(0.09 if manga.title == 'Old' else 0.01)
        return manga, [], '', {}, {}
    monkeypatch.setattr(SearchView, '_load_manga_full_details', load)
    monkeypatch.setattr(SearchView, '_check_better_sources_worker', lambda *args: None)
    view = SearchView()
    view.select_manga(Manga('Old', 'https://example.test/old', 'MangaDex'))
    view.select_manga(Manga('New', 'https://example.test/new', 'MangaDex'))
    spin(qapp, lambda: not active_workers())
    assert view.current_manga.title == 'New'
    assert view.current_details.title == 'New'
    view.deleteLater()


def test_enter_cannot_start_duplicate_search(qapp, monkeypatch):
    calls = []
    def search(query):
        calls.append(query)
        time.sleep(0.05)
        return []
    view = SearchView()
    view.source_combo.setCurrentText('MangaDex')
    monkeypatch.setattr('ui.views.search_view.ScraperFactory.get_scraper', lambda source: type('Scraper', (), {'search': staticmethod(search)})())
    view.search_input.setText('test')
    view.start_search()
    view.start_search()
    spin(qapp, lambda: not active_workers())
    assert calls == ['test']
    assert view.search_btn.isEnabled()
    view.deleteLater()


def test_worker_survives_owner_reference_drop(qapp):
    worker = FetchWorker(lambda: (time.sleep(0.03), 'done')[1])
    worker.start()
    del worker
    gc.collect()
    assert active_workers()
    spin(qapp, lambda: not active_workers())


def test_reader_switches_modes_without_deleting_image_label(qapp, monkeypatch):
    monkeypatch.setattr(PageFetcherWorker, 'run', lambda self: self.pages_ready.emit([Page(1, 'https://example.test/1.jpg'), Page(2, 'https://example.test/2.jpg')]))
    monkeypatch.setattr(PageDownloaderWorker, 'run', lambda self: self.page_downloaded.emit(self.idx, image_bytes()))
    reader = ReaderDialog(Chapter('Ch. 1', '1', '', 'Test', 'MangaDex'), object())
    reader.show()
    spin(qapp, lambda: len(reader.page_cache) == 2 and not active_workers())
    assert not reader.completed_reading
    original_label = reader.img_label
    for _ in range(4):
        reader.toggle_mode()
        qapp.processEvents()
    assert reader.img_label is original_label
    reader.next_page()
    assert reader.completed_reading
    reader.close()
    reader.deleteLater()


def test_failed_reader_does_not_mark_chapter_read(qapp, monkeypatch):
    monkeypatch.setattr(PageFetcherWorker, 'run', lambda self: self.error.emit('offline'))
    reader = ReaderDialog(Chapter('Ch. 1', '1', '', 'Test', 'MangaDex'), object())
    spin(qapp, lambda: not active_workers())
    assert not reader.completed_reading
    reader.close()


def test_cancelled_running_download_cannot_be_removed(qapp, monkeypatch):
    from downloader.worker import DownloadWorker
    def run(self):
        self.job.status = DownloadStatus.DOWNLOADING
        self.job_started.emit(self.job.job_id)
        time.sleep(0.08)
        self.job.status = DownloadStatus.CANCELLED
        self.job_failed.emit(self.job.job_id, 'cancelled')
    monkeypatch.setattr(DownloadWorker, 'run', run)
    view = DownloadsView()
    job = make_job()
    view.add_jobs([job])
    spin(qapp, lambda: job.status == DownloadStatus.DOWNLOADING)
    view.cancel_job(job.job_id)
    view.clear_completed()
    assert view.table.rowCount() == 1
    spin(qapp, lambda: not active_workers())
    view.clear_completed()
    assert view.table.rowCount() == 0
    view.deleteLater()


def test_queue_is_bounded_and_duplicate_jobs_are_ignored(qapp, monkeypatch):
    from downloader.worker import DownloadWorker
    def run(self):
        self.job.status = DownloadStatus.DOWNLOADING
        time.sleep(0.05)
        self.job.status = DownloadStatus.COMPLETED
        self.job_completed.emit(self.job.job_id, '/tmp/result.cbz')
    monkeypatch.setattr(DownloadWorker, 'run', run)
    view = DownloadsView()
    jobs = [make_job(str(i), number=str(i)) for i in range(4)]
    view.add_jobs(jobs + [make_job('duplicate', number='0')])
    assert len(view.download_tasks) == 2
    assert len(view.jobs) == 4
    assert len(view._pending) == 2
    spin(qapp, lambda: all(job.status == DownloadStatus.COMPLETED for job in jobs) and not active_workers())
    assert len(view.download_tasks) == 4
    view.deleteLater()


def test_source_changes_take_effect_without_restart(qapp, monkeypatch, tmp_path):
    from config import config_manager
    from scrapers.factory import ScraperFactory
    from ui.views.settings_view import SettingsView
    monkeypatch.setattr(config_manager, 'config_path', tmp_path / 'config.json')
    monkeypatch.setitem(config_manager.config, 'download_dir', str(tmp_path / 'downloads'))
    monkeypatch.setattr('ui.views.settings_view.QMessageBox.information', lambda *args: None)
    old = ScraperFactory.get_scraper('MangaDex')
    view = SettingsView()
    view.md_domain_input.setText('https://example.test')
    view.save_settings()
    assert ScraperFactory.get_scraper('MangaDex').base_url == 'https://example.test'
    assert old.base_url != 'https://example.test'
    view.deleteLater()
    config_manager.config['mangadex_domain'] = 'https://api.mangadex.org'
    ScraperFactory.reload()
