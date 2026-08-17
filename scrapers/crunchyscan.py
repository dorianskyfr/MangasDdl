import json
import re
import urllib.parse
import httpx
from bs4 import BeautifulSoup
from typing import List
from models import Manga, Chapter, Page
from scrapers.base import BaseScraper
from config import config_manager

ALIAS_MAP = {
    "my dress up darling": "sexy cosplay doll",
    "my dress-up darling": "sexy cosplay doll",
    "sono bisque doll": "sexy cosplay doll",
    "bisque doll": "sexy cosplay doll",
}


class CrunchyScanScraper(BaseScraper):
    """
    Scraper pour SushiScan / Crunchyscan (France)
    Utilise https://sushiscan.fr pour une disponibilité 100% sans erreur 403.
    """
    def __init__(self):
        self._domain = config_manager.get("crunchyscan_domain", "https://sushiscan.fr")
        self.headers = {
            "User-Agent": config_manager.get("user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
            "Referer": f"{self._domain}/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        }

    @property
    def source_name(self) -> str:
        return "Crunchyscan"

    @property
    def base_url(self) -> str:
        return self._domain

    def _get_client(self) -> httpx.Client:
        return httpx.Client(headers=self.headers, follow_redirects=True, timeout=12.0)

    def search(self, query: str) -> List[Manga]:
        results = []
        seen_urls = set()

        raw_query = query.strip().lower()

        # Détection spéciale pour séparer Classroom of the Elite en 3 entrées distinctes sur Crunchyscan
        if any(k in raw_query for k in ["classroom of the elite", "horikita", "cote", "youkoso", "2nd year"]):
            base_url = f"{self.base_url}/catalogue/1-classroom-of-the-elite/"
            thumb = "https://sushiscan.fr/wp-content/uploads/classroom-of-the-elite.jpg"
            return [
                Manga(
                    title="Classroom of the Elite (1ère Année / Year 1)",
                    url=f"{base_url}#year1",
                    source=self.source_name,
                    cover_url=thumb
                ),
                Manga(
                    title="Classroom of the Elite (2ème Année / 2nd Year)",
                    url=f"{base_url}#year2",
                    source=self.source_name,
                    cover_url=thumb
                ),
                Manga(
                    title="Classroom of the Elite: Horikita (Spin-off)",
                    url=f"{base_url}#horikita",
                    source=self.source_name,
                    cover_url=thumb
                ),
            ]

        search_query = ALIAS_MAP.get(raw_query, raw_query)

        # Mots clés significatifs pour le filtrage de pertinence
        q_words = [w for w in search_query.split() if len(w) > 2]

        encoded_query = urllib.parse.quote(search_query)
        search_url = f"{self.base_url}/?s={encoded_query}"

        try:
            with self._get_client() as client:
                resp = client.get(search_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "lxml")
                    links = soup.select("a[href*='/catalogue/']")
                    for l in links:
                        manga_url = l.get("href", "")
                        if not manga_url or manga_url in seen_urls or manga_url.endswith("/catalogue/") or "?" in manga_url:
                            continue

                        title_el = l.select_one(".tt, .title, h2, h3, .post-title, div.title") or l
                        raw_title = title_el.get_text(strip=True) if title_el else ""
                        clean_title = re.sub(r'^(En Cours|Terminé|En Attente|Abandonné)', '', raw_title, flags=re.IGNORECASE)
                        clean_title = re.sub(r'(Chapitre|Volume|Tome)\s*\d+.*$', '', clean_title, flags=re.IGNORECASE).strip()

                        if not clean_title:
                            clean_title = manga_url.rstrip("/").split("/")[-1].replace("-", " ").title()

                        searchable_text = f"{clean_title.lower()} {manga_url.lower()}"
                        if q_words:
                            all_match = all(
                                re.search(r'\b' + re.escape(w) + r'\b', searchable_text)
                                or w in clean_title.lower().split()
                                for w in q_words
                            )
                            if not all_match:
                                continue

                        seen_urls.add(manga_url)

                        img_el = l.select_one("img") or (l.parent.select_one("img") if l.parent else None)
                        cover_url = None
                        if img_el:
                            cover_url = img_el.get("src") or img_el.get("data-src")

                        results.append(Manga(
                            title=clean_title,
                            url=manga_url,
                            source=self.source_name,
                            cover_url=cover_url
                        ))

        except Exception as e:
            print(f"[{self.source_name}] Erreur recherche: {e}")

        # Tri par pertinence
        def sort_key(m):
            t = m.title.lower().strip()
            if t == search_query:
                return (0, t)
            if t.startswith(search_query):
                return (1, t)
            if search_query in t:
                return (2, t)
            return (3, t)

        results.sort(key=sort_key)

        # Fallback slug direct
        if not results and query:
            slug = search_query.replace(" ", "-")
            direct_urls = [
                f"{self.base_url}/catalogue/{slug}/",
                f"{self.base_url}/catalogue/1-{slug}/",
                f"{self.base_url}/catalogue/{slug}-scan/",
                f"{self.base_url}/manga/{slug}/"
            ]
            for d_url in direct_urls:
                try:
                    with self._get_client() as client:
                        r = client.get(d_url)
                        if r.status_code == 200:
                            soup = BeautifulSoup(r.text, "lxml")
                            title_el = soup.select_one("h1.entry-title, h1")
                            title = title_el.get_text(strip=True) if title_el else query.title()
                            img_el = soup.select_one(".thumb img, .summary_image img, img.wp-post-image")
                            cover_url = (img_el.get("src") or img_el.get("data-src")) if img_el else None
                            results.append(Manga(
                                title=title,
                                url=d_url,
                                source=self.source_name,
                                cover_url=cover_url
                            ))
                            break
                except Exception:
                    pass

        return results

    def get_manga_details(self, manga_url: str) -> Manga:
        clean_url = manga_url.split("#")[0]
        manga = Manga(title="", url=manga_url, source=self.source_name)

        if "#year2" in manga_url:
            manga.title = "Classroom of the Elite (2ème Année / 2nd Year)"
        elif "#horikita" in manga_url:
            manga.title = "Classroom of the Elite: Horikita (Spin-off)"
        elif "#year1" in manga_url:
            manga.title = "Classroom of the Elite (1ère Année / Year 1)"

        try:
            with self._get_client() as client:
                resp = client.get(clean_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "lxml")
                    if not manga.title:
                        title_el = soup.select_one("h1.entry-title, h1, .post-title")
                        manga.title = title_el.get_text(strip=True) if title_el else clean_url.rstrip("/").split("/")[-1].replace("-", " ").title()

                    synopsis_el = soup.select_one(".entry-content, .summary__content, .manga-excerpt, .description, div[itemprop='description']")
                    if synopsis_el:
                        manga.synopsis = synopsis_el.get_text(strip=True)

                    img_el = soup.select_one(".thumb img, .summary_image img, img.wp-post-image")
                    if img_el:
                        manga.cover_url = img_el.get("src") or img_el.get("data-src")

                    genres_els = soup.select(".mgen a, .genres-content a, .genre a")
                    manga.genres = [g.get_text(strip=True) for g in genres_els if g.get_text(strip=True)]
        except Exception as e:
            print(f"[{self.source_name}] Erreur détails: {e}")
        return manga

    def get_chapters(self, manga_url: str) -> List[Chapter]:
        chapters = []
        clean_url = manga_url.split("#")[0]
        manga_title = clean_url.rstrip('/').split('/')[-1].replace('-', ' ').title()

        display_title = manga_title
        if "#year2" in manga_url:
            display_title = "Classroom of the Elite (2ème Année / 2nd Year)"
        elif "#horikita" in manga_url:
            display_title = "Classroom of the Elite: Horikita (Spin-off)"
        elif "#year1" in manga_url:
            display_title = "Classroom of the Elite (1ère Année / Year 1)"

        try:
            with self._get_client() as client:
                resp = client.get(clean_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "lxml")
                    links = soup.select("#chapterlist li a, .wp-manga-chapter a, ul.cl-effect-1 a, .eplister a, .cl-effect-1 a")
                    seen = set()
                    for link in links:
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
                            manga_title=display_title,
                            source=self.source_name
                        ))

                    chapters.reverse()

                    # Filtrage propre par sous-section
                    if "#year1" in manga_url:
                        # Volume 1 à Volume 7
                        filtered = []
                        for c in chapters:
                            m = re.search(r'\d+', c.number)
                            if m and int(m.group()) <= 7:
                                filtered.append(c)
                        chapters = filtered if any("volume" in c.title.lower() for c in chapters) else chapters[:57]
                    elif "#year2" in manga_url:
                        # Volume 8 et plus
                        filtered = []
                        for c in chapters:
                            m = re.search(r'\d+', c.number)
                            if m and int(m.group()) >= 8:
                                filtered.append(c)
                        chapters = filtered if any("volume" in c.title.lower() for c in chapters) else chapters[57:]
                    elif "#horikita" in manga_url:
                        # Horikita spin-off (Volume 1 à 2 ou chapitres 1 à 12)
                        chapters = chapters[:2] if any("volume" in c.title.lower() for c in chapters) else chapters[:12]

        except Exception as e:
            print(f"[{self.source_name}] Erreur chapitres: {e}")
        return chapters

    def get_chapter_pages(self, chapter_url: str) -> List[Page]:
        pages = []
        try:
            with self._get_client() as client:
                resp = client.get(chapter_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "lxml")
                    imgs = soup.select("#readerarea img, .reading-content img, .rd-reading-area img")
                    if imgs:
                        for idx, img in enumerate(imgs, 1):
                            src = img.get("src") or img.get("data-src")
                            if src and not src.endswith("loading.gif"):
                                pages.append(Page(number=idx, url=src.strip(), referer=chapter_url))

                    if not pages:
                        scripts = soup.find_all("script")
                        for script in scripts:
                            if script.string and "ts_reader.run" in script.string:
                                match = re.search(r'ts_reader\.run\((.*?)\);', script.string, re.DOTALL)
                                if match:
                                    try:
                                        data = json.loads(match.group(1))
                                        sources = data.get("sources", [])
                                        if sources:
                                            img_urls = sources[0].get("images", [])
                                            for idx, url in enumerate(img_urls, 1):
                                                pages.append(Page(number=idx, url=url, referer=chapter_url))
                                    except Exception:
                                        pass
                                break
        except Exception as e:
            print(f"[{self.source_name}] Erreur pages: {e}")
        return pages
