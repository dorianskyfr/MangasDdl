from typing import Dict, List
from scrapers.base import BaseScraper
from scrapers.anime_sama import AnimeSamaScraper
from scrapers.crunchyscan import CrunchyScanScraper
from scrapers.japscan import JapScanScraper
from scrapers.unekoscans import UNekoScansScraper
from scrapers.scan_vf import ScanVFScraper
from scrapers.mangadex import MangaDexScraper

class ScraperFactory:
    _scrapers: Dict[str, BaseScraper] = {}

    @classmethod
    def initialize(cls):
        if not cls._scrapers:
            anime_sama = AnimeSamaScraper()
            crunchy_scan = CrunchyScanScraper()
            japscan = JapScanScraper()
            unekoscans = UNekoScansScraper()
            scan_vf = ScanVFScraper()
            mangadex = MangaDexScraper()
            cls._scrapers[anime_sama.source_name] = anime_sama
            cls._scrapers[crunchy_scan.source_name] = crunchy_scan
            cls._scrapers[japscan.source_name] = japscan
            cls._scrapers[unekoscans.source_name] = unekoscans
            cls._scrapers[scan_vf.source_name] = scan_vf
            cls._scrapers[mangadex.source_name] = mangadex

    @classmethod
    def get_scraper(cls, name: str) -> BaseScraper:
        cls.initialize()
        if name not in cls._scrapers:
            raise ValueError(f"Source de scraping inconnue: '{name}'")
        return cls._scrapers[name]

    @classmethod
    def list_sources(cls) -> List[str]:
        cls.initialize()
        return list(cls._scrapers.keys())
