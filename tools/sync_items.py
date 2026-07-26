#!/usr/bin/env python3
"""
Synchronise `data/items.json` avec le contenu de `images/thumb/`.

Le fichier data/items.json reste la source de verite : ce script ne fait
qu'ajouter les nouvelles photos et signaler celles qui ont disparu. Les
statuts, titres, notes et l'ordre existants sont preserves.

Usage :
    source ~/.pyenv/versions/.venv/bin/activate  # meme environnement que
                                                 # tools/build_images.py
    python3 tools/sync_items.py            # ajoute les nouveautes
    python3 tools/sync_items.py --prune    # retire aussi les entrees sans image
    python3 tools/sync_items.py --check    # ne modifie rien, sort en erreur si desynchronise

Ce script n'utilise que la bibliotheque standard : il fonctionne meme sans le
venv actif. L'activation est indiquee pour garder la meme suite de commandes
que build_images.py, qui, lui, en a besoin.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "items.json"
THUMB_DIR = ROOT / "images" / "thumb"

DEFAULT_STATUS = "available"

# Libelles proposes pour les nouvelles categories. Un dossier absent de cette
# table recoit un libelle derive de son nom, a corriger a la main si besoin.
KNOWN_LABELS = {
    "materiel-cave": "Materiel de cave",
    "materiel-bricolage": "Materiel de bricolage",
}

TEMPLATE = {
    "title": "A vendre / a donner",
    "intro": (
        "Aucun prix n'est fixe : tout est a discuter, gratuit ou contre une somme à convenir. "
        "Les objets peuvent partir a l'unite ou par lot."
    ),
    "contact": {"email": "alexandre.tacchini+petites-annonces@gmail.com"},
    "categories": [],
}


def label_for(category_id: str) -> str:
    return KNOWN_LABELS.get(category_id, category_id.replace("-", " ").capitalize())


def scan_images() -> dict[str, list[str]]:
    """Les identifiants de photos presents sur le disque, par categorie."""
    if not THUMB_DIR.is_dir():
        sys.exit(f"{THUMB_DIR} est introuvable : lancez d'abord tools/build_images.py")
    return {
        d.name: sorted(p.stem for p in d.glob("*.webp"))
        for d in sorted(THUMB_DIR.iterdir())
        if d.is_dir()
    }


def load_data() -> dict:
    if not DATA_FILE.exists():
        return json.loads(json.dumps(TEMPLATE))
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prune", action="store_true", help="retirer les entrees sans image")
    parser.add_argument("--check", action="store_true", help="verifier sans rien modifier")
    args = parser.parse_args()

    on_disk = scan_images()
    data = load_data()
    categories = data.setdefault("categories", [])
    by_id = {c["id"]: c for c in categories}

    added: list[str] = []
    missing: list[str] = []
    pruned: list[str] = []

    for category_id, image_ids in on_disk.items():
        category = by_id.get(category_id)
        if category is None:
            category = {"id": category_id, "label": label_for(category_id), "items": []}
            categories.append(category)
            by_id[category_id] = category

        items = category.setdefault("items", [])
        known = {item["id"] for item in items}

        for image_id in image_ids:
            if image_id not in known:
                items.append({"id": image_id, "status": DEFAULT_STATUS})
                added.append(f"{category_id}/{image_id}")

        available = set(image_ids)
        orphans = [item for item in items if item["id"] not in available]
        for orphan in orphans:
            missing.append(f"{category_id}/{orphan['id']}")
            if args.prune:
                items.remove(orphan)
                pruned.append(f"{category_id}/{orphan['id']}")

    for category in categories:
        if category["id"] not in on_disk:
            missing.append(f"{category['id']}/ (categorie entiere)")

    for entry in added:
        print(f"  + {entry}")
    for entry in missing:
        print(f"  ? {entry} : entree sans image" + (" (retiree)" if entry in pruned else ""))

    if args.check:
        if added or missing:
            print(f"\nDesynchronise : {len(added)} a ajouter, {len(missing)} sans image.")
            return 1
        print("data/items.json est a jour.")
        return 0

    if not added and not pruned:
        print("Rien a faire : data/items.json est deja a jour.")
        return 0

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    total = sum(len(c.get("items", [])) for c in categories)
    print(f"\ndata/items.json mis a jour : {total} objets.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
