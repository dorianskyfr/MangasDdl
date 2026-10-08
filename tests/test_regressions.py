import io
import json
import time
import zipfile
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

import httpx
from PIL import Image
from config import ConfigManager, config_manager
from downloader.exporter import Exporter
from downloader.worker import DownloadWorker
from models import Manga, Page, Chapter, DownloadJob, DownloadStatus
from storage import atomic_json_write, user_file
from updater import _parse_version


def image_bytes():
    stream = io.BytesIO()
    Image.new('RGB', (32, 48), '#8463d3').save(stream, 'JPEG')
    return stream.getvalue()


def make_job(job_id='test', fmt='CBZ', number='1'):
    return DownloadJob(job_id, 'Test & Manga', number, 'Chapitre 1', 'https://example.test/chapter', 'MangaDex', export_format=fmt)


def setup_download(monkeypatch, tmp_path, pages, responder):
    monkeypatch.setitem(config_manager.config, 'download_dir', str(tmp_path))
    scraper = type('Scraper', (), {'get_chapter_pages': lambda self, url: pages})()
    monkeypatch.setattr('downloader.worker.ScraperFactory.get_scraper', lambda source: scraper)
    client = httpx.Client
    monkeypatch.setattr('downloader.worker.httpx.Client', lambda **kwargs: client(transport=httpx.MockTransport(responder), **kwargs))


def test_small_valid_image_downloads_and_xml_metadata(monkeypatch, tmp_path):
    setup_download(monkeypatch, tmp_path, [Page(1, 'https://example.test/1.jpg')], lambda request: httpx.Response(200, content=image_bytes()))
    job = make_job()
    DownloadWorker(job).run()
    assert job.status == DownloadStatus.COMPLETED
    assert job.downloaded_pages == 1
    with zipfile.ZipFile(job.save_path) as archive:
        assert ElementTree.fromstring(archive.read('ComicInfo.xml')).find('Series').text == job.manga_title
        assert 'page_001.jpg' in archive.namelist()


def test_missing_page_never_exports_partial_chapter(monkeypatch, tmp_path):
    pages = [Page(1, 'https://example.test/1.jpg'), Page(2, 'https://example.test/2.jpg')]
    setup_download(monkeypatch, tmp_path, pages, lambda request: httpx.Response(404) if request.url.path.endswith('2.jpg') else httpx.Response(200, content=image_bytes()))
    job = make_job()
    DownloadWorker(job).run()
    assert job.status == DownloadStatus.FAILED
    assert job.downloaded_pages == 1
    assert not list(tmp_path.rglob('*.cbz'))
    assert list(tmp_path.rglob('*.jpg'))


def test_failed_export_keeps_images(monkeypatch, tmp_path):
    setup_download(monkeypatch, tmp_path, [Page(1, 'https://example.test/1.jpg')], lambda request: httpx.Response(200, content=image_bytes()))
    monkeypatch.setattr(Exporter, 'export_cbz', lambda *args, **kwargs: False)
    job = make_job()
    DownloadWorker(job).run()
    assert job.status == DownloadStatus.FAILED
    assert list(tmp_path.rglob('*.jpg'))


def test_missing_volume_chapter_cannot_be_omitted(monkeypatch, tmp_path):
    setup_download(monkeypatch, tmp_path, [], lambda request: httpx.Response(404))
    monkeypatch.setattr('downloader.worker.VolumeCoverProvider.get_volume_cover_url', lambda *args: None)
    job = make_job()
    job.is_volume = True
    job.volume_number = 1
    job.chapters_list = [Chapter('Chapitre 1', '1', job.chapter_url, job.manga_title, job.source)]
    DownloadWorker(job).run()
    assert job.status == DownloadStatus.FAILED
    assert not list(tmp_path.rglob('*.cbz'))


def test_filename_cannot_escape_download_directory(monkeypatch, tmp_path):
    setup_download(monkeypatch, tmp_path, [Page(1, 'https://example.test/1.jpg')], lambda request: httpx.Response(200, content=image_bytes()))
    job = make_job(number='../../escaped')
    DownloadWorker(job).run()
    assert job.status == DownloadStatus.COMPLETED
    assert Path(job.save_path).is_relative_to(tmp_path)


def test_invalid_configuration_recovers_valid_fields(tmp_path):
    path = tmp_path / 'config.json'
    path.write_text(json.dumps({'max_concurrent_threads': 'bad', 'theme': 'light', 'download_dir': ''}))
    config = ConfigManager(path)
    assert config.get('max_concurrent_threads') == 4
    assert config.get('theme') == 'light'
    original = config.config.copy()
    import pytest
    with pytest.raises(ValueError):
        config.update({'download_dir': str(tmp_path), 'mangadex_domain': 'wrong'})
    assert config.config == original


def test_atomic_save_failure_preserves_original(monkeypatch, tmp_path):
    path = tmp_path / 'state.json'
    atomic_json_write(path, {'saved': True})
    monkeypatch.setattr('storage.os.replace', lambda *args: (_ for _ in ()).throw(OSError('read-only')))
    import pytest
    with pytest.raises(OSError):
        atomic_json_write(path, {'saved': False})
    assert json.loads(path.read_text()) == {'saved': True}
    assert not list(tmp_path.glob('*.tmp'))


def test_invalid_pdf_does_not_replace_existing_export(tmp_path):
    images = tmp_path / 'images'
    images.mkdir()
    (images / 'page.png').write_bytes(b'not an image')
    output = tmp_path / 'book.pdf'
    output.write_bytes(b'previous export')
    assert not Exporter.export_pdf(images, output)
    assert output.read_bytes() == b'previous export'


def test_epub_title_with_xml_characters(tmp_path):
    (tmp_path / 'page.jpg').write_bytes(image_bytes())
    output = tmp_path / 'book.epub'
    assert Exporter.export_epub(tmp_path, output, manga_title='A & B <C>')
    with zipfile.ZipFile(output) as archive:
        ElementTree.fromstring(archive.read('OEBPS/content.opf'))
        ElementTree.fromstring(archive.read('OEBPS/page_0001.xhtml'))
        assert archive.infolist()[0].filename == 'mimetype'
        assert archive.infolist()[0].compress_type == zipfile.ZIP_STORED


def test_release_version_comparison():
    assert _parse_version('1.0') == _parse_version('v1.0.0')
    assert _parse_version('1.0.1') > _parse_version('1.0.0')
    assert _parse_version('1.0.0-beta.1') < _parse_version('1.0.0')


def test_bonus_filter_matches_words_instead_of_substrings():
    from ui.views.search_view import is_bonus_chapter, get_official_main_limit
    chapter = Chapter('Expression et espoir', '12', '', '', '')
    assert not is_bonus_chapter(chapter)
    chapter.title = 'Chapitre spécial'
    assert is_bonus_chapter(chapter)
    assert get_official_main_limit('The Beginning After The End') is None


def test_cross_source_fallback_cannot_choose_wrong_series():
    from models import matching_manga
    results = [Manga('Boruto', '/wrong', 'MangaDex'), Manga('Naruto', '/right', 'MangaDex')]
    assert matching_manga(results, 'NARUTO').url == '/right'
    assert matching_manga(results, 'One Piece') is None


def test_retry_reuses_verified_pages_and_fetches_missing_page(monkeypatch, tmp_path):
    calls = []
    retry = [False]
    def respond(request):
        calls.append(request.url.path)
        if request.url.path == '/2.jpg' and not retry[0]:
            return httpx.Response(404)
        return httpx.Response(200, content=image_bytes())
    pages = [Page(1, 'https://example.test/1.jpg'), Page(2, 'https://example.test/2.jpg')]
    setup_download(monkeypatch, tmp_path, pages, respond)
    job = make_job()
    DownloadWorker(job).run()
    assert job.status == DownloadStatus.FAILED
    retry[0] = True
    DownloadWorker(job).run()
    assert job.status == DownloadStatus.COMPLETED
    assert calls.count('/1.jpg') == 1
    assert calls.count('/2.jpg') == 2
    with zipfile.ZipFile(job.save_path) as archive:
        assert len([name for name in archive.namelist() if name.endswith('.jpg')]) == 2
