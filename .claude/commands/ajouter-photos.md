---
description: Classe des photos par catégorie, les convertit en WebP, met à jour data/items.json et publie sur main
argument-hint: [chemins des photos ou d'un dossier — glisser-déposer les fichiers dans le prompt]
allowed-tools: Read, Edit, Glob, Grep, Bash(git:*), Bash(python3:*), Bash(pip:*), Bash(~/.pyenv/versions/.venv/bin/python3:*), Bash(~/.pyenv/versions/.venv/bin/pip:*), Bash(sips:*), Bash(cp:*), Bash(mkdir:*), Bash(ls:*), Bash(mktemp:*), Bash(file:*)
---

Photos à ajouter : $ARGUMENTS

Objectif : ranger ces photos dans `pictures/<categorie>/`, régénérer les WebP,
mettre à jour `data/items.json`, puis publier sur `main`. Suivre les étapes dans
l'ordre. En cas d'échec d'une étape, s'arrêter et expliquer — ne jamais commiter
un état à moitié construit.

## 0. Récupérer les fichiers source

Les photos peuvent arriver de deux façons :

- **Chemins de fichiers** (glisser-déposer dans le terminal, ou chemin tapé,
  ou dossier) : c'est le cas normal, les fichiers existent sur le disque.
- **Images collées dans le prompt** (Ctrl+V) : elles n'ont pas de chemin sur le
  disque, il est donc **impossible d'en récupérer le fichier d'origine**. Dans
  ce cas, s'arrêter et demander de glisser les fichiers ou de donner le chemin
  du dossier qui les contient. Ne pas tenter de recréer l'image.

Constituer la liste des fichiers source : développer les dossiers reçus, ne
garder que les extensions acceptées par `tools/build_images.py`
(`.heic .heif .jpg .jpeg .png .webp .tif .tiff`), ignorer les fichiers cachés.
Si la liste est vide, s'arrêter et le dire.

## 1. Préparer le dépôt et l'environnement Python

```bash
git -C . switch main && git pull origin main
```

S'il y a des modifications non commitées sans rapport, le signaler et demander
quoi en faire avant de continuer.

Pour Python, **ne pas utiliser `source … activate`** : chaque commande `Bash`
part d'un shell neuf, l'activation ne survit pas d'un appel à l'autre. Appeler
l'interpréteur du venv directement :

```bash
VENV=~/.pyenv/versions/.venv
[ -x "$VENV/bin/python3" ] || python3 -m venv "$VENV"
"$VENV/bin/python3" -c "import PIL" 2>/dev/null || "$VENV/bin/pip" install Pillow
"$VENV/bin/python3" -c "import PIL; print('Pillow', PIL.__version__)"
command -v sips >/dev/null || echo "sips absent : le HEIC ne pourra pas être décodé (macOS requis)"
```

## 2. Analyser chaque photo et en déduire la catégorie

Lister d'abord les catégories déjà existantes — ce sont elles qu'il faut
réutiliser en priorité :

```bash
ls images/thumb/
```

Puis regarder chaque photo. Le HEIC n'est pas lisible directement : en produire
une copie JPEG réduite dans un dossier temporaire (jamais dans le dépôt) et lire
celle-là :

```bash
TMP=$(mktemp -d)
sips -s format jpeg -Z 1024 "<source.heic>" --out "$TMP/<nom>.jpg"
```

Lire chaque image (l'aperçu pour le HEIC, le fichier lui-même sinon) et décider
d'une catégorie d'après ce qu'elle montre.

Règles de nommage des catégories :

- **minuscules, ASCII sans accent, mots séparés par `-`** :
  `materiel-cave`, `outillage-jardin`, `vaisselle`. Jamais d'espace, de
  majuscule, d'accent ni de `_`.
- **En français**, comme tout le site.
- **Réutiliser une catégorie existante dès qu'elle convient.** Ne pas créer
  `outils-bricolage` alors que `materiel-bricolage` existe. Une nouvelle
  catégorie ne se justifie que si aucune existante ne colle vraiment.
- Rester générique : la catégorie regroupe une famille d'objets, elle ne décrit
  pas l'objet précis. En dernier recours, `divers`.

Avant de copier quoi que ce soit, présenter le classement proposé (une ligne par
photo : nom de fichier → catégorie, et la mention « nouvelle catégorie » le cas
échéant) pour que ce soit vérifiable d'un coup d'œil.

## 3. Copier les photos dans `pictures/<categorie>/`

L'identifiant d'un objet est le nom de fichier sans extension : **deux photos ne
peuvent pas porter le même nom**, même dans deux catégories différentes.
Vérifier les collisions avant de copier :

```bash
ls pictures/*/ images/thumb/*/ 2>/dev/null | grep -i "<nom-sans-extension>"
```

En cas de collision, renommer la nouvelle photo (`IMG_0494-2.HEIC`) plutôt
qu'écraser l'existante, et le signaler.

Copier avec `cp` — **jamais `mv`** : le fichier d'origine de l'utilisateur ne
doit pas disparaître, `pictures/` n'est pas sauvegardé.

```bash
mkdir -p "pictures/<categorie>" && cp -n "<source>" "pictures/<categorie>/"
```

## 4. Déclarer les nouvelles catégories

Pour chaque catégorie qui n'existait pas encore, ajouter une entrée dans
`KNOWN_LABELS` de `tools/sync_items.py` avec un libellé français lisible, tel
qu'il s'affichera sur le site — accents compris, majuscule initiale
uniquement :

```python
KNOWN_LABELS = {
    "materiel-cave": "Materiel de cave",
    "materiel-bricolage": "Materiel de bricolage",
    "outillage-jardin": "Outillage de jardin",   # <- ajout
}
```

Sans cette entrée, `sync_items.py` fabrique un libellé approximatif
(`outillage-jardin` → « Outillage jardin »).

## 5. Convertir et synchroniser

```bash
VENV=~/.pyenv/versions/.venv
"$VENV/bin/python3" tools/build_images.py
"$VENV/bin/python3" tools/sync_items.py
```

`build_images.py` ne retraite que les nouveautés, applique la rotation EXIF aux
pixels et **supprime toutes les métadonnées, GPS compris**. `sync_items.py`
n'ajoute que les entrées manquantes : les `status`, `title`, `note` et l'ordre
existants sont préservés. Si `build_images.py` signale des échecs, les rapporter
et ne pas commiter.

Si un libellé de nouvelle catégorie a été ajouté à l'étape 4 après un premier
`sync_items.py`, corriger aussi le `label` dans `data/items.json` : le script ne
réécrit pas les catégories déjà présentes.

## 6. Vérifier avant de publier

```bash
VENV=~/.pyenv/versions/.venv
"$VENV/bin/python3" -m json.tool data/items.json > /dev/null   # JSON valide
"$VENV/bin/python3" tools/sync_items.py --check                # images et JSON synchronisés
git status --porcelain                                          # aucun fichier de pictures/
```

`pictures/` est dans `.gitignore` : si un HEIC apparaît dans `git status`,
s'arrêter — les photos brutes contiennent les coordonnées GPS de la prise de vue
et ne doivent jamais être publiées.

## 7. Commiter sur `main`

Ajouter uniquement les chemins concernés — pas de `git add -A`, pour ne pas
emporter des modifications sans rapport :

```bash
git add images data/items.json tools/sync_items.py
git commit -m "feat: Add <N> photos (<categories>)"
git push -u origin main
```

Message de commit en anglais, préfixe conventionnel, comme le reste de
l'historique (`feat:` pour un ajout de photos). En cas d'échec réseau du push,
réessayer jusqu'à 4 fois (2s, 4s, 8s, 16s).

## 8. Rendre compte

Terminer par un récapitulatif court :

- combien de photos ajoutées, et dans quelles catégories ;
- les nouvelles catégories créées, avec leur libellé ;
- les collisions de noms ou photos ignorées, s'il y en a eu ;
- le rappel que les originaux de `pictures/` ne sont pas versionnés et doivent
  être sauvegardés ailleurs ;
- l'URL du site : <https://tacchinia.github.io/a-vendre/> (quelques minutes
  avant que GitHub Pages ne serve la nouvelle version).

Les objets sont publiés sans titre ni description — c'est volontaire. Proposer,
sans le faire d'office, d'ajouter un `title` ou une `note` dans
`data/items.json` pour les objets qui ne se devinent pas sur la photo.
Rappeler qu'aucun prix ne doit jamais figurer nulle part.
