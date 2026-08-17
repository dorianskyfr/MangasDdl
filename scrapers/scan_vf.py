"""
Scan-VF Scraper v1.0
===================

Scraper pour Scan-VF (https://scan-vf.co)
- Site francophone avec des scans VF
- Utilise le sitemap et le scraping direct
"""

import re
import urllib.parse
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Optional



from models import Manga, Chapter, Page
from scrapers.base import BaseScraper, global_cache, logger, cached
from config import config_manager


# ============================================================================
# CONSTANTES
# ============================================================================

SITEMAP_CACHE_KEY = "scan_vf_sitemap"


# ============================================================================
# SCRAPER
# ============================================================================

class ScanVFScraper(BaseScraper):
    """Scraper pour Scan-VF."""
    
    timeout = 15.0
    
    def __init__(self):
        super().__init__()
        self._domain = config_manager.get("scan_vf_domain", "https://www.scan-vf.net")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    
    @property
    def source_name(self) -> str:
        return "Scan-VF"
    
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
        
        # Essayer plusieurs URLs de sitemap
        sitemap_urls = [
            f"{self.base_url}/sitemap.xml",
            f"{self.base_url}/sitemap_index.xml",
        ]
        
        for sitemap_url in sitemap_urls:
            try:
                response = self._get(sitemap_url, headers=self._get_client_headers())
                if self._check_response(response, f"sitemap {sitemap_url}"):
                    soup = self._soup(response)
                    urls = soup.find_all("loc")
                    
                    for url in urls:
                        url_text = url.get_text(strip=True)
                        if "/manga/" in url_text or "/series/" in url_text:
                            slug = url_text.rstrip("/").split("/")[-1]
                            if slug and slug not in ["manga", "series"]:
                                title = slug.replace("-", " ").title()
                                results.append({
                                    "title": title,
                                    "url": url_text,
                                    "slug": slug
                                })
                    
                    if results:
                        break
            
            except Exception as e:
                logger.warning(f"[{self.source_name}] Erreur sitemap {sitemap_url}: {e}")
        
        if results:
            global_cache.set(cache_key, results, ttl=3600)
        
        return results
    
    # ========================================================================
    # RECHERCHE
    # ========================================================================
    
    def search(self, query: str) -> List[Manga]:
        """Recherche des mangas sur Scan-VF via l'API de recherche directe."""
        return self._search_direct(query)
    
    def _search_direct(self, query: str) -> List[Manga]:
        """Recherche directe via l'endpoint de recherche JSON de scan-vf.net."""
        results = []
        search_url = f"{self.base_url}/search?query={urllib.parse.quote(query)}"
        headers = {
            **self._get_client_headers(),
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.base_url}/"
        }

        try:
            with httpx.Client(headers=headers, timeout=10.0, follow_redirects=True, verify=False) as client:
                r = client.get(search_url)
                if r.status_code == 200:
                    data = r.json()
                    for item in data.get("suggestions", []):
                        title = item.get("value", "")
                        slug = item.get("data", "")
                        if slug:
                            manga_url = f"{self.base_url}/{slug}"
                            results.append(Manga(
                                title=title,
                                url=manga_url,
                                source=self.source_name,
                            ))
        except Exception as e:
            import traceback; traceback.print_exc()
            logger.debug(f"[{self.source_name}] Erreur recherche directe: {e}")

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
                
                title_el = soup.select_one("h1.entry-title, h1, .post-title")
                manga.title = title_el.get_text(strip=True) if title_el else manga_url.rstrip("/").split("/")[-1].replace("-", " ").title()
                
                synopsis_el = soup.select_one(".entry-content, .summary__content, .manga-excerpt, .description")
                if synopsis_el:
                    manga.synopsis = synopsis_el.get_text(strip=True)
                
                img_el = soup.select_one(".thumb img, .summary_image img, img.wp-post-image, .img-responsive")
                if img_el:
                    manga.cover_url = img_el.get("src") or img_el.get("data-src")
                
                genres_els = soup.select(".mgen a, .genres-content a, .genre a, .tags a")
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
            with httpx.Client(headers=self._get_client_headers(), timeout=12.0, follow_redirects=True, verify=False) as client:
                r = client.get(manga_url)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "lxml")
                    
                    chap_links = [
                        a for a in soup.find_all("a")
                        if ("chapitre" in a.get("href", "").lower() or "chapitre" in a.get_text().lower())
                        and not a.get("href", "").endswith("/latest-release")
                    ]
                    seen = set()
                    
                    for link in chap_links:
                        chap_url = link.get("href", "")
                        if not chap_url or chap_url in seen:
                            continue
                        seen.add(chap_url)
                        
                        chap_text = link.get_text(strip=True)
                        chap_clean = re.sub(r'\(.*?\)', '', chap_text).strip()
                        
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
            logger.debug(f"[{self.source_name}] Erreur chapitres: {e}")
        
        return chapters
    
    # ========================================================================
    # PAGES
    # ========================================================================
    
    def get_chapter_pages(self, chapter_url: str) -> List[Page]:
        """Recupere les pages d'un chapitre."""
        pages = []
        
        try:
            with httpx.Client(headers=self._get_client_headers(), timeout=12.0, follow_redirects=True, verify=False) as client:
                r = client.get(chapter_url)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "lxml")
                    
                    imgs = soup.select("img.img-responsive, img.scan-page, #viewer img, .viewer-cnt img, .page-img img")
                    for idx, img in enumerate(imgs, 1):
                        src = img.get("data-src") or img.get("src") or img.get("data-url")
                        if src and not src.startswith("data:"):
                            abs_url = urllib.parse.urljoin(chapter_url, src.strip())
                            pages.append(Page(number=idx, url=abs_url, referer=chapter_url))

                
                if not pages:
                    scripts = soup.find_all("script")
                    for script in scripts:
                        if script.string and ("images" in script.string or "data-src" in script.string):
                            matches = re.findall(
                                r'https?://[^\s"\']+\.(?:jpg|jpeg|png|webp)',
                                script.string
                            )
                            for idx, url in enumerate(matches, 1):
                                pages.append(Page(number=idx, url=url, referer=chapter_url))
                            if pages:
                                break
        
        except Exception as e:
            logger.debug(f"[{self.source_name}] Erreur pages: {e}")

        
        logger.debug(f"[{self.source_name}] Pages pour {chapter_url}: {len(pages)}")
        return pages
