from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QSpinBox, QComboBox, QFrame,
    QMessageBox, QCheckBox, QGroupBox, QScrollArea
)
from PySide6.QtCore import Signal
from config import config_manager
from ui.theme import theme_manager


class SettingsView(QWidget):
    """Vue des parametres de l'application avec categories."""
    
    log_signal = Signal(str, str)
    theme_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        # Layout principal avec scroll
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(20)
        
        scroll_area.setWidget(container)
        
        # Layout principal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll_area)

        # Titre
        title = QLabel("Parametres de l'application")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #38bdf8;")
        main_layout.addWidget(title)

        # =====================================================================
        # 1. CATEGORIE: APPARENCE
        # =====================================================================
        self.create_appearance_group(main_layout)

        # =====================================================================
        # 2. CATEGORIE: TELECHARGEMENT
        # =====================================================================
        self.create_download_group(main_layout)

        # =====================================================================
        # 3. CATEGORIE: DOSSIERS
        # =====================================================================
        self.create_folders_group(main_layout)

        # =====================================================================
        # 4. CATEGORIE: SOURCES
        # =====================================================================
        self.create_sources_group(main_layout)

        # =====================================================================
        # Bouton d'enregistrement
        # =====================================================================
        save_btn = QPushButton("Enregistrer les modifications")
        save_btn.setFixedHeight(44)
        save_btn.setStyleSheet("font-size: 14px; font-weight: bold;")
        save_btn.clicked.connect(self.save_settings)
        main_layout.addWidget(save_btn)
        main_layout.addStretch()

    def create_appearance_group(self, layout):
        """Crée le groupe Apparence."""
        group = QGroupBox("Apparence")
        group.setStyleSheet("QGroupBox { font-size: 16px; font-weight: bold; border: none; padding-top: 12px; margin-top: 16px; } QGroupBox::title { subcontrol-origin: margin; left: 0px; padding: 0 4px; color: #38bdf8; }"  )
        
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)

        # Theme selector
        theme_layout = QHBoxLayout()
        theme_label = QLabel("Theme de l'application:")
        theme_label.setStyleSheet("font-weight: bold;")
        theme_layout.addWidget(theme_label)
        theme_layout.addStretch()

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Sombre", "Clair"])
        self.theme_combo.setCurrentText("Sombre" if theme_manager.is_dark else "Clair")
        self.theme_combo.currentTextChanged.connect(self.on_theme_selected)
        self.theme_combo.setFixedWidth(140)
        theme_layout.addWidget(self.theme_combo)
        
        group_layout.addLayout(theme_layout)

        # Separateur
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #1e293b; margin: 8px 0;")
        group_layout.addWidget(sep)

        # Format d'exportation
        format_layout = QHBoxLayout()
        format_label = QLabel("Format d'exportation des chapitres:")
        format_label.setStyleSheet("font-weight: bold;")
        format_layout.addWidget(format_label)
        format_layout.addStretch()

        self.format_combo = QComboBox()
        self.format_combo.addItems(["CBZ", "PDF", "EPUB", "Images"])
        self.format_combo.setCurrentText(config_manager.get("export_format", "CBZ"))
        self.format_combo.setFixedWidth(140)
        format_layout.addWidget(self.format_combo)
        group_layout.addLayout(format_layout)

        layout.addWidget(group)

    def create_download_group(self, layout):
        """Crée le groupe Téléchargement."""
        group = QGroupBox("Telechargement")
        group.setStyleSheet("QGroupBox { font-size: 16px; font-weight: bold; border: none; padding-top: 12px; margin-top: 16px; } QGroupBox::title { subcontrol-origin: margin; left: 0px; padding: 0 4px; color: #38bdf8; }"  )
        
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)

        # Threads
        threads_layout = QHBoxLayout()
        threads_label = QLabel("Threads de telechargement simultanes:")
        threads_label.setStyleSheet("font-weight: bold;")
        threads_layout.addWidget(threads_label)
        threads_layout.addStretch()

        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, 16)
        self.threads_spin.setValue(config_manager.get("max_concurrent_threads", 4))
        self.threads_spin.setFixedWidth(60)
        threads_layout.addWidget(self.threads_spin)
        group_layout.addLayout(threads_layout)

        # Separateur
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #1e293b; margin: 8px 0;")
        group_layout.addWidget(sep)

        # Regroupement en Tomes
        vol_layout = QHBoxLayout()
        vol_label = QLabel("Regroupement en Tomes:")
        vol_label.setStyleSheet("font-weight: bold;")
        vol_layout.addWidget(vol_label)
        vol_layout.addStretch()

        self.group_vol_cb = QCheckBox("Activer par defaut")
        self.group_vol_cb.setChecked(config_manager.get("group_by_volume", False))
        vol_layout.addWidget(self.group_vol_cb)
        group_layout.addLayout(vol_layout)

        # Chapitres par tome
        chaps_vol_layout = QHBoxLayout()
        chaps_vol_layout.addSpacing(24)
        chaps_label = QLabel("Chapitres par tome:")
        chaps_label.setStyleSheet("font-weight: bold;")
        chaps_vol_layout.addWidget(chaps_label)
        chaps_vol_layout.addStretch()

        self.vol_spin = QSpinBox()
        self.vol_spin.setRange(2, 50)
        self.vol_spin.setValue(config_manager.get("chapters_per_volume", 5))
        self.vol_spin.setFixedWidth(60)
        chaps_vol_layout.addWidget(self.vol_spin)
        
        vol_unit = QLabel("chapitres")
        vol_unit.setStyleSheet("color: #94a3b8;")
        chaps_vol_layout.addWidget(vol_unit)
        group_layout.addLayout(chaps_vol_layout)

        layout.addWidget(group)

    def create_folders_group(self, layout):
        """Crée le groupe Dossiers."""
        group = QGroupBox("Dossiers")
        group.setStyleSheet("QGroupBox { font-size: 16px; font-weight: bold; border: none; padding-top: 12px; margin-top: 16px; } QGroupBox::title { subcontrol-origin: margin; left: 0px; padding: 0 4px; color: #38bdf8; }"  )
        
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)

        # Dossier de telechargement
        dir_layout = QHBoxLayout()
        dir_label = QLabel("Repertoire de telechargement:")
        dir_label.setStyleSheet("font-weight: bold;")
        dir_layout.addWidget(dir_label)
        dir_layout.addStretch()

        self.dir_input = QLineEdit()
        self.dir_input.setText(config_manager.get("download_dir"))
        self.dir_input.setMinimumWidth(300)
        dir_layout.addWidget(self.dir_input)

        browse_btn = QPushButton("Parcourir...")
        browse_btn.setObjectName("SecondaryButton")
        browse_btn.clicked.connect(self.browse_folder)
        dir_layout.addWidget(browse_btn)
        
        group_layout.addLayout(dir_layout)

        # Auto open folder
        auto_open_layout = QHBoxLayout()
        auto_open_label = QLabel("Ouvrir automatiquement le dossier:")
        auto_open_label.setStyleSheet("font-weight: bold;")
        auto_open_layout.addWidget(auto_open_label)
        auto_open_layout.addStretch()

        self.auto_open_cb = QCheckBox("Ouvrir au telechargement")
        self.auto_open_cb.setChecked(config_manager.get("auto_open_folder", False))
        auto_open_layout.addWidget(self.auto_open_cb)
        group_layout.addLayout(auto_open_layout)

        layout.addWidget(group)

    def create_sources_group(self, layout):
        """Crée le groupe Sources avec les 6 sources configurables."""
        group = QGroupBox("Sources de Scraping (6 Domaines)")
        group.setStyleSheet("QGroupBox { font-size: 16px; font-weight: bold; border: none; padding-top: 12px; margin-top: 16px; } QGroupBox::title { subcontrol-origin: margin; left: 0px; padding: 0 4px; color: #38bdf8; }"  )
        
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(10)

        sources_fields = [
            ("as_domain_input", "Domaine Anime-Sama:", "anime_sama_domain", "https://anime-sama.to"),
            ("js_domain_input", "Domaine JapScan:", "japscan_domain", "https://www.japscan.foo"),
            ("cs_domain_input", "Domaine Crunchyscan / SushiScan:", "crunchyscan_domain", "https://sushiscan.fr"),
            ("un_domain_input", "Domaine UNekoScans:", "unekoscans_domain", "https://unekoscans.fr"),
            ("sv_domain_input", "Domaine Scan-VF:", "scan_vf_domain", "https://scan-vf.co"),
            ("md_domain_input", "Domaine MangaDex API:", "mangadex_domain", "https://api.mangadex.org"),
        ]

        for attr_name, label_text, config_key, default_val in sources_fields:
            row_layout = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-weight: bold;")
            row_layout.addWidget(lbl)
            row_layout.addStretch()

            input_widget = QLineEdit()
            input_widget.setText(config_manager.get(config_key, default_val))
            input_widget.setMinimumWidth(280)
            setattr(self, attr_name, input_widget)

            row_layout.addWidget(input_widget)
            group_layout.addLayout(row_layout)

        test_sources_btn = QPushButton("🧪 Tester la réactivité des 6 sources (Ping/LATENCE)")
        test_sources_btn.setObjectName("SecondaryButton")
        test_sources_btn.setHeight = 36
        test_sources_btn.clicked.connect(self.test_all_sources_ping)
        group_layout.addWidget(test_sources_btn)

        layout.addWidget(group)

    def test_all_sources_ping(self):
        """Teste la latence HTTP et le statut des 6 sources de scraping."""
        import time
        import httpx
        from scrapers.factory import ScraperFactory

        results = []
        sources = ScraperFactory.list_sources()

        for name in sources:
            try:
                scr = ScraperFactory.get_scraper(name)
                url = scr.base_url
                t0 = time.time()
                with httpx.Client(timeout=6.0, follow_redirects=True, verify=False) as c:
                    r = c.get(url)
                dt = (time.time() - t0) * 1000
                if r.status_code < 400:
                    results.append(f"🟢 {name}: {dt:.0f} ms (OK - Status {r.status_code})")
                else:
                    results.append(f"🟠 {name}: {dt:.0f} ms (Status {r.status_code})")
            except Exception as e:
                results.append(f"🔴 {name}: Échec ({e})")

        msg = "Résultats des pings de latence des 6 sources :\n\n" + "\n".join(results)
        QMessageBox.information(self, "Latence des Sources", msg)


    def on_theme_selected(self, theme_name: str):
        """Appelé lorsque le theme est selectionne."""
        theme_value = "dark" if theme_name == "Sombre" else "light"
        self.theme_changed.emit(theme_value)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Selectionner le repertoire de destination", self.dir_input.text()
        )
        if folder:
            self.dir_input.setText(folder)

    def save_settings(self):
        """Sauvegarde tous les parametres."""
        # Apparence
        theme_name = self.theme_combo.currentText()
        theme_value = "dark" if theme_name == "Sombre" else "light"
        config_manager.set("theme", theme_value)
        theme_manager.set_theme(theme_value)
        
        config_manager.set("export_format", self.format_combo.currentText())
        
        # Telechargement
        config_manager.set("max_concurrent_threads", self.threads_spin.value())
        config_manager.set("group_by_volume", self.group_vol_cb.isChecked())
        config_manager.set("chapters_per_volume", self.vol_spin.value())
        
        # Dossiers
        config_manager.set("download_dir", self.dir_input.text().strip())
        config_manager.set("auto_open_folder", self.auto_open_cb.isChecked())
        
        # 6 Sources
        config_manager.set("anime_sama_domain", self.as_domain_input.text().strip())
        config_manager.set("japscan_domain", self.js_domain_input.text().strip())
        config_manager.set("crunchyscan_domain", self.cs_domain_input.text().strip())
        config_manager.set("unekoscans_domain", self.un_domain_input.text().strip())
        config_manager.set("scan_vf_domain", self.sv_domain_input.text().strip())
        config_manager.set("mangadex_domain", self.md_domain_input.text().strip())

        self.log_signal.emit("SUCCESS", "Paramètres des 6 sources sauvegardés avec succès.")
        QMessageBox.information(self, "Paramètres enregistrés", "Vos paramètres et les domaines des 6 sources ont été enregistrés.")

