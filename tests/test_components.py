import unittest
import os
import shutil
from pathlib import Path
from PIL import Image

from scrapers.factory import ScraperFactory
from downloader.exporter import Exporter
from models import Manga, Chapter, Page, DownloadJob

class TestMangaDownloader(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("test_output")
        self.test_dir.mkdir(exist_ok=True)
        
        # Créer des images de test fictives
        for i in range(1, 4):
            img = Image.new('RGB', (100, 150), color=(73, 109, 137))
            img.save(self.test_dir / f"page_{i:03d}.jpg")

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_scraper_factory(self):
        sources = ScraperFactory.list_sources()
        self.assertIn("Anime-Sama", sources)
        self.assertIn("Crunchyscan", sources)
        
        as_scraper = ScraperFactory.get_scraper("Anime-Sama")
        self.assertEqual(as_scraper.source_name, "Anime-Sama")
        
        cs_scraper = ScraperFactory.get_scraper("Crunchyscan")
        self.assertEqual(cs_scraper.source_name, "Crunchyscan")

    def test_export_cbz(self):
        cbz_file = self.test_dir / "test_chapter.cbz"
        success = Exporter.export_cbz(self.test_dir, cbz_file)
        self.assertTrue(success)
        self.assertTrue(cbz_file.exists())
        self.assertGreater(cbz_file.stat().st_size, 0)

    def test_export_pdf(self):
        pdf_file = self.test_dir / "test_chapter.pdf"
        success = Exporter.export_pdf(self.test_dir, pdf_file)
        self.assertTrue(success)
        self.assertTrue(pdf_file.exists())
        self.assertGreater(pdf_file.stat().st_size, 0)

if __name__ == "__main__":
    unittest.main()
