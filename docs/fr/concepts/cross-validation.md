# Validation croisée

## Principe

Un découpage unique en apprentissage et test donne un score qui dépend du hasard de ce
découpage. La validation croisée divise la table en plis ; le modèle est entraîné plusieurs
fois, et chaque fois testé sur un pli différent. On obtient une moyenne et un écart-type du
score, bien plus fiables qu'une valeur isolée.

## Nœuds concernés

| Nœud | Rôle |
|---|---|
| **Validation croisée** (`cross_validate`) | scores d'apprentissage et de test par pli, pour une ou plusieurs métriques |
| **Prédictions hors pli** (`cross_val_predict`) | prédiction de chaque ligne par un modèle qui ne l'a pas vue, à relier aux nœuds d'évaluation |
| **Comparer des modèles** | jusqu'à 6 modèles évalués sur les mêmes plis, avec classement et dispersion |
| **Test de permutation** (`permutation_test_score`) | comparaison du score à celui obtenu sur des cibles mélangées (p-valeur) |
| **Recherche d'hyperparamètres** | `GridSearchCV` / `RandomizedSearchCV` ; sortie « Recherche » pour la validation imbriquée |
| **Courbe d'apprentissage**, **Courbe de validation** | score en fonction de la taille des données ou d'un hyperparamètre |

Tous prennent en entrée un modèle (configuration) et une table : les réglages du modèle sont
repris (`clone`) et il est réentraîné sur chaque pli. Avec un Pipeline en entrée, la
préparation des données est elle aussi réapprise dans chaque pli.

## Stratégies

Le groupe **Validation croisée** de ces nœuds propose toutes les stratégies de
`sklearn.model_selection` :

| Stratégie | Usage |
|---|---|
| **Automatique** | `StratifiedKFold` en classification (proportions de classes conservées), `KFold` sinon |
| `KFold`, `StratifiedKFold` | cas général |
| `RepeatedKFold`, `RepeatedStratifiedKFold` | plusieurs répétitions de k plis avec des découpages différents, pour une estimation plus stable |
| `ShuffleSplit`, `StratifiedShuffleSplit` | tirages aléatoires indépendants de l'apprentissage et du test |
| `GroupKFold`, `StratifiedGroupKFold`, `GroupShuffleSplit`, `LeaveOneGroupOut` | données groupées (plusieurs lignes par patient, client, site…) : un groupe ne doit jamais se trouver des deux côtés |
| `TimeSeriesSplit` | séries temporelles : le futur est toujours prédit à partir du passé |
| `LeaveOneOut` | très petits jeux de données (un modèle par ligne, donc coûteux) |

Les paramètres associés sont le nombre de plis (`n_splits`), le nombre de répétitions, la
part de test (stratégies ShuffleSplit), la colonne de groupes (stratégies par groupes), le
mélange et la graine.

!!! warning "Données groupées et temporelles"
    Si une même personne apparaît sur plusieurs lignes, un `KFold` ordinaire en place
    certaines en apprentissage et d'autres en test ; le modèle reconnaît la personne et le
    score est trop optimiste. Il faut alors une stratégie par groupes. Pour des données
    datées, on utilise `TimeSeriesSplit`, et un partitionnement sans mélange.

## Validation croisée imbriquée

Le meilleur score d'une recherche d'hyperparamètres est optimiste : les réglages ont été
retenus parce qu'ils réussissaient sur ces plis-là. Pour estimer la performance de toute la
démarche (« régler, puis entraîner »), on imbrique deux boucles. La boucle interne est la
recherche elle-même, avec la stratégie de découpage du nœud **Recherche
d'hyperparamètres** ; elle choisit les réglages. La boucle externe est une **Validation
croisée** qui évalue la recherche complète sur des plis qu'elle n'a jamais vus.

Dans KataML, reliez la sortie **Recherche (configuration)** du nœud de recherche à une
**Validation croisée** (ou à une comparaison de modèles, une courbe d'apprentissage…), avec
la même table. La recherche est refaite dans chaque pli externe, et la vue indique les
hyperparamètres retenus dans chaque pli. La sortie **Meilleur modèle** transmet au contraire
un réglage figé, dont la réévaluation donne un score optimiste.

```text
Pipeline ──▶ Recherche d'hyperparamètres ── Recherche (configuration) ──▶ Validation croisée
              (boucle interne : choisir)                                 (boucle externe : évaluer)
```

!!! note "Groupes"
    La boucle externe peut utiliser une stratégie par groupes, mais pas la recherche
    interne, pour laquelle il faut choisir une autre stratégie.

Voir le [tutoriel 6](../tutorials/06-tuning.md).

## Métriques

Le paramètre **Métriques** accepte tous les noms de `sklearn.metrics.get_scorer_names()` :
`accuracy`, `balanced_accuracy`, `f1_macro`, `roc_auc`, `r2`, `neg_root_mean_squared_error`…
Laissé vide, il correspond au score par défaut du modèle : l'exactitude en classification,
le R² en régression. Les métriques d'erreur sont négatives (`neg_…`), de sorte qu'une valeur
plus grande soit toujours meilleure.
