"""
Fournisseur de couvertures de tomes officielles via MangaDex API (Spécifique au tome)
avec fallback sur AniList API (Couverture principale).
"""
import re
import urllib.parse
import httpx
from typing import Dict, Optional, List


class VolumeCoverProvider:
    _manga_id_cache: Dict[str, str] = {}
    _cover_cache: Dict[str, str] = {}

    @classmethod
    def get_volume_cover_url(cls, manga_title: str, volume_number: int, alt_title: Optional[str] = None) -> Optional[str]:
        """
        Récupère la couverture officielle spécifique du tome via MangaDex.
        Si introuvable, bascule automatiquement sur la couverture principale haute résolution AniList.
        """
        cache_key = f"{manga_title.lower().strip()}_vol_{volume_number}"
        if cache_key in cls._cover_cache:
            return cls._cover_cache[cache_key]

        from downloader.mangadex_volume import MultiSourceVolumeProvider
        meta = MultiSourceVolumeProvider.get_manga_meta(manga_title)
        matched_name = meta.get("matched_title") or alt_title

        candidates = [manga_title.strip()]
        if matched_name and matched_name != manga_title:
            candidates.append(matched_name.strip())

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        specific_cover_url = None

        try:
            with httpx.Client(headers=headers, timeout=5.0, follow_redirects=True) as client:
                manga_id = None
                for cand in candidates:
                    cand_key = cand.lower()
                    if cand_key in cls._manga_id_cache:
                        manga_id = cls._manga_id_cache[cand_key]
                        break
                    
                    search_url = f"https://api.mangadex.org/manga?title={urllib.parse.quote(cand)}&limit=5"
                    r = client.get(search_url)
                    if r.status_code == 200:
                        data = r.json().get("data", [])
                        if data:
                            manga_id = data[0]["id"]
                            cls._manga_id_cache[cand_key] = manga_id
                            break

                # 2. Chercher la cover spécifique pour ce volume
                if manga_id:
                    cover_url = f"https://api.mangadex.org/cover?manga[]={manga_id}&limit=100"
                    r_cov = client.get(cover_url)
                    if r_cov.status_code == 200:
                        covers = r_cov.json().get("data", [])
                        vol_str = str(volume_number)
                        for c in covers:
                            vol = c.get("attributes", {}).get("volume")
                            if vol == vol_str or vol == f"{volume_number}.0":
                                fn = c.get("attributes", {}).get("fileName")
                                if fn:
                                    specific_cover_url = f"https://uploads.mangadex.org/covers/{manga_id}/{fn}"
                                    break
        except Exception as e:
            print(f"[VolumeCoverProvider] Erreur MangaDex pour Tome {volume_number}: {e}")

        # 3. Si cover spécifique trouvée
        if specific_cover_url:
            cls._cover_cache[cache_key] = specific_cover_url
            return specific_cover_url

        # 4. Fallback sur AniList cover_url ou get_main_cover_url
        if meta.get("cover_url"):
            cls._cover_cache[cache_key] = meta["cover_url"]
            return meta["cover_url"]

        for cand in candidates:
            fallback_url = cls.get_main_cover_url(cand)
            if fallback_url:
                cls._cover_cache[cache_key] = fallback_url
                return fallback_url

        return None

    @classmethod
    def get_main_cover_url(cls, manga_title: str) -> Optional[str]:
        """Récupère l'image de couverture principale d'un manga via l'API AniList GraphQL."""
        clean_title = manga_title.strip()
        cache_key = f"main_cover_{clean_title.lower()}"

        if cache_key in cls._cover_cache:
            return cls._cover_cache[cache_key]

        query = """
        query ($search: String) {
            Media (search: $search, type: MANGA) {
                coverImage {
                    extraLarge
                    large
                }
            }
        }
        """

        try:
            with httpx.Client(timeout=6.0) as client:
                r = client.post(
                    "https://graphql.anilist.co",
                    json={"query": query, "variables": {"search": clean_title}}
                )
                if r.status_code == 200:
                    data = r.json()
                    media = data.get("data", {}).get("Media")
                    if media and media.get("coverImage"):
                        cover_url = media["coverImage"].get("extraLarge") or media["coverImage"].get("large")
                        if cover_url:
                            cls._cover_cache[cache_key] = cover_url
                            return cover_url
        except Exception:
            pass

        return None
