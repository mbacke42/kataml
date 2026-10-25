# Espace de travail et fichiers

## L'espace de travail

Toutes les données de KataML sont rangées dans un dossier, l'**espace de travail** :

```text
workspace/
  data/        fichiers importés (CSV) et données des exemples
  workflows/   workflows enregistrés (.json)
  components/  composants réutilisables (.json)
  extensions/  blocs personnalisés (.py)
  reports/     rapports générés (.html)
  exports/     sorties des nœuds d'écriture (CSV, modèles)
  openml/      cache des jeux téléchargés depuis OpenML
  .cache/      résultats des nœuds (cache disque)
  theme.css    personnalisation des couleurs (facultatif, voir Apparence)
```

Son emplacement dépend du mode de lancement :

| Lancement | Espace de travail |
|---|---|
| AppImage Linux | `kataml-workspace/`, à côté du fichier `.AppImage` |
| zip Windows | `workspace/`, à côté de `KataML.bat` |
| `uv tool install` | `~/kataml` |
| depuis le dépôt (`kataml.sh`) | `workspace/` dans le dépôt |
| option `--workspace` ou variable `KATAML_WORKSPACE` | le dossier indiqué |

Si le dossier prévu n'est pas inscriptible, KataML se replie sur `~/kataml`.

## Les workflows

Un workflow est un fichier JSON : nœuds (type, position, annotation, paramètres),
connexions, annotations, composants et réglages du rapport. Il est :

- sauvegardé automatiquement dans le navigateur à chaque modification, et restauré au
  lancement suivant ;
- enregistré dans `workspace/workflows` avec ++ctrl+s++ ;
- exporté ou importé en fichier `.json` depuis la boîte **Ouvrir**, pour l'envoyer à
  quelqu'un ou le versionner avec Git.

Les workflows ne contiennent pas les données : un *Lecteur CSV* référence un fichier de
`workspace/data` (ou un chemin absolu). Pour partager un workflow, joignez ses fichiers de
données.

## Les données

- Import d'un CSV : bouton **Importer** du *Lecteur CSV*, ou glisser le fichier sur le
  canevas. Il est copié dans `workspace/data`.
- Téléchargement d'une table : bouton **CSV** du panneau des sorties, ou clic droit sur le
  nœud. Un modèle se télécharge au format joblib.
- Les nœuds **Écriture CSV** et **Écriture de modèle** écrivent dans `workspace/exports`
  (ou un chemin absolu) à chaque exécution, ce qui sert notamment en ligne de commande.

## Sécurité et confidentialité

KataML fonctionne entièrement sur votre machine : aucune donnée n'est envoyée sur
Internet. Seul le nœud *Jeu de données OpenML* télécharge des données depuis openml.org,
quand vous l'exécutez.
