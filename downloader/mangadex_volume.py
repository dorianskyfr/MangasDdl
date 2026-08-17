from __future__ import annotations
"""
Module de publication officielle (AniList + Kitsu)
Comportement strict & gestion intelligente des séries en cours (One Piece, Jujutsu, etc.).
"""
import re
import urllib.parse
import httpx
from typing import Dict, List, Optional, Tuple

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"


class MultiSourceVolumeProvider:
    _cache: Dict[str, Tuple[str, Dict[int, List[str]]]] = {}
    # Cache de métadonnées supplémentaires : manga_title -> {"status": str, "total_volumes": int|None}
    _meta_cache: Dict[str, dict] = {}

    @classmethod
    def get_official_volumes_for_chapters(cls, manga_title: str, available_chapters: List[str]) -> Tuple[str, Dict[int, List[str]]]:
        """
        Interroge AniList et Kitsu.
        Retourne (nom_source, vmap) si trouvé, ou ("Indisponible", {}) si rien n'est trouvé.
        """
        if not available_chapters:
            return ("Indisponible", {})

        cache_key = manga_title.lower().strip()
        if cache_key in cls._cache and cls._cache[cache_key][1]:
            return cls._cache[cache_key]

        clean_title = manga_title.strip()

        title_variants = [clean_title]
        if " " in clean_title:
            title_variants.append(clean_title.replace(" ", "-"))

        # ── TIER 1 : AniList GraphQL ────────────────────────────
        for variant in title_variants:
            al_info = cls._get_anilist_info(variant)
            if al_info:
                v_count = al_info.get("volumes")
                c_count = al_info.get("chapters")
                status = al_info.get("status")  # FINISHED, RELEASING, NOT_YET_RELEASED, CANCELLED, HIATUS
                
                is_estimated = False
                if not v_count:
                    v_count = max(1, round(len(available_chapters) / 10.0))
                    is_estimated = True
                if not c_count:
                    c_count = len(available_chapters)

                v_map = cls._build_ratio_map(available_chapters, v_count, c_count, manga_title=clean_title)
                if v_map:
                    source_label = f"Estimation AniList ({len(v_map)} tomes)" if is_estimated else f"AniList Officiel ({len(v_map)} tomes)"
                    res = (source_label, v_map)
                    cls._cache[cache_key] = res
                    cls._meta_cache[cache_key] = {
                        "status": status,
                        "total_volumes": len(v_map),
                        "total_chapters": al_info.get("chapters"),
                    }
                    return res

        # ── TIER 2 : Kitsu API ──────────────────────────────────
        for variant in title_variants:
            kitsu_info = cls._get_kitsu_info(variant)
            if kitsu_info:
                v_count = kitsu_info.get("volumes")
                c_count = kitsu_info.get("chapters")
                status = kitsu_info.get("status")  # current, finished, tba, unreleased, upcoming
                
                is_estimated = False
                if not v_count:
                    v_count = max(1, round(len(available_chapters) / 10.0))
                    is_estimated = True
                if not c_count:
                    c_count = len(available_chapters)

                v_map = cls._build_ratio_map(available_chapters, v_count, c_count, manga_title=clean_title)
                if v_map:
                    source_label = f"Estimation Kitsu ({len(v_map)} tomes)" if is_estimated else f"Kitsu Officiel ({len(v_map)} tomes)"
                    res = (source_label, v_map)
                    cls._cache[cache_key] = res
                    cls._meta_cache[cache_key] = {
                        "status": status,
                        "total_volumes": len(v_map),
                        "total_chapters": kitsu_info.get("chapters"),
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
        """Retourne les métadonnées du manga (status, total_volumes, total_chapters).
        Doit être appelé APRÈS get_official_volumes_for_chapters()."""
        cache_key = manga_title.lower().strip()
        return cls._meta_cache.get(cache_key, {})

    @classmethod
    def _build_ratio_map(cls, available_chapters: List[str], total_volumes: int, total_chapters: int, manga_title: str = "") -> Dict[int, List[str]]:
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

        chap_per_vol = max(1, round(total_chapters / total_volumes)) if (total_chapters > 0 and total_volumes > 0) else 10
        vmap: Dict[int, List[str]] = {}

        for i in range(0, len(available_chapters), chap_per_vol):
            vol_num = (i // chap_per_vol) + 1
            chunk = available_chapters[i : i + chap_per_vol]
            vmap[vol_num] = chunk

        # Si le dernier tome n'a que 1 ou 2 chapitres isolés, les fusionner avec le tome précédent pour éviter un mini-tome
        if len(vmap) > 1:
            last_vol_num = max(vmap.keys())
            if len(vmap[last_vol_num]) <= 2:
                prev_vol_num = last_vol_num - 1
                vmap[prev_vol_num].extend(vmap[last_vol_num])
                del vmap[last_vol_num]

        return vmap


    @classmethod
    def _get_anilist_info(cls, title: str) -> Optional[dict]:
        query = """
        query ($search: String) {
          Media (search: $search, type: MANGA) {
            title { romaji english native }
            volumes
            chapters
            status
          }
        }
        """
        try:
            with httpx.Client(timeout=4.0) as c:
                r = c.post("https://graphql.anilist.co", json={"query": query, "variables": {"search": title}})
            if r.status_code == 200:
                m = r.json().get("data", {}).get("Media")
                if m:
                    t_info = m.get("title", {})
                    all_titles = [t_info.get("romaji", ""), t_info.get("english", ""), t_info.get("native", "")]
                    search_words = set(title.lower().split())
                    matched = any(all(w in t.lower() for w in search_words) for t in all_titles if t)
                    if matched:
                        return {
                            "volumes": m.get("volumes"),
                            "chapters": m.get("chapters"),
                            "status": m.get("status"),  # FINISHED, RELEASING, NOT_YET_RELEASED, CANCELLED, HIATUS
                        }
        except Exception:
            pass
        return None

    @classmethod
    def _get_kitsu_info(cls, title: str) -> Optional[dict]:
        encoded_title = urllib.parse.quote(title)
        url = f"https://kitsu.io/api/edge/manga?filter[text]={encoded_title}&page[limit]=1"
        try:
            with httpx.Client(headers={"User-Agent": UA}, timeout=4.0) as c:
                r = c.get(url)
            if r.status_code == 200:
                items = r.json().get("data", [])
                if items:
                    attrs = items[0]["attributes"]
                    c_title = attrs.get("canonicalTitle", "").lower()
                    if any(w in c_title for w in title.lower().split()):
                        v = attrs.get("volumeCount")
                        c_count = attrs.get("chapterCount")
                        # Kitsu status: current, finished, tba, unreleased, upcoming
                        status_raw = attrs.get("status", "")
                        return {"volumes": v, "chapters": c_count, "status": status_raw}
        except Exception:
            pass
        return None


# Alias de compatibilité
MangaDexVolumeProvider = MultiSourceVolumeProvider
