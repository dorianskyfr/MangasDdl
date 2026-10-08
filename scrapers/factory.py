from threading import RLock
from scrapers.anime_sama import AnimeSamaScraper
from scrapers.crunchyscan import CrunchyScanScraper
from scrapers.japscan import JapScanScraper
from scrapers.unekoscans import UNekoScansScraper
from scrapers.scan_vf import ScanVFScraper
from scrapers.mangadex import MangaDexScraper


class ScraperFactory:
    _scrapers = {}
    _lock = RLock()
    _types = (AnimeSamaScraper, CrunchyScanScraper, JapScanScraper, UNekoScansScraper, ScanVFScraper, MangaDexScraper)

    @classmethod
    def initialize(cls):
        with cls._lock:
            if not cls._scrapers:
                instances = [scraper_type() for scraper_type in cls._types]
                cls._scrapers = {instance.source_name: instance for instance in instances}

    @classmethod
    def reload(cls):
        # Existing requests keep their instances; subsequent requests use new domains.
        with cls._lock:
            cls._scrapers = {}
            cls.initialize()

    @classmethod
    def get_scraper(cls, name):
        with cls._lock:
            cls.initialize()
            if name not in cls._scrapers:
                raise ValueError(f"Source de scraping inconnue : '{name}'")
            return cls._scrapers[name]

    @classmethod
    def list_sources(cls):
        with cls._lock:
            cls.initialize()
            return list(cls._scrapers)
