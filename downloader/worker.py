"""
Worker de téléchargement avec support des chapitres individuels et des Tomes (Volumes).
"""
import time
import os
import re
import traceback
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx
from PySide6.QtCore import QObject, Signal, QThread

from models import DownloadJob, DownloadStatus, Page, Chapter
from scrapers.factory import ScraperFactory
from downloader.exporter import Exporter
from downloader.volume_cover_provider import VolumeCoverProvider
from config import config_manager

DEBUG_LOG = Path(__file__).parent.parent / "download_debug.log"

def _dbg(msg: str):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


class DownloadWorkerSignals(QObject):
    job_started = Signal(str)
    job_progress = Signal(str, int, int, str)   # job_id, downloaded, total, speed
    job_completed = Signal(str, str)             # job_id, final_path
    job_failed = Signal(str, str)                # job_id, error_message
    log_message = Signal(str, str)               # level, text


class DownloadTask(QThread):
    def __init__(self, job: DownloadJob):
        super().__init__()
        self.job = job
        self.signals = DownloadWorkerSignals()
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        # Log file en mode append (ne pas effacer le fichier existant)

        self.job.status = DownloadStatus.DOWNLOADING
        self.signals.job_started.emit(self.job.job_id)

        is_vol = self.job.is_volume
        label_type = f"Tome {self.job.volume_number:02d} ({self.job.chapter_number})" if is_vol else f"Chap. {self.job.chapter_number}"

        _dbg(f"=== DÉBUT TÉLÉCHARGEMENT ===")
        _dbg(f"Manga: {self.job.manga_title!r}")
        _dbg(f"Type: {'Tome' if is_vol else 'Chapitre'}")
        _dbg(f"Libellé: {self.job.chapter_number!r}")
        _dbg(f"Source: {self.job.source!r}")
        _dbg(f"Format: {self.job.export_format!r}")

        self.signals.log_message.emit(
            "INFO",
            f"⬇ Démarrage : {self.job.manga_title} — {label_type}"
        )

        # ── Préparation du dossier ──────────────────────────────
        safe_manga = "".join(
            c for c in self.job.manga_title
            if c.isalnum() or c in (' ', '_', '-', '.')
        ).strip() or "Manga"

        if is_vol:
            folder_name = f"Tome_{self.job.volume_number:02d}"
        else:
            folder_name = f"Chapitre_{self.job.chapter_number}"

        base_dest = Path(config_manager.get("download_dir", str(Path.home() / "Downloads" / "MangaDownloader")))
        manga_dir = base_dest / safe_manga
        dest_dir = manga_dir / folder_name

        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            err = f"Impossible de créer le dossier : {e}"
            _dbg(f"ERREUR: {err}")
            self._fail(err)
            return

        try:
            scraper = ScraperFactory.get_scraper(self.job.source)
            max_threads = max(1, config_manager.get("max_concurrent_threads", 4))
            base_headers = {
                "User-Agent": config_manager.get("user_agent"),
                "Accept": "image/webp,image/avif,image/*,*/*;q=0.8",
            }

            # ── 1. Récupération des pages ─────────────────────────
            # Liste de tuples : (dest_filename, page_obj)
            tasks_to_download: list[tuple[str, Page]] = []

            if is_vol:
                # Regroupement de plusieurs chapitres
                chaps = self.job.chapters_list
                vol_num = self.job.volume_number
                _dbg(f"Téléchargement du Tome {vol_num} ({len(chaps)} chapitres)...")

                # Insérer la couverture officielle du Tome comme toute première page (Page 0)
                cover_url = VolumeCoverProvider.get_volume_cover_url(self.job.manga_title, vol_num)
                if cover_url:
                    _dbg(f"  Couverture officielle trouvée pour le Tome {vol_num}: {cover_url}")
                    tasks_to_download.append(("c000_p000_cover", Page(number=0, url=cover_url, referer=None)))

                def fetch_pages_safe(c_num, c_url):
                    try:
                        p_list = scraper.get_chapter_pages(c_url)
                        if p_list:
                            return p_list
                    except Exception:
                        pass
                    
                    _dbg(f"  ⚠️ Source {self.job.source} a renvoyé 0 page pour le chap {c_num}. Basculement automatique...")
                    self.signals.log_message.emit(
                        "WARNING",
                        f"⚠️ {self.job.source} bloqué sur chap {c_num}. Basculement automatique sur les autres sources..."
                    )
                    fallback_sources = ["Anime-Sama", "Crunchyscan", "Scan-VF", "MangaDex"]
                    for alt_src in fallback_sources:
                        if alt_src == self.job.source:
                            continue
                        try:
                            alt_scraper = ScraperFactory.get_scraper(alt_src)
                            search_res = alt_scraper.search(self.job.manga_title)
                            if search_res:
                                alt_chaps = alt_scraper.get_chapters(search_res[0].url)
                                matched = next((c for c in alt_chaps if str(c.number) == str(c_num)), None)
                                if matched:
                                    alt_pages = alt_scraper.get_chapter_pages(matched.url)
                                    if alt_pages:
                                        self.signals.log_message.emit(
                                            "SUCCESS",
                                            f"✅ Chapitre {c_num} : {len(alt_pages)} pages récupérées via {alt_src} !"
                                        )
                                        return alt_pages
                        except Exception as alt_err:
                            _dbg(f"  Erreur de basculement sur {alt_src}: {alt_err}")
                    return []

                for c_idx, chap in enumerate(chaps, 1):
                    pages = fetch_pages_safe(chap.number, chap.url)
                    _dbg(f"  Chapitre {chap.number}: {len(pages)} pages")
                    for p in pages:
                        fname = f"c{c_idx:03d}_p{p.number:03d}"
                        tasks_to_download.append((fname, p))
            else:
                # Chapitre individuel direct
                pages = fetch_pages_safe(self.job.chapter_number, self.job.chapter_url)
                _dbg(f"Pages trouvées: {len(pages)}")
                for p in pages:
                    fname = f"page_{p.number:03d}"
                    tasks_to_download.append((fname, p))

            if not tasks_to_download:
                raise ValueError("Aucune image trouvée pour ce téléchargement.")

            self.job.total_pages = len(tasks_to_download)
            self.job.downloaded_pages = 0

            self.signals.log_message.emit(
                "INFO",
                f"{self.job.total_pages} pages au total à télécharger..."
            )

            start_time = time.time()
            total_bytes = 0
            fail_count = 0

            def download_single_item(item: tuple[str, Page]) -> tuple[bool, int]:
                if self._is_cancelled:
                    return False, 0

                fname, page = item
                url_clean = page.url.split("?")[0]
                ext = url_clean.rsplit(".", 1)[-1].lower()
                if ext not in ("jpg", "jpeg", "png", "webp", "avif"):
                    ext = "jpg"

                file_path = dest_dir / f"{fname}.{ext}"

                if file_path.exists() and file_path.stat().st_size > 2048:
                    return True, file_path.stat().st_size

                headers = {
                    **base_headers,
                    "Referer": page.referer or self.job.chapter_url,
                }

                for attempt in range(4):
                    if self._is_cancelled:
                        return False, 0
                    try:
                        with httpx.Client(headers=headers, timeout=30.0, follow_redirects=True) as client:
                            resp = client.get(page.url)
                            if resp.status_code == 200 and len(resp.content) > 1024:
                                content = resp.content
                                # Watermark pour la couverture du tome
                                if fname == "c000_p000_cover" and is_vol:
                                    try:
                                        from PIL import Image, ImageDraw, ImageFont
                                        import io
                                        img = Image.open(io.BytesIO(content)).convert("RGBA")
                                        draw = ImageDraw.Draw(img)
                                        text = f"TOME {self.job.volume_number:02d}"
                                        
                                        try:
                                            font_size = max(40, img.width // 10)
                                            font = ImageFont.truetype("arialbd.ttf", font_size)
                                        except Exception:
                                            font = ImageFont.load_default()
                                            
                                        try:
                                            bbox = draw.textbbox((0,0), text, font=font)
                                            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                                        except AttributeError:
                                            tw, th = draw.textsize(text, font=font)
                                            
                                        margin = 20
                                        x = img.width - tw - margin
                                        y = margin
                                        
                                        pad = 10
                                        rect_shape = [x - pad, y - pad, x + tw + pad, y + th + pad]
                                        overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
                                        draw_ov = ImageDraw.Draw(overlay)
                                        draw_ov.rectangle(rect_shape, fill=(0, 0, 0, 200))
                                        img = Image.alpha_composite(img, overlay)
                                        
                                        draw = ImageDraw.Draw(img)
                                        draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
                                        
                                        img = img.convert("RGB")
                                        out_bytes = io.BytesIO()
                                        img.save(out_bytes, format="JPEG", quality=90)
                                        content = out_bytes.getvalue()
                                        ext = "jpg"
                                        file_path = dest_dir / f"{fname}.{ext}"
                                    except Exception as e:
                                        _dbg(f"Erreur watermark cover: {e}")
                                
                                file_path.write_bytes(content)
                                return True, len(content)
                            elif resp.status_code == 404:
                                return False, 0
                    except Exception:
                        pass
                    time.sleep(2 ** attempt)

                return False, 0

            # ── 2. Téléchargement multi-threadé ───────────────────
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                futures = {executor.submit(download_single_item, t): t for t in tasks_to_download}
                for future in as_completed(futures):
                    if self._is_cancelled:
                        break
                    try:
                        success, size = future.result()
                        if success:
                            total_bytes += size
                        else:
                            fail_count += 1
                        self.job.downloaded_pages += 1

                        elapsed = max(time.time() - start_time, 0.001)
                        speed_kbs = (total_bytes / 1024) / elapsed
                        speed_str = (f"{speed_kbs/1024:.2f} Mo/s" if speed_kbs >= 1024
                                     else f"{speed_kbs:.0f} Ko/s")
                        self.job.speed = speed_str
                        self.job.progress = (self.job.downloaded_pages / self.job.total_pages) * 100

                        self.signals.job_progress.emit(
                            self.job.job_id,
                            self.job.downloaded_pages,
                            self.job.total_pages,
                            speed_str,
                        )
                    except Exception as e:
                        fail_count += 1
                        self.job.downloaded_pages += 1

            if self._is_cancelled:
                self.job.status = DownloadStatus.FAILED
                self.job.error_message = "Annulé"
                self.signals.job_failed.emit(self.job.job_id, "Téléchargement annulé.")
                return

            valid_images = (
                list(dest_dir.glob("*.jpg")) + list(dest_dir.glob("*.jpeg")) +
                list(dest_dir.glob("*.png")) + list(dest_dir.glob("*.webp")) +
                list(dest_dir.glob("*.avif"))
            )

            if not valid_images:
                raise ValueError(f"Aucune image valide téléchargée ({fail_count} échecs).")

            # ── 2.5. Assemblage Vertical Webtoon (Uniquement si Webtoon/Manhwa) ──
            is_webtoon = any(w in self.job.manga_title.lower() for w in [
                "tbate", "begining", "beginning", "solo leveling", "tower of god",
                "god of high school", "omniscient", "webtoon", "manhwa", "magic emperor",
                "tomb raider", "nano machine", "mercenary enrollment", "eleceed",
                "second life ranker", "overgeared", "return of the mount hua"
            ]) or config_manager.get("stitch_all_as_webtoon", False)

            if is_webtoon:
                _dbg("Assemblage des bandes verticales Webtoon...")
                self.signals.log_message.emit("INFO", "📜 Assemblage des bandes verticales Webtoon...")
                Exporter.stitch_webtoon_images(dest_dir)

            # ── 3. Exportation ─────────────────────────────────────
            fmt = self.job.export_format or config_manager.get("export_format", "CBZ")
            final_output_path = str(dest_dir)

            if is_vol:
                out_name = f"{safe_manga} - Tome {self.job.volume_number:02d} ({self.job.chapter_number})"
            else:
                out_name = f"{safe_manga} - Chapitre_{self.job.chapter_number}"

            import shutil

            if fmt == "CBZ":
                cbz_path = manga_dir / f"{out_name}.cbz"
                if Exporter.export_cbz(
                    dest_dir,
                    cbz_path,
                    manga_title=self.job.manga_title,
                    chapter_number=str(self.job.chapter_number),
                    volume_number=self.job.volume_number if is_vol else None
                ):
                    final_output_path = str(cbz_path)

                    try:
                        shutil.rmtree(dest_dir)
                    except Exception as e:
                        _dbg(f"Erreur nettoyage dossier images: {e}")
            elif fmt == "PDF":
                pdf_path = manga_dir / f"{out_name}.pdf"
                if Exporter.export_pdf(dest_dir, pdf_path):
                    final_output_path = str(pdf_path)
                    try:
                        shutil.rmtree(dest_dir)
                    except Exception as e:
                        _dbg(f"Erreur nettoyage dossier images: {e}")

            self.job.status = DownloadStatus.COMPLETED
            self.job.progress = 100.0
            self.job.save_path = final_output_path
            self.signals.job_completed.emit(self.job.job_id, final_output_path)
            self.signals.log_message.emit(
                "SUCCESS",
                f"✅ Terminé : {self.job.manga_title} — {label_type} ({len(valid_images)} pages)"
            )
            _dbg(f"=== SUCCÈS : {final_output_path} ===")

        except Exception as e:
            tb = traceback.format_exc()
            _dbg(f"EXCEPTION FATALE: {type(e).__name__}: {e}\n{tb}")
            self._fail(str(e))

    def _fail(self, msg: str):
        self.job.status = DownloadStatus.FAILED
        self.job.error_message = msg
        self.signals.job_failed.emit(self.job.job_id, msg)
        self.signals.log_message.emit(
            "ERROR",
            f"❌ Échec : {self.job.manga_title} — {msg}"
        )
        _dbg(f"=== ÉCHEC : {msg} ===")
