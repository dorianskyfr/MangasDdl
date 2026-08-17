import os
import zipfile
from pathlib import Path
from typing import List
from PIL import Image
import img2pdf

class Exporter:
    @staticmethod
    def export_cbz(images_dir: Path, output_cbz_path: Path, manga_title: str = "", chapter_number: str = "", volume_number: int = None):
        """
        Convertit un dossier d'images en archive CBZ (Comic Book Zip) avec métadonnées ComicInfo.xml.
        """
        try:
            image_files = sorted([
                f for f in images_dir.iterdir()
                if f.is_file() and f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp', '.avif')
            ])

            if not image_files:
                raise ValueError("Aucune image trouvée à exporter dans le dossier.")

            output_cbz_path.parent.mkdir(parents=True, exist_ok=True)

            # Génération du ComicInfo.xml pour compatibilité Tachiyomi / Mihon / YACReader
            comic_info_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<ComicInfo xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <Series>{manga_title or 'Manga'}</Series>
  <Number>{chapter_number or '1'}</Number>
  {f'<Volume>{volume_number}</Volume>' if volume_number else ''}
  <LanguageISO>fr</LanguageISO>
  <Format>Digital Scan</Format>
  <ScanInformation>Antigravity Manga Scraper v3.0</ScanInformation>
</ComicInfo>"""

            with zipfile.ZipFile(output_cbz_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Écrire ComicInfo.xml
                zipf.writestr("ComicInfo.xml", comic_info_xml.encode("utf-8"))
                for img_path in image_files:
                    zipf.write(img_path, arcname=img_path.name)
            return True
        except Exception as e:
            print(f"[Exporter] Erreur lors de la création du CBZ {output_cbz_path}: {e}")
            return False


    @staticmethod
    def export_pdf(images_dir: Path, output_pdf_path: Path):
        """
        Convertit un dossier d'images en document PDF unique.
        """
        try:
            image_files = sorted([
                f for f in images_dir.iterdir()
                if f.is_file() and f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp', '.avif')
            ])

            if not image_files:
                raise ValueError("Aucune image trouvée à exporter dans le dossier.")

            output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

            # Convertir les images webp ou formats non directement supportés en PNG/JPG temporaires si nécessaire
            converted_paths = []
            temp_files = []

            for img_path in image_files:
                if img_path.suffix.lower() in ('.webp', '.gif', '.avif'):
                    try:
                        im = Image.open(img_path).convert('RGB')
                        temp_png = img_path.with_suffix('.converted.jpg')
                        im.save(temp_png, 'JPEG', quality=95)
                        converted_paths.append(str(temp_png))
                        temp_files.append(temp_png)
                    except Exception:
                        converted_paths.append(str(img_path))
                else:
                    converted_paths.append(str(img_path))

            # Utilisation de img2pdf pour un PDF haute qualité
            with open(output_pdf_path, "wb") as f:
                f.write(img2pdf.convert(converted_paths))

            # Nettoyage des fichiers temporaires
            for temp_f in temp_files:
                if temp_f.exists():
                    temp_f.unlink()

            return True
        except Exception as e:
            print(f"[Exporter] Erreur lors de la création du PDF {output_pdf_path}: {e}")
            return False

    @staticmethod
    def stitch_webtoon_images(images_dir: Path, max_strip_height: int = 15000) -> bool:
        """
        Assemblage automatique vertical des découpes d'un Webtoon en bandes continues.
        """
        try:
            image_files = sorted([
                f for f in images_dir.iterdir()
                if f.is_file() and f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp', '.avif')
                and not f.name.startswith("c000_p000_cover")
            ])

            if len(image_files) <= 1:
                return False

            groups = {}
            for f in image_files:
                prefix = f.name.split("_p")[0] if "_p" in f.name else "strip"
                groups.setdefault(prefix, []).append(f)

            stitched_any = False
            for prefix, files in groups.items():
                if len(files) <= 1:
                    continue

                imgs = []
                target_w = 1000
                for img_p in files:
                    try:
                        im = Image.open(img_p).convert("RGB")
                        w, h = im.size
                        if w > 0 and h > 0:
                            nh = int(h * (target_w / float(w)))
                            imgs.append(im.resize((target_w, nh), Image.Resampling.LANCZOS))
                    except Exception as e:
                        print(f"[WebtoonStitch] Erreur image {img_p}: {e}")

                if not imgs:
                    continue

                strips = []
                curr_strip = []
                curr_h = 0

                for im in imgs:
                    if curr_strip and (curr_h + im.height > max_strip_height):
                        strips.append(curr_strip)
                        curr_strip = [im]
                        curr_h = im.height
                    else:
                        curr_strip.append(im)
                        curr_h += im.height

                if curr_strip:
                    strips.append(curr_strip)

                for s_idx, strip in enumerate(strips, 1):
                    s_height = sum(i.height for i in strip)
                    canvas = Image.new("RGB", (target_w, s_height), (255, 255, 255))
                    y = 0
                    for i in strip:
                        canvas.paste(i, (0, y))
                        y += i.height

                    out_name = f"{prefix}_webtoon_strip_{s_idx:02d}.jpg"
                    out_path = images_dir / out_name
                    canvas.save(out_path, "JPEG", quality=92)
                    stitched_any = True

                for orig_f in files:
                    try:
                        orig_f.unlink()
                    except Exception:
                        pass

            return stitched_any
        except Exception as e:
            print(f"[Exporter] Erreur assemblage vertical Webtoon: {e}")
            return False
