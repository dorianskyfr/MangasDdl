import json
import logging
from pathlib import Path
from urllib.parse import urlparse
from app_info import APP_VERSION
from storage import user_file, atomic_json_write

DEFAULT_DOWNLOAD_DIR = str(Path.home() / "Downloads" / "MangaDownloader")

DEFAULT_CONFIG = {
    "download_dir": DEFAULT_DOWNLOAD_DIR,
    "max_concurrent_threads": 4,
    "export_format": "CBZ",  # Options: "Images", "CBZ", "PDF"
    "chapters_per_volume": 5,
    "group_by_volume": False,
    "auto_open_folder": False,
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "theme": "dark",  # dark or light
    "anime_sama_domain": "https://anime-sama.to",
    "crunchyscan_domain": "https://sushiscan.fr",
    "japscan_domain": "https://www.japscan.foo",
    "unekoscans_domain": "https://unekoscans.fr",
    "scan_vf_domain": "https://www.scan-vf.net",
    "mangadex_domain": "https://api.mangadex.org"
}


class ConfigManager:
    def __init__(self, config_file=None):
        self.config_path = Path(config_file) if config_file else user_file("config.json")
        self.config = DEFAULT_CONFIG.copy()
        self.load()
        from ui.theme import theme_manager
        theme_manager.set_theme(self.get("theme"))

    @staticmethod
    def validate(values):
        config = DEFAULT_CONFIG.copy()
        config.update(values)
        for name, lo, hi in (("max_concurrent_threads", 1, 16), ("chapters_per_volume", 1, 100)):
            value = config[name]
            if isinstance(value, bool) or not isinstance(value, int) or not lo <= value <= hi:
                raise ValueError(f"Valeur invalide pour {name} ({lo} à {hi}).")
        if config["theme"] not in ("dark", "light"):
            raise ValueError("Thème inconnu.")
        if config["export_format"] not in ("Images", "CBZ", "PDF", "EPUB"):
            raise ValueError("Format d'export inconnu.")
        if not isinstance(config["download_dir"], str) or not config["download_dir"].strip():
            raise ValueError("Choisissez un dossier de téléchargement.")
        config["download_dir"] = str(Path(config["download_dir"]).expanduser().resolve())
        for key in DEFAULT_CONFIG:
            if key.endswith("_domain"):
                url = config[key]
                parsed = urlparse(url) if isinstance(url, str) else None
                if not parsed or parsed.scheme not in ("https", "http") or not parsed.hostname:
                    raise ValueError(f"Adresse invalide pour {key} : utilisez une URL HTTP ou HTTPS.")
                config[key] = url.rstrip("/")
        return config

    def load(self):
        if not self.config_path.exists():
            return
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("La configuration doit être un objet JSON.")
            # Old releases shipped a developer's absolute Windows path.
            if data.get("download_dir") in ("C:/Users/gcdor/Documents/Mangas scraper", "C:/Users/doria/Downloads/MangaDownloader"):
                data["download_dir"] = DEFAULT_DOWNLOAD_DIR
            migrations = {
                "anime_sama_domain": ("https://anime-sama.fr",),
                "crunchyscan_domain": ("https://crunchyscan.fr",),
                "japscan_domain": ("https://japscan.co", "https://japscan.ws", "https://www.japscan.co"),
                "scan_vf_domain": ("https://scan-vf.co", "https://www.scan-vf.co", "https://scan-vf.net"),
            }
            for key, old in migrations.items():
                if str(data.get(key, "")).rstrip("/") in old:
                    data[key] = DEFAULT_CONFIG[key]
            # Recover valid preferences even when one field is malformed.
            for key, value in data.items():
                try:
                    self.config = self.validate({**self.config, key: value})
                except (ValueError, TypeError):
                    logging.warning("Configuration ignorée : %s", key)
        except (OSError, ValueError, TypeError):
            logging.warning("Configuration illisible : %s", self.config_path)

    def save(self):
        atomic_json_write(self.config_path, self.config)

    def get(self, key, default=None):
        return self.config.get(key, default)

    def update(self, values):
        candidate = self.validate({**self.config, **values})
        Path(candidate["download_dir"]).mkdir(parents=True, exist_ok=True)
        atomic_json_write(self.config_path, candidate)
        self.config = candidate

    def set(self, key, value):
        self.update({key: value})


config_manager = ConfigManager()
