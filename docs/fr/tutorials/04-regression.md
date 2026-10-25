# 4. Régression : prédire une valeur

!!! abstract "Objectifs"
    - Construire un modèle de régression et lire ses métriques (R², MAE, RMSE).
    - Comparer plusieurs modèles sur les mêmes plis.
    - Comprendre pourquoi un score de test isolé peut induire en erreur.

    Prérequis : [tutoriel 1](01-first-workflow.md). Durée : 30 min.

## Les données

Le jeu *diabetes* de scikit-learn décrit 442 patients par 10 variables : âge, sexe, indice
de masse corporelle `bmi`, pression artérielle `bp` et six mesures sanguines `s1` à `s6`,
déjà centrées et réduites. La cible est une mesure quantitative de la progression de la
maladie un an plus tard ; le modèle prédit un nombre et non une catégorie.

## Étape 1 : explorer

1. Ajoutez un **Jeu de données scikit-learn** réglé sur `diabetes`.
2. Reliez-lui une **Matrice de corrélation** (Visualisation). `bmi` et `s5` sont les
   variables les plus corrélées à `target`, et `s1` et `s2` sont très corrélées entre elles.
3. Ajoutez un **Partitionnement** avec une proportion de test de `0.2` et la graine `0`. On
   ne stratifie pas en régression.

## Étape 2 : deux modèles

| Nœud | Famille | Réglages |
|---|---|---|
| **Ridge** | Modèles linéaires | cible `target`, `alpha` = `1.0` |
| **HistGradientBoostingRegressor** | Ensembles | cible `target`, `max_iter` = `150`, `learning_rate` = `0.05`, `max_depth` = `3`, `min_samples_leaf` = `20` |

`Ridge` est une régression linéaire régularisée : elle pénalise les grands coefficients pour
limiter le surapprentissage. Le *gradient boosting* construit une suite d'arbres, chacun
corrigeant les erreurs des précédents, ce qui lui permet de capter des effets non linéaires
et des interactions.

## Étape 3 : comparer

Ajoutez **Comparer des modèles** (Sélection et évaluation de modèles › Validation croisée),
en reliant **Table** à la sortie **Apprentissage**, **Modèle 1** à Ridge et **Modèle 2** au
gradient boosting, puis exécutez.

![Comparaison](../../assets/screenshots/fr/tuto-compare.png){ .shot }

| Modèle | R² moyen (5 plis) | écart-type |
|---|---|---|
| Gradient boosting | 0,435 | 0,130 |
| Ridge | 0,413 | 0,067 |

L'écart entre les deux modèles (0,02) est bien plus petit que leurs écarts-types : ils sont
à égalité. Le tableau **Scores par pli** montre d'ailleurs que chacun l'emporte sur
certains plis. Ridge est plus stable, et 50 fois plus rapide à entraîner.

!!! info "Le R²"
    Le coefficient de détermination vaut 1 pour des prédictions parfaites et 0 pour un
    modèle qui prédit toujours la moyenne ; il devient négatif pour un modèle plus mauvais
    encore. Un R² de 0,43 signifie qu'environ 43 % de la variance de la progression est
    expliquée : les 10 variables ne suffisent pas à prédire précisément l'évolution d'un
    patient.

## Étape 4 : évaluer sur le test

Ajoutez un **Prédicteur** (gradient boosting et sortie **Test**), puis **Évaluation
régression**.

![Métriques de régression](../../assets/screenshots/fr/tuto-regression-metrics.png){ .shot }

Le R² de test n'est que de 0,19, contre 0,43 en validation croisée. Le modèle n'est pas
en cause : le test ne compte que 89 patients, et le pli 4 de la comparaison donnait déjà un
R² de 0,20. Sur si peu de données, un score de test isolé varie beaucoup ; la moyenne et
l'écart-type de la validation croisée en donnent une idée plus juste.

Les autres métriques s'expriment dans l'unité de la cible :

| Métrique | Valeur | Lecture |
|---|---|---|
| MAE (erreur absolue moyenne) | 48,6 | erreur moyenne de 49 points |
| RMSE (racine de l'erreur quadratique moyenne) | 64,3 | pénalise davantage les grosses erreurs |
| Erreur absolue médiane | 38,8 | la moitié des erreurs est inférieure à 39 points |

Le graphique prédit / réel et l'histogramme des résidus indiquent si les erreurs sont
systématiques, par exemple des valeurs élevées sous-estimées.

??? question "La cible varie de 25 à 346 : une MAE de 49 est-elle grande ?"
    Il faut la comparer à celle d'un modèle naïf. Un **DummyRegressor**, qui prédit la
    moyenne de l'apprentissage, a une MAE d'environ 59 : le modèle réduit l'erreur d'un
    cinquième environ, un gain réel mais modeste.

## Étape 5 : identifier les variables utiles

Ajoutez **Importance des variables** (modèle : gradient boosting ; table : **Test**) et
**Dépendance partielle** (variables `bmi`, `s5`, `bp`). `s5`, `bmi` et `bp` dominent. La
dépendance partielle montre que la progression prédite augmente avec l'IMC de façon presque
linéaire, ce qui explique que Ridge fasse aussi bien. Le [tutoriel 9](09-understanding.md)
détaille ces outils.

!!! example "Dans scikit-learn"
    ```python
    from sklearn.linear_model import Ridge
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.model_selection import KFold, cross_val_score

    cv = KFold(5, shuffle=True, random_state=0)       # les mêmes plis pour tous
    for model in (Ridge(alpha=1.0),
                  HistGradientBoostingRegressor(max_iter=150, learning_rate=0.05,
                                                max_depth=3, min_samples_leaf=20)):
        s = cross_val_score(model, X_train, y_train, cv=cv, scoring="r2")
        print(type(model).__name__, s.mean(), s.std())
    ```

## À vous de jouer

- [ ] Ajoutez **LinearRegression**, **Lasso** et **RandomForestRegressor** à la
  comparaison, qui accepte jusqu'à 6 modèles.
- [ ] Dans la comparaison, passez la stratégie à `RepeatedKFold` (5 plis, 5 répétitions).
  Les écarts-types diminuent-ils ? Le classement change-t-il ?
- [ ] Changez la graine du partitionnement et relevez chaque fois le R² de test. Que
  constatez-vous ?

## Exemple corrigé

**Ouvrir › Exemples › Régression : diabète**.

![Exemple corrigé](../../assets/screenshots/fr/02_regression_diabete-canvas.png){ .shot }
