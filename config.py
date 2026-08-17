import json
import os
from pathlib import Path

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
    def __init__(self, config_file: str = "config.json"):
        self.config_path = Path(config_file)
        self.config = DEFAULT_CONFIG.copy()
        self.load()
        
        # Appliquer le thème au démarrage
        from ui.theme import theme_manager
        theme = self.get("theme", "dark")
        theme_manager.set_theme(theme)

    def load(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Migrations automatiques vers les domaines actifs
                    if data.get("anime_sama_domain") == "https://anime-sama.fr":
                        data["anime_sama_domain"] = "https://anime-sama.to"
                    if data.get("crunchyscan_domain") in ["https://crunchyscan.fr", "https://crunchyscan.fr/"]:
                        data["crunchyscan_domain"] = "https://sushiscan.fr"
                    if data.get("japscan_domain") in ["https://japscan.co", "https://japscan.ws", "https://www.japscan.co"]:
                        data["japscan_domain"] = "https://www.japscan.foo"
                    if data.get("scan_vf_domain") in ["https://scan-vf.co", "https://www.scan-vf.co", "https://scan-vf.net"]:
                        data["scan_vf_domain"] = "https://www.scan-vf.net"
                    # Migration du thème si absent
                    if "theme" not in data:
                        data["theme"] = "dark"
                    if "auto_open_folder" not in data:
                        data["auto_open_folder"] = False
                    # Migration des nouveaux domaines si absents
                    if "japscan_domain" not in data:
                        data["japscan_domain"] = "https://www.japscan.foo"
                    if "unekoscans_domain" not in data:
                        data["unekoscans_domain"] = "https://unekoscans.fr"
                    if "scan_vf_domain" not in data:
                        data["scan_vf_domain"] = "https://www.scan-vf.net"

                    if "mangadex_domain" not in data:
                        data["mangadex_domain"] = "https://api.mangadex.org"
                    self.config.update(data)
            except Exception as e:
                print(f"Erreur lors du chargement de la config: {e}")
        else:
            self.save()

    def save(self):
        try:
            os.makedirs(self.config["download_dir"], exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde de la config: {e}")

    def get(self, key: str, default=None):
        return self.config.get(key, default)

    def set(self, key: str, value):
        self.config[key] = value
        self.save()

config_manager = ConfigManager()
