"""
uNekoscans Scraper v1.0
======================

Scraper pour uNekoscans (https://unekoscans.fr)
- Site francophone avec un large catalogue
- Utilise le sitemap et le scraping direct
"""

import re
import urllib.parse
from typing import List, Dict, Optional

from models import Manga, Chapter, Page
from scrapers.base import BaseScraper, global_cache, logger, cached
from config import config_manager


# ============================================================================
# CONSTANTES
# ============================================================================

SITEMAP_CACHE_KEY = "unekoscans_sitemap"


# ============================================================================
# SCRAPER
# ============================================================================

class UNekoScansScraper(BaseScraper):
    """Scraper pour uNekoscans."""
    
    timeout = 15.0
    
    def __init__(self):
        super().__init__()
        self._domain = config_manager.get("unekoscans_domain", "https://unekoscans.fr")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        }
    
    @property
    def source_name(self) -> str:
        return "UNekoScans"
    
    @property
    def base_url(self) -> str:
        return self._domain
    
    def _get_client_headers(self) -> dict:
        """Retourne les headers avec User-Agent aleatoire."""
        return {**self.headers, "User-Agent": self.get_random_user_agent()}
    
    # ========================================================================
    # SITEMAP
    # ========================================================================
    
    @cached(ttl=3600)
    def _get_sitemap(self) -> List[Dict]:
        """Recupere le sitemap du site."""
        cache_key = SITEMAP_CACHE_KEY
        cached = global_cache.get(cache_key)
        if cached:
            return cached
        
        results = []
        sitemap_url = f"{self.base_url}/sitemap_index.xml"
        
        try:
            response = self._get(sitemap_url, headers=self._get_client_headers())
            if self._check_response(response, "sitemap_index"):
                soup = self._soup(response)
                sitemap_links = soup.find_all("loc")
                
                for loc in sitemap_links:
                    sitemap_url = loc.get_text(strip=True)
                    if "post-sitemap" in sitemap_url:
                        # Charger chaque sitemap
                        sitemap_response = self._get(sitemap_url, headers=self._get_client_headers())
                        if self._check_response(sitemap_response, sitemap_url):
                            sitemap_soup = self._soup(sitemap_response)
                            urls = sitemap_soup.find_all("loc")
                            for url in urls:
                                url_text = url.get_text(strip=True)
                                if "/manga/" in url_text:
                                    slug = url_text.rstrip("/").split("/")[-1]
                                    title = slug.replace("-", " ").title()
                                    results.append({
                                        "title": title,
                                        "url": url_text,
                                        "slug": slug
                                    })
        
        except Exception as e:
            logger.debug(f"[{self.source_name}] Erreur sitemap: {e}")

        
        if results:
            global_cache.set(cache_key, results, ttl=3600)
        
        return results
    
    # ========================================================================
    # RECHERCHE
    # ========================================================================
    
    def search(self, query: str) -> List[Manga]:
        """Recherche des mangas sur uNekoscans (sécurisé contre les pannes DNS)."""
        try:
            sitemap = self._get_sitemap()
            if not sitemap:
                return self._search_direct(query)
        except Exception as e:
            return self._search_direct(query)

        
        raw_query = query.strip().lower()
        q_words = [w for w in raw_query.split() if len(w) > 2]
        
        results = []
        seen_urls = set()
        
        for item in sitemap:
            url = item["url"]
            if url in seen_urls:
                continue
            
            title = item["title"]
            slug = item["slug"]
            slug_clean = slug.replace("-", " ")
            title_lower = title.lower()
            
            # Filtrage par mots-cles
            if q_words:
                searchable = f"{title_lower} {slug_clean}"
                all_match = all(
                    re.search(r'\b' + re.escape(w) + r'\b', searchable)
                    or w in slug_clean.split("-")
                    for w in q_words
                )
                if not all_match:
                    continue
            
            seen_urls.add(url)
            results.append(Manga(
                title=title,
                url=url,
                source=self.source_name,
            ))
        
        # Tri par pertinence
        def sort_key(m):
            t = m.title.lower()
            if t == raw_query:
                return (0, t)
            if t.startswith(raw_query):
                return (1, t)
            if raw_query in t:
                return (2, t)
            return (3, t)
        
        results.sort(key=sort_key)
        logger.info(f"[{self.source_name}] Recherche '{query}': {len(results)} resultats")
        return results[:25]
    
    def _search_direct(self, query: str) -> List[Manga]:
        """Recherche directe via l'endpoint de recherche."""
        results = []
        search_url = f"{self.base_url}/?s={urllib.parse.quote(query)}"
        
        try:
            response = self._get(search_url, headers=self._get_client_headers())
            if self._check_response(response, "recherche directe"):
                soup = self._soup(response)
                items = soup.select(".c-tile")
                
                for item in items:
                    link = item.select_one("a")
                    if link:
                        url = link.get("href", "")
                        title = link.get_text(strip=True)
                        
                        img = item.select_one("img")
                        cover_url = None
                        if img:
                            cover_url = img.get("src") or img.get("data-src")
                        
                        results.append(Manga(
                            title=title,
                            url=url,
                            source=self.source_name,
                            cover_url=cover_url
                        ))
        
        except Exception as e:
            logger.error(f"[{self.source_name}] Erreur recherche directe: {e}")
        
        return results[:25]
    
    # ========================================================================
    # DETAILS MANGA
    # ========================================================================
    
    @cached(ttl=3600)
    def get_manga_details(self, manga_url: str) -> Manga:
        """Recupere les details d'un manga."""
        manga = Manga(title="", url=manga_url, source=self.source_name)
        
        try:
            response = self._get(manga_url, headers=self._get_client_headers())
            if self._check_response(response, manga_url):
                soup = self._soup(response)
                
                title_el = soup.select_one("h1.entry-title, h1")
                manga.title = title_el.get_text(strip=True) if title_el else manga_url.rstrip("/").split("/")[-1].replace("-", " ").title()
                
                synopsis_el = soup.select_one(".entry-content, .summary__content, .manga-excerpt, .description")
                if synopsis_el:
                    manga.synopsis = synopsis_el.get_text(strip=True)
                
                img_el = soup.select_one(".thumb img, .summary_image img, img.wp-post-image")
                if img_el:
                    manga.cover_url = img_el.get("src") or img_el.get("data-src")
                
                genres_els = soup.select(".mgen a, .genres-content a, .genre a")
                manga.genres = [g.get_text(strip=True) for g in genres_els if g.get_text(strip=True)]
        
        except Exception as e:
            logger.error(f"[{self.source_name}] Erreur details: {e}")
        
        return manga
    
    # ========================================================================
    # CHAPITRES
    # ========================================================================
    
    @cached(ttl=3600)
    def get_chapters(self, manga_url: str) -> List[Chapter]:
        """Recupere la liste des chapitres."""
        chapters = []
        manga_title = manga_url.rstrip("/").split("/")[-1].replace("-", " ").title()
        
        try:
            response = self._get(manga_url, headers=self._get_client_headers())
            if self._check_response(response, manga_url):
                soup = self._soup(response)
                
                # Trouver la liste des chapitres
                chap_links = soup.select(".wp-manga-chapter a, #chapterlist a, .eplister a, .cl-effect-1 a")
                seen = set()
                
                for link in chap_links:
                    chap_url = link.get("href", "")
                    if not chap_url or chap_url in seen:
                        continue
                    seen.add(chap_url)
                    
                    chap_text = link.get_text(strip=True)
                    chap_clean = re.sub(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}, \d{4}', '', chap_text).strip()
                    
                    num_match = re.search(r'(\d+(?:\.\d+)?)', chap_clean)
                    num = num_match.group(1) if num_match else "1"
                    
                    chapters.append(Chapter(
                        title=chap_clean if chap_clean else f"Chapitre {num}",
                        number=num,
                        url=chap_url,
                        manga_title=manga_title,
                        source=self.source_name
                    ))
                
                chapters.reverse()
        
        except Exception as e:
            logger.error(f"[{self.source_name}] Erreur chapitres: {e}")
        
        logger.info(f"[{self.source_name}] Chapitres pour {manga_title}: {len(chapters)}")
        return chapters
    
    # ========================================================================
    # PAGES
    # ========================================================================
    
    def get_chapter_pages(self, chapter_url: str) -> List[Page]:
        """Recupere les pages d'un chapitre."""
        pages = []
        
        try:
            response = self._get(chapter_url, headers=self._get_client_headers())
            if self._check_response(response, chapter_url):
                soup = self._soup(response)
                
                # Methode 1: Images directes dans le reader
                imgs = soup.select("#readerarea img, .reading-content img, .rd-reading-area img, .reader-img img")
                for idx, img in enumerate(imgs, 1):
                    src = img.get("src") or img.get("data-src")
                    if src and not src.endswith("loading.gif"):
                        abs_url = urllib.parse.urljoin(chapter_url, src.strip())
                        pages.append(Page(number=idx, url=abs_url, referer=chapter_url))
                
                # Methode 2: Chercher dans les scripts JS
                if not pages:
                    scripts = soup.find_all("script")
                    for script in scripts:
                        if script.string and ("images" in script.string or "data-src" in script.string):
                            matches = re.findall(r'https?://[^\s"\']+\.(?:jpg|jpeg|png|webp)', script.string)
                            for idx, url in enumerate(matches, 1):
                                pages.append(Page(number=idx, url=url, referer=chapter_url))
                            if pages:
                                break
        
        except Exception as e:
            logger.error(f"[{self.source_name}] Erreur pages: {e}")
        
        logger.debug(f"[{self.source_name}] Pages pour {chapter_url}: {len(pages)}")
        return pages
