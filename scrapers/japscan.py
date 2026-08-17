import re
import urllib.parse
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from models import Manga, Chapter, Page
from scrapers.base import BaseScraper
from config import config_manager


class JapScanScraper(BaseScraper):
    """
    Scraper pour JapScan (japscan.foo).
    La page d'accueil est accessible sans Cloudflare et contient le catalogue
    complet avec le dernier numéro de chapitre de chaque manga.
    Les pages manga individuelles sont protégées par Cloudflare,
    donc on génère les URLs de chapitres à partir du numéro max.
    """

    # Cache partagé : slug -> max_chapter_num (extrait de la homepage)
    _homepage_cache: Dict[str, dict] = {}

    def __init__(self):
        self._domain = config_manager.get("japscan_domain", "https://www.japscan.foo")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.japscan.foo/"
        }

    @property
    def source_name(self) -> str:
        return "JapScan"

    @property
    def base_url(self) -> str:
        return self._domain

    def _get_client(self) -> httpx.Client:
        return httpx.Client(headers=self.headers, follow_redirects=True, timeout=12.0, verify=False)


    # ──────────────────────────────────────────────────────────────
    # Homepage catalog extraction (pas de Cloudflare)
    # ──────────────────────────────────────────────────────────────
    def _ensure_homepage_loaded(self):
        """Charge et parse la page d'accueil une seule fois pour extraire
        tous les slugs de mangas et leur dernier numéro de chapitre."""
        if JapScanScraper._homepage_cache:
            return

        try:
            with self._get_client() as client:
                resp = client.get(self.base_url)
                if resp.status_code != 200:
                    return

                soup = BeautifulSoup(resp.text, "lxml")
                links = soup.select("a[href*='/manga/']")

                for link in links:
                    href = link.get("href", "")
                    parts = href.strip("/").split("/")
                    if len(parts) < 2 or parts[0] != "manga":
                        continue

                    slug = parts[1]
                    chap_num = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else None

                    # Extraire le titre propre
                    txt = link.get_text(strip=True)
                    # Le texte contient souvent "Title 1189" -> on retire le numéro final
                    title = re.sub(r'\s*\d+$', '', txt).strip()
                    # Retirer les textes de statut (En Cours, Terminé, etc.)
                    title = re.sub(r'^(En Cours|Terminé|OFFICIEL|En Attente|Abandonné)\s*,?\s*', '', title, flags=re.IGNORECASE).strip()
                    # Retirer les descriptions de chapitres (ex: "Chapitre 1189: Le roi du monde")
                    title = re.sub(r'^(Chapitre|Volume)\s*\d+.*$', '', title, flags=re.IGNORECASE).strip()
                    title = re.sub(r',?\s*(Chapitre|Volume)\s*$', '', title, flags=re.IGNORECASE).strip()
                    # Retirer les numéros restants type "1189: description"
                    title = re.sub(r'^\d+\s*:\s*.+$', '', title).strip()

                    # Ignorer les titres vides ou trop courts (bruit HTML)
                    slug_title = slug.replace("-", " ").title()
                    noise_words = {"officiel", "en cours", "terminé", "chapitre", "volume", "tome",
                                   "en attente", "abandonné", "scan", "vf", "fr", ""}
                    if not title or title.lower() in noise_words or len(title) < 3:
                        title = slug_title

                    # Extraire la couverture depuis le parent card
                    cover_url = None
                    img_el = link.select_one("img")
                    if not img_el and link.parent:
                        img_el = link.parent.select_one("img")
                    if img_el:
                        raw_cover = img_el.get("src") or img_el.get("data-src") or ""
                        # Ignorer les data:image placeholders (1px transparent)
                        if raw_cover and not raw_cover.startswith("data:"):
                            cover_url = raw_cover

                    if slug not in JapScanScraper._homepage_cache:
                        JapScanScraper._homepage_cache[slug] = {
                            "title": title,
                            "max_chapter": chap_num or 0,
                            "cover_url": cover_url,
                        }
                    else:
                        # Mettre à jour le max_chapter si plus grand
                        existing = JapScanScraper._homepage_cache[slug]
                        if chap_num and chap_num > existing["max_chapter"]:
                            existing["max_chapter"] = chap_num
                        # Préférer un titre plus long et descriptif
                        if title and title.lower() not in noise_words:
                            if (existing["title"] == slug_title
                                    or existing["title"].lower() in noise_words
                                    or len(title) > len(existing["title"])):
                                existing["title"] = title
                        if not existing["cover_url"] and cover_url:
                            existing["cover_url"] = cover_url

        except Exception as e:
            print(f"[{self.source_name}] Erreur chargement homepage: {e}")

    # ──────────────────────────────────────────────────────────────
    # Search
    # ──────────────────────────────────────────────────────────────
    def search(self, query: str) -> List[Manga]:
        self._ensure_homepage_loaded()

        raw_query = query.strip().lower()

        # Alias de recherche
        alias_map = {
            "my dress up darling": "sexy cosplay doll",
            "my dress-up darling": "sexy cosplay doll",
            "sono bisque doll": "sexy cosplay doll",
            "jujutsu": "jujutsu kaisen",
            "naruto shippuden": "naruto",
            "naruto shippūden": "naruto",
            "attack on titan": "shingeki no kyojin",
            "snk": "shingeki no kyojin",
            "aot": "shingeki no kyojin",
            "lattaque des titans": "shingeki no kyojin",
            "l attaque des titans": "shingeki no kyojin",
        }

        search_query = alias_map.get(raw_query, raw_query)
        q_words = [w for w in search_query.split() if len(w) > 2]

        results = []

        for slug, info in JapScanScraper._homepage_cache.items():
            title = info["title"]
            slug_clean = slug.replace("-", " ").lower()
            title_lower = title.lower()

            # Filtrage par mots-clés : TOUS les mots doivent matcher (word-boundary)
            if q_words:
                searchable = f"{title_lower} {slug_clean}"
                # Chaque mot de la requête doit apparaître comme mot entier
                all_match = all(
                    re.search(r'\b' + re.escape(w) + r'\b', searchable)
                    or w in slug_clean.split("-")
                    for w in q_words
                )
                if not all_match:
                    continue

            manga_url = f"{self.base_url}/manga/{slug}/"
            results.append(Manga(
                title=title,
                url=manga_url,
                source=self.source_name,
                cover_url=info.get("cover_url"),
            ))

        # Tri par pertinence : exact match en premier
        def sort_key(m):
            t = m.title.lower()
            if t == search_query:
                return (0, t)
            if t.startswith(search_query):
                return (1, t)
            if search_query in t:
                return (2, t)
            return (3, t)

        results.sort(key=sort_key)

        # Fallback slug direct si aucun résultat
        if not results and query:
            slug = search_query.replace(" ", "-")
            manga_url = f"{self.base_url}/manga/{slug}/"
            results.append(Manga(
                title=search_query.title(),
                url=manga_url,
                source=self.source_name,
                cover_url=None,
            ))

        return results[:25]

    # ──────────────────────────────────────────────────────────────
    # Manga details
    # ──────────────────────────────────────────────────────────────
    def get_manga_details(self, manga_url: str) -> Manga:
        slug = manga_url.rstrip("/").split("/")[-1]
        self._ensure_homepage_loaded()

        info = JapScanScraper._homepage_cache.get(slug, {})
        title = info.get("title", slug.replace("-", " ").title())
        cover_url = info.get("cover_url")

        return Manga(
            title=title,
            url=manga_url,
            source=self.source_name,
            cover_url=cover_url,
        )

    # ──────────────────────────────────────────────────────────────
    # Chapters — Génère la liste complète à partir du max connu
    # ──────────────────────────────────────────────────────────────
    def get_chapters(self, manga_url: str) -> List[Chapter]:
        slug = manga_url.rstrip("/").split("/")[-1]
        self._ensure_homepage_loaded()

        info = JapScanScraper._homepage_cache.get(slug, {})
        max_chap = info.get("max_chapter", 0)
        manga_title = info.get("title", slug.replace("-", " ").title())
        KNOWN_MAX_CHAPTERS = {
            "naruto": 700,
            "bleach": 686,
            "demon-slayer": 205,
            "kimetsu-no-yaiba": 205,
            "attack-on-titan": 139,
            "shingeki-no-kyojin": 139,
            "death-note": 108,
            "dragon-ball": 519,
            "fullmetal-alchemist": 108,
            "haikyu": 402,
            "tokyo-ghoul": 143,
            "tokyo-ghoul-re": 179,
            "gintama": 704,
            "fairy-tail": 545,
            "assassination-classroom": 180,
            "slam-dunk": 276,
            "jujutsu-kaisen": 271,
            "my-hero-academia": 430,
            "the-beginning-after-the-end": 245,
            "the-begining-after-the-end": 245,
            "tbate": 245,
            "solo-leveling": 200,
            "one-piece": 1190,
            "blue-lock": 280,
            "chainsaw-man": 180,
            "black-clover": 370,
            "kingdom": 815,
        }
        known_max = KNOWN_MAX_CHAPTERS.get(slug, 0)
        if known_max <= 0:
            s_clean = slug.lower().replace("-", " ")
            if "tbate" in s_clean or ("begin" in s_clean and "after" in s_clean):
                known_max = 245

        if known_max > max_chap:
            max_chap = known_max

        if max_chap <= 0:
            # Dernier recours : tenter de scraper la page manga directement
            max_chap = self._try_scrape_max_chapter(manga_url, slug)

        if max_chap <= 0:
            return []

        chapters = []
        for num in range(1, max_chap + 1):
            chap_str = str(num)
            chap_url = f"{self.base_url}/manga/{slug}/{chap_str}/"
            chapters.append(Chapter(
                title=f"Chapitre {chap_str}",
                number=chap_str,
                url=chap_url,
                manga_title=manga_title,
                source=self.source_name,
            ))

        return chapters

    def _try_scrape_max_chapter(self, manga_url: str, slug: str) -> int:
        """Tente de scraper la page manga pour trouver le dernier chapitre.
        Peut échouer si Cloudflare bloque."""
        try:
            with self._get_client() as client:
                resp = client.get(manga_url)
                if resp.status_code == 200 and "déménagé" not in resp.text:
                    soup = BeautifulSoup(resp.text, "lxml")
                    links = soup.select(f"a[href*='/manga/{slug}/']")
                    max_num = 0
                    for link in links:
                        href = link.get("href", "")
                        parts = href.strip("/").split("/")
                        if len(parts) >= 3 and parts[2].isdigit():
                            max_num = max(max_num, int(parts[2]))
                    return max_num
        except Exception:
            pass
        return 0

    # ──────────────────────────────────────────────────────────────
    # Chapter pages
    # ──────────────────────────────────────────────────────────────
    def get_chapter_pages(self, chapter_url: str) -> List[Page]:
        pages = []
        try:
            with self._get_client() as client:
                resp = client.get(chapter_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "lxml")

                    # 1. Images directes dans le reader
                    imgs = soup.select("#reader img, .img-fluid, #image img, img.data-img, img[data-src]")
                    for idx, img in enumerate(imgs, 1):
                        src = img.get("data-src") or img.get("src")
                        if src and not src.endswith("loading.gif"):
                            # Résoudre les URLs relatives
                            abs_url = urllib.parse.urljoin(chapter_url, src.strip())
                            pages.append(Page(number=idx, url=abs_url, referer=chapter_url))

                    # 2. Fallback : chercher dans les scripts JS
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
            print(f"[{self.source_name}] Erreur pages: {e}")

        return pages
