# Le Pipeline et la fuite d'information

## La fuite d'information

Une évaluation n'est fiable que si les données de test n'ont joué aucun rôle dans
l'apprentissage, préparation des données comprise. Plusieurs pratiques courantes laissent
pourtant le test influencer le modèle :

- normaliser (`StandardScaler`) toute la table avant la validation croisée, si bien que les
  moyennes et écarts-types tiennent compte des plis de test ;
- sélectionner les variables (`SelectKBest`) en regardant toutes les lignes ;
- remplacer les valeurs manquantes par la médiane de toute la table.

Le score obtenu est alors trop optimiste et ne se retrouvera pas sur de nouvelles données.

!!! example "Démonstration (tutoriel 2)"
    Avec une cible tirée au hasard et 2 000 variables de bruit, sélectionner les 20
    « meilleures » variables sur toute la table, puis évaluer par validation croisée, donne
    81 % d'exactitude. Avec un Pipeline, la sélection est refaite dans chaque pli et le
    score tombe à 52 %, le niveau du hasard. Voir le [tutoriel 2](../tutorials/02-leakage.md).

## `sklearn.pipeline.Pipeline`

Un Pipeline enchaîne des transformeurs et un modèle en un seul estimateur. Lorsqu'il est
ajusté, chaque étape l'est sur les seules données d'apprentissage ; lorsqu'il est évalué par
validation croisée, le Pipeline entier est réajusté dans chaque pli.

![Workflow avec Pipeline](../../assets/screenshots/fr/pipeline-workflow.png){ .shot }

## Le nœud Pipeline

| Port d'entrée | À relier à |
|---|---|
| **Table brute** | la table avant prétraitement, avec la cible |
| **Modèle** | la sortie d'un nœud d'apprentissage (ou d'un transformeur, pour un Pipeline de transformation) |
| **Prétraitement 1, 2, 3** | les sorties *Transformeur*, dans l'ordre d'application (facultatives) |

Le nœud reprend les réglages de chaque étape et réentraîne l'ensemble sur la table brute.
Le Pipeline obtenu s'applique directement aux données brutes de test avec le Prédicteur,
sans nœud *Appliquer un transformeur*. Il s'évalue sans fuite avec **Validation croisée**,
**Comparer des modèles**, **Courbe d'apprentissage**, etc. Il se règle avec **Recherche
d'hyperparamètres**, où ses paramètres s'appellent `prep1__<transformeur>__<paramètre>` et
`model__<paramètre>` ; la vue du Pipeline liste tous les paramètres réglables.

![Vue du Pipeline](../../assets/screenshots/fr/pipeline-view.png){ .shot }

### Création depuis la sélection

Sélectionnez les transformeurs et le modèle sur le canevas, puis faites un clic droit ›
**Créer un Pipeline**. Le nœud est ajouté et relié dans le bon ordre (la table brute est
celle qui alimente le premier transformeur), puis contracté, comme décrit plus bas.

### Création depuis une validation croisée

Quand un modèle entraîné sur la sortie d'un prétraitement est relié à une **Validation
croisée**, ou à une comparaison, une recherche d'hyperparamètres, une courbe d'apprentissage
ou de validation, l'inspecteur de ce nœud signale que le prétraitement ne sera pas refait
dans chaque pli.

![Avertissement dans l'inspecteur](../../assets/screenshots/fr/cv-hint.png){ .shot }

Le bouton **Créer le Pipeline et l'utiliser** crée le Pipeline (prétraitements et modèle),
le relie à la place du modèle et, si la table évaluée était une table transformée, la
remplace par la table brute.

### Pipeline contracté

Un Pipeline et ses nœuds « recette » (prétraitements et modèle) forment un
[composant](components.md) réduit : un seul nœud, avec une entrée (la table brute), une
sortie (le Pipeline), et la liste de ses étapes en sous-titre.

![Pipeline contracté](../../assets/screenshots/fr/pipeline-contracted.png){ .shot }

Un double-clic déplie le Pipeline : ses étapes réapparaissent dans un cadre pour être
configurées, et **Réduire** le replie. Un Pipeline construit à la main se contracte par clic
droit › **Contracter le Pipeline**, et **Dissocier** rend les nœuds indépendants.

### Erreurs fréquentes

*« StandardScaler n'accepte que des colonnes numériques… »* : sans colonnes choisies, un
transformeur s'applique à toutes, y compris à une cible textuelle. Indiquez la cible dans
son champ **Cible**, ou choisissez les colonnes à transformer.

*« Le prétraitement transforme la colonne cible »* : un transformeur réglé sur « toutes les
colonnes » a inclus la cible. Indiquez la cible dans ce transformeur.

Lorsque le modèle n'utilisait qu'une partie des colonnes produites, le Pipeline ajoute
automatiquement une étape de sélection (`select`) qui lui fournit exactement ses variables.

## Équivalent Python

```python
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_validate

pipe = Pipeline([
    ("prep1", ColumnTransformer([("scale", StandardScaler(), colonnes)], remainder="passthrough")),
    ("model", RandomForestClassifier(n_estimators=200, random_state=0)),
])
scores = cross_validate(pipe, X, y, cv=5)      # le scaler est réajusté à chaque pli
```

L'export Python de KataML produit ce type de code.
