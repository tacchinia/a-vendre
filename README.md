# À vendre / à donner

Galerie statique des objets encore à céder — vendus à prix libre ou donnés,
à l'unité ou par lot. Aucun prix n'est affiché : tout est à discuter.

**→ <https://tacchinia.github.io/a-vendre/>**

## Mettre à jour

```bash
# activer l'environnement virtuel (une fois par terminal — Pillow y est installé)
source ~/.pyenv/versions/.venv/bin/activate

# déposer les photos dans pictures/<categorie>/, puis :
python3 tools/build_images.py     # conversion en WebP optimisés
python3 tools/sync_items.py       # mise à jour de data/items.json
git add -A && git commit -m "Mise à jour des objets" && git push
```

Marquer un objet parti ou réservé : changer son `status` dans
`data/items.json` (`available` / `reserved` / `sold`), puis pousser.

Le détail des règles et des cas particuliers est dans [CLAUDE.md](CLAUDE.md).

## Notes techniques

- Site entièrement statique : aucune dépendance, aucune étape de compilation.
  GitHub Pages sert directement la branche `main`.
- `tools/build_images.py` applique la rotation EXIF aux pixels et supprime
  toutes les métadonnées, coordonnées GPS comprises, avant publication.
- Les photos brutes (`pictures/`) ne sont pas versionnées : elles n'existent
  qu'en local et doivent être sauvegardées séparément.
- Prérequis des scripts : macOS (`sips`, pour décoder le HEIC) et Pillow,
  installé dans l'environnement virtuel `~/.pyenv/versions/.venv` — il faut
  l'activer avant de lancer les scripts (voir ci-dessus). Le `python3` du
  système n'a pas Pillow.
