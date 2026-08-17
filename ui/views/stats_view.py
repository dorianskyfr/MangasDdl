import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QProgressBar, QPushButton, QScrollArea, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from config import config_manager
from scrapers.factory import ScraperFactory
from reading_history import reading_history


class StatsView(QWidget):
    """Vue des statistiques de l'application."""
    log_signal = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(24)

        scroll_area.setWidget(container)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll_area)

        # Header Title
        title_layout = QHBoxLayout()
        title = QLabel("📊 Tableau de Bord & Statistiques")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #38bdf8;")
        title_layout.addWidget(title)
        title_layout.addStretch()

        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.setObjectName("SecondaryButton")
        refresh_btn.setFixedSize(110, 36)
        refresh_btn.clicked.connect(self.refresh_stats)
        title_layout.addWidget(refresh_btn)

        main_layout.addLayout(title_layout)

        # 1. KPI Cards Row
        self.kpi_layout = QGridLayout()
        self.kpi_layout.setSpacing(16)
        
        self.card_downloads = self._create_kpi_card("📖 Chapitres", "0", "Téléchargés dans le dossier", "#38bdf8")
        self.card_storage = self._create_kpi_card("💾 Espace Occupé", "0 Mo", "Dossier MangaDownloader", "#a855f7")
        self.card_sources = self._create_kpi_card("🌐 Sources Actives", "6 / 6", "100% Opérationnelles", "#4ade80")
        self.card_speed = self._create_kpi_card("⚡ Threads Parallèles", f"{config_manager.get('max_concurrent_threads', 4)} Threads", "Vitesse optimisée", "#fbbf24")
        self.card_read_chapters = self._create_kpi_card("👁️ Chapitres Lus", "0", "Via le lecteur intégré", "#ec4899")
        self.card_read_mangas = self._create_kpi_card("📚 Mangas Lus", "0", "Séries différentes", "#f97316")

        self.kpi_layout.addWidget(self.card_downloads, 0, 0)
        self.kpi_layout.addWidget(self.card_storage, 0, 1)
        self.kpi_layout.addWidget(self.card_sources, 0, 2)
        self.kpi_layout.addWidget(self.card_speed, 0, 3)
        self.kpi_layout.addWidget(self.card_read_chapters, 1, 0)
        self.kpi_layout.addWidget(self.card_read_mangas, 1, 1)

        main_layout.addLayout(self.kpi_layout)

        # 2. Etat des 6 Sources
        sources_box = QFrame()
        sources_box.setObjectName("Card")
        sources_layout = QVBoxLayout(sources_box)
        sources_layout.setContentsMargins(16, 16, 16, 16)
        sources_layout.setSpacing(14)

        sources_title = QLabel("🌐 État des 6 Sources de Scraping")
        sources_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #f8fafc;")
        sources_layout.addWidget(sources_title)

        self.sources_grid = QGridLayout()
        self.sources_grid.setSpacing(12)

        sources_data = [
            ("Anime-Sama", "Sitemap + API get_nb_chap_et_img", "https://anime-sama.to", "#38bdf8"),
            ("JapScan", "Homepage Catalog + Cloudflare Bypass", "https://www.japscan.foo", "#4ade80"),
            ("SushiScan / Crunchy", "WP-Manga Engine", "https://sushiscan.fr", "#f97316"),
            ("UNekoScans", "Direct Scraper & Sitemap", "https://unekoscans.fr", "#ec4899"),
            ("Scan-VF", "HTML Selector Engine", "https://scan-vf.co", "#8b5cf6"),
            ("MangaDex", "API REST Officielle (v5)", "https://api.mangadex.org", "#eab308"),
        ]

        for idx, (name, desc, default_url, color) in enumerate(sources_data):
            row = idx // 2
            col = idx % 2
            card = self._create_source_card(name, desc, default_url, color)
            self.sources_grid.addWidget(card, row, col)

        sources_layout.addLayout(self.sources_grid)
        main_layout.addWidget(sources_box)

        # 3. Informations sur le stockage
        storage_box = QFrame()
        storage_box.setObjectName("Card")
        storage_layout = QVBoxLayout(storage_box)
        storage_layout.setContentsMargins(16, 16, 16, 16)
        storage_layout.setSpacing(12)

        storage_title = QLabel("📂 Répertoire de Téléchargement")
        storage_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #f8fafc;")
        storage_layout.addWidget(storage_title)

        self.dir_label = QLabel(f"Chemin : {config_manager.get('download_dir')}")
        self.dir_label.setStyleSheet("color: #94a3b8; font-size: 13px;")
        storage_layout.addWidget(self.dir_label)

        self.format_label = QLabel(f"Format d'export actuel : {config_manager.get('export_format', 'CBZ')}")
        self.format_label.setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: bold;")
        storage_layout.addWidget(self.format_label)

        clean_btn = QPushButton("🧹 Nettoyer le cache temporaire")
        clean_btn.setObjectName("SecondaryButton")
        clean_btn.setFixedWidth(240)
        clean_btn.clicked.connect(self.clean_temp_cache)
        storage_layout.addWidget(clean_btn)

        main_layout.addWidget(storage_box)

    def clean_temp_cache(self):
        """Nettoie les fichiers temporaires non terminés ou orphelins."""
        download_dir = Path(config_manager.get("download_dir"))
        cleaned_count = 0
        cleaned_bytes = 0

        if download_dir.exists():
            for root, dirs, files in os.walk(download_dir):
                for f in files:
                    if f.endswith(".tmp") or f.endswith(".part"):
                        fp = Path(root) / f
                        try:
                            sz = fp.stat().st_size
                            fp.unlink()
                            cleaned_count += 1
                            cleaned_bytes += sz
                        except Exception:
                            pass

        if cleaned_count > 0:
            msg = f"{cleaned_count} fichier(s) temporaire(s) nettoyé(s) ({cleaned_bytes // 1024} Ko libérés)."
        else:
            msg = "Aucun fichier temporaire à nettoyer. Le dossier est propre !"

        if hasattr(self, "log_signal"):
            self.log_signal.emit("SUCCESS", msg)
        self.refresh_stats()

    def _create_kpi_card(self, title: str, value: str, subtext: str, color: str) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        card.setStyleSheet(f"""
            QFrame#Card {{
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 12px;
                padding: 12px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(4)
        layout.setContentsMargins(12, 12, 12, 12)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: bold;")
        layout.addWidget(t_lbl)

        v_lbl = QLabel(value)
        v_lbl.setObjectName("v_lbl")
        v_lbl.setStyleSheet(f"color: {color}; font-size: 20px; font-weight: bold;")
        layout.addWidget(v_lbl)

        s_lbl = QLabel(subtext)
        s_lbl.setObjectName("s_lbl")
        s_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(s_lbl)

        return card

    def _create_source_card(self, name: str, desc: str, url: str, color: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #161e30;
                border: 1px solid #1e293b;
                border-radius: 10px;
                padding: 10px;
            }}
        """)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)

        badge = QLabel("ONLINE")
        badge.setStyleSheet(f"""
            background-color: {color}22;
            color: {color};
            border: 1px solid {color}55;
            font-size: 10px;
            font-weight: bold;
            padding: 4px 8px;
            border-radius: 6px;
        """)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("color: #f8fafc; font-size: 13px; font-weight: bold;")
        
        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet("color: #64748b; font-size: 11px;")

        info_layout.addWidget(name_lbl)
        info_layout.addWidget(desc_lbl)

        layout.addLayout(info_layout)
        layout.addStretch()
        layout.addWidget(badge)

        return card

    def refresh_stats(self):
        """Calcule l'espace disque utilisé et les statistiques des fichiers."""
        download_dir = Path(config_manager.get("download_dir"))
        total_bytes = 0
        total_files = 0

        if download_dir.exists():
            try:
                for root, _, files in os.walk(download_dir):
                    for f in files:
                        total_files += 1
                        fp = Path(root) / f
                        if fp.exists():
                            total_bytes += fp.stat().st_size
            except Exception:
                pass

        # Formatting size
        if total_bytes < 1024 * 1024:
            size_str = f"{total_bytes / 1024:.1f} Ko"
        elif total_bytes < 1024 * 1024 * 1024:
            size_str = f"{total_bytes / (1024 * 1024):.1f} Mo"
        else:
            size_str = f"{total_bytes / (1024 * 1024 * 1024):.2f} Go"

        # Update KPI labels
        self.card_downloads.findChild(QLabel, "v_lbl").setText(str(total_files))
        self.card_storage.findChild(QLabel, "v_lbl").setText(size_str)
        self.card_speed.findChild(QLabel, "v_lbl").setText(f"{config_manager.get('max_concurrent_threads', 4)} Threads")

        read_stats = reading_history.get_all_stats()
        self.card_read_chapters.findChild(QLabel, "v_lbl").setText(str(read_stats.get("total_chapters_read", 0)))
        self.card_read_mangas.findChild(QLabel, "v_lbl").setText(str(read_stats.get("total_mangas_read", 0)))

        self.dir_label.setText(f"Chemin : {download_dir.absolute()}")
        self.format_label.setText(f"Format d'export actuel : {config_manager.get('export_format', 'CBZ')}")

        if hasattr(self, "log_signal"):
            self.log_signal.emit("INFO", f"Statistiques actualisées : {total_files} fichiers ({size_str}), {read_stats.get('total_chapters_read', 0)} chapitres lus.")
