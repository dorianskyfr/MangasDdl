from __future__ import annotations
"""
Module de métadonnées & publication officielle universelle (AniList + MangaDex + Kitsu)
Comportement strict & gestion intelligente des mangas, manhwas et webtoons terminés ou en cours.
"""
import re
import urllib.parse
import httpx
from typing import Dict, List, Optional, Tuple

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
STOPWORDS = {"the", "a", "an", "no", "ni", "ga", "de", "to", "wa", "mo", "in", "of", "and", "du", "au", "la", "le", "les", "des", "tei", "san"}


def score_match(query_str: str, target_str: str) -> float:
    if not query_str or not target_str:
        return 0.0
    q = query_str.lower().strip()
    t = target_str.lower().strip()
    if q == t:
        return 10.0
    
    q_words = set(re.findall(r'\w+', q)) - STOPWORDS
    t_words = set(re.findall(r'\w+', t)) - STOPWORDS
    
    if not q_words or not t_words:
        return 0.0
    if q_words == t_words:
        return 9.5
    if q_words.issubset(t_words):
        return 7.0 + (len(q_words) / len(t_words))
    if t_words.issubset(q_words):
        return 6.0 + (len(t_words) / len(q_words))
    
    inter = len(q_words & t_words)
    if inter > 0:
        return (inter / len(q_words | t_words)) * 5.0
    return 0.0


class MultiSourceVolumeProvider:
    _cache: Dict[str, Tuple[str, Dict[int, List[str]]]] = {}
    _meta_cache: Dict[str, dict] = {}

    @classmethod
    def get_official_volumes_for_chapters(
        cls, manga_title: str, available_chapters: List[str], alt_titles: Optional[List[str]] = None
    ) -> Tuple[str, Dict[int, List[str]]]:
        """
        Interroge AniList, MangaDex et Kitsu avec le titre et les titres alternatifs.
        Retourne (nom_source, vmap).
        """
        if not available_chapters:
            return ("Indisponible", {})

        cache_key = manga_title.lower().strip()
        if cache_key in cls._cache and cls._cache[cache_key][1]:
            return cls._cache[cache_key]

        clean_title = manga_title.strip()
        candidates = [clean_title]
        if alt_titles:
            candidates.extend([a.strip() for a in alt_titles if a.strip()])

        # Nettoyage des sous-titres / parenthèses
        for t in list(candidates):
            c_no_paren = re.sub(r'[\(\[\{].*?[\)\]\}]', '', t).strip()
            if c_no_paren and c_no_paren not in candidates:
                candidates.append(c_no_paren)
            c_no_punct = re.sub(r'[^\w\s]', ' ', t).strip()
            if c_no_punct and c_no_punct not in candidates:
                candidates.append(c_no_punct)

        # ── 1. TIER 1 : AniList GraphQL avec recherche scorée ────────────────
        al_info = cls._get_anilist_info(candidates)
        if al_info:
            v_count = al_info.get("volumes")
            c_count = al_info.get("chapters")
            status = al_info.get("status")  # FINISHED, RELEASING, NOT_YET_RELEASED, CANCELLED, HIATUS

            is_estimated = False
            if not v_count:
                v_count = max(1, round(len(available_chapters) / 9.0))
                is_estimated = True
            if not c_count:
                c_count = len(available_chapters)

            v_map = cls._build_ratio_map(available_chapters, v_count, c_count, manga_title=clean_title, is_finished=(status == "FINISHED"))
            if v_map:
                source_label = f"Estimation AniList ({len(v_map)} tomes)" if is_estimated else f"AniList Officiel ({len(v_map)} tomes)"
                res = (source_label, v_map)
                cls._cache[cache_key] = res
                cls._meta_cache[cache_key] = {
                    "status": status,
                    "total_volumes": len(v_map),
                    "total_chapters": al_info.get("chapters") or len(available_chapters),
                    "genres": al_info.get("genres", []),
                    "synopsis": al_info.get("synopsis", ""),
                    "cover_url": al_info.get("cover_url"),
                    "matched_title": al_info.get("title", clean_title)
                }
                return res

        # ── 2. TIER 2 : MangaDex API ──────────────────────────────────────────
        md_info = cls._get_mangadex_info(candidates)
        if md_info:
            v_count = md_info.get("volumes")
            c_count = md_info.get("chapters")
            status = md_info.get("status")

            is_estimated = False
            if not v_count:
                v_count = max(1, round(len(available_chapters) / 9.0))
                is_estimated = True
            if not c_count:
                c_count = len(available_chapters)

            v_map = cls._build_ratio_map(available_chapters, v_count, c_count, manga_title=clean_title, is_finished=(status == "FINISHED"))
            if v_map:
                source_label = f"Estimation MangaDex ({len(v_map)} tomes)" if is_estimated else f"MangaDex Officiel ({len(v_map)} tomes)"
                res = (source_label, v_map)
                cls._cache[cache_key] = res
                cls._meta_cache[cache_key] = {
                    "status": status,
                    "total_volumes": len(v_map),
                    "total_chapters": md_info.get("chapters") or len(available_chapters),
                    "genres": md_info.get("genres", []),
                    "synopsis": md_info.get("synopsis", ""),
                    "cover_url": md_info.get("cover_url"),
                    "matched_title": md_info.get("title", clean_title)
                }
                return res

        # ── 3. TIER 3 : Kitsu API ────────────────────────────────────────────
        kt_info = cls._get_kitsu_info(candidates)
        if kt_info:
            v_count = kt_info.get("volumes")
            c_count = kt_info.get("chapters")
            raw_st = kt_info.get("status", "")
            status = "FINISHED" if raw_st == "finished" else ("RELEASING" if raw_st == "current" else "FINISHED")

            is_estimated = False
            if not v_count:
                v_count = max(1, round(len(available_chapters) / 9.0))
                is_estimated = True
            if not c_count:
                c_count = len(available_chapters)

            v_map = cls._build_ratio_map(available_chapters, v_count, c_count, manga_title=clean_title, is_finished=(status == "FINISHED"))
            if v_map:
                source_label = f"Estimation Kitsu ({len(v_map)} tomes)" if is_estimated else f"Kitsu Officiel ({len(v_map)} tomes)"
                res = (source_label, v_map)
                cls._cache[cache_key] = res
                cls._meta_cache[cache_key] = {
                    "status": status,
                    "total_volumes": len(v_map),
                    "total_chapters": kt_info.get("chapters") or len(available_chapters),
                    "genres": kt_info.get("genres", []),
                    "synopsis": kt_info.get("synopsis", ""),
                    "cover_url": None,
                    "matched_title": kt_info.get("title", clean_title)
                }
                return res

        # Fallback ratio standard (~9 chap/tome)
        v_count = max(1, round(len(available_chapters) / 9.0))
        v_map = cls._build_ratio_map(available_chapters, v_count, len(available_chapters), manga_title=clean_title)
        if v_map:
            res = (f"Tomes Officiels (~{len(v_map)} tomes)", v_map)
            cls._cache[cache_key] = res
            return res

        return ("Indisponible", {})

    @classmethod
    def get_manga_meta(cls, manga_title: str) -> dict:
        """Retourne les métadonnées enrichies du manga avec normalisation robuste."""
        if not manga_title:
            return {}
        cache_key = manga_title.lower().strip()
        if cache_key in cls._meta_cache:
            return cls._meta_cache[cache_key]

        # Normalisation sans tirets ni ponctuation
        clean_key = re.sub(r'[^a-z0-9]', '', cache_key)
        for k, v in cls._meta_cache.items():
            if re.sub(r'[^a-z0-9]', '', k) == clean_key:
                return v

        # Correspondance par mots clés
        k_words = set(re.findall(r'\w+', cache_key)) - STOPWORDS
        if k_words:
            for k, v in cls._meta_cache.items():
                stored_words = set(re.findall(r'\w+', k)) - STOPWORDS
                if stored_words and (k_words == stored_words or k_words.issubset(stored_words) or stored_words.issubset(k_words)):
                    return v

        return {}

    @classmethod
    def _build_ratio_map(
        cls, available_chapters: List[str], total_volumes: int, total_chapters: int,
        manga_title: str = "", is_finished: bool = False
    ) -> Dict[int, List[str]]:
        if not available_chapters or total_volumes <= 0:
            return {}

        # Règle spéciale Naruto : 72 tomes officiels pour les 700 chapitres + Tome 73 (Gaiden & Bonus 701-712)
        if "naruto" in manga_title.lower() and len(available_chapters) >= 700:
            vmap = {}
            main_chaps = available_chapters[:700]
            bonus_chaps = available_chapters[700:]
            c_per_v = 700 / 72.0

            for v in range(1, 73):
                start = int(round((v - 1) * c_per_v))
                end = int(round(v * c_per_v))
                vmap[v] = main_chaps[start:end]

            if bonus_chaps:
                vmap[73] = bonus_chaps
            return vmap

        chap_per_vol = max(1, round(total_chapters / total_volumes)) if (total_chapters > 0 and total_volumes > 0) else 9
        vmap: Dict[int, List[str]] = {}

        for i in range(0, len(available_chapters), chap_per_vol):
            vol_num = (i // chap_per_vol) + 1
            chunk = available_chapters[i : i + chap_per_vol]
            vmap[vol_num] = chunk

        # Si le dernier tome n'a que 1 ou 2 chapitres isolés, les fusionner avec le tome précédent
        if len(vmap) > 1:
            last_vol_num = max(vmap.keys())
            if len(vmap[last_vol_num]) <= 2:
                prev_vol_num = last_vol_num - 1
                vmap[prev_vol_num].extend(vmap[last_vol_num])
                del vmap[last_vol_num]

        return vmap

    @classmethod
    def _get_anilist_info(cls, candidates: List[str]) -> Optional[dict]:
        query = """
        query ($search: String) {
          Page(page: 1, perPage: 8) {
            media(search: $search, type: MANGA) {
              id
              title { romaji english native }
              synonyms
              description
              genres
              volumes
              chapters
              status
              coverImage { extraLarge large }
            }
          }
        }
        """
        best_match = None
        best_score = 0.0

        for cand in candidates:
            if len(cand) < 2:
                continue
            try:
                with httpx.Client(timeout=4.0) as c:
                    r = c.post("https://graphql.anilist.co", json={"query": query, "variables": {"search": cand}})
                if r.status_code == 200:
                    media_list = r.json().get("data", {}).get("Page", {}).get("media", [])
                    for m in media_list:
                        t_info = m.get("title", {})
                        all_t = [t_info.get("romaji"), t_info.get("english"), t_info.get("native")]
                        all_t.extend(m.get("synonyms", []))
                        all_t = [t for t in all_t if t]

                        for t in all_t:
                            s = score_match(cand, t)
                            if s > best_score:
                                best_score = s
                                best_match = m
            except Exception:
                pass

        if best_match and best_score >= 1.5:
            m = best_match
            name = m['title'].get('english') or m['title'].get('romaji') or candidates[0]
            synopsis_clean = re.sub(r'<[^>]+>', '', m.get("description") or "").strip()
            return {
                "title": name,
                "volumes": m.get("volumes"),
                "chapters": m.get("chapters"),
                "status": m.get("status"),  # FINISHED, RELEASING, NOT_YET_RELEASED, CANCELLED, HIATUS
                "genres": m.get("genres", []),
                "synopsis": synopsis_clean,
                "cover_url": m.get("coverImage", {}).get("extraLarge") or m.get("coverImage", {}).get("large"),
            }
        return None

    @classmethod
    def _get_mangadex_info(cls, candidates: List[str]) -> Optional[dict]:
        for cand in candidates:
            if len(cand) < 2:
                continue
            try:
                with httpx.Client(timeout=4.0) as c:
                    r = c.get("https://api.mangadex.org/manga", params={"title": cand, "limit": 5})
                if r.status_code == 200:
                    items = r.json().get("data", [])
                    for item in items:
                        attrs = item.get("attributes", {})
                        md_titles = list(attrs.get("title", {}).values())
                        for alt in attrs.get("altTitles", []):
                            md_titles.extend(alt.values())

                        md_status = attrs.get("status")
                        status_trans = {
                            "completed": "FINISHED",
                            "ongoing": "RELEASING",
                            "cancelled": "CANCELLED",
                            "hiatus": "HIATUS"
                        }.get(md_status, "FINISHED")

                        v_str = attrs.get("lastVolume")
                        c_str = attrs.get("lastChapter")
                        v_count = int(v_str) if (v_str and v_str.isdigit()) else None
                        c_count = int(float(c_str)) if (c_str and re.match(r'^\d+(\.\d+)?$', c_str)) else None

                        desc = attrs.get("description", {})
                        synopsis = desc.get("fr") or desc.get("en") or ""
                        genres = [
                            t.get("attributes", {}).get("name", {}).get("en")
                            for t in attrs.get("tags", [])
                            if t.get("attributes", {}).get("name", {}).get("en")
                        ]

                        return {
                            "title": md_titles[0] if md_titles else cand,
                            "volumes": v_count,
                            "chapters": c_count,
                            "status": status_trans,
                            "genres": genres,
                            "synopsis": synopsis,
                            "cover_url": None,
                        }
            except Exception:
                pass
        return None

    @classmethod
    def _get_kitsu_info(cls, candidates: List[str]) -> Optional[dict]:
        for cand in candidates:
            if len(cand) < 2:
                continue
            encoded_title = urllib.parse.quote(cand)
            url = f"https://kitsu.io/api/edge/manga?filter[text]={encoded_title}&page[limit]=3"
            try:
                with httpx.Client(headers={"User-Agent": UA}, timeout=4.0) as c:
                    r = c.get(url)
                if r.status_code == 200:
                    items = r.json().get("data", [])
                    if items:
                        attrs = items[0]["attributes"]
                        v = attrs.get("volumeCount")
                        c_count = attrs.get("chapterCount")
                        status_raw = attrs.get("status", "")
                        synopsis = attrs.get("synopsis", "")
                        return {
                            "title": attrs.get("canonicalTitle", cand),
                            "volumes": v,
                            "chapters": c_count,
                            "status": status_raw,
                            "genres": [],
                            "synopsis": synopsis,
                        }
            except Exception:
                pass
        return None


# Alias de compatibilité
MangaDexVolumeProvider = MultiSourceVolumeProvider
