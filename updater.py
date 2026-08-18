"""
Module de recherche de mise à jour & affichage des notes de version (Patch Notes)
depuis le dépôt GitHub officiel dorianskyfr/MangasDdl.
"""
import re
import httpx
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextBrowser, QFrame, QWidget
)
from PySide6.QtGui import QFont, QDesktopServices
from PySide6.QtCore import QUrl

APP_VERSION = "0.1"
GITHUB_REPO = "dorianskyfr/MangasDdl"
RELEASES_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
ALL_RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases"


def _parse_version(v_str: str) -> tuple:
    """Transforme 'v0.1' ou '0.1.2' en tuple d'entiers pour comparaison (0, 1, 2)."""
    clean = re.sub(r'^[vV]', '', v_str.strip())
    parts = []
    for p in clean.split('.'):
        if p.isdigit():
            parts.append(int(p))
        else:
            num = re.findall(r'\d+', p)
            parts.append(int(num[0]) if num else 0)
    return tuple(parts)


def markdown_to_html(md: str) -> str:
    """Convertit un Markdown GitHub basique en HTML stylisé avec CSS moderne."""
    if not md:
        return "<p>Aucune note de version spécifiée.</p>"

    html = md
    # Titres
    html = re.sub(r'^### (.*?)$', r'<h4 style="color: #38bdf8; margin: 12px 0 6px 0;">\1</h4>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*?)$', r'<h3 style="color: #60a5fa; margin: 16px 0 8px 0; border-bottom: 1px solid #334155; padding-bottom: 4px;">\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.*?)$', r'<h2 style="color: #93c5fd; margin: 18px 0 10px 0;">\1</h2>', html, flags=re.MULTILINE)

    # Gras & Italique
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong style="color: #f8fafc;">\1</strong>', html)
    html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)

    # Listes à puces
    html = re.sub(r'^\s*[-*]\s+(.*?)$', r'<li style="margin-bottom: 4px; color: #cbd5e1;">\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'(<li.*?>.*?</li>)+', r'<ul style="margin: 6px 0; padding-left: 20px;">\g<0></ul>', html, flags=re.DOTALL)

    # Emojis & Badges
    html = html.replace("✅", '<span style="color: #4ade80;">✅</span>')
    html = html.replace("🚀", '<span style="color: #38bdf8;">🚀</span>')
    html = html.replace("🛠️", '<span style="color: #f59e0b;">🛠️</span>')
    html = html.replace("🏁", '<span style="color: #4ade80;">🏁</span>')

    # Retours à la ligne
    html = html.replace("\n\n", "<br/>")

    return f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; line-height: 1.6; color: #cbd5e1;">
        {html}
    </div>
    """


class UpdateCheckWorker(QThread):
    """Vérifie les mises à jour en arrière-plan au démarrage."""
    update_result = Signal(bool, str, str, str, str)  # is_newer, latest_ver, release_title, html_notes, download_url
    check_failed = Signal(str)

    def __init__(self, manual: bool = False):
        super().__init__()
        self.manual = manual

    def run(self):
        headers = {
            "User-Agent": "MangasDdl-App",
            "Accept": "application/vnd.github.v3+json"
        }
        try:
            with httpx.Client(headers=headers, timeout=6.0, follow_redirects=True) as client:
                r = client.get(RELEASES_API_URL)
                if r.status_code == 200:
                    data = r.json()
                    tag_name = data.get("tag_name", "0.1")
                    clean_tag = re.sub(r'^[vV]', '', tag_name)
                    release_title = data.get("name") or f"Version {clean_tag}"
                    body = data.get("body", "")
                    html_url = data.get("html_url", f"https://github.com/{GITHUB_REPO}/releases")

                    cur_v = _parse_version(APP_VERSION)
                    lat_v = _parse_version(clean_tag)
                    is_newer = (lat_v > cur_v)

                    html_notes = markdown_to_html(body)
                    self.update_result.emit(is_newer, clean_tag, release_title, html_notes, html_url)
                elif r.status_code == 404:
                    # Pas encore de release GitHub en ligne
                    if self.manual:
                        self.update_result.emit(
                            False, APP_VERSION, f"MangasDdl v{APP_VERSION} (À jour)", 
                            "<p>Vous utilisez la dernière version disponible (v0.1) !</p>", 
                            f"https://github.com/{GITHUB_REPO}"
                        )
                else:
                    if self.manual:
                        self.check_failed.emit(f"Erreur GitHub (HTTP {r.status_code})")
        except Exception as e:
            if self.manual:
                self.check_failed.emit(f"Impossible de vérifier les mises à jour: {e}")


class PatchNotesDialog(QDialog):
    """Dialogue élégant affichant les notes de version et propositions de mise à jour."""

    def __init__(self, version: str, title: str, html_notes: str, url: str, is_update: bool = False, parent=None):
        super().__init__(parent)
        self.download_url = url
        self.setWindowTitle(f"Notes de Version — MangasDdl v{version}")
        self.resize(620, 520)
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #1e293b;
                border-radius: 12px;
            }
            QTextBrowser {
                background-color: #0b0f19;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 14px;
                color: #cbd5e1;
            }
            QPushButton {
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header card
        header = QFrame()
        header.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1e293b, stop:1 #0f172a); border-radius: 8px; padding: 10px;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(12, 10, 12, 10)

        icon_label = QLabel("🚀" if is_update else "📋")
        icon_label.setStyleSheet("font-size: 28px;")
        h_layout.addWidget(icon_label)

        title_vbox = QVBoxLayout()
        h_title = QLabel(f"Nouvelle version disponible : v{version}" if is_update else title)
        h_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
        h_sub = QLabel(f"Version actuelle installée : v{APP_VERSION}  ·  Dernière version : v{version}")
        h_sub.setStyleSheet("font-size: 12px; color: #94a3b8;")
        title_vbox.addWidget(h_title)
        title_vbox.addWidget(h_sub)
        h_layout.addLayout(title_vbox)
        h_layout.addStretch()

        badge = QLabel("NOUVEAU" if is_update else "ACTUEL")
        badge.setStyleSheet(
            "background-color: #0284c7; color: white; border-radius: 10px; padding: 4px 10px; font-size: 11px; font-weight: bold;"
            if is_update else
            "background-color: #334155; color: #94a3b8; border-radius: 10px; padding: 4px 10px; font-size: 11px; font-weight: bold;"
        )
        h_layout.addWidget(badge)
        layout.addWidget(header)

        # Notes de version (TextBrowser)
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setHtml(html_notes)
        layout.addWidget(self.browser)

        # Footer boutons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        gh_btn = QPushButton("🌐 Voir sur GitHub")
        gh_btn.setStyleSheet("background-color: #1e293b; color: #94a3b8; border: 1px solid #334155;")
        gh_btn.clicked.connect(self._open_github)
        btn_layout.addWidget(gh_btn)

        btn_layout.addStretch()

        if is_update:
            dl_btn = QPushButton("⬇️ Télécharger la mise à jour")
            dl_btn.setStyleSheet("background-color: #0284c7; color: white; border: none;")
            dl_btn.clicked.connect(self._open_download)
            btn_layout.addWidget(dl_btn)

        close_btn = QPushButton("Fermer")
        close_btn.setStyleSheet("background-color: #334155; color: #f8fafc; border: none;")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _open_github(self):
        QDesktopServices.openUrl(QUrl(self.download_url))

    def _open_download(self):
        QDesktopServices.openUrl(QUrl(self.download_url))
        self.accept()
