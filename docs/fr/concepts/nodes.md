# Nœuds, ports et modèles

## Les nœuds

Un nœud reçoit des entrées, leur applique une opération réglée par ses paramètres et
produit des sorties. On en distingue deux familles.

Les nœuds générés depuis scikit-learn correspondent chacun à un estimateur
(`LogisticRegression`, `StandardScaler`, `KMeans`, `IsolationForest`…). Leurs
hyperparamètres, leurs types, leurs valeurs par défaut et leur aide sont lus dans
scikit-learn au démarrage, et suivent donc la version installée.

Les nœuds propres à KataML couvrent la lecture et l'écriture de fichiers, la manipulation
de tables avec pandas, les graphiques, l'évaluation, la validation croisée, l'inspection des
modèles, le Pipeline et les rapports.

La [référence des nœuds](../reference/index.md) les décrit tous.

## Les ports

| Port | Forme | Contenu |
|---|---|---|
| table | triangle | un `pandas.DataFrame` |
| modèle | carré | un estimateur scikit-learn ajusté, avec ses variables (`features`), sa cible et ses classes |

Un port modèle transporte, en plus de l'objet scikit-learn, la liste des colonnes attendues
et le nom de la cible. Le *Prédicteur* n'a donc besoin d'aucun réglage : il applique le
modèle aux bonnes colonnes et nomme la prédiction `Prediction (cible)`.

## Rôles des estimateurs

| Rôle | Nœud d'apprentissage | Sorties | Application |
|---|---|---|---|
| classifieur, régresseur | cible et variables | modèle | **Prédicteur** (`predict`, `predict_proba`) |
| clustering, mélange gaussien | variables | table avec l'étiquette de cluster, modèle | Prédicteur (si `predict` existe) |
| transformeur (prétraitement, décomposition…) | colonnes à transformer | table transformée, transformeur | **Appliquer un transformeur** (`transform`) |
| détection d'anomalies | variables | table avec une colonne *Anomalie* (1/0) et un score, modèle | Prédicteur (nouveautés) |
| covariance, densité, voisins | variables | table enrichie (distance de Mahalanobis, log-densité, voisins), modèle | aucune |
| méta-estimateur (vote, empilement, un-contre-tous, RFE, multisortie…) | modèles branchés en entrée | modèle | Prédicteur |

## Ajuster sur une table, appliquer à une autre

En apprentissage supervisé, le modèle est ajusté (`fit`) sur des données d'apprentissage,
puis appliqué (`predict`, `transform`) à des données qu'il n'a jamais vues. Dans KataML,
cela donne :

```
Partitionnement ─ Apprentissage ─▶ Nœud d'apprentissage ─ Modèle ─▶ Prédicteur ─▶ Évaluation
                └ Test ─────────────────────────────────────────────▲
```

De même, un transformeur ajusté sur l'apprentissage (sortie *Transformeur*) s'applique au
test avec *Appliquer un transformeur* : la normalisation utilise alors les moyennes de
l'apprentissage et non celles du test. Le [Pipeline](pipeline.md) automatise ces
enchaînements.

## Cible et variables

Les nœuds supervisés demandent une colonne cible. Laissée vide, la liste **Variables
explicatives** désigne toutes les autres colonnes. Les variables doivent être numériques ;
une colonne de texte déclenche un message qui propose de l'encoder (`OneHotEncoder`,
`OrdinalEncoder`) ou de l'exclure.

Les transformeurs agissent sur les colonnes choisies (toutes sauf la cible si la liste est
vide) et conservent les autres, comme `ColumnTransformer(remainder="passthrough")`.
Indiquer la cible dans un transformeur l'exclut de la transformation ; c'est obligatoire
pour les transformeurs supervisés (`SelectKBest`, `LinearDiscriminantAnalysis`…).

## Estimateurs de base et méta-estimateurs

Certains estimateurs en contiennent d'autres : `BaggingClassifier(estimator=…)`,
`VotingClassifier(estimators=[…])`, `RFE(estimator=…)`, `MultiOutputRegressor(estimator=…)`.
Dans KataML, on relie la sortie modèle d'un nœud d'apprentissage à leur port « Estimateur
de base » ou « Modèle 1, 2… ». Les réglages de ce nœud sont repris (`clone`) et l'ensemble
est réentraîné.
