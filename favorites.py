import json
from pathlib import Path
from typing import List, Dict
from models import Manga

FAVORITES_FILE = Path("favorites.json")

class FavoritesManager:
    """Gestionnaire des mangas favoris / bibliothèque de l'utilisateur."""

    def __init__(self):
        self.favorites: Dict[str, dict] = {}
        self.load()

    def load(self):
        if FAVORITES_FILE.exists():
            try:
                with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.favorites = data
            except Exception as e:
                print(f"[Favorites] Erreur chargement favoris: {e}")
                self.favorites = {}

    def save(self):
        try:
            with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
                json.dump(self.favorites, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Favorites] Erreur sauvegarde favoris: {e}")

    def add_favorite(self, manga: Manga):
        key = manga.title.strip().lower()
        self.favorites[key] = {
            "title": manga.title,
            "url": manga.url,
            "source": manga.source,
            "cover_url": manga.cover_url,
            "added_at": manga.title
        }
        self.save()

    def remove_favorite(self, manga_title: str):
        key = manga_title.strip().lower()
        if key in self.favorites:
            del self.favorites[key]
            self.save()

    def is_favorite(self, manga_title: str) -> bool:
        if not manga_title:
            return False
        return manga_title.strip().lower() in self.favorites

    def toggle_favorite(self, manga: Manga) -> bool:
        if self.is_favorite(manga.title):
            self.remove_favorite(manga.title)
            return False
        else:
            self.add_favorite(manga)
            return True

    def list_favorites(self) -> List[Manga]:
        res = []
        for data in self.favorites.values():
            res.append(Manga(
                title=data["title"],
                url=data["url"],
                source=data["source"],
                cover_url=data.get("cover_url")
            ))
        return res

favorites_manager = FavoritesManager()
