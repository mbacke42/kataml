# 10. Rapport, export et bloc personnalisé

!!! abstract "Objectifs"
    - Produire un rapport HTML commenté à partir d'un workflow.
    - Exporter le workflow en script Python ou en notebook Jupyter.
    - Écrire un nœud en Python.

    Prérequis : [tutoriel 1](01-first-workflow.md). Durée : 40 min.

Ce tutoriel s'appuie sur l'exemple **Ouvrir › Exemples › Classification des iris**.

## Partie A : le rapport

### Étape 1 : commenter avec des blocs de texte

L'exemple contient deux nœuds **Texte du rapport** (catégorie **Rapport**), intitulés
« Introduction » et « Conclusion ». Sans port, ils ne calculent rien : ils portent un titre
de section et un texte en Markdown (titres `##`, listes, gras, italique, liens). Ajoutez-en
un troisième, « Méthode », qui justifie l'emploi du Pipeline :

```markdown
## Méthode

La normalisation et la forêt aléatoire sont réunies dans un **Pipeline**,
évalué par validation croisée à 5 plis sur les données d'apprentissage.
```

### Étape 2 : générer le rapport

Cliquez sur **Rapport** (++ctrl+p++).

![Boîte de dialogue Rapport](../../assets/screenshots/fr/dialog-report.png){ .shot }

La boîte de dialogue demande un titre et, facultativement, un auteur. Quatre options
contrôlent le schéma du workflow, les annotations, l'aperçu des tables pour les nœuds sans
vue et le script Python en annexe. La liste **Contenu et ordre des sections** propose chaque
nœud comme section : cochez ceux à inclure et ordonnez-les avec les flèches ↑ ↓, en plaçant
« Méthode » après « Introduction ».

**Générer le rapport** exécute les nœuds qui ne l'ont pas encore été, puis enregistre un
fichier dans `workspace/reports`.

![Rapport](../../assets/screenshots/fr/report-page.png){ .shot }

Le rapport est un fichier HTML autonome. Il s'ouvre hors ligne dans n'importe quel
navigateur, ses graphiques restent interactifs au survol, et il s'imprime proprement en PDF
(++ctrl+p++ dans le navigateur). Les choix faits dans la boîte de dialogue sont enregistrés
avec le workflow. Voir [Rapports](../reports.md).

## Partie B : passer au code

**Exporter** affiche le code Python du workflow, avec coloration syntaxique. Le bouton
**Copier** et le bouton **Script `….py`** donnent un script qui refait le workflow avec
pandas et scikit-learn seulement, dans l'ordre d'exécution, une section par nœud. Le bouton
**Notebook `….ipynb`** produit un notebook avec une cellule par nœud, précédée de son titre ;
les annotations du canevas y deviennent des cellules de texte. Le fichier `.json` du
workflow s'exporte, lui, depuis **Ouvrir**.

![Boîte de dialogue Exporter](../../assets/screenshots/fr/dialog-export.png){ .shot }

Le script reprend les objets de scikit-learn utilisés par les nœuds (`Pipeline`,
`cross_validate`, `DecisionBoundaryDisplay`…). On peut ainsi construire une analyse dans
l'interface, puis la poursuivre en Python.

La ligne de commande exécute un workflow sans interface et produit les mêmes fichiers :

```bash
kataml run iris.json --rapport rapport.html --script iris.py --notebook iris.ipynb
```

Voir [Ligne de commande](../cli.md).

## Partie C : écrire un nœud

Cette partie crée un nœud « Écrêtage » qui ramène les valeurs extrêmes des colonnes
numériques à des quantiles choisis (*winsorisation*), une opération absente du catalogue.

### Étape 1 : créer le bloc

1. En haut du dépôt, cliquez sur **Mes blocs**, puis sur **Nouveau bloc**.
2. Renseignez **Nom** `Écrêtage`, **Description** « Limite les valeurs aux quantiles
   choisis », **Entrées** *Une table*, puis cliquez sur **Créer**.

![Mes blocs](../../assets/screenshots/fr/blocks-new.png){ .shot }

Un fichier Python commenté s'ouvre dans l'éditeur intégré.

### Étape 2 : écrire le code

Gardez l'en-tête du fichier (docstring, `import`, `KATAML_EXTENSION`) et remplacez le
décorateur `@register(…)` et la fonction `run` par :

```python
@register(
    "ext.ecretage",
    "Écrêtage",
    "Mes blocs",
    "Limite les valeurs des colonnes numériques aux quantiles choisis (winsorisation).",
    inputs=[("Table", DATA)],
    outputs=[("Table", DATA)],
    params=[
        P("columns", "Colonnes (vide = toutes les numériques)", "columns", [], port=0),
        P("low", "Quantile bas", "float", 0.01),
        P("high", "Quantile haut", "float", 0.99),
    ],
)
def ecretage(ctx, p):
    df = ctx.data(0).copy()
    cols = p["columns"] or list(df.select_dtypes("number").columns)
    check_columns(df, cols)
    if not 0 <= p["low"] < p["high"] <= 1:
        raise NodeError("Il faut 0 ≤ quantile bas < quantile haut ≤ 1.")
    for c in cols:
        df[c] = df[c].clip(df[c].quantile(p["low"]), df[c].quantile(p["high"]))
    return [df]
```

Cliquez sur **Enregistrer et recharger** (++ctrl+s++). Le message « Enregistré et rechargé :
1 nœud(s) » confirme le chargement ; une erreur de syntaxe s'afficherait sous l'éditeur.

![Éditeur de bloc](../../assets/screenshots/fr/blocks-editor.png){ .shot }

### Étape 3 : utiliser le bloc

Le nœud **Écrêtage** apparaît dans le dépôt, catégorie **Mes blocs**. Placé entre un Lecteur
CSV et un nœud Statistiques, il se comporte comme un nœud intégré : formulaire de
configuration, feu d'état, cache, table de sortie. Le paramètre de type `columns` propose
automatiquement les colonnes de la table d'entrée ; choisissez-les de façon à ne pas écrêter
la cible.

!!! tip "Depuis un Script Python"
    Un nœud **Script Python** se convertit en bloc par clic droit › **Convertir en bloc
    réutilisable**.

Les vues, les modèles en entrée, l'export Python et la distribution en paquets sont décrits
dans [Blocs personnalisés](../blocks.md).

## À vous de jouer

- [ ] Ajoutez au bloc une vue indiquant combien de valeurs ont été écrêtées : déclarez
  `has_view=True` dans `register`, puis appelez
  `ctx.add_view({"type": "metrics", "items": [{"label": "Valeurs écrêtées", "value": n}]})`.
- [ ] Générez le rapport du [tutoriel 3](03-csv-cleaning.md) avec le script Python en
  annexe, et imprimez-le en PDF.
- [ ] Exportez un workflow en notebook et exécutez-le dans Jupyter
  (`uvx --with scikit-learn --with pandas jupyter lab`).
