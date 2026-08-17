"""
Vue de gestion des téléchargements.
Bug fixes majeurs :
- get_row_by_job_id : utilise maintenant un dictionnaire job_id -> row (fiable)
- Navigation vers le bon dossier / fichier CBZ/PDF à la fin
- Statut coloré selon l'état
- Compteur de téléchargements actifs dans le titre
"""
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QProgressBar, QPushButton, QHeaderView,
    QFrame, QMessageBox, QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QDesktopServices, QColor, QBrush

from models import DownloadJob, DownloadStatus
from downloader.worker import DownloadTask


class DownloadsView(QWidget):
    log_signal = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.download_tasks: dict[str, DownloadTask] = {}
        self.jobs: dict[str, DownloadJob] = {}
        # Mapping job_id -> numéro de ligne du tableau (stable)
        self._row_map: dict[str, int] = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header_card = QFrame()
        header_card.setObjectName("Card")
        header_layout = QHBoxLayout(header_card)

        self.title_label = QLabel("Gestionnaire de Téléchargements")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        self.clear_btn = QPushButton("Nettoyer terminés")
        self.clear_btn.setObjectName("SecondaryButton")
        self.clear_btn.clicked.connect(self.clear_completed)
        header_layout.addWidget(self.clear_btn)

        self.cancel_all_btn = QPushButton("Tout annuler")
        self.cancel_all_btn.setObjectName("SecondaryButton")
        self.cancel_all_btn.clicked.connect(self.cancel_all)
        header_layout.addWidget(self.cancel_all_btn)

        layout.addWidget(header_card)

        # Tableau
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Manga", "Chap.", "Source", "Progression", "Vitesse", "Statut", "Actions"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("alternate-background-color: #1a1d2b;")

        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.Stretch)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(6, QHeaderView.Fixed)
        self.table.setColumnWidth(6, 185)
        self.table.setRowHeight(0, 40)
        layout.addWidget(self.table)

    # ─────────────────────────────────────────────────────
    # Ajout de tâches
    # ─────────────────────────────────────────────────────
    def add_jobs(self, jobs: list):
        for job in jobs:
            if job.job_id in self.jobs:
                continue

            self.jobs[job.job_id] = job
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setRowHeight(row, 40)
            # Mémoriser le row index par job_id (stable)
            self._row_map[job.job_id] = row

            self.table.setItem(row, 0, QTableWidgetItem(job.manga_title))
            chap_lbl = f"Tome {job.volume_number:02d} ({job.chapter_number})" if job.is_volume else f"Chap. {job.chapter_number}"
            self.table.setItem(row, 1, QTableWidgetItem(chap_lbl))
            self.table.setItem(row, 2, QTableWidgetItem(job.source))

            pbar = QProgressBar()
            pbar.setRange(0, 100)
            pbar.setValue(0)
            pbar.setTextVisible(True)
            pbar.setFormat("%p%")
            self.table.setCellWidget(row, 3, pbar)

            self.table.setItem(row, 4, QTableWidgetItem("—"))
            self.table.setItem(row, 5, QTableWidgetItem("En attente"))

            # Boutons Actions
            action_w = QWidget()
            action_l = QHBoxLayout(action_w)
            action_l.setContentsMargins(4, 2, 4, 2)
            action_l.setSpacing(6)
            action_l.setAlignment(Qt.AlignCenter)

            cancel_btn = QPushButton("✕ Annuler")
            cancel_btn.setObjectName("SecondaryButton")
            cancel_btn.setStyleSheet("padding: 3px 8px; font-size: 11px; min-width: 70px;")
            cancel_btn.clicked.connect(lambda _, jid=job.job_id: self.cancel_job(jid))
            action_l.addWidget(cancel_btn)

            open_btn = QPushButton("📂 Ouvrir")
            open_btn.setEnabled(False)
            open_btn.setStyleSheet("padding: 3px 8px; font-size: 11px; min-width: 70px;")
            open_btn.clicked.connect(lambda _, jid=job.job_id: self.open_job_folder(jid))
            action_l.addWidget(open_btn)

            self.table.setCellWidget(row, 6, action_w)

            # Lancer le worker
            task = DownloadTask(job)
            task.signals.job_started.connect(self.on_job_started)
            task.signals.job_progress.connect(self.on_job_progress)
            task.signals.job_completed.connect(self.on_job_completed)
            task.signals.job_failed.connect(self.on_job_failed)
            task.signals.log_message.connect(self.log_signal.emit)
            self.download_tasks[job.job_id] = task
            task.start()

        self._update_title()

    # ─────────────────────────────────────────────────────
    # Callbacks signaux (thread-safe grâce aux signaux Qt)
    # ─────────────────────────────────────────────────────
    def _get_row(self, job_id: str) -> int:
        """Retourne le row index stable depuis le dictionnaire (O(1))."""
        return self._row_map.get(job_id, -1)

    def _set_status(self, row: int, text: str, color: str = "#cbd5e1"):
        item = self.table.item(row, 5)
        if item:
            item.setText(text)
            item.setForeground(QBrush(QColor(color)))

    def on_job_started(self, job_id: str):
        row = self._get_row(job_id)
        if row >= 0:
            self._set_status(row, "⬇ Téléchargement…", "#38bdf8")

    def on_job_progress(self, job_id: str, downloaded: int, total: int, speed: str):
        row = self._get_row(job_id)
        if row < 0:
            return
        pbar = self.table.cellWidget(row, 3)
        if pbar and total > 0:
            pbar.setValue(int(downloaded / total * 100))
        spd_item = self.table.item(row, 4)
        if spd_item:
            spd_item.setText(speed)
        self._set_status(row, f"{downloaded}/{total} pages", "#38bdf8")

    def on_job_completed(self, job_id: str, final_path: str):
        job = self.jobs.get(job_id)
        if job:
            job.save_path = final_path
        row = self._get_row(job_id)
        if row < 0:
            return
        pbar = self.table.cellWidget(row, 3)
        if pbar:
            pbar.setValue(100)
        spd_item = self.table.item(row, 4)
        if spd_item:
            spd_item.setText("—")
        self._set_status(row, "✅ Terminé", "#4ade80")
        # Activer bouton "Ouvrir", désactiver "Annuler"
        action_w = self.table.cellWidget(row, 6)
        if action_w:
            btns = action_w.findChildren(QPushButton)
            if len(btns) >= 2:
                btns[0].setEnabled(False)
                btns[1].setEnabled(True)
        self._update_title()

    def on_job_failed(self, job_id: str, error: str):
        row = self._get_row(job_id)
        if row >= 0:
            spd_item = self.table.item(row, 4)
            if spd_item:
                spd_item.setText("—")
            self._set_status(row, "❌ Échec", "#f87171")
            action_w = self.table.cellWidget(row, 6)
            if action_w:
                btns = action_w.findChildren(QPushButton)
                if btns:
                    try:
                        btns[0].disconnect()
                    except Exception:
                        pass
                    btns[0].setText("🔄 Relancer")
                    btns[0].setEnabled(True)
                    btns[0].clicked.connect(lambda _, jid=job_id: self.retry_job(jid))
        self._update_title()

    def retry_job(self, job_id: str):
        job = self.jobs.get(job_id)
        if not job:
            return
        row = self._get_row(job_id)
        if row >= 0:
            self._set_status(row, "En attente", "#94a3b8")
            action_w = self.table.cellWidget(row, 6)
            if action_w:
                btns = action_w.findChildren(QPushButton)
                if btns:
                    try:
                        btns[0].disconnect()
                    except Exception:
                        pass
                    btns[0].setText("✕ Annuler")
                    btns[0].setEnabled(True)
                    btns[0].clicked.connect(lambda _, jid=job_id: self.cancel_job(jid))

        task = DownloadTask(job)
        task.signals.job_started.connect(self.on_job_started)
        task.signals.job_progress.connect(self.on_job_progress)
        task.signals.job_completed.connect(self.on_job_completed)
        task.signals.job_failed.connect(self.on_job_failed)
        task.signals.log_message.connect(self.log_signal.emit)
        self.download_tasks[job.job_id] = task
        task.start()


    # ─────────────────────────────────────────────────────
    # Actions
    # ─────────────────────────────────────────────────────
    def cancel_job(self, job_id: str):
        task = self.download_tasks.get(job_id)
        if task and task.isRunning():
            task.cancel()
        row = self._get_row(job_id)
        if row >= 0:
            self._set_status(row, "⏹ Annulé", "#fbbf24")

    def cancel_all(self):
        for task in self.download_tasks.values():
            if task.isRunning():
                task.cancel()

    def clear_completed(self):
        to_remove = []
        for job_id, row in sorted(self._row_map.items(), key=lambda x: x[1], reverse=True):
            status = self.table.item(row, 5)
            if status and any(
                kw in status.text() for kw in ("Terminé", "Échec", "Annulé")
            ):
                to_remove.append((job_id, row))

        for job_id, row in to_remove:
            self.table.removeRow(row)
            self._row_map.pop(job_id, None)
            self.jobs.pop(job_id, None)
            self.download_tasks.pop(job_id, None)

        # Reconstruire le mapping row après suppression
        self._row_map = {}
        for r in range(self.table.rowCount()):
            chap_item = self.table.item(r, 1)
            manga_item = self.table.item(r, 0)
            if not chap_item or not manga_item:
                continue
            chap_text = chap_item.text()
            manga_text = manga_item.text()
            for jid, job in self.jobs.items():
                if jid not in self._row_map:
                    job_lbl = (
                        f"Tome {job.volume_number:02d} ({job.chapter_number})"
                        if job.is_volume
                        else f"Chap. {job.chapter_number}"
                    )
                    if manga_text == job.manga_title and chap_text == job_lbl:
                        self._row_map[jid] = r
                        break

        self._update_title()

    def open_job_folder(self, job_id: str):
        job = self.jobs.get(job_id)
        if not job or not job.save_path:
            return
        path = Path(job.save_path)
        folder = path.parent if path.is_file() else path
        if folder.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
        else:
            QMessageBox.warning(self, "Dossier introuvable", str(folder))

    def _update_title(self):
        active = sum(1 for t in self.download_tasks.values() if t.isRunning())
        self.title_label.setText(
            f"Gestionnaire de Téléchargements"
            + (f"  ({active} en cours)" if active else "")
        )
