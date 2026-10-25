# 6. Régler les hyperparamètres

!!! abstract "Objectifs"
    - Chercher les meilleurs hyperparamètres avec `GridSearchCV`.
    - Lire une courbe d'apprentissage pour savoir si davantage de données aiderait.
    - Comprendre pourquoi le meilleur score d'une recherche est optimiste, et mener une
      validation croisée imbriquée.

    Prérequis : tutoriels [2](02-leakage.md) et [5](05-overfitting.md). Durée : 40 min.

## Les données et le modèle

Le **Jeu de données scikit-learn** `breast_cancer` décrit 569 tumeurs par 30 mesures
d'images ; la cible est bénigne ou maligne (37 % de tumeurs malignes). Le modèle est une
machine à vecteurs de support (`SVC`, noyau RBF). Ce modèle est très sensible à l'échelle
des variables : il est précédé d'un **StandardScaler** (cible `target`), et les deux sont
réunis dans un **Pipeline** dont la table brute est le jeu de données.

Deux hyperparamètres gouvernent le SVC à noyau RBF. `C` fixe le coût des erreurs
d'apprentissage : une grande valeur donne une frontière qui colle aux données, une petite
valeur une frontière plus lisse, plus régularisée. `gamma` règle la portée de l'influence de
chaque point : plus il est grand, plus cette influence est locale et la frontière
irrégulière.

## Étape 1 : situer `C` avec une courbe de validation

Ajoutez une **Courbe de validation**, avec **Modèle** relié au Pipeline et **Table** au jeu
de données. Réglez **Hyperparamètre** sur `model__C`, **Valeurs testées** sur
`[0.001, 0.01, 0.1, 1, 10, 100, 1000]` et cochez **Échelle logarithmique**.

| `C` | apprentissage | validation |
|---|---|---|
| 0,001 à 0,01 | 0,627 | 0,627 |
| 0,1 | 0,956 | 0,949 |
| 1 | 0,987 | 0,977 |
| 100 à 1000 | 1,000 | 0,963 |

??? question "Pourquoi exactement 0,627 pour les petites valeurs de `C` ?"
    C'est la proportion de tumeurs bénignes : trop régularisé, le modèle prédit « bénigne »
    pour toutes les tumeurs. C'est un cas extrême de sous-apprentissage.

## Étape 2 : la recherche sur grille

Ajoutez **Recherche d'hyperparamètres**, avec **Modèle (configuration)** relié au Pipeline
et **Table** au jeu de données, et la **Grille de paramètres** suivante :

```json
{
  "model__C": [0.1, 1, 10, 100],
  "model__gamma": ["scale", 0.01, 0.001]
}
```

Choisissez la **Métrique** `roc_auc` et 5 plis. Chacune des 12 combinaisons (4 × 3) est
évaluée en validation croisée, soit 60 ajustements.

![Recherche sur grille](../../assets/screenshots/fr/tuto-grid.png){ .shot }

La meilleure combinaison est `C = 10`, `gamma = 0.01`, avec une AUC de 0,996. Les six
premières combinaisons du classement se tiennent entre 0,994 et 0,996 ; ces écarts d'au plus
0,002 restent bien inférieurs à l'écart-type entre plis (0,005) et ne sont pas
significatifs. Retenir la plus régularisée d'entre elles (ici `C = 1`, `gamma = "scale"`,
deuxième du classement) est un choix raisonnable.

La sortie **Meilleur modèle** est le Pipeline réentraîné sur toutes les données avec ces
réglages ; **Résultats** contient le tableau complet `cv_results_`.

!!! tip "Grilles plus grandes"
    Avec beaucoup d'hyperparamètres, la **Stratégie de recherche** **Aléatoire
    (RandomizedSearchCV)**, avec un nombre d'**Itérations** fixé, explore un grand espace
    bien plus efficacement pour le même coût.

## Étape 3 : l'effet de la taille des données

Ajoutez une **Courbe d'apprentissage**, avec **Modèle** relié au meilleur modèle et
**Table** au jeu de données.

![Courbe d'apprentissage](../../assets/screenshots/fr/tuto-learning-curve.png){ .shot }

Le score de validation passe de 0,94 avec 45 exemples à 0,98 avec 455, puis se stabilise,
et l'écart avec l'apprentissage reste faible. Collecter davantage de données n'apporterait
presque rien ; pour progresser, il faudrait de meilleures variables.

??? question "À quoi ressemblerait la courbe d'un modèle qui manque de données ?"
    La courbe de validation monterait encore à droite et resterait nettement sous la courbe
    d'apprentissage : chaque exemple supplémentaire améliorerait le modèle.

## Étape 4 : évaluer le modèle réglé

Reliez une **Validation croisée** au meilleur modèle : elle donne une AUC de 0,996 et une
exactitude de 0,979. Ce score est légèrement optimiste, car les hyperparamètres ont été
choisis parce qu'ils réussissaient sur ces mêmes plis ; c'est une forme atténuée de fuite
d'information. Deux méthodes l'évitent.

La première consiste à partitionner d'abord : la recherche se fait sur l'apprentissage
seulement, puis le Prédicteur et l'évaluation sur le test, qui n'a servi à aucun choix.

La seconde est la validation croisée imbriquée : la recherche est refaite à l'intérieur de
chaque pli d'une validation croisée externe. Branchez une seconde **Validation croisée** sur
la troisième sortie du nœud de recherche, **Recherche (configuration)**, et sur la même
table.

![Validation croisée imbriquée](../../assets/screenshots/fr/tuto-nested.png){ .shot }

| Évaluation | Exactitude | AUC |
|---|---|---|
| CV du meilleur modèle (optimiste) | 0,979 | 0,996 |
| CV imbriquée | 0,975 | 0,995 |

La vue de la validation imbriquée liste aussi les hyperparamètres retenus dans chaque pli :
`C = 10` quatre fois, `C = 1` une fois. Elle évalue donc la procédure de réglage
(« chercher le meilleur `C` sur cette grille ») et non un réglage particulier, et c'est son
score qu'il faut annoncer comme performance attendue.

L'optimisme reste faible dans cet exemple (12 combinaisons aux scores très proches). Il
grandit avec le nombre de combinaisons testées et la rareté des données, comme le montre le
troisième exercice ci-dessous.

!!! example "Dans scikit-learn"
    ```python
    from sklearn.model_selection import GridSearchCV, cross_validate, learning_curve
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import SVC

    pipe = Pipeline([("prep1", StandardScaler()), ("model", SVC())])
    grid = {"model__C": [0.1, 1, 10, 100], "model__gamma": ["scale", 0.01, 0.001]}
    search = GridSearchCV(pipe, grid, cv=5, scoring="roc_auc").fit(X, y)
    print(search.best_params_, search.best_score_)
    sizes, train, valid = learning_curve(search.best_estimator_, X, y, cv=5)
    nested = cross_validate(GridSearchCV(pipe, grid, cv=5), X, y, cv=5)   # imbriquée
    ```

## À vous de jouer

- [ ] Appliquez la première méthode : Partitionnement stratifié, recherche sur
  l'apprentissage, évaluation sur le test.
- [ ] Ajoutez `"model__kernel": ["rbf", "linear"]` à la grille. Combien de combinaisons
  sont testées ? Le noyau linéaire fait-il aussi bien ?
- [ ] Générez des données de pur hasard avec un **Script Python**, comme au
  [tutoriel 2](02-leakage.md) mais avec 60 lignes et 50 variables (`size=(60, 50)`,
  `range(50)`, `size=60`). Construisez un Pipeline **SelectKBest** (cible `target`) et
  **KNeighborsClassifier**, puis lancez une recherche sur la grille
  `{"prep1__SelectKBest__k": [1, 2, 3, 5, 10, 20, 50], "model__n_neighbors": [1, 3, 5, 7, 9, 15]}`.
  Comparez le meilleur score de la recherche (environ 0,68) à celui de la validation
  imbriquée (environ 0,57, proche du hasard). Que remarquez-vous dans les hyperparamètres
  retenus à chaque pli ?
- [ ] Refaites la recherche en mode aléatoire, avec 8 itérations et davantage de valeurs de
  `C` (`[0.1, 0.3, 1, 3, 10, 30, 100]`).

## Exemple corrigé

**Ouvrir › Exemples › Réglage d'hyperparamètres**.

![Exemple corrigé](../../assets/screenshots/fr/05_reglage_hyperparametres-canvas.png){ .shot }
