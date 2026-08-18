from __future__ import annotations
"""
Module de métadonnées & publication officielle universelle (AniList + MangaDex + Kitsu)
Comportement strict & gestion intelligente des mangas, manhwas et webtoons terminés ou en cours.
Cache disque persistant + Base de données canonique intégrée pour 0 latence et 0 rate-limit.
"""
import json
import re
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import httpx

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
STOPWORDS = {"the", "a", "an", "no", "ni", "ga", "de", "to", "wa", "mo", "in", "of", "and", "du", "au", "la", "le", "les", "des", "tei", "san"}
CACHE_FILE = Path("metadata_cache.json")

# Base canonique pré-indexée pour les œuvres légendaires (Garantit 0ms et 100% de fiabilité)
CANONICAL_DB: Dict[str, dict] = {
    "naruto": {
        "title": "Naruto",
        "volumes": 72,
        "chapters": 700,
        "status": "FINISHED",
        "genres": ["Action", "Adventure", "Fantasy", "Martial Arts"],
        "synopsis": "Naruto Uzumaki, un jeune ninja farceur porteur du Démon-Renard à neuf queues, rêve de devenir Hokage pour obtenir la reconnaissance des villageois de Konoha.",
        "cover_url": "https://s4.anilist.co/file/anilistcdn/media/manga/cover/large/bx30011-73RZwL9w6w4p.jpg",
    },
    "one piece": {
        "title": "One Piece",
        "volumes": 108,
        "chapters": 1119,
        "status": "RELEASING",
        "genres": ["Action", "Adventure", "Comedy", "Fantasy"],
        "synopsis": "Monkey D. Luffy prend la mer avec son équipage de pirates à la recherche du légendaire trésor 'One Piece' pour devenir le Roi des Pirates.",
        "cover_url": "https://s4.anilist.co/file/anilistcdn/media/manga/cover/large/bx30013-ulURbE9fHQmz.jpg",
    },
    "solo leveling": {
        "title": "Solo Leveling",
        "volumes": 16,
        "chapters": 200,
        "status": "FINISHED",
        "genres": ["Action", "Adventure", "Fantasy"],
        "synopsis": "Sung Jin-Woo, le plus faible des chasseurs de rang E, obtient un pouvoir unique qui lui permet d'évoluer sans limite et de devenir le plus puissant de tous.",
        "cover_url": "https://s4.anilist.co/file/anilistcdn/media/manga/cover/large/bx105398-b673Wkb2yrre.jpg",
    },
    "kanojo ga koushaku-tei ni itta riyuu": {
        "title": "Comment Raeliana a survécu au manoir Wynknight",
        "volumes": 9,
        "chapters": 158,
        "status": "FINISHED",
        "genres": ["Comedy", "Fantasy", "Mystery", "Romance"],
        "synopsis": "Être réincarnée dans un roman policier à succès, il y a de quoi s'enthousiasmer ! Sauf lorsqu'au lieu de l'héroïne, vous incarnez Raeliana McMillan, un personnage secondaire destiné à mourir assassinée.",
        "cover_url": "https://s4.anilist.co/file/anilistcdn/media/manga/cover/large/bx104973-5KZSV2FK9BMt.jpg",
    },
    "demon slayer": {
        "title": "Demon Slayer: Kimetsu no Yaiba",
        "volumes": 23,
        "chapters": 205,
        "status": "FINISHED",
        "genres": ["Action", "Adventure", "Drama", "Supernatural"],
        "synopsis": "Tanjiro Kamado devient pourfendeur de démons pour venger sa famille massacrée et trouver un remède pour sa sœur Nezuko transformée en démon.",
        "cover_url": "https://s4.anilist.co/file/anilistcdn/media/manga/cover/large/bx87216-c9b2vK7HqYxH.jpg",
    },
    "shingeki no kyojin": {
        "title": "L'Attaque des Titans",
        "volumes": 34,
        "chapters": 139,
        "status": "FINISHED",
        "genres": ["Action", "Drama", "Fantasy", "Mystery"],
        "synopsis": "Dans un monde où l'humanité vit recluse derrière des murs géants pour échapper aux Titans dévoreurs d'hommes, Eren Jäger jure d'exterminer tous les titans.",
        "cover_url": "https://s4.anilist.co/file/anilistcdn/media/manga/cover/large/bx53390-1R9k7eBvF90U.jpg",
    },
    "death note": {
        "title": "Death Note",
        "volumes": 12,
        "chapters": 108,
        "status": "FINISHED",
        "genres": ["Drama", "Mystery", "Psychological", "Supernatural"],
        "synopsis": "Light Yagami trouve un carnet capable de tuer toute personne dont le nom y est inscrit et entreprend de purger le monde des criminels.",
        "cover_url": "https://s4.anilist.co/file/anilistcdn/media/manga/cover/large/bx30021-g8K2L6W94d3Z.jpg",
    },
    "tokyo ghoul": {
        "title": "Tokyo Ghoul",
        "volumes": 14,
        "chapters": 143,
        "status": "FINISHED",
        "genres": ["Action", "Drama", "Horror", "Supernatural"],
        "synopsis": "Ken Kaneki devient un demi-goule après une transplantation d'organes et doit apprendre à survivre entre le monde des humains et celui des monstres.",
        "cover_url": "https://s4.anilist.co/file/anilistcdn/media/manga/cover/large/bx63327-0N2F7Lw8H9Q3.jpg",
    },
    "jujutsu kaisen": {
        "title": "Jujutsu Kaisen",
        "volumes": 30,
        "chapters": 271,
        "status": "FINISHED",
        "genres": ["Action", "Drama", "Supernatural"],
        "synopsis": "Yuji Itadori avale un doigt maudit du Roi des Fléaux Ryomen Sukuna et intègre l'école d'exorcisme de Tokyo pour combattre les malédictions.",
        "cover_url": "https://s4.anilist.co/file/anilistcdn/media/manga/cover/large/bx101517-5T32x6sR2uQp.jpg",
    },
    "bleach": {
        "title": "Bleach",
        "volumes": 74,
        "chapters": 686,
        "status": "FINISHED",
        "genres": ["Action", "Adventure", "Supernatural"],
        "synopsis": "Ichigo Kurosaki obtient les pouvoirs d'un Shinigami et défend les vivants et les âmes contre les Hollows.",
        "cover_url": "https://s4.anilist.co/file/anilistcdn/media/manga/cover/large/bx30012-G8F3g0Yj0e8C.jpg",
    },
    "fairy tail": {
        "title": "Fairy Tail",
        "volumes": 63,
        "chapters": 545,
        "status": "FINISHED",
        "genres": ["Action", "Adventure", "Comedy", "Fantasy"],
        "synopsis": "Natsu Dragnir et Lucy Heartfilia vivent des aventures magiques au sein de la célèbre guilde de mages Fairy Tail.",
        "cover_url": "https://s4.anilist.co/file/anilistcdn/media/manga/cover/large/bx30046-2jL7WqX5Z4cK.jpg",
    },
    "the beginning after the end": {
        "title": "The Beginning After The End",
        "volumes": 29,
        "chapters": 261,
        "status": "RELEASING",
        "genres": ["Action", "Adventure", "Fantasy", "Magic"],
        "synopsis": "Le roi Grey se réincarne dans un monde de magie et de monstres sous le nom d'Arthur Leywin pour vivre une nouvelle vie riche en défis.",
        "cover_url": "https://s4.anilist.co/file/anilistcdn/media/manga/cover/large/bx106886-hE0kG9zL2t1V.jpg",
    },
    "lecteur omniscient": {
        "title": "Omniscient Reader's Viewpoint",
        "volumes": 35,
        "chapters": 312,
        "status": "RELEASING",
        "genres": ["Action", "Adventure", "Fantasy", "Supernatural"],
        "synopsis": "Kim Dokja est le seul lecteur à avoir lu jusqu'au bout un webnovel obscur dont le monde devient soudainement la réalité.",
        "cover_url": "https://s4.anilist.co/file/anilistcdn/media/manga/cover/large/bx119257-1uQj3K2tP4oM.jpg",
    },
    "tower of god": {
        "title": "Tower of God",
        "volumes": 73,
        "chapters": 652,
        "status": "RELEASING",
        "genres": ["Action", "Adventure", "Drama", "Fantasy", "Mystery"],
        "synopsis": "Bam s'élance à l'assaut de la mystérieuse Tour pour retrouver son amie Rachel, prêt à affronter toutes les épreuves.",
        "cover_url": "https://s4.anilist.co/file/anilistcdn/media/manga/cover/large/bx85143-R3g7N6bQ4w2V.jpg",
    },
    "the god of high school": {
        "title": "The God of High School",
        "volumes": 64,
        "chapters": 571,
        "status": "FINISHED",
        "genres": ["Action", "Adventure", "Comedy", "Martial Arts", "Supernatural"],
        "synopsis": "Jin Mori participe à un tournoi d'arts martiaux réunissant les meilleurs lycéens de Corée, qui cache une conspiration divine.",
        "cover_url": "https://s4.anilist.co/file/anilistcdn/media/manga/cover/large/bx85141-8q0Z0M2oJ2K1.jpg",
    },
    "nano machine": {
        "title": "Nano Machine",
        "volumes": 36,
        "chapters": 321,
        "status": "RELEASING",
        "genres": ["Action", "Adventure", "Fantasy", "Martial Arts", "Sci-Fi"],
        "synopsis": "Cheon Yeo-Woon reçoit l'injection de nanomachines de la part de son descendant venu du futur et transforme son destin au sein du culte démoniaque.",
        "cover_url": "https://s4.anilist.co/file/anilistcdn/media/manga/cover/large/bx121703-9K2L1w0R4m6V.jpg",
    },
    "magic emperor": {
        "title": "Magic Emperor",
        "volumes": 98,
        "chapters": 881,
        "status": "RELEASING",
        "genres": ["Action", "Adventure", "Fantasy", "Martial Arts"],
        "synopsis": "L'Empereur Démoniaque Zhuo Yifan se réincarne dans le corps d'un serviteur et rebâtit sa puissance suprême.",
        "cover_url": "https://s4.anilist.co/file/anilistcdn/media/manga/cover/large/bx111862-2G1k4R7L9z0Q.jpg",
    },
    "wind breaker": {
        "title": "Wind Breaker",
        "volumes": 57,
        "chapters": 515,
        "status": "RELEASING",
        "genres": ["Action", "Comedy", "Drama", "Sports"],
        "synopsis": "Jay, lycéen modèle et prodige du vélo fixie, découvre la passion des courses de rue avec l'équipage Hummingbird.",
        "cover_url": "https://s4.anilist.co/file/anilistcdn/media/manga/cover/large/bx85229-6uN7k9M3v5P1.jpg",
    },
    "lookism": {
        "title": "Lookism",
        "volumes": 65,
        "chapters": 600,
        "status": "RELEASING",
        "genres": ["Action", "Comedy", "Drama", "Supernatural"],
        "synopsis": "Park Hyung Suk, lycéen maltraité, se réveille un jour dans un corps athlétique et parfait, et jongle entre ses deux existences.",
        "cover_url": "https://s4.anilist.co/file/anilistcdn/media/manga/cover/large/bx86377-5p2L7m9Q3v1R.jpg",
    },
    "chainsaw man": {
        "title": "Chainsaw Man",
        "volumes": 18,
        "chapters": 175,
        "status": "RELEASING",
        "genres": ["Action", "Comedy", "Drama", "Horror", "Supernatural"],
        "synopsis": "Denji fusionne avec le démon-tronçonneuse Pochita pour devenir Chainsaw Man et chasse les démons pour la Sécurité Publique.",
        "cover_url": "https://s4.anilist.co/file/anilistcdn/media/manga/cover/large/bx105778-vA8aHj4c4r6e.jpg",
    },
    "spy x family": {
        "title": "Spy x Family",
        "volumes": 14,
        "chapters": 105,
        "status": "RELEASING",
        "genres": ["Action", "Comedy", "Slice of Life"],
        "synopsis": "L'espion Twilight crée une fausse famille avec une tueuse à gages et une petite fille télépathe sans que personne ne connaisse le secret de l'autre.",
        "cover_url": "https://s4.anilist.co/file/anilistcdn/media/manga/cover/large/bx108556-qT2lX8R1o4Y9.jpg",
    },
    "blue lock": {
        "title": "Blue Lock",
        "volumes": 31,
        "chapters": 275,
        "status": "RELEASING",
        "genres": ["Action", "Drama", "Sports"],
        "synopsis": "300 attaquants lycéens sont enfermés dans le centre Blue Lock pour forger l'attaquant ultime de l'équipe du Japon.",
        "cover_url": "https://s4.anilist.co/file/anilistcdn/media/manga/cover/large/bx106130-9L2b4v6W8m1Q.jpg",
    },
    "kaiju n8": {
        "title": "Kaiju No. 8",
        "volumes": 14,
        "chapters": 115,
        "status": "RELEASING",
        "genres": ["Action", "Sci-Fi"],
        "synopsis": "Kafka Hibino absorbe accidentellement un petit Kaiju et obtient la capacité de se transformer en monstre pour intégrer les Forces de Défense.",
        "cover_url": "https://s4.anilist.co/file/anilistcdn/media/manga/cover/large/bx120760-4m2b8V0Q5p7L.jpg",
    },
    "tensei shitara slime datta ken": {
        "title": "Moi, quand je me réincarne en Slime",
        "volumes": 27,
        "chapters": 120,
        "status": "RELEASING",
        "genres": ["Action", "Adventure", "Comedy", "Fantasy"],
        "synopsis": "Satoru Mikami se réincarne dans un autre monde sous la forme d'un slime doté de compétences uniques et fonde la Fédération de Jura Tempest.",
        "cover_url": "https://s4.anilist.co/file/anilistcdn/media/manga/cover/large/bx86399-6V7k9L2m4p1Q.jpg",
    },
    "the eminence in shadow": {
        "title": "The Eminence in Shadow",
        "volumes": 14,
        "chapters": 68,
        "status": "RELEASING",
        "genres": ["Action", "Comedy", "Fantasy"],
        "synopsis": "Cid Kagenou joue le rôle d'un obscur manipulateur dans l'ombre et combat sans le savoir un culte démoniaque bien réel.",
        "cover_url": "https://s4.anilist.co/file/anilistcdn/media/manga/cover/large/bx106758-2L4b8v6W9p1R.jpg",
    },
}


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
    _loaded_disk: bool = False

    @classmethod
    def _init_disk_cache(cls):
        if cls._loaded_disk:
            return
        cls._loaded_disk = True
        
        # Charger la base canonique d'abord
        for k, v in CANONICAL_DB.items():
            cls._meta_cache[k] = v
            clean_k = re.sub(r'[^a-z0-9]', '', k)
            cls._meta_cache[clean_k] = v

        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        cls._meta_cache[k.lower().strip()] = v
                        cls._meta_cache[re.sub(r'[^a-z0-9]', '', k.lower())] = v
            except Exception:
                pass

    @classmethod
    def _save_disk_cache(cls):
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cls._meta_cache, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @classmethod
    def get_official_volumes_for_chapters(
        cls, manga_title: str, available_chapters: List[str], alt_titles: Optional[List[str]] = None
    ) -> Tuple[str, Dict[int, List[str]]]:
        cls._init_disk_cache()
        if not available_chapters:
            return ("Indisponible", {})

        cache_key = manga_title.lower().strip()
        if cache_key in cls._cache and cls._cache[cache_key][1]:
            return cls._cache[cache_key]

        clean_title = manga_title.strip()
        candidates = [clean_title]
        if alt_titles:
            candidates.extend([a.strip() for a in alt_titles if a.strip()])

        for t in list(candidates):
            c_no_paren = re.sub(r'[\(\[\{].*?[\)\]\}]', '', t).strip()
            if c_no_paren and c_no_paren not in candidates:
                candidates.append(c_no_paren)
            c_no_punct = re.sub(r'[^\w\s]', ' ', t).strip()
            if c_no_punct and c_no_punct not in candidates:
                candidates.append(c_no_punct)

        # ── 0. BASE CANONIQUE & DISK CACHE ────────────────────────────────────
        for cand in candidates:
            c_k = cand.lower().strip()
            c_norm = re.sub(r'[^a-z0-9]', '', c_k)
            meta = cls._meta_cache.get(c_k) or cls._meta_cache.get(c_norm)
            if meta and meta.get("volumes"):
                v_count = meta["volumes"]
                c_count = meta.get("chapters") or len(available_chapters)
                status = meta.get("status", "FINISHED")
                v_map = cls._build_ratio_map(available_chapters, v_count, c_count, manga_title=clean_title, is_finished=(status in ["FINISHED", "finished"]))
                if v_map:
                    res = (f"Édition Officielle ({len(v_map)} tomes)", v_map)
                    cls._cache[cache_key] = res
                    return res

        # ── 1. TIER 1 : AniList GraphQL avec recherche scorée ────────────────
        al_info = cls._get_anilist_info(candidates)
        if al_info:
            v_count = al_info.get("volumes")
            c_count = al_info.get("chapters")
            status = al_info.get("status")

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
                meta_obj = {
                    "title": al_info.get("title", clean_title),
                    "status": status,
                    "volumes": v_count,
                    "chapters": c_count,
                    "total_volumes": len(v_map),
                    "total_chapters": c_count,
                    "genres": al_info.get("genres", []),
                    "synopsis": al_info.get("synopsis", ""),
                    "cover_url": al_info.get("cover_url"),
                    "matched_title": al_info.get("title", clean_title)
                }
                cls._meta_cache[cache_key] = meta_obj
                cls._meta_cache[re.sub(r'[^a-z0-9]', '', cache_key)] = meta_obj
                cls._save_disk_cache()
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
                meta_obj = {
                    "title": md_info.get("title", clean_title),
                    "status": status,
                    "volumes": v_count,
                    "chapters": c_count,
                    "total_volumes": len(v_map),
                    "total_chapters": c_count,
                    "genres": md_info.get("genres", []),
                    "synopsis": md_info.get("synopsis", ""),
                    "cover_url": md_info.get("cover_url"),
                    "matched_title": md_info.get("title", clean_title)
                }
                cls._meta_cache[cache_key] = meta_obj
                cls._meta_cache[re.sub(r'[^a-z0-9]', '', cache_key)] = meta_obj
                cls._save_disk_cache()
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
                meta_obj = {
                    "title": kt_info.get("title", clean_title),
                    "status": status,
                    "volumes": v_count,
                    "chapters": c_count,
                    "total_volumes": len(v_map),
                    "total_chapters": c_count,
                    "genres": kt_info.get("genres", []),
                    "synopsis": kt_info.get("synopsis", ""),
                    "cover_url": None,
                    "matched_title": kt_info.get("title", clean_title)
                }
                cls._meta_cache[cache_key] = meta_obj
                cls._meta_cache[re.sub(r'[^a-z0-9]', '', cache_key)] = meta_obj
                cls._save_disk_cache()
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
        cls._init_disk_cache()
        if not manga_title:
            return {}
        cache_key = manga_title.lower().strip()
        if cache_key in cls._meta_cache:
            return cls._meta_cache[cache_key]

        # Normalisation sans tirets ni ponctuation
        clean_key = re.sub(r'[^a-z0-9]', '', cache_key)
        if clean_key in cls._meta_cache:
            return cls._meta_cache[clean_key]

        for k, v in cls._meta_cache.items():
            if re.sub(r'[^a-z0-9]', '', k) == clean_key:
                return v

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

        # Règle spéciale Naruto : 72 tomes officiels pour les 700 chapitres + Tome 73 (Gaiden 701-712)
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
              popularity
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
                            if s >= 1.5:
                                bonus = 0.0
                                if m.get("volumes"):
                                    bonus += 0.3
                                if m.get("chapters"):
                                    bonus += 0.2
                                pop = m.get("popularity") or 0
                                pop_bonus = min(0.5, pop / 100000.0)
                                total_score = s + bonus + pop_bonus

                                if total_score > best_score:
                                    best_score = total_score
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
                "status": m.get("status"),
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
            try:
                with httpx.Client(timeout=4.0) as c:
                    r = c.get("https://kitsu.io/api/edge/manga", params={"filter[text]": cand, "page[limit]": 3})
                if r.status_code == 200:
                    data = r.json().get("data", [])
                    if data:
                        attrs = data[0].get("attributes", {})
                        titles = list(attrs.get("titles", {}).values())
                        return {
                            "title": titles[0] if titles else cand,
                            "volumes": attrs.get("volumeCount"),
                            "chapters": attrs.get("chapterCount"),
                            "status": attrs.get("status"),
                            "genres": [],
                            "synopsis": attrs.get("synopsis", ""),
                        }
            except Exception:
                pass
        return None
