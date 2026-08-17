import re
import difflib
import httpx
from urllib.parse import quote
from bs4 import BeautifulSoup
from typing import List, Optional, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from models import Manga, Chapter, Page
from scrapers.base import BaseScraper
from config import config_manager

CDN_THUMB = "https://cdn.jsdelivr.net/gh/Anime-Sama/IMG@img/contenu/thumb"


class AnimeSamaScraper(BaseScraper):
    _sitemap_cache: List[dict] = []
    # Cache slug -> {"nom": str, "data": {chap: nb_pages}}
    _manga_data_cache: Dict[str, dict] = {}

    def __init__(self):
        self._domain = config_manager.get("anime_sama_domain", "https://anime-sama.to")
        self.headers = {
            "User-Agent": config_manager.get("user_agent"),
            "Referer": self._domain,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        }

    @property
    def source_name(self) -> str:
        return "Anime-Sama"

    @property
    def base_url(self) -> str:
        return self._domain

    def _get_client(self, referer: str = None) -> httpx.Client:
        h = {**self.headers}
        if referer:
            h["Referer"] = referer
        return httpx.Client(headers=h, follow_redirects=True, timeout=12.0)

    # ──────────────────────────────────────────────────────────────
    # Sitemap
    # ──────────────────────────────────────────────────────────────
    def _ensure_sitemap_loaded(self):
        if AnimeSamaScraper._sitemap_cache:
            return
        try:
            with self._get_client() as c:
                r = c.get(f"{self.base_url}/sitemap.xml")
            if r.status_code != 200:
                return
            urls = re.findall(r'<loc>(https?://[^<]+/catalogue/[^/]+/?)</loc>', r.text)
            for u in urls:
                slug = u.rstrip("/").split("/")[-1]
                if slug and slug != "catalogue":
                    title = slug.replace("-", " ").title()
                    AnimeSamaScraper._sitemap_cache.append(
                        {"title": title, "slug": slug, "url": u.rstrip("/") + "/"}
                    )
        except Exception as e:
            print(f"[AnimeSama] Sitemap error: {e}")

    # ──────────────────────────────────────────────────────────────
    # API officielle : get_nb_chap_et_img.php
    # ──────────────────────────────────────────────────────────────
    def _call_api(self, nom: str, slug: str) -> Optional[Dict]:
        api_url = f"{self.base_url}/s2/scans/get_nb_chap_et_img.php?oeuvre={quote(nom)}"
        headers = {
            "User-Agent": config_manager.get("user_agent"),
            "Referer": f"{self.base_url}/catalogue/{slug}/scan/vf/",
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        }
        try:
            with httpx.Client(headers=headers, follow_redirects=True, timeout=10.0) as c:
                r = c.get(api_url)
            if r.status_code == 200:
                data = r.json()
                if "error" not in data and data:
                    return {str(k): int(v) for k, v in data.items()}
        except Exception as e:
            print(f"[AnimeSama] API error for '{nom}': {e}")
        return None

    def _get_manga_data(self, slug: str) -> Tuple[str, Dict]:
        cache_key = slug
        if cache_key in AnimeSamaScraper._manga_data_cache:
            cached = AnimeSamaScraper._manga_data_cache[cache_key]
            return cached["nom"], cached["data"]

        clean_slug = slug.split("#")[0]
        scan_url = f"{self.base_url}/catalogue/{clean_slug}/scan/vf/"

        raw_nom = ""
        try:
            with self._get_client(referer=self.base_url) as c:
                r = c.get(scan_url)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "lxml")
                el = soup.select_one("#titreOeuvre")
                if el:
                    # NE PAS strip : l'API anime-sama exige le nom exact
                    # y compris les espaces trailing (ex: "Naruto  ", "Blue Lock  ")
                    raw_nom = el.decode_contents()
        except Exception as e:
            print(f"[AnimeSama] Page scan error for {clean_slug}: {e}")

        candidates = []
        if "one-piece" in clean_slug.lower():
            if "#couleur" in slug.lower():
                candidates.insert(0, "One Piece Couleur")
            else:
                candidates.insert(0, "One Piece")

        if raw_nom:
            # Version brute en premier (avec espaces trailing potentiels)
            candidates.append(raw_nom)
            stripped_nom = raw_nom.strip()
            if stripped_nom != raw_nom:
                candidates.append(stripped_nom)
            candidates.append(raw_nom.replace("&amp;", "&"))
            candidates.append(BeautifulSoup(raw_nom, "lxml").get_text())

        title_from_sitemap = clean_slug.replace("-", " ").title()
        candidates.append(title_from_sitemap)

        # Dédupliquer en préservant l'ordre et les espaces exactes
        uniq_candidates = []
        seen_candidates = set()
        for cand in candidates:
            if cand and cand not in seen_candidates:
                seen_candidates.add(cand)
                uniq_candidates.append(cand)

        data = None
        found_nom = uniq_candidates[0] if uniq_candidates else title_from_sitemap

        for cand in uniq_candidates:
            res = self._call_api(cand, clean_slug)
            if res:
                data = res
                found_nom = cand
                break

        if not data:
            data = {}
            print(f"[AnimeSama] Aucune donnée API pour slug={clean_slug}")

        AnimeSamaScraper._manga_data_cache[clean_slug] = {"nom": found_nom, "data": data}
        return found_nom, data


    def search(self, query: str) -> List[Manga]:
        self._ensure_sitemap_loaded()

        raw_q = query.lower().strip()
        
        # Détection spéciale pour séparer One Piece (Normal vs Couleur)
        if raw_q == "one piece" or raw_q == "one-piece" or raw_q == "op":
            base_url = f"{self.base_url}/catalogue/one-piece/"
            thumb = f"{CDN_THUMB}/one-piece.webp"
            return [
                Manga(
                    title="One Piece (Édition Classique — 1190 chapitres)",
                    url=f"{base_url}#normal",
                    source=self.source_name,
                    cover_url=thumb
                ),
                Manga(
                    title="One Piece (Scans Couleur — 1004 chapitres)",
                    url=f"{base_url}#couleur",
                    source=self.source_name,
                    cover_url=thumb
                ),
            ]

        # Détection spéciale pour séparer Classroom of the Elite en 3 entrées distinctes
        if any(k in raw_q for k in ["classroom of the elite", "horikita", "cote", "youkoso", "2nd year"]):
            base_url = f"{self.base_url}/catalogue/classroom-of-the-elite/"
            thumb = f"{CDN_THUMB}/classroom-of-the-elite.webp"
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

        alias_map = {
            "my dress up darling": "sexy cosplay doll",
            "my dress-up darling": "sexy cosplay doll",
            "sono bisque doll": "sexy cosplay doll",
            "naruto shippuden": "naruto",
            "naruto shippūden": "naruto",
            "attack on titan": "shingeki no kyojin",
            "snk": "shingeki no kyojin",
            "aot": "shingeki no kyojin",
            "lattaque des titans": "shingeki no kyojin",
            "l attaque des titans": "shingeki no kyojin",
            "jujutsu": "jujutsu kaisen",
            "op": "one piece",
        }

        q_raw = alias_map.get(raw_q, raw_q)
        q_clean = re.sub(r"[^a-z0-9 ]", "", q_raw)
        q_words = [w for w in q_clean.split() if len(w) > 1]

        scored: List[Tuple[float, dict]] = []
        seen: set = set()

        for item in AnimeSamaScraper._sitemap_cache:
            url = item["url"]
            if url in seen:
                continue

            slug = item["slug"]
            title = item["title"]
            slug_clean = slug.replace("-", " ")
            title_norm = re.sub(r"[^a-z0-9 ]", "", title.lower())
            title_words_list = title_norm.split()

            score = 0.0

            if q_raw == title.lower() or q_raw == slug_clean or q_clean == title_norm:
                score = 2.0
            elif title_norm.startswith(q_clean) or title.lower().startswith(q_raw):
                score = 1.8
            elif q_raw in title.lower() or q_raw in slug_clean or q_clean in title_norm:
                score = 1.5 if title_norm.startswith(q_clean) else 1.1
            else:
                r_title = difflib.SequenceMatcher(None, q_clean, title_norm).ratio()
                r_slug  = difflib.SequenceMatcher(None, q_clean, slug_clean).ratio()
                best = max(r_title, r_slug)

                if q_words:
                    per_word = []
                    best_pos = []
                    for qw in q_words:
                        br, bp = 0.0, len(title_words_list)
                        for pos, tw in enumerate(title_words_list):
                            rv = difflib.SequenceMatcher(None, qw, tw).ratio()
                            if rv > br:
                                br, bp = rv, pos
                        per_word.append(br)
                        best_pos.append(bp)

                    word_score = sum(per_word) / len(per_word)
                    all_good = all(s >= 0.82 for s in per_word)
                    word_final = word_score * (1.0 if all_good else 0.78)

                    avg_pos = sum(best_pos) / len(best_pos)
                    if avg_pos > 1 and len(q_words) <= 1:
                        word_final *= 0.80

                    if (title_words_list and q_words and
                            difflib.SequenceMatcher(None, q_words[0], title_words_list[0]).ratio() > 0.85):
                        word_final += 0.10

                    score = max(best, word_final)
                else:
                    score = best

            if score >= 0.65:
                seen.add(url)
                scored.append((score, item))

        scored.sort(key=lambda x: (-x[0], x[1]["title"]))

        return [
            Manga(
                title=item["title"],
                url=item["url"],
                source=self.source_name,
                cover_url=f"{CDN_THUMB}/{item['slug']}.webp",
            )
            for _, item in scored[:25]
        ]

    def get_manga_details(self, manga_url: str) -> Manga:
        raw_slug = manga_url.rstrip("/").split("/")[-1]
        clean_slug = raw_slug.split("#")[0]
        
        display_title = clean_slug.replace("-", " ").title()
        if "#year2" in manga_url:
            display_title = "Classroom of the Elite (2ème Année / 2nd Year)"
        elif "#horikita" in manga_url:
            display_title = "Classroom of the Elite √Horikita (Spin-off)"
        elif "#year1" in manga_url:
            display_title = "Classroom of the Elite (1ère Année / Year 1)"

        manga = Manga(
            title=display_title,
            url=manga_url,
            source=self.source_name,
            cover_url=f"{CDN_THUMB}/{clean_slug}.webp"
        )
        return manga

    def get_chapters(self, manga_url: str) -> List[Chapter]:
        clean_url = manga_url.split("#")[0].rstrip("/")
        clean_slug = clean_url.split("/")[-1]
        nom_exact, data = self._get_manga_data(clean_slug)

        display_title = clean_slug.replace("-", " ").title()
        if "one-piece" in clean_slug.lower():
            if "#couleur" in manga_url:
                display_title = "One Piece (Scans Couleur)"
            else:
                display_title = "One Piece (Édition Classique)"
        elif "#year2" in manga_url:
            display_title = "Classroom of the Elite (2ème Année / 2nd Year)"
        elif "#horikita" in manga_url:
            display_title = "Classroom of the Elite √Horikita (Spin-off)"
        elif "#year1" in manga_url:
            display_title = "Classroom of the Elite (1ère Année / Year 1)"

        if not data:
            return []

        def parse_chap_num(k: str) -> float:
            try:
                return float(k)
            except ValueError:
                m = re.search(r'(\d+(?:\.\d+)?)', k)
                return float(m.group(1)) if m else 0.0

        sorted_chaps = sorted(data.keys(), key=parse_chap_num)

        # Anchor (ex: #normal, #couleur, #year1, #year2, #horikita)
        anchor = "#" + manga_url.split("#")[1] if "#" in manga_url else ""

        # Plafond / filtrage par sous-section si demandé
        if "#horikita" in manga_url:
            # Spin-off Horikita (Chapitres 1 à 12)
            sorted_chaps = [c for c in sorted_chaps if parse_chap_num(c) <= 12]
        elif "#year2" in manga_url:
            # 2nd Year (Chapitres 58 et plus)
            sorted_chaps = [c for c in sorted_chaps if parse_chap_num(c) >= 58]
        elif "#year1" in manga_url:
            # Year 1 (Chapitres 1 à 57)
            sorted_chaps = [c for c in sorted_chaps if parse_chap_num(c) <= 57]

        chapters = []
        for chap_num_str in sorted_chaps:
            chap_url = f"{self.base_url}/catalogue/{clean_slug}/scan/vf/?chap={chap_num_str}{anchor}"
            chapters.append(
                Chapter(
                    title=f"Chapitre {chap_num_str}",
                    number=chap_num_str,
                    url=chap_url,
                    manga_title=display_title,
                    source=self.source_name,
                )
            )
        return chapters

    def get_chapter_pages(self, chapter_url: str) -> List[Page]:
        parsed = httpx.URL(chapter_url)
        clean_slug = parsed.path.strip("/").split("/")[1]
        anchor = "#" + chapter_url.split("#")[1] if "#" in chapter_url else ""
        raw_slug_with_anchor = clean_slug + anchor
        chap_num_str = parsed.params.get("chap", "1")

        nom_exact, data = self._get_manga_data(raw_slug_with_anchor)

        nb_pages = data.get(chap_num_str, 0)
        if nb_pages == 0:
            for k, v in data.items():
                try:
                    if float(k) == float(chap_num_str):
                        nb_pages = v
                        break
                except ValueError:
                    pass

        if nb_pages == 0:
            print(f"[AnimeSama] 0 pages trouvées pour chap={chap_num_str} dans {clean_slug}")
            return []

        base_img_url = f"{self.base_url}/s2/scans/{quote(nom_exact)}/{chap_num_str}"

        pages = []
        for page_num in range(1, nb_pages + 1):
            img_url = f"{base_img_url}/{page_num}.jpg"
            pages.append(
                Page(
                    number=page_num,
                    url=img_url,
                    referer=f"{self.base_url}/catalogue/{clean_slug}/scan/vf/"
                )
            )
        return pages
