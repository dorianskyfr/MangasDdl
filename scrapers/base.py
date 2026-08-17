"""
Base Scraper Module v2.0
======================

Ce module fournit l'infrastructure de base pour tous les scrapers avec :
- Support synchrones et asynchrones
- Gestion des erreurs et retry automatique
- Timeout configurable
- Cache persistant (JSON)
- Rotation des User-Agents
- Logging structure

Utilisation :
    from scrapers.base import BaseScraper, ScraperConfig
    
    class MonScraper(BaseScraper):
        def search(self, query): ...
        def get_manga_details(self, url): ...
        def get_chapters(self, url): ...
        def get_chapter_pages(self, url): ...
"""

import json
import os
import time
import random
import logging
import hashlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from functools import wraps

import httpx
from bs4 import BeautifulSoup

from models import Manga, Chapter, Page
from config import config_manager


# ============================================================================
# CONSTANTES
# ============================================================================

DEFAULT_TIMEOUT = 12.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0
DEFAULT_CACHE_DIR = Path.home() / ".manga_scraper_cache"

# Liste de User-Agents pour la rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]


# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger("scrapers")


def setup_scraper_logging(level=logging.INFO):
    """Configure le logging pour les scrapers."""
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(handler)
    logger.setLevel(level)


# ============================================================================
# CACHE PERSISTANT
# ============================================================================

class ScraperCache:
    """Gestionnaire de cache persistant pour les scrapers."""
    
    def __init__(self, cache_dir: Path = DEFAULT_CACHE_DIR):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache: Dict[str, Any] = {}
    
    def _get_cache_path(self, key: str) -> Path:
        """Retourne le chemin du fichier de cache."""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"
    
    def get(self, key: str, default=None):
        """Recupere une valeur du cache."""
        if key in self._memory_cache:
            return self._memory_cache[key]
        
        cache_file = self._get_cache_path(key)
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'expires' not in data or data['expires'] > time.time():
                        self._memory_cache[key] = data.get('value', default)
                        return self._memory_cache[key]
            except Exception as e:
                logger.warning(f"Erreur de lecture du cache pour {key}: {e}")
        
        return default
    
    def set(self, key: str, value, ttl: int = 3600):
        """Stocke une valeur dans le cache.
        
        Args:
            key: Clef de cache
            value: Valeur a stocker
            ttl: Time-to-live en secondes (0 = jamais n'expire)
        """
        self._memory_cache[key] = value
        
        if ttl > 0:
            expires = time.time() + ttl
        else:
            expires = 0
        
        data = {'value': value, 'expires': expires}
        cache_file = self._get_cache_path(key)
        
        try:
            import dataclasses
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=lambda o: dataclasses.asdict(o) if dataclasses.is_dataclass(o) else str(o))
        except Exception as e:
            logger.debug(f"Erreur d'ecriture du cache pour {key}: {e}")

    
    def delete(self, key: str):
        """Supprime une entrée du cache."""
        self._memory_cache.pop(key, None)
        cache_file = self._get_cache_path(key)
        if cache_file.exists():
            cache_file.unlink()
    
    def clear(self):
        """Efface tout le cache."""
        self._memory_cache.clear()
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()


# Instance globale du cache
global_cache = ScraperCache()


# ============================================================================
# DECORATEURS UTILES
# ============================================================================

def retry(max_attempts: int = DEFAULT_MAX_RETRIES, 
          delay: float = DEFAULT_RETRY_DELAY,
          exceptions: tuple = (Exception,)):
    """Decorateur pour retry automatique."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay * (attempt + 1))
                        logger.debug(f"Tentative {attempt + 1}/{max_attempts} echouee pour {func.__name__}: {e}")
            
            logger.debug(f"Toutes les tentatives ({max_attempts}) echouees pour {func.__name__}")
            raise last_exception
        return wrapper
    return decorator



def cached(ttl: int = 3600, key_func: Callable = None):
    """Decorateur pour cache les resultats."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{args}:{frozenset(kwargs.items())}"
            
            result = global_cache.get(cache_key)
            if result is not None:
                logger.debug(f"Cache hit pour {cache_key}")
                return result
            
            result = func(*args, **kwargs)
            if result is not None:
                global_cache.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator


# ============================================================================
# UTILITAIRES HTTP
# ============================================================================

class HTTPClient:
    """Client HTTP avec gestion des erreurs et retry."""
    
    def __init__(self, 
                 timeout: float = DEFAULT_TIMEOUT,
                 max_retries: int = DEFAULT_MAX_RETRIES,
                 retry_delay: float = DEFAULT_RETRY_DELAY,
                 use_proxy: bool = False):
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.use_proxy = use_proxy
        self._client: Optional[httpx.Client] = None
    
    def get_random_user_agent(self) -> str:
        """Retourne un User-Agent aleatoire."""
        return random.choice(USER_AGENTS)
    
    def get_client(self, headers: Dict = None) -> httpx.Client:
        """Retourne un client httpx configure."""
        if self._client is None or self._client.is_closed:
            base_headers = {
                "User-Agent": self.get_random_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            }
            if headers:
                base_headers.update(headers)
            
            self._client = httpx.Client(
                headers=base_headers,
                timeout=self.timeout,
                follow_redirects=True
            )
        return self._client
    
    def close(self):
        """Fermer le client."""
        if self._client and not self._client.is_closed:
            self._client.close()
    
    @retry()
    def get(self, url: str, headers: Dict = None, **kwargs) -> httpx.Response:
        """Effectue une requete GET avec retry."""
        client = self.get_client(headers)
        try:
            response = client.get(url, **kwargs)
            return response
        finally:
            pass
    
    @retry()
    def post(self, url: str, data=None, headers: Dict = None, **kwargs) -> httpx.Response:
        """Effectue une requete POST avec retry."""
        client = self.get_client(headers)
        try:
            response = client.post(url, data=data, **kwargs)
            return response
        finally:
            pass


# ============================================================================
# BASE SCRAPER
# ============================================================================

class BaseScraper(ABC):
    """
    Classe de base pour tous les scrapers de mangas.
    
    Fournit :
    - Client HTTP avec retry et timeout
    - Cache persistant
    - Logging
    - Gestion des erreurs
    - Utilitaires de parsing HTML
    """
    
    # Timeout par defaut pour ce scraper
    timeout: float = DEFAULT_TIMEOUT
    
    # Nom de la source (a implementer)
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Nom de la source (ex: Anime-Sama, Crunchyscan)."""
        pass
    
    # URL de base (a implementer)
    @property
    @abstractmethod
    def base_url(self) -> str:
        """URL de base du site web."""
        pass
    
    def __init__(self):
        """Initialisation du scraper."""
        self.http_client = HTTPClient(timeout=self.timeout)
        self._user_agent_index = 0
    
    def get_random_user_agent(self) -> str:
        """Retourne un User-Agent aleatoire."""
        return self.http_client.get_random_user_agent()
    
    def rotate_user_agent(self) -> str:
        """Change le User-Agent pour le prochain request."""
        self._user_agent_index = (self._user_agent_index + 1) % len(USER_AGENTS)
        return USER_AGENTS[self._user_agent_index]
    
    @retry()
    def _get(self, url: str, headers: Dict = None, **kwargs) -> httpx.Response:
        """Effectue une requete GET avec gestion des erreurs."""
        return self.http_client.get(url, headers=headers, **kwargs)
    
    @retry()
    def _post(self, url: str, data=None, headers: Dict = None, **kwargs) -> httpx.Response:
        """Effectue une requete POST avec gestion des erreurs."""
        return self.http_client.post(url, data=data, headers=headers, **kwargs)
    
    def _soup(self, response: httpx.Response) -> Optional[BeautifulSoup]:
        """Convertit une reponse HTTP en BeautifulSoup."""
        if response.status_code == 200:
            try:
                return BeautifulSoup(response.text, "lxml")
            except Exception as e:
                logger.error(f"Erreur de parsing HTML: {e}")
        return None
    
    def _get_soup(self, url: str, headers: Dict = None) -> Optional[BeautifulSoup]:
        """Recupere et parse une URL en BeautifulSoup."""
        response = self._get(url, headers=headers)
        return self._soup(response)
    
    def _check_response(self, response: httpx.Response, context: str = "") -> bool:
        """Verifie si une reponse HTTP est valide."""
        if response.status_code != 200:
            logger.warning(f"[{self.source_name}] Reponse {response.status_code} pour {context}")
            return False
        
        # Verifier les erreurs Cloudflare
        if "cloudflare" in response.text.lower():
            logger.error(f"[{self.source_name}] Bloque par Cloudflare pour {context}")
            return False
        
        # Verifier les pages d'erreur
        if any(err in response.text.lower() for err in ["404", "not found", "error"]):
            logger.warning(f"[{self.source_name}] Page d'erreur detectee pour {context}")
            return False
        
        return True
    
    # ========================================================================
    # METHODES ABSTRAITES A IMPLEMENTER
    # ========================================================================
    
    @abstractmethod
    def search(self, query: str) -> List[Manga]:
        """
        Recherche des mangas correspondant au mot-cle donne.
        
        Args:
            query: Le terme de recherche
            
        Returns:
            Liste de Manga correspondants
        """
        pass
    
    @abstractmethod
    def get_manga_details(self, manga_url: str) -> Manga:
        """
        Recupere les details d'un manga (synopsis, genres, couverture).
        
        Args:
            manga_url: URL du manga
            
        Returns:
            Manga avec les details
        """
        pass
    
    @abstractmethod
    def get_chapters(self, manga_url: str) -> List[Chapter]:
        """
        Recupere la liste de tous les chapitres disponibles pour un manga.
        
        Args:
            manga_url: URL du manga
            
        Returns:
            Liste de Chapter
        """
        pass
    
    @abstractmethod
    def get_chapter_pages(self, chapter_url: str) -> List[Page]:
        """
        Recupere la liste des URLs d'images (pages) d'un chapitre.
        
        Args:
            chapter_url: URL du chapitre
            
        Returns:
            Liste de Page
        """
        pass
    
    # ========================================================================
    # UTILITAIRES
    # ========================================================================
    
    def extract_number(self, text: str) -> Optional[float]:
        """Extrait un nombre d'un texte."""
        import re
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return None
    
    def normalize_title(self, title: str) -> str:
        """Normalise un titre de manga."""
        import re
        title = title.strip()
        title = re.sub(r'[\W_]+', ' ', title)
        title = re.sub(r'\s+', ' ', title)
        return title.strip().title()
    
    def sanitize_url(self, url: str) -> str:
        """Nettoie une URL."""
        url = url.strip()
        url = url.rstrip('/')
        return url
    
    def close(self):
        """Fermer le client HTTP."""
        if hasattr(self, 'http_client') and self.http_client:
            self.http_client.close()
    
    def __del__(self):
        """Destructeur."""
        try:
            self.close()
        except Exception:
            pass
