from __future__ import annotations
import os
import zipfile
import io
import re
from pathlib import Path
from typing import List, Optional
from PIL import Image
import img2pdf


def _natural_sort_key(s: Path):
    """Tri naturel pour que 'page_2' vienne avant 'page_10'."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s.name)]


class Exporter:
    @staticmethod
    def export_cbz(
        images_dir: Path,
        output_cbz_path: Path,
        manga_title: str = "",
        chapter_number: str = "",
        volume_number: Optional[int] = None
    ) -> bool:
        """
        Convertit un dossier d'images en archive CBZ (Comic Book Zip) avec métadonnées ComicInfo.xml standard.
        """
        try:
            image_files = sorted([
                f for f in images_dir.iterdir()
                if f.is_file() and f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp', '.avif')
            ], key=_natural_sort_key)

            if not image_files:
                raise ValueError("Aucune image trouvée à exporter dans le dossier.")

            output_cbz_path.parent.mkdir(parents=True, exist_ok=True)

            # Métadonnées ComicInfo.xml pour compatibilité YACReader, Mihon, Chunky, Perfect Viewer
            title_clean = manga_title.strip() or 'Manga'
            chap_clean = str(chapter_number).strip() or '1'
            vol_tag = f"<Volume>{volume_number}</Volume>" if volume_number is not None else ""

            comic_info_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<ComicInfo xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <Series>{title_clean}</Series>
  <Number>{chap_clean}</Number>
  {vol_tag}
  <LanguageISO>fr</LanguageISO>
  <Format>Digital</Format>
  <ScanInformation>MangasDdl v3.0 Pro</ScanInformation>
  <PageCount>{len(image_files)}</PageCount>
</ComicInfo>"""

            with zipfile.ZipFile(output_cbz_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.writestr("ComicInfo.xml", comic_info_xml.encode("utf-8"))
                for img_path in image_files:
                    zipf.write(img_path, arcname=img_path.name)
            return True
        except Exception as e:
            print(f"[Exporter] Erreur lors de la création du CBZ {output_cbz_path}: {e}")
            return False

    @staticmethod
    def export_pdf(images_dir: Path, output_pdf_path: Path) -> bool:
        """
        Convertit un dossier d'images en document PDF unique et optimisé.
        """
        try:
            image_files = sorted([
                f for f in images_dir.iterdir()
                if f.is_file() and f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp', '.avif')
            ], key=_natural_sort_key)

            if not image_files:
                raise ValueError("Aucune image trouvée à exporter dans le dossier.")

            output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

            converted_paths = []
            temp_files = []

            for img_path in image_files:
                if img_path.suffix.lower() in ('.webp', '.gif', '.avif', '.png'):
                    try:
                        with Image.open(img_path) as im:
                            rgb_im = im.convert('RGB')
                            temp_jpg = img_path.with_suffix('.pdf_temp.jpg')
                            rgb_im.save(temp_jpg, 'JPEG', quality=95)
                            converted_paths.append(str(temp_jpg))
                            temp_files.append(temp_jpg)
                    except Exception:
                        converted_paths.append(str(img_path))
                else:
                    converted_paths.append(str(img_path))

            try:
                with open(output_pdf_path, "wb") as f:
                    f.write(img2pdf.convert(converted_paths))
            except Exception as pdf_err:
                # Fallback PIL direct si img2pdf échoue
                print(f"[Exporter] img2pdf échoué ({pdf_err}), bascule sur PIL...")
                pil_imgs = []
                for p in converted_paths:
                    try:
                        im = Image.open(p).convert('RGB')
                        pil_imgs.append(im)
                    except Exception:
                        pass
                if pil_imgs:
                    pil_imgs[0].save(output_pdf_path, save_all=True, append_images=pil_imgs[1:], resolution=100.0, quality=92)
                    for im in pil_imgs:
                        im.close()

            # Nettoyage sécurisé des fichiers temporaires
            for temp_f in temp_files:
                try:
                    if temp_f.exists():
                        temp_f.unlink()
                except Exception:
                    pass

            return True
        except Exception as e:
            print(f"[Exporter] Erreur lors de la création du PDF {output_pdf_path}: {e}")
            return False

    @staticmethod
    def export_epub(
        images_dir: Path,
        output_epub_path: Path,
        manga_title: str = "",
        chapter_number: str = "",
        volume_number: Optional[int] = None
    ) -> bool:
        """
        Convertit un dossier d'images en livre EPUB 3 au format standard Manga/Comics (Compatible Kobo, Apple Books, Calibre).
        """
        try:
            image_files = sorted([
                f for f in images_dir.iterdir()
                if f.is_file() and f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp', '.avif')
            ], key=_natural_sort_key)

            if not image_files:
                return False

            output_epub_path.parent.mkdir(parents=True, exist_ok=True)
            title = f"{manga_title} - Tome {volume_number}" if volume_number else f"{manga_title} - Chapitre {chapter_number}"

            with zipfile.ZipFile(output_epub_path, 'w', zipfile.ZIP_DEFLATED) as epub:
                # mimetype (doit être non compressé en premier)
                epub.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)

                # container.xml
                container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""
                epub.writestr("META-INF/container.xml", container_xml)

                manifest_items = []
                spine_items = []

                for idx, img_p in enumerate(image_files, 1):
                    ext = img_p.suffix.lower().replace('.', '')
                    mime = "image/jpeg" if ext in ('jpg', 'jpeg') else f"image/{ext}"
                    img_id = f"img_{idx:04d}"
                    page_id = f"page_{idx:04d}"

                    epub.write(img_p, f"OEBPS/images/{img_p.name}")
                    manifest_items.append(f'<item id="{img_id}" href="images/{img_p.name}" media-type="{mime}"/>')
                    manifest_items.append(f'<item id="{page_id}" href="{page_id}.xhtml" media-type="application/xhtml+xml"/>')
                    spine_items.append(f'<itemref idref="{page_id}"/>')

                    xhtml_content = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>{title} - Page {idx}</title>
  <style type="text/css">
    @page {{ margin: 0; padding: 0; }}
    body {{ margin: 0; padding: 0; background-color: #000000; text-align: center; }}
    img {{ max-width: 100%; max-height: 100vh; height: auto; object-fit: contain; }}
  </style>
</head>
<body>
  <div><img src="images/{img_p.name}" alt="Page {idx}"/></div>
</body>
</html>"""
                    epub.writestr(f"OEBPS/{page_id}.xhtml", xhtml_content)

                content_opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="pub-id">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="pub-id">urn:uuid:mangasddl-{abs(hash(title))}</dc:identifier>
    <dc:title>{title}</dc:title>
    <dc:language>fr</dc:language>
    <meta property="rendition:layout">pre-paginated</meta>
    <meta property="rendition:orientation">auto</meta>
    <meta property="rendition:spread">none</meta>
  </metadata>
  <manifest>
    {chr(10).join(manifest_items)}
  </manifest>
  <spine>
    {chr(10).join(spine_items)}
  </spine>
</package>"""
                epub.writestr("OEBPS/content.opf", content_opf)

            return True
        except Exception as e:
            print(f"[Exporter] Erreur création EPUB {output_epub_path}: {e}")
            return False

    @staticmethod
    def stitch_webtoon_images(images_dir: Path, max_strip_height: int = 15000) -> bool:
        """
        Assemblage automatique vertical des découpes d'un Webtoon en bandes continues HD.
        Préserve la résolution native sans perte de netteté.
        """
        try:
            image_files = sorted([
                f for f in images_dir.iterdir()
                if f.is_file() and f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp', '.avif')
                and not f.name.startswith("c000_p000_cover")
            ], key=_natural_sort_key)

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

                opened_imgs = []
                widths = []
                for img_p in files:
                    try:
                        im = Image.open(img_p).convert("RGB")
                        opened_imgs.append((img_p, im))
                        widths.append(im.width)
                    except Exception as e:
                        print(f"[WebtoonStitch] Erreur ouverture {img_p}: {e}")

                if not opened_imgs:
                    continue

                # Déterminer la largeur cible optimale (médiane ou max raisonnable)
                target_w = max(widths) if widths else 1080
                target_w = min(max(target_w, 800), 2160)

                resized_imgs = []
                for img_p, im in opened_imgs:
                    w, h = im.size
                    if w != target_w:
                        nh = int(h * (target_w / float(w)))
                        res_im = im.resize((target_w, nh), Image.Resampling.LANCZOS)
                        im.close()
                        resized_imgs.append(res_im)
                    else:
                        resized_imgs.append(im)

                strips = []
                curr_strip = []
                curr_h = 0

                for im in resized_imgs:
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
                        i.close()

                    out_name = f"{prefix}_webtoon_strip_{s_idx:03d}.jpg"
                    out_path = images_dir / out_name
                    canvas.save(out_path, "JPEG", quality=94, optimize=True)
                    canvas.close()
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
