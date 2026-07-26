#!/usr/bin/env python3
"""
Convertit les photos brutes de `pictures/<categorie>/` en WebP optimises pour le web.

Pour chaque photo source, deux fichiers sont produits :
  - images/thumb/<categorie>/<id>.webp  (grille, cote long 800px)
  - images/full/<categorie>/<id>.webp   (lightbox, cote long 1800px)

Points importants :
  - La rotation EXIF est appliquee aux pixels (les navigateurs n'appliquent pas
    l'orientation EXIF de maniere fiable sur les WebP).
  - Toutes les metadonnees EXIF sont supprimees, y compris les coordonnees GPS.
    Les photos publiees ne revelent donc pas l'adresse ou elles ont ete prises.
  - Les fichiers deja convertis sont ignores, sauf avec --force.

Usage :
    source ~/.pyenv/versions/.venv/bin/activate  # indispensable : Pillow n'est
                                                 # installe que dans ce venv
    python3 tools/build_images.py
    python3 tools/build_images.py --force        # tout reconvertir
    python3 tools/build_images.py --clean        # supprimer les WebP orphelins

Prerequis : macOS (pour `sips`, qui decode le HEIC) et Pillow.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    sys.exit(
        "Pillow est introuvable. L'environnement virtuel n'est probablement pas actif :\n"
        "    source ~/.pyenv/versions/.venv/bin/activate\n"
        "puis relancer cette commande. Si Pillow y manque aussi : pip install Pillow"
    )

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / "pictures"
THUMB_DIR = ROOT / "images" / "thumb"
FULL_DIR = ROOT / "images" / "full"

# Extensions acceptees en entree. Le HEIC passe par `sips`, le reste par Pillow.
HEIC_SUFFIXES = {".heic", ".heif"}
DIRECT_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}

THUMB_MAX = 800
THUMB_QUALITY = 78
FULL_MAX = 1800
FULL_QUALITY = 82


def source_images(category_dir: Path) -> list[Path]:
    """Toutes les images d'une categorie, triees, en ignorant .DS_Store et cie."""
    accepted = HEIC_SUFFIXES | DIRECT_SUFFIXES
    return sorted(
        p
        for p in category_dir.iterdir()
        if p.is_file() and not p.name.startswith(".") and p.suffix.lower() in accepted
    )


def load_image(path: Path, workdir: Path) -> Image.Image:
    """Charge une image source, en passant par sips pour le HEIC."""
    if path.suffix.lower() in HEIC_SUFFIXES:
        intermediate = workdir / (path.stem + ".png")
        result = subprocess.run(
            ["sips", "-s", "format", "png", str(path), "--out", str(intermediate)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not intermediate.exists():
            raise RuntimeError(f"sips n'a pas pu decoder {path.name}: {result.stderr.strip()}")
        return Image.open(intermediate)
    return Image.open(path)


def render(image: Image.Image, destination: Path, max_side: int, quality: int) -> None:
    """Redimensionne (sans agrandir) et enregistre en WebP, sans metadonnees."""
    copy = image.copy()
    copy.thumbnail((max_side, max_side), Image.LANCZOS)
    if copy.mode not in ("RGB", "L"):
        copy = copy.convert("RGB")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Pillow n'ecrit pas l'EXIF en WebP si on ne le lui passe pas explicitement :
    # les donnees GPS et l'orientation d'origine ne sont donc pas publiees.
    copy.save(destination, "WEBP", quality=quality, method=6)


def process(path: Path, category: str, workdir: Path, force: bool) -> bool:
    """Convertit une photo. Retourne True si des fichiers ont ete ecrits."""
    thumb = THUMB_DIR / category / f"{path.stem}.webp"
    full = FULL_DIR / category / f"{path.stem}.webp"

    if not force and thumb.exists() and full.exists():
        source_mtime = path.stat().st_mtime
        if thumb.stat().st_mtime >= source_mtime and full.stat().st_mtime >= source_mtime:
            return False

    with load_image(path, workdir) as image:
        # Applique la rotation EXIF aux pixels une bonne fois pour toutes.
        oriented = ImageOps.exif_transpose(image)
        render(oriented, full, FULL_MAX, FULL_QUALITY)
        render(oriented, thumb, THUMB_MAX, THUMB_QUALITY)
    return True


def clean_orphans(categories: dict[str, list[Path]]) -> list[Path]:
    """Supprime les WebP qui n'ont plus de photo source correspondante."""
    expected = {
        (category, path.stem) for category, paths in categories.items() for path in paths
    }
    removed = []
    for base in (THUMB_DIR, FULL_DIR):
        if not base.exists():
            continue
        for webp in base.glob("*/*.webp"):
            if (webp.parent.name, webp.stem) not in expected:
                webp.unlink()
                removed.append(webp)
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="reconvertir meme si a jour")
    parser.add_argument("--clean", action="store_true", help="supprimer les WebP orphelins")
    args = parser.parse_args()

    if not SOURCE_DIR.is_dir():
        sys.exit(f"Dossier source introuvable : {SOURCE_DIR}")

    categories = {
        d.name: source_images(d)
        for d in sorted(SOURCE_DIR.iterdir())
        if d.is_dir() and not d.name.startswith(".")
    }
    if not categories:
        sys.exit(f"Aucune categorie dans {SOURCE_DIR} (attendu : pictures/<categorie>/)")

    converted = skipped = 0
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        for category, paths in categories.items():
            print(f"\n{category} ({len(paths)} photos)")
            for path in paths:
                try:
                    if process(path, category, workdir, args.force):
                        converted += 1
                        print(f"  + {path.name}")
                    else:
                        skipped += 1
                except Exception as exc:  # noqa: BLE001 - on veut continuer le lot
                    failures.append(f"{category}/{path.name}: {exc}")
                    print(f"  ! {path.name} -> {exc}")

    if args.clean:
        for webp in clean_orphans(categories):
            print(f"  - orphelin supprime : {webp.relative_to(ROOT)}")

    total = sum(len(p) for p in categories.values())
    print(f"\n{converted} converties, {skipped} deja a jour, {total} photos au total.")

    if failures:
        print(f"\n{len(failures)} echec(s) :")
        for failure in failures:
            print(f"  {failure}")
        return 1

    print("\nPensez a mettre a jour data/items.json (voir CLAUDE.md).")
    return 0


if __name__ == "__main__":
    if not shutil.which("sips"):
        sys.exit("`sips` introuvable : ce script necessite macOS pour decoder le HEIC.")
    sys.exit(main())
