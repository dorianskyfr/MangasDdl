# 📚 MangasDdl — Téléchargeur & Lecteur de Mangas / Webtoons

Application de bureau moderne et complète en **Python / PySide6 (Qt6)** pour rechercher, lire et télécharger des chapitres et des tomes complets de mangas et webtoons en haute résolution depuis plusieurs sources francophones et internationales.

---

## ✨ Fonctionnalités Principales

- 🔍 **Multi-Sources Intégrées** :
  - **Anime-Sama** (Catalogue complet, haute vitesse)
  - **SushiScan / CrunchyScan**
  - **JapScan**
  - **Scan-VF**
  - **MangaDex** (API officielle)
- 🛡️ **Basculement Automatique (Fallback)** : Si une source est bloquée par Cloudflare ou rencontre une erreur, l'application bascule automatiquement et de façon transparente vers une autre source pour télécharger les pages.
- 📦 **Regroupement en Tomes Officiels** :
  - Détection et regroupement automatique des chapitres en tomes officiels via **AniList**, **Kitsu** et **MangaDex**.
  - Récupération des couvertures officielles en HD.
  - Incrustation automatique du libellé **TOME XX** en haut de couverture pour une identification instantanée sur liseuse (Kobo, Kindle).
- 📜 **Mode Webtoon Intelligent** :
  - Détection automatique des manhwas / webtoons (*TBATE, Solo Leveling, Tower of God, etc.*).
  - Assemblage (*stitching*) vertical sans perte jusqu'à 15 000 px pour une fluidité parfaite sur liseuse et lecteur d'images.
- 📖 **Visionneuse Intégrée (Reader)** :
  - Lecture page par page ou défilement continu vertical Webtoon.
  - Mise en cache et préchargement fluide.
- 💾 **Formats d'Export Multiples** :
  - **CBZ** (Idéal pour liseuses et Comic Readers)
  - **PDF**
  - **EPUB**
  - **Dossier d'Images**
- ⭐ **Gestion des Favoris & Bibliothèque** : Suivez vos lectures et retrouvez vos mangas préférés en un clic.
- ⚡ **Téléchargement Multi-threadé** : Téléchargement rapide et parallèle avec gestion des reprises et des timeouts.

---

## 🚀 Installation & Lancement

### Prérequis
- **Python 3.10+** (Recommandé : Python 3.11 à 3.14)
- **Git**

### 1. Cloner le dépôt
```bash
git clone https://github.com/dorianskyfr/MangasDdl.git
cd MangasDdl
```

### 2. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 3. Lancer l'application
Double-cliquez sur `Lancer_App.bat` ou lancez en ligne de commande :
```bash
python main.py
```

---

## 🛠️ Architecture du Projet

```text
├── downloader/             # Moteur de téléchargement, export (CBZ/PDF), stitching & covers
│   ├── exporter.py         # Création CBZ, PDF, EPUB, stitching Webtoon
│   ├── mangadex_volume.py  # Mapping des chapitres par tomes officiels (AniList/Kitsu)
│   ├── volume_cover_provider.py # Récupération des covers HD & fallbacks
│   └── worker.py           # Worker de téléchargement multi-threadé & basculement
├── scrapers/               # Scrapers par site avec gestion des formats
│   ├── anime_sama.py
│   ├── crunchyscan.py
│   ├── japscan.py
│   ├── mangadex.py
│   ├── scan_vf.py
│   ├── unekoscans.py
│   └── factory.py          # Fabrique de scrapers
├── ui/                     # Interface graphique PySide6 (Qt6)
│   ├── main_window.py      # Fenêtre principale & navigation
│   ├── theme.py            # Thème Dark Moderne & styles QSS
│   ├── views/              # Vues (Recherche, Téléchargements, Bibliothèque, Paramètres)
│   └── widgets/            # Lecteur intégré, visionneuse de logs, notifications
├── config.py               # Gestionnaire de configuration (JSON)
├── favorites.py            # Gestionnaire des favoris
├── models.py               # Modèles de données (Manga, Chapter, Page, DownloadJob)
└── main.py                 # Point d'entrée de l'application
```

---

## 📄 Licence
Projet distribué sous licence MIT.
