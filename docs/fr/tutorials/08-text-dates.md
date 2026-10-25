# 8. Texte et dates

!!! abstract "Objectifs"
    - Transformer du texte en variables numériques (TF-IDF) et le classer.
    - Extraire des caractéristiques de dates, avec un encodage cyclique.
    - Évaluer correctement un modèle sur des données temporelles.

    Prérequis : tutoriels [2](02-leakage.md) et [4](04-regression.md). Durée : 45 min.

## Partie A : classer des avis clients

### Les données

`avis.csv` contient 900 avis courts et leur sentiment (`positif` ou `négatif`). Beaucoup
sont nuancés (« La livraison était rapide, mais le produit était cassé »), certains
contiennent des négations (« pas terrible », « pas mal »), et quelques étiquettes sont
fausses, comme dans toute annotation réelle.

### Étape 1 : vectoriser

Un modèle ne travaille que sur des nombres ; le texte doit d'abord être converti.

1. Ajoutez un **Lecteur CSV** réglé sur `avis.csv`, puis un **Partitionnement** (test
   `0.25`, stratifié selon `sentiment`, graine `0`).
2. Ajoutez **TfidfVectorizer** (Transformations de données › Extraction de
   caractéristiques) sur l'apprentissage, avec **Colonne de texte** `avis`,
   `ngram_range` = `(1, 2)`, `min_df` = `2` et `max_features` = `2000`.

![TF-IDF](../../assets/screenshots/fr/tuto-text-tfidf.png){ .shot }

Chaque terme du vocabulaire devient une colonne : les mots seuls et, avec
`ngram_range = (1, 2)`, les paires de mots consécutifs (« pas terrible », « très déçu »).
`min_df = 2` écarte les termes présents dans un seul avis. La valeur TF-IDF est élevée quand
un terme est fréquent dans l'avis mais rare dans l'ensemble des avis : « cassé » pèse plus
que « le ». Le vocabulaire compte ici 443 termes.

??? question "Pourquoi les paires de mots sont-elles utiles ?"
    Pris séparément, « pas » et « terrible » sont ambigus, alors que « pas terrible » est
    clairement négatif. Les bigrammes conservent une partie de l'ordre des mots, et donc
    des négations.

### Étape 2 : deux modèles dans des Pipelines

1. Ajoutez **LogisticRegression** (`max_iter` = `1000`) et **MultinomialNB**
   (Apprentissage supervisé › Bayésien naïf), tous deux sur la table vectorisée, avec la
   cible `sentiment`.
2. Créez un **Pipeline** pour chacun : **Table brute** reliée à la sortie
   **Apprentissage**, **Modèle** au modèle, **Prétraitement 1** à la sortie **Transformeur**
   du TfidfVectorizer. Le vocabulaire est ainsi réappris dans chaque pli ; sans Pipeline,
   le vocabulaire et les fréquences tiendraient compte du test, ce qui constituerait une
   fuite.
3. Ajoutez **Comparer des modèles** sur l'apprentissage, avec les deux Pipelines.

![Comparaison texte](../../assets/screenshots/fr/tuto-text-compare.png){ .shot }

| Modèle | Exactitude (5 plis) |
|---|---|
| Pipeline régression logistique | 0,895 ± 0,025 |
| Pipeline bayésien naïf | 0,886 ± 0,025 |

Les deux modèles font jeu égal. Sur le test (Prédicteur et Évaluation classification), la
régression logistique obtient 0,88. En triant la table de prédictions par
`Prediction (sentiment)`, on constate que les erreurs portent surtout sur des avis nuancés
ou mal étiquetés.

## Partie B : prévoir des locations de vélos

### Les données

`velos.csv` rassemble 6 480 relevés horaires d'un service de vélos en libre-service, de
janvier à septembre 2024 : date et heure, température, humidité (`humidite`) et nombre de
locations (`locations`).

### Étape 3 : caractéristiques de dates

Une date brute (`2024-03-14 08:00`) n'est pas exploitable telle quelle. Ajoutez
**Caractéristiques de dates** (Manipulation), avec **Colonnes de dates** `date`,
**Éléments à extraire** `month`, `dayofweek`, `hour`, `is_weekend`, et cochez **Encodage
cyclique (sin/cos)**.

L'encodage cyclique ajoute, pour chaque élément périodique, son sinus et son cosinus. Le
modèle voit alors 23 h et 0 h comme voisines, alors que les nombres 23 et 0 sont éloignés.

```text
heure  →  angle = 2π · heure / 24  →  (sin, cos)       0 h et 23 h : points voisins du cercle
```

### Étape 4 : partitionner dans le temps

Ajoutez un **Partitionnement** avec un test de `0.25` et **Mélanger** décoché. Le test
couvre alors la fin de la période, de fin juillet à fin septembre : le modèle est évalué
comme il sera utilisé, en prévoyant l'avenir à partir du passé.

!!! warning "Données temporelles"
    Mélanger avant de découper placerait dans l'apprentissage des heures voisines de celles
    du test. Le modèle interpolerait au lieu de prévoir, et le score serait trop optimiste.
    Pour une validation croisée, utilisez la stratégie `TimeSeriesSplit`.

### Étape 5 : modèle et évaluation

Ajoutez **HistGradientBoostingRegressor** avec la cible `locations`, `max_iter` = `300` et
`learning_rate` = `0.08`, puis un Prédicteur sur le test et une **Évaluation régression** :
le R² atteint 0,987 et la MAE 12,5 locations par heure.

??? question "Pourquoi la MAPE (erreur relative moyenne) est-elle démesurée ?"
    La MAPE divise chaque erreur par la valeur réelle. Certaines heures de nuit comptent
    zéro location, et la division par une valeur nulle ou presque fait exploser la moyenne.
    La MAPE ne convient pas aux cibles qui peuvent valoir zéro ; la MAE ou la RMSE sont
    préférables.

### Étape 6 : le rôle de l'heure dans le modèle

Ajoutez **Importance des variables** et **Dépendance partielle** (variables `date_hour`,
`temperature`, `humidite`) sur le test.

![Dépendance partielle](../../assets/screenshots/fr/tuto-dates-pdp.png){ .shot }

La température a un effet fort et presque linéaire : de 12 à 24 °C, les locations prédites
augmentent d'environ 38 par heure.

L'heure est de loin la variable la plus importante, mais l'information se répartit entre
`date_hour`, `date_hour_sin` et `date_hour_cos`. La courbe de dépendance de `date_hour`
seule montre les pointes de 8 h et de 16 à 18 h, mais atténuées, car faire varier
`date_hour` en gardant son sinus et son cosinus fixes ne correspond à aucune situation
réelle. Avec des variables redondantes, l'importance et la dépendance partielle
s'interprètent par groupe de variables.

!!! example "Dans scikit-learn"
    ```python
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.pipeline import make_pipeline
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import TimeSeriesSplit, cross_val_score

    text_model = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=2000),
                               LogisticRegression(max_iter=1000))
    text_model.fit(train["avis"], train["sentiment"])

    df["date_hour"] = df["date"].dt.hour
    df["date_hour_sin"] = np.sin(2 * np.pi * df["date_hour"] / 24)
    df["date_hour_cos"] = np.cos(2 * np.pi * df["date_hour"] / 24)
    cross_val_score(model, X, y, cv=TimeSeriesSplit(n_splits=5))
    ```

## À vous de jouer

- [ ] Avis : remplacez `ngram_range` par `(1, 1)` (mots seuls). L'exactitude baisse-t-elle ?
- [ ] Avis : essayez **CountVectorizer** à la place de TF-IDF avec le bayésien naïf.
- [ ] Vélos : décochez l'encodage cyclique. Le score change-t-il beaucoup ? Les arbres
  savent découper l'heure en intervalles ; l'encodage cyclique sert surtout aux modèles
  linéaires et aux plus proches voisins.
- [ ] Vélos : remplacez le gradient boosting par **Ridge**, avec et sans encodage cyclique.
- [ ] Vélos : ajoutez une **Validation croisée** avec la stratégie `TimeSeriesSplit`.

## Exemples corrigés

**Ouvrir › Exemples › Texte : classer des avis** et **Dates : locations de vélos**.

![Exemple corrigé (texte)](../../assets/screenshots/fr/07_texte_avis-canvas.png){ .shot }
![Exemple corrigé (dates)](../../assets/screenshots/fr/09_velos_dates-canvas.png){ .shot }
