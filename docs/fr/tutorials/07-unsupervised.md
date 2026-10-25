# 7. Apprentissage non supervisé

!!! abstract "Objectifs"
    - Regrouper des données sans étiquette avec les k-moyennes et un mélange gaussien.
    - Visualiser des données à 4 dimensions grâce à l'ACP.
    - Détecter des anomalies avec `IsolationForest`.

    Prérequis : [tutoriel 1](01-first-workflow.md). Durée : 30 min.

## Apprendre sans cible

En apprentissage non supervisé, il n'y a pas de réponse à prédire : on cherche une
structure dans les données, qu'il s'agisse de groupes, de directions principales ou de
points atypiques. Les nœuds correspondants ne demandent donc pas de colonne cible ; ils
ajoutent une colonne à la table, par exemple un numéro de cluster ou un indicateur
d'anomalie.

## Étape 1 : des données à 4 dimensions

1. Ajoutez un **Jeu de données scikit-learn** réglé sur `make_blobs`, avec **Nombre
   d'échantillons** `600`, **Nombre de variables** `4`, **Nombre de classes / centres** `4`
   et **Graine aléatoire** `7`.
2. Le générateur fournit l'appartenance réelle de chaque point dans `target`. Pour
   travailler comme si elle était inconnue, retirez-la avec un **Filtre de colonnes**
   (**Mode** *Retirer la sélection*, colonne `target`).
3. Ajoutez un **StandardScaler** sans cible. Les k-moyennes reposent sur des distances, et
   les variables doivent donc avoir la même échelle.

## Étape 2 : les k-moyennes

Ajoutez **KMeans** (Apprentissage non supervisé › Clustering) avec `n_clusters` = `4`,
`n_init` = `10` et `random_state` = `0`, puis exécutez.

![KMeans](../../assets/screenshots/fr/tuto-kmeans.png){ .shot }

La table reçoit une colonne `Cluster` (de 0 à 3). La vue indique la taille de chaque
cluster et le coefficient de silhouette, ici 0,77 sur une échelle de −1 à 1 : plus il est
proche de 1, plus chaque point est proche de son cluster et éloigné des autres.

??? question "Comment choisir le nombre de clusters quand on ne le connaît pas ?"
    En essayant plusieurs valeurs de `n_clusters` (de 2 à 8) et en comparant la silhouette,
    qui culmine au bon nombre quand les groupes sont nets. Sur des données réelles, il
    n'existe souvent pas de nombre unique : le choix dépend de l'usage.

## Étape 3 : visualiser les clusters par ACP

Quatre dimensions ne se dessinent pas. L'analyse en composantes principales projette les
données sur les directions de plus grande variance.

1. Ajoutez **PCA** (Apprentissage non supervisé › Décomposition) sur la sortie de KMeans,
   avec `n_components` = `2` et **Colonnes** `x0`, `x1`, `x2`, `x3`, afin de ne pas
   transformer `Cluster`.
2. Ajoutez un **Nuage de points** : **Axe X** `pca0`, **Axe Y** `pca1`, **Couleur**
   `Cluster`.

![Clusters projetés par ACP](../../assets/screenshots/fr/tuto-pca-clusters.png){ .shot }

Les quatre groupes apparaissent bien séparés, chacun dans sa couleur. La vue de PCA donne la
part de variance expliquée par chaque composante ; plus elle est élevée, plus la projection
est fidèle.

## Étape 4 : un mélange gaussien

Ajoutez **GaussianMixture** (Apprentissage non supervisé › Mélanges gaussiens) sur la table
normalisée, avec `n_components` = `4`, `random_state` = `0` et **Nom de la colonne de
cluster** `Composante`. Un mélange gaussien est un modèle probabiliste : chaque groupe y est
une loi normale de forme propre (une ellipse), et chaque point reçoit une probabilité
d'appartenance à chaque groupe. Sur ces données bien séparées, il retrouve les mêmes groupes
que les k-moyennes.

## Étape 5 : détecter les anomalies

Ajoutez **IsolationForest** (Apprentissage non supervisé › Détection de nouveautés et
d'anomalies) sur la table normalisée, avec `contamination` = `0.03` (proportion attendue
d'environ 3 % de points atypiques) et `random_state` = `0`. Reliez-lui un **Nuage de
points** : **Axe X** `x0`, **Axe Y** `x1`, **Couleur** `Anomalie`.

![Anomalies](../../assets/screenshots/fr/tuto-outliers.png){ .shot }

Les points marqués `1` se trouvent en périphérie des groupes. La méthode construit une forêt
d'arbres qui coupent l'espace au hasard : un point isolé en peu de coupes est jugé atypique.
La colonne de score classe les points du plus au moins suspect.

!!! example "Dans scikit-learn"
    ```python
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA
    from sklearn.ensemble import IsolationForest
    from sklearn.metrics import silhouette_score

    Xs = StandardScaler().fit_transform(X)
    labels = KMeans(n_clusters=4, n_init=10, random_state=0).fit_predict(Xs)
    print(silhouette_score(Xs, labels))
    proj = PCA(n_components=2).fit_transform(Xs)
    outlier = IsolationForest(contamination=0.03, random_state=0).fit_predict(Xs) == -1
    ```

## À vous de jouer

- [ ] Relancez KMeans avec 2, 3, 5 et 6 clusters en relevant chaque fois la silhouette.
- [ ] Gardez `target` en l'excluant seulement du StandardScaler et de KMeans (par leurs
  listes de colonnes), puis colorez le nuage de l'ACP par `target`, puis par `Cluster`. Les
  clusters correspondent-ils aux groupes réels ? Les numéros de cluster, eux, sont
  arbitraires.
- [ ] Remplacez KMeans par **DBSCAN** ou **AgglomerativeClustering**.
- [ ] Comparez avec l'exemple **Clustering : k-moyennes et ACP**, qui applique la même
  démarche à d'autres données.

## Exemples corrigés

**Ouvrir › Exemples › Non supervisé : clusters et anomalies**, et **Clustering :
k-moyennes et ACP**.

![Exemple corrigé](../../assets/screenshots/fr/11_non_supervise-canvas.png){ .shot }
