# À vendre / à donner — guide de maintenance

Galerie statique d'objets à céder (vendus à prix libre ou donnés).
Publiée sur GitHub Pages : **<https://tacchinia.github.io/a-vendre/>**

Site 100 % statique : pas de framework, pas d'étape de compilation, aucune
dépendance JavaScript. Un `git push` sur `main` suffit à mettre en ligne.

---

## Structure

```text
index.html              page unique
assets/style.css        styles (thème clair/sombre automatique)
assets/app.js           rendu de la galerie + visionneuse — piloté par data/items.json
data/items.json         SOURCE DE VÉRITÉ : la liste des objets            <- à éditer
images/thumb/<cat>/     vignettes WebP 800 px      (généré)
images/full/<cat>/      photos WebP 1800 px        (généré)
pictures/<cat>/         photos brutes HEIC/JPEG    (LOCAL, non versionné)
tools/build_images.py   photos brutes -> WebP
tools/sync_items.py     images -> data/items.json
```

## Règles à respecter

1. **Aucun prix, jamais.** Tout est « à discuter » : gratuit ou petite
   participation, à l'unité ou par lot. Ne pas ajouter de champ prix, ni de
   panier, ni de formulaire de paiement.
2. **Le site est en français.**
3. **`data/items.json` est la source de vérité.** `assets/app.js` ne contient
   aucune donnée en dur : ajouter ou retirer un objet ne demande jamais de
   toucher au JavaScript ni au HTML.
4. **Ne jamais éditer à la main les fichiers de `images/`** : ils sont
   régénérés par `tools/build_images.py`. Les photos brutes restent dans
   `pictures/`.
5. **`pictures/` n'est pas versionné** (voir `.gitignore`) : les HEIC pèsent
   ~145 Mo et contiennent les coordonnées GPS de la prise de vue. Seuls les
   WebP générés — dont toutes les métadonnées EXIF ont été supprimées — sont
   publiés. **Les originaux n'existent donc qu'en local : les sauvegarder
   ailleurs.**
6. **Pas de dépendance externe** : ni CDN, ni police distante, ni bibliothèque.
7. Un objet = une photo. L'identifiant d'un objet est le nom de fichier de sa
   photo, sans extension (`IMG_0494`).

---

## Prérequis — activer l'environnement virtuel

Les scripts de `tools/` ont besoin de **Pillow**, qui n'est installé que dans
l'environnement virtuel `~/.pyenv/versions/.venv`. Le `python3` du système ne
l'a pas. **Activer l'environnement avant toute commande `python3` :**

```bash
source ~/.pyenv/versions/.venv/bin/activate
```

Sans cette étape, les scripts s'arrêtent sur `Pillow est requis`. L'activation
vaut pour toute la session du terminal : une seule fois suffit, pas besoin de
la répéter entre deux commandes. Pour en sortir : `deactivate`.

Vérifier que c'est bon :

```bash
python3 -c "import PIL; print(PIL.__version__)"   # doit afficher 12.x
```

Si l'environnement a disparu, le recréer :

```bash
python3 -m venv ~/.pyenv/versions/.venv
source ~/.pyenv/versions/.venv/bin/activate
pip install Pillow
```

`sips`, l'autre prérequis (décodage HEIC), est fourni par macOS : rien à
installer.

---

## Ajouter des objets

```bash
# 0. Activer l'environnement virtuel (une fois par terminal)
source ~/.pyenv/versions/.venv/bin/activate
# 1. Déposer les photos dans pictures/<categorie>/  (HEIC, JPEG ou PNG)
# 2. Convertir (ne retraite que les nouveautés)
python3 tools/build_images.py
# 3. Ajouter les nouvelles entrées dans data/items.json (statuts existants préservés)
python3 tools/sync_items.py
# 4. Publier
git add -A && git commit -m "Ajout de N objets" && git push
```

Une nouvelle catégorie se crée simplement en créant un dossier dans
`pictures/`. `sync_items.py` l'ajoute à `data/items.json` avec un libellé
deviné depuis le nom du dossier — le corriger à la main dans le JSON
(le libellé est ce qui s'affiche sur le site), et l'ajouter au passage à
`KNOWN_LABELS` dans `tools/sync_items.py`.

## Marquer un objet vendu ou réservé

Modifier son `status` dans `data/items.json`, puis commiter :

| `status`      | Affichage                                                                             |
|---------------|---------------------------------------------------------------------------------------|
| `"available"` | normal, compté dans « N objets disponibles »                                          |
| `"reserved"`  | badge « Réservé », photo atténuée, non compté                                         |
| `"sold"`      | badge « Parti », photo en gris, bouton contact masqué, masquable via la case à cocher |

## Retirer un objet

Supprimer la photo de `pictures/<cat>/`, puis :

```bash
source ~/.pyenv/versions/.venv/bin/activate   # si ce n'est pas déjà fait
python3 tools/build_images.py --clean         # supprime les WebP orphelins
python3 tools/sync_items.py --prune           # retire l'entrée de data/items.json
```

Préférer `status: "sold"` à la suppression : cela garde la trace de ce qui est
parti et évite qu'on redemande l'objet.

## Champs de `data/items.json`

```jsonc
{
  "title": "À vendre / à donner",       // titre de la page et de l'onglet
  "intro": "…",                          // paragraphe d'introduction
  "contact": { "email": "…" },           // destinataire des liens mailto
  "categories": [
    {
      "id": "materiel-cave",             // = nom du dossier dans images/ et pictures/
      "label": "Matériel de cave",       // libellé affiché
      "items": [
        {
          "id": "IMG_0494",              // = nom du fichier photo sans extension
          "status": "available",         // available | reserved | sold
          "title": "Établi en bois",     // facultatif — sinon la catégorie sert de libellé
          "note": "à démonter sur place" // facultatif — affiché dans la visionneuse
        }
      ]
    }
  ]
}
```

`title` et `note` sont facultatifs et absents par défaut : la galerie est
volontairement composée de photos seules. Les renseigner sur un objet précis
suffit à le décrire, sans avoir à le faire pour tous les autres.

## Vérifier avant de publier

```bash
source ~/.pyenv/versions/.venv/bin/activate        # si ce n'est pas déjà fait
python3 -m json.tool data/items.json > /dev/null   # JSON valide
python3 tools/sync_items.py --check                # images et JSON synchronisés
python3 -m http.server 8000                        # puis http://localhost:8000
```

Le site charge `data/items.json` via `fetch()` : l'ouvrir directement en
`file://` ne fonctionne pas, il faut passer par un serveur local.
