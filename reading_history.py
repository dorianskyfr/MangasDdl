"""
Gestionnaire de l'historique de lecture.
Permet de suivre quels chapitres ont été lus et quand.
"""
import json
import time
from pathlib import Path
from typing import Dict, List, Optional

READING_HISTORY_FILE = Path("reading_history.json")


class ReadingHistoryManager:
    """Suit la progression de lecture par manga."""

    def __init__(self):
        self.history: Dict[str, dict] = {}
        self.load()

    def load(self):
        if READING_HISTORY_FILE.exists():
            try:
                with open(READING_HISTORY_FILE, "r", encoding="utf-8") as f:
                    self.history = json.load(f)
            except Exception:
                self.history = {}

    def save(self):
        try:
            with open(READING_HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def mark_as_read(self, manga_title: str, chapter_number: str, source: str):
        """Marque un chapitre comme lu."""
        key = manga_title.strip().lower()
        if key not in self.history:
            self.history[key] = {
                "title": manga_title,
                "source": source,
                "chapters_read": {},
                "last_read": None,
                "total_read": 0,
            }

        entry = self.history[key]
        ch_key = str(chapter_number).strip()
        if ch_key not in entry["chapters_read"]:
            entry["chapters_read"][ch_key] = {
                "read_at": time.strftime("%Y-%m-%d %H:%M"),
            }
            entry["total_read"] = len(entry["chapters_read"])

        entry["last_read"] = ch_key
        entry["last_read_at"] = time.strftime("%Y-%m-%d %H:%M")
        self.save()

    def is_read(self, manga_title: str, chapter_number: str) -> bool:
        """Vérifie si un chapitre a été lu."""
        key = manga_title.strip().lower()
        entry = self.history.get(key)
        if not entry:
            return False
        return str(chapter_number).strip() in entry.get("chapters_read", {})

    def get_last_read(self, manga_title: str) -> Optional[str]:
        """Retourne le dernier chapitre lu pour un manga."""
        key = manga_title.strip().lower()
        entry = self.history.get(key)
        if entry:
            return entry.get("last_read")
        return None

    def get_read_count(self, manga_title: str) -> int:
        """Retourne le nombre de chapitres lus pour un manga."""
        key = manga_title.strip().lower()
        entry = self.history.get(key)
        if entry:
            return entry.get("total_read", 0)
        return 0

    def get_all_stats(self) -> dict:
        """Retourne les statistiques globales de lecture."""
        total_mangas = len(self.history)
        total_chapters = sum(
            e.get("total_read", 0) for e in self.history.values()
        )
        return {
            "total_mangas_read": total_mangas,
            "total_chapters_read": total_chapters,
        }

    def get_recent_reads(self, limit: int = 10) -> List[dict]:
        """Retourne les mangas lus récemment."""
        entries = []
        for data in self.history.values():
            if data.get("last_read_at"):
                entries.append({
                    "title": data["title"],
                    "source": data.get("source", ""),
                    "last_chapter": data.get("last_read", "?"),
                    "last_read_at": data.get("last_read_at", ""),
                    "total_read": data.get("total_read", 0),
                })
        entries.sort(key=lambda x: x.get("last_read_at", ""), reverse=True)
        return entries[:limit]


reading_history = ReadingHistoryManager()
