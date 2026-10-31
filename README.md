# KataML — fork pour macOS (non officiel)

> **Fork non officiel.** KataML a été créé par **fredbl**, auteur et mainteneur du projet
> d'origine : <https://gitlab.com/fredbl/kataml> (licence MIT). Ce dépôt n'est pas le
> projet officiel : il contient des modifications réalisées par Pape Ndiogou SEYE, étudiant en
> master Statistique pour l'évaluation et la prévision (SEP) à l'Université de Reims
> Champagne-Ardenne, à partir de la version 0.5.8. Pour la version officielle, les
> versions portables et la documentation, reportez-vous au dépôt d'origine.

## Ce que ce fork ajoute

- **Lecteur Parquet / Excel** et **Lecteur SQL** (SQLite, PostgreSQL, MySQL ; URL lue dans
  `$DATABASE_URL` pour ne pas enregistrer de mot de passe).
- **Import d'un script Python** en schéma, sans l'exécuter : lecture des données,
  préparation pandas, `train_test_split`, modèles, `Pipeline`, métriques, validation
  croisée, sur un ou plusieurs fichiers.
- **Fenêtre « Données et scripts »** : bibliothèque de scripts et import d'un dossier de
  projet complet.
- **Calculs plus rapides** sur les gros jeux de données (tous les cœurs du processeur,
  options `--jobs` et `--cache-mb`).
- **Encodeurs plus sûrs** sur les colonnes texte (TargetEncoder, OneHotEncoder…).

Le détail des modifications, des tests et des fichiers concernés est dans le rapport
[`rapport/rapport_modifications_kataml.pdf`](rapport/rapport_modifications_kataml.pdf).

### Lancer sur macOS

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # une seule fois
./kataml.sh                                       # le navigateur s'ouvre
uv run python -m unittest discover -v tests       # tests
```

---

*Ci-dessous, le README du projet d'origine.*

# KataML

*Keen-edged Analytics Toolkit for Applied Machine Learning*

KataML est un atelier visuel de machine learning. On y relie des nœuds sur un canevas, on les
configure et on les exécute, on inspecte les modèles et leurs sorties, puis on exporte le
workflow en script Python ou en notebook Jupyter. Tous les calculs passent par scikit-learn et
pandas. Le nom évoque le katana, un outil tranchant, et le *kata*, une suite de gestes que l'on
répète pour les maîtriser.

Documentation et tutoriels, en français et en anglais : <https://fredbl.gitlab.io/kataml/>

| | |
|---|---|
| Dépendances | `scikit-learn` et `pandas` ; serveur en bibliothèque standard Python, interface en HTML/CSS/JS sans framework ni CDN, utilisable hors ligne |
| Installation | dans `.venv/` à l'intérieur du dossier, ou versions portables ; aucun droit administrateur |
| Couverture | plus de 230 nœuds : chaque estimateur de scikit-learn est disponible, ou son absence est justifiée (un test le vérifie) ; hyperparamètres, types, valeurs par défaut et aides sont lus dans scikit-learn et suivent la version installée |
| Organisation | dépôt classé selon les chapitres du guide de scikit-learn, ou selon les modules de l'API |
| Langues | interface en français ou en anglais ; en anglais, les nœuds portent les noms de scikit-learn (`train_test_split`, `cross_validate`, `GridSearchCV`…) |
| Évaluation | Pipeline sans fuite d'information, toutes les stratégies de validation croisée, validation imbriquée, comparaison de modèles |
| Inspection | frontières de décision, arbres, courbes de validation et d'apprentissage, dépendance partielle, importance par permutation |
| Partage | rapports HTML autonomes (imprimables en PDF), export en script ou en notebook, exécution en ligne de commande |
| Extension | blocs écrits en Python dans l'éditeur intégré (« Mes blocs ») ou distribués en paquets |

## Démarrage

### Versions portables (sans rien installer)

Chaque [release](https://gitlab.com/fredbl/kataml/-/releases) fournit deux paquets qui
embarquent Python, pandas et scikit-learn :

- **Linux** : `KataML-<version>-x86_64.AppImage`. Rendez-le exécutable (`chmod +x`), puis
  lancez-le. Les données sont rangées dans `kataml-workspace/`, à côté du fichier. Si
  l'AppImage refuse de démarrer faute de FUSE, lancez-la avec `--appimage-extract-and-run`.
- **Windows** : `KataML-<version>-windows-x64.zip`. Dézippez, puis double-cliquez sur
  `KataML.bat`. Les données sont rangées dans `workspace/`, à côté du lanceur ; le dossier
  peut être déplacé ou copié sur une clé USB.

Le bouton ⏻ en haut à droite arrête le serveur.

### Avec uv

Prérequis : [uv](https://docs.astral.sh/uv/). Il s'installe sans droits administrateur :

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Installer la commande `kataml`

```bash
uv tool install git+https://gitlab.com/fredbl/kataml.git
kataml
```

La commande est placée dans `~/.local/bin` et ses dépendances dans un environnement isolé
géré par uv. Les données, workflows et exports vont dans `~/kataml` (ou dans le dossier
indiqué par `--workspace` ou par la variable `KATAML_WORKSPACE`).

Mise à jour et désinstallation :

```bash
uv tool upgrade kataml
uv tool uninstall kataml
```

Pour essayer sans rien installer :

```bash
uvx --from git+https://gitlab.com/fredbl/kataml.git kataml
```

### Depuis une copie du dépôt

```bash
git clone https://gitlab.com/fredbl/kataml.git
cd kataml
./kataml.sh
```

Sous Windows, lancez `kataml.bat`. Au premier lancement, uv télécharge si besoin un Python
compatible et installe les dépendances dans `.venv/` (environ 30 secondes). Dans ce mode, le
dossier de travail est `workspace/`, à côté du code.

Le navigateur s'ouvre sur `http://127.0.0.1:8765/`. Options :

```text
kataml --port 9000          # autre port
kataml --no-browser         # ne pas ouvrir le navigateur
kataml --workspace ~/tp-ml  # autre dossier de travail
```

Sans uv, avec un Python ≥ 3.10 qui dispose de `venv` :

```bash
python3 -m venv .venv && .venv/bin/pip install .
.venv/bin/kataml
```

## Interface

| Élément | Rôle |
|---|---|
| Dépôt de nœuds | Panneau de gauche : vue « Guide » (chapitres du guide scikit-learn) ou « API » (modules), recherche en français ou en anglais (« forêt », « acp », « normalisation »…) |
| Canevas | Zone centrale : glisser-déposer, connexions, zoom, annotations, copier-coller, annuler/rétablir |
| Feux d'état | Rouge = à configurer ou en erreur, orange = prêt, vert = exécuté |
| Ports | Triangle = table (DataFrame), carré = modèle (estimateur ajusté) |
| Configuration | Panneau de droite, appliqué immédiatement |
| Description | Onglet « Description » et lien vers la documentation scikit-learn |
| Sorties | Panneau du bas : table paginée et triable, profil des colonnes, modèle, vue graphique |
| Apprentissage / prédiction | Nœud d'apprentissage → port modèle → « Prédicteur » |
| Transformation | Nœud transformeur → port modèle → « Appliquer un transformeur » (même transformation sur le jeu de test) |
| Pipeline | Table brute + modèle + prétraitements → un seul `sklearn.pipeline.Pipeline` (clic droit sur une sélection → « Créer un Pipeline ») |
| Composants | Groupe de nœuds réduit en un seul nœud à ports (Ctrl+G), enregistrable dans « Mes composants » |
| Organisation | Disposition automatique du graphe en couches (L) |
| Arrêter | Interrompt le calcul en cours ; les résultats déjà obtenus sont conservés |
| Rapport | Fichier HTML autonome : schéma, sections choisies et ordonnées, blocs « Texte du rapport » (Ctrl+P) |
| Mes blocs | Créer, modifier et recharger ses propres nœuds Python ; convertir un Script Python en bloc |
| Apparence | Mode automatique, clair ou sombre, couleur principale (sept teintes ou personnalisée), fond du canevas ; `theme.css` dans l'espace de travail pour une charte complète |

## Nœuds

| Famille | Contenu |
|---|---|
| Entrées / sorties | lecteur CSV (bouton d'import ou fichier glissé sur le canevas), jeux de données scikit-learn et générateurs (`make_moons`, `make_blobs`…), jeux OpenML (téléchargés une fois, puis mis en cache), écriture CSV, écriture de modèle (joblib) |
| Manipulation | filtres de colonnes et de lignes (`DataFrame.query`), nouvelle colonne (`DataFrame.eval`), partitionnement (`train_test_split`), échantillonnage, tri, conversion de types, caractéristiques de dates (encodage cyclique), GroupBy, jointure, concaténation, renommage, lignes incomplètes, script Python |
| Visualisation | statistiques, nuage de points, histogramme, boîtes à moustaches, matrice de corrélation, vue de table |
| Prétraitement | tous les transformeurs de scikit-learn (normalisation, encodage, imputation, sélection de variables dont RFE et SelectFromModel, PCA…) et la vectorisation de texte (TF-IDF, sac de mots, hachage) ; le transformeur ajusté sort sur un port modèle |
| Apprentissage supervisé | tous les classifieurs et régresseurs, poids des observations (`sample_weight`), estimateur de base au choix pour Bagging, AdaBoost, CalibratedClassifierCV, SelfTraining, RANSAC et TransformedTargetRegressor ; vote, empilement, un-contre-tous, multisortie |
| Apprentissage non supervisé | clustering, mélanges gaussiens, décomposition, variétés, détection d'anomalies (IsolationForest, LocalOutlierFactor, OneClassSVM…), covariance, densité, plus proches voisins |
| Pipelines | prétraitements et modèle réunis dans un `sklearn.pipeline.Pipeline`, affiché contracté sur le canevas |
| Évaluation | métriques de classification et matrice de confusion, métriques de régression et résidus, courbes ROC, précision-rappel et de calibration |
| Inspection | frontière de décision, arbre dessiné, dépendance partielle, importance par permutation |
| Sélection de modèles | validation croisée avec toutes les stratégies de scikit-learn, prédictions hors pli, test de permutation, comparaison de modèles, `GridSearchCV` / `RandomizedSearchCV` (avec validation imbriquée), seuil de décision, courbes de validation et d'apprentissage |

## Rapports

Le bouton **Rapport** (Ctrl+P) ouvre une boîte où l'on choisit les nœuds à inclure, leur
ordre, le titre, l'auteur et les options (schéma du workflow, annotations, aperçu des tables,
script Python en annexe). Les nœuds manquants sont exécutés, puis le rapport est enregistré
dans `workspace/reports/`. C'est un fichier HTML unique, lisible hors ligne, qui s'ouvre
dans un navigateur et s'imprime en PDF. Les blocs **Texte du rapport** (catégorie
« Rapport ») ajoutent introduction, commentaires et conclusion en Markdown.

Sans interface, par exemple pour relancer une analyse chaque semaine ou depuis une CI :

```bash
kataml run mon_workflow.json --rapport rapport.html
kataml run mon_workflow.json --script analyse.py --notebook analyse.ipynb
```

Le code de retour vaut 1 si un nœud échoue, et `--lang en` produit le rapport en anglais. Les
réglages du rapport enregistrés dans le workflow (choix et ordre des sections) sont repris.

## Blocs personnalisés

**Mes blocs** (en haut du dépôt) crée un bloc à partir d'un modèle commenté, l'ouvre dans un
éditeur intégré et le recharge à chaud ; les erreurs s'affichent sous l'éditeur. Un clic droit
sur un nœud « Script Python » le convertit en bloc réutilisable. Les blocs sont des fichiers
Python de `workspace/extensions/`, chargés aussi par les versions portables et par
`kataml run`. Pour diffuser des blocs, on les publie dans un paquet Python qui déclare un
point d'entrée `kataml.extensions`. Guide complet : [Blocs personnalisés](https://fredbl.gitlab.io/kataml/blocks/)
([source](docs/fr/blocks.md)) ;
exemple de paquet : [extensions/kataml-exemple](extensions/kataml-exemple).

## Fichiers

```text
~/kataml/     (ou workspace/ depuis une copie du dépôt)
  data/        fichiers importés (et données des exemples)
  workflows/   workflows enregistrés (.json)
  components/  composants réutilisables (.json)
  extensions/  blocs personnalisés (.py)
  reports/     rapports générés (.html)
  exports/     sorties des nœuds d'écriture
  openml/      cache des jeux OpenML
  .cache/      résultats des nœuds (1 Go max., réglable par KATAML_CACHE_MB)
  theme.css    personnalisation des couleurs (facultatif)
```

Les résultats des nœuds sont conservés sur disque : après un redémarrage, les nœuds déjà
exécutés restent verts et leurs sorties s'affichent sans recalcul.

Les workflows peuvent aussi être exportés ou importés en `.json` depuis la boîte « Ouvrir ».
Le workflow courant est sauvegardé automatiquement dans le navigateur.

## Sécurité

Le serveur écoute uniquement sur `127.0.0.1`. Chaque requête d'API doit porter un jeton aléatoire
généré au démarrage, et l'en-tête `Host` est vérifié (protection contre CSRF et DNS rebinding).
Le nœud « Script Python » exécute du code arbitraire : ne lancez `--host 0.0.0.0` que sur un
réseau de confiance.

## Développement

```text
kataml/
  sk_catalog.py   introspection de scikit-learn (estimateurs, hyperparamètres, docstrings)
  nodes.py        registre des nœuds de base : exécution et génération de code Python
  nodes_compose.py, nodes_explain.py, nodes_data.py
                  Pipeline et méta-estimateurs, explicabilité, texte / dates / OpenML
  engine.py       exécution des workflows, cache mémoire et disque par signature
  worker.py       moteur dans un processus séparé (annulation des calculs)
  export.py       export en script Python et en notebook Jupyter
  report.py       rapports HTML autonomes ; cli.py : kataml run
  extension.py    API publique et chargement des blocs personnalisés
  server.py       serveur HTTP et API JSON
  static/         interface (index.html, css/app.css, js/*.js)
  examples/       workflows d'exemple et leurs données
tests/            tests de bout en bout (exemples + scripts exportés)
docs/             documentation MkDocs (docs/fr, docs/en, docs/assets)
tools/            versions portables, documentation (référence, captures d'écran)
```

```bash
uv run python -m unittest discover tests
```

### Documentation

La documentation (MkDocs Material, bilingue) est publiée sur GitLab Pages par la CI à chaque
push sur la branche principale. La référence des nœuds (`docs/*/reference/`) et les captures
d'écran (`docs/assets/screenshots/`) sont générées et ne sont pas versionnées :

```bash
uv sync --group docs
PLAYWRIGHT_BROWSERS_PATH=.build-cache/ms-playwright uv run --group docs playwright install chromium
uv run --group docs python tools/gen_docs.py        # référence des nœuds (fr, en)
PLAYWRIGHT_BROWSERS_PATH=.build-cache/ms-playwright uv run --group docs python tools/screenshots.py
uv run --group docs mkdocs serve                    # http://127.0.0.1:8000
```

Les captures rejouent des scénarios dans Chromium sans interface, sur un espace de travail
temporaire ; `--only interface,tutorials` ou `--lang en` en limitent la portée.

### Versions portables et releases

`tools/build_portable.py` construit l'AppImage et le zip Windows depuis Linux, sans runner
Windows : il télécharge un Python relocalisable
([python-build-standalone](https://github.com/astral-sh/python-build-standalone)) pour chaque
plateforme, y installe les wheels officielles avec `uv pip install --python-platform`, nettoie,
précompile, puis empaquette.

```bash
uv run --no-project python tools/build_portable.py --smoke-test   # résultat dans dist/
```

En CI (`.gitlab-ci.yml`), les tests tournent à chaque push. Un tag `vX.Y.Z` (identique à la
version de `pyproject.toml`) construit les deux paquets, les dépose dans le Package Registry
du projet et crée la release GitLab correspondante :

```bash
git tag v0.5.2 && git push origin v0.5.2
```
