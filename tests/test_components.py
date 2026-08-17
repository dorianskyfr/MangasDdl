import unittest
import os
import sys
import shutil
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image
from scrapers.factory import ScraperFactory
from downloader.exporter import Exporter
from downloader.volume_cover_provider import VolumeCoverProvider
from models import Manga, Chapter, Page, DownloadJob, DownloadStatus
from config import config_manager


class TestMangaDownloader(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("test_output")
        self.test_dir.mkdir(exist_ok=True)
        
        # Créer des images de test fictives
        for i in range(1, 6):
            img = Image.new('RGB', (200, 300), color=(50 * i % 255, 100, 150))
            img.save(self.test_dir / f"page_{i:03d}.jpg")

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_scraper_factory(self):
        sources = ScraperFactory.list_sources()
        self.assertIn("Anime-Sama", sources)
        self.assertIn("Crunchyscan", sources)
        self.assertIn("MangaDex", sources)
        self.assertIn("Scan-VF", sources)
        
        as_scraper = ScraperFactory.get_scraper("Anime-Sama")
        self.assertEqual(as_scraper.source_name, "Anime-Sama")
        
        cs_scraper = ScraperFactory.get_scraper("Crunchyscan")
        self.assertEqual(cs_scraper.source_name, "Crunchyscan")

    def test_export_cbz(self):
        cbz_file = self.test_dir / "test_chapter.cbz"
        success = Exporter.export_cbz(self.test_dir, cbz_file, manga_title="Test Manga", chapter_number="1", volume_number=1)
        self.assertTrue(success)
        self.assertTrue(cbz_file.exists())
        self.assertGreater(cbz_file.stat().st_size, 0)

    def test_export_pdf(self):
        pdf_file = self.test_dir / "test_chapter.pdf"
        success = Exporter.export_pdf(self.test_dir, pdf_file)
        self.assertTrue(success)
        self.assertTrue(pdf_file.exists())
        self.assertGreater(pdf_file.stat().st_size, 0)

    def test_export_epub(self):
        epub_file = self.test_dir / "test_chapter.epub"
        success = Exporter.export_epub(self.test_dir, epub_file, manga_title="Test Manga", chapter_number="1", volume_number=1)
        self.assertTrue(success)
        self.assertTrue(epub_file.exists())
        self.assertGreater(epub_file.stat().st_size, 0)

    def test_webtoon_stitching(self):
        stitch_dir = self.test_dir / "stitch_test"
        stitch_dir.mkdir(exist_ok=True)
        for i in range(1, 5):
            img = Image.new('RGB', (800, 400), color=(100, 150, 200))
            img.save(stitch_dir / f"c001_p{i:03d}.jpg")
        
        stitched = Exporter.stitch_webtoon_images(stitch_dir, max_strip_height=1000)
        self.assertTrue(stitched)
        strips = list(stitch_dir.glob("*_webtoon_strip_*.jpg"))
        self.assertGreater(len(strips), 0)

    def test_models_and_config(self):
        manga = Manga(title="Solo Leveling", url="https://example.com", source="Anime-Sama")
        self.assertEqual(manga.title, "Solo Leveling")
        
        chap = Chapter(title="Chapitre 1", number="1", url="https://example.com/1", manga_title="Solo Leveling", source="Anime-Sama")
        self.assertEqual(chap.number, "1")

        self.assertIsNotNone(config_manager.get("download_dir"))


if __name__ == "__main__":
    unittest.main()
