"""
MangaDex Scraper v2.0 (REST API v5 Officielle)
==============================================
"""

import urllib.parse
from typing import List, Optional
import httpx

from models import Manga, Chapter, Page
from scrapers.base import BaseScraper, logger
from config import config_manager


class MangaDexScraper(BaseScraper):
    """Scraper pour MangaDex utilisant l'API REST v5 officielle."""
    
    timeout = 15.0
    
    def __init__(self):
        super().__init__()
        self._api_url = config_manager.get("mangadex_domain", "https://api.mangadex.org")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }

    @property
    def source_name(self) -> str:
        return "MangaDex"

    @property
    def base_url(self) -> str:
        return self._api_url

    def search(self, query: str) -> List[Manga]:
        """Recherche de mangas sur MangaDex via l'API v5."""
        raw_query = query.strip()
        if not raw_query:
            return []

        results = []
        url = f"{self.base_url}/manga?title={urllib.parse.quote(raw_query)}&limit=20&includes[]=cover_art&order[followedCount]=desc"

        try:
            with httpx.Client(headers=self.headers, timeout=12.0, follow_redirects=True) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    data = resp.json().get("data", [])
                    for item in data:
                        m_id = item.get("id")
                        attrs = item.get("attributes", {})
                        title_obj = attrs.get("title", {})
                        title = title_obj.get("fr") or title_obj.get("en") or list(title_obj.values())[0] if title_obj else "Manga Inconnu"

                        # Image de couverture
                        cover_url = None
                        for rel in item.get("relationships", []):
                            if rel.get("type") == "cover_art":
                                file_name = rel.get("attributes", {}).get("fileName")
                                if file_name:
                                    cover_url = f"https://uploads.mangadex.org/covers/{m_id}/{file_name}.512.jpg"
                                break

                        results.append(Manga(
                            title=title,
                            url=f"{self.base_url}/manga/{m_id}",
                            source=self.source_name,
                            cover_url=cover_url
                        ))
        except Exception as e:
            logger.debug(f"[{self.source_name}] Erreur recherche: {e}")

        # Tri par pertinence : correspondance exacte en premier
        def sort_key(m):
            t = m.title.lower()
            q = raw_query.lower()
            if t == q:
                return (0, t)
            if t.startswith(q):
                return (1, t)
            if q in t:
                return (2, t)
            return (3, t)

        results.sort(key=sort_key)
        return results

    def get_manga_details(self, manga_url: str) -> Manga:
        """Récupère les détails d'un manga via l'API v5."""
        manga_id = manga_url.rstrip("/").split("/")[-1]
        manga = Manga(title="", url=manga_url, source=self.source_name)
        try:
            with httpx.Client(headers=self.headers, timeout=12.0, follow_redirects=True) as client:
                resp = client.get(f"{self.base_url}/manga/{manga_id}?includes[]=cover_art")
                if resp.status_code == 200:
                    item = resp.json().get("data", {})
                    attrs = item.get("attributes", {})
                    title_obj = attrs.get("title", {})
                    manga.title = title_obj.get("fr") or title_obj.get("en") or list(title_obj.values())[0] if title_obj else "Manga Inconnu"
                    desc_obj = attrs.get("description", {})
                    manga.synopsis = desc_obj.get("fr") or desc_obj.get("en") or ""
        except Exception as e:
            logger.debug(f"[{self.source_name}] Erreur details: {e}")
        return manga


    def get_chapters(self, manga_url: str) -> List[Chapter]:
        """Récupère les chapitres disponibles en Français ou fallback toutes langues."""
        chapters = []
        manga_id = manga_url.rstrip("/").split("/")[-1]
        
        manga_title = "Manga"
        details = self.get_manga_details(manga_url)
        if details and details.title:
            manga_title = details.title

        content_ratings = "contentRating[]=safe&contentRating[]=suggestive&contentRating[]=erotica&contentRating[]=pornographic"

        def _fetch_all_feed(base_feed_url: str) -> list:
            """Récupère tous les chapitres avec pagination (max 500 par requête)."""
            all_data = []
            offset = 0
            try:
                with httpx.Client(headers=self.headers, timeout=12.0, follow_redirects=True) as client:
                    while True:
                        url = f"{base_feed_url}&offset={offset}"
                        resp = client.get(url)
                        if resp.status_code != 200:
                            break
                        result = resp.json()
                        batch = result.get("data", [])
                        if not batch:
                            break
                        all_data.extend(batch)
                        total = result.get("total", 0)
                        offset += len(batch)
                        if offset >= total:
                            break
            except Exception as e:
                logger.debug(f"[{self.source_name}] Erreur pagination: {e}")
            return all_data

        url_fr = f"{self.base_url}/manga/{manga_id}/feed?translatedLanguage[]=fr&{content_ratings}&order[chapter]=asc&limit=500"
        url_all = f"{self.base_url}/manga/{manga_id}/feed?{content_ratings}&order[chapter]=asc&limit=500"

        data = _fetch_all_feed(url_fr)
        
        # Fallback si 0 chapitre en FR
        if not data:
            data = _fetch_all_feed(url_all)

        seen_chaps = set()
        for item in data:
            ch_id = item.get("id")
            attrs = item.get("attributes", {})
            num = attrs.get("chapter")
            
            # Ignorer les chapitres sans numéro (oneshots, extras)
            if not num:
                continue
            
            # Filtrer les chapitres sans images (externes ou vides)
            pages_count = attrs.get("pages", 0)
            if pages_count == 0:
                continue
            
            if num in seen_chaps:
                continue
            seen_chaps.add(num)
            
            raw_title = attrs.get("title")
            lang = attrs.get("translatedLanguage", "").upper()
            lang_str = f" [{lang}]" if lang else ""
            title = f"Chapitre {num}" + (f" : {raw_title}" if raw_title else "") + lang_str
            
            chapters.append(Chapter(
                title=title,
                number=num,
                url=f"{self.base_url}/at-home/server/{ch_id}",
                manga_title=manga_title,
                source=self.source_name
            ))

        return chapters

    def get_chapter_pages(self, chapter_url: str) -> List[Page]:
        """Récupère les liens d'images d'un chapitre via l'endpoint @at-home."""
        pages = []
        try:
            with httpx.Client(headers=self.headers, timeout=12.0, follow_redirects=True) as client:
                resp = client.get(chapter_url)
                if resp.status_code == 200:
                    data = resp.json()
                    base_url = data.get("baseUrl")
                    ch_hash = data.get("chapter", {}).get("hash")
                    filenames = data.get("chapter", {}).get("data", [])

                    if base_url and ch_hash and filenames:
                        for idx, fname in enumerate(filenames, 1):
                            img_url = f"{base_url}/data/{ch_hash}/{fname}"
                            pages.append(Page(
                                number=idx,
                                url=img_url,
                                referer="https://mangadex.org/"
                            ))
        except Exception as e:
            logger.debug(f"[{self.source_name}] Erreur pages: {e}")

        return pages
