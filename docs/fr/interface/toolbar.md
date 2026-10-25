# Barre d'outils

![Barre d'outils](../../assets/screenshots/fr/toolbar.png){ .shot }

## Nom du workflow

Le champ à gauche contient le nom du workflow ; cliquez pour le modifier. Un point orange
signale des modifications non enregistrées dans l'espace de travail (le navigateur, lui,
sauvegarde automatiquement en continu).

## Boutons

| Bouton | Raccourci | Action |
|---|---|---|
| **Nouveau** | | workflow vide (confirmation si des modifications ne sont pas enregistrées) |
| **Ouvrir** | | ouvrir un workflow enregistré, un exemple ou un tutoriel, ou importer un fichier `.json` |
| **Données** | | données du projet (CSV, Parquet, Excel, SQLite) et bibliothèque de scripts Python à convertir en schéma |
| **Enregistrer** | ++ctrl+s++ | enregistrer dans `workspace/workflows` (++ctrl+shift+s++ : enregistrer sous un autre nom) |
| ↶ / ↷ | ++ctrl+z++ / ++ctrl+y++ | annuler / rétablir (structure, paramètres, positions) |
| **Annotation** | ++a++ | ajouter une note sur le canevas |
| **Exporter** | | script Python ou notebook Jupyter équivalent |
| **Rapport** | ++ctrl+p++ | générer un rapport HTML (voir [Rapports](../reports.md)) |
| **Organiser** | ++l++ | disposer automatiquement le graphe (la sélection, ou tout le workflow) |
| **Réinitialiser** | | effacer tous les résultats (et le cache) |
| **Tout exécuter** | ++shift+f7++ | exécuter tous les nœuds configurés |
| **Arrêter** | | interrompre le calcul en cours (visible pendant une exécution) |

Sur les écrans moyens, les boutons secondaires n'affichent que leur icône : leur libellé
apparaît au survol.

## Ouvrir

![Boîte « Ouvrir »](../../assets/screenshots/fr/dialog-open.png){ .shot }

La boîte liste **vos workflows** (dossier `workspace/workflows`) et les **exemples**
fournis avec KataML, qui servent de corrigés aux [tutoriels](../tutorials/index.md).
Le bouton **Importer un fichier .json** charge un workflow reçu par ailleurs ; **Exporter
le workflow courant** l'enregistre sous forme de fichier.

### Importer un script Python

**Importer un script Python (.py)** reconstruit le schéma à partir d'un script pandas /
scikit-learn : chaque lecture de fichier, partition, transformeur, modèle, prédiction,
métrique ou validation croisée devient un nœud relié aux autres. Le script n'est pas
exécuté, seulement analysé.

- Si le script importe ses propres modules (`from monprojet.config import CIBLE`),
  sélectionnez-les en même temps : leurs constantes et fonctions sont reprises.
- Les opérations pandas non reconnues (`df["x"] = …`, `df.query(…)`) deviennent des nœuds
  **Script Python** qui les reproduisent.
- Une note jaune sur le canevas liste ce qui n'a pas pu être déduit (fichier, colonne cible
  calculée…) : complétez ces nœuds dans l'inspecteur, puis exécutez.

## Données et scripts

Le bouton **Données** ouvre une fenêtre en deux parties.

- **Données** (`workspace/data`) : fichiers CSV, Parquet, Excel et bases SQLite. **Au
  canevas** crée le lecteur adapté au format ; **Importer** ajoute des fichiers (ou
  déposez-les dans la fenêtre).
- **Scripts** (`workspace/scripts`) : la bibliothèque de scripts Python du projet.
  **Ajouter** des fichiers `.py`, **Nouveau** pour partir d'un modèle commenté, **Voir /
  modifier** pour les éditer. Cochez le ou les scripts à convertir, puis **Créer le
  schéma** : les autres scripts servent de modules s'ils sont importés.

**Importer un dossier de projet** prend tout un dossier : les scripts rejoignent la
bibliothèque (les dossiers `.venv`, `.git`, caches… sont ignorés) et les fichiers de données
sont repérés ; seuls ceux que le schéma lit sont importés au moment de la conversion.

### Bases de données

Le nœud **Lecteur SQL** lit une base SQLite (`.db`, `.sqlite`) de `workspace/data`, ouverte
en lecture seule, ou une base PostgreSQL / MySQL par son URL de connexion, par exemple
`postgresql+psycopg://utilisateur@localhost:5432/base`. Ces bases demandent un pilote :
`uv pip install sqlalchemy "psycopg[binary]"` (PostgreSQL) ou `uv pip install sqlalchemy pymysql`
(MySQL), dans le dossier de KataML.

!!! tip "Mot de passe"
    Écrivez `$DATABASE_URL` à la place de l'URL : elle est lue dans la variable
    d'environnement du même nom (`export DATABASE_URL=…` avant de lancer KataML), et aucun
    mot de passe n'est enregistré dans le workflow.

## Exporter en Python

![Export Python](../../assets/screenshots/fr/dialog-export.png){ .shot }

KataML traduit le workflow en code pandas / scikit-learn, nœud par nœud, dans l'ordre
d'exécution :

- **Script** `.py` : autonome, exécutable avec `python mon_workflow.py` ;
- **Notebook** `.ipynb` : une cellule par nœud, précédée d'un titre ; les annotations
  deviennent des cellules de texte.

Lire l'export d'un workflow que l'on a construit montre comment chaque nœud s'écrit en
scikit-learn.

## Arrêter un calcul

Les calculs tournent dans un processus séparé. **Arrêter** l'interrompt immédiatement
(même au milieu d'un long entraînement) puis le relance ; les résultats déjà obtenus sont
conservés grâce au cache. Voir [Exécution et cache](../concepts/execution.md).
