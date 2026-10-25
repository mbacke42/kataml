# 7. Unsupervised learning

!!! abstract "Objectives"
    - Group unlabelled data with k-means and a Gaussian mixture.
    - Visualise 4-dimensional data with PCA.
    - Detect outliers with `IsolationForest`.

    Prerequisites: [tutorial 1](01-first-workflow.md). Time: 30 min.

## Learning without a target

In unsupervised learning there is no answer to predict: the aim is to find structure in the
data, whether groups, main directions or atypical points. The corresponding nodes therefore
ask for no target column; they add a column to the table, such as a cluster number or an
outlier flag.

## Step 1: 4-dimensional data

1. Add a **scikit-learn dataset** set to `Generator: Gaussian blobs` (`make_blobs`), with
   **Number of samples** `600`, **Number of features** `4`, **Number of classes / centers**
   `4` and **Random state** `7`.
2. The generator provides each point's true membership in `target`. To work as if it were
   unknown, remove it with a **Column filter** (**Mode** *Remove selection*, column
   `target`).
3. Add a **StandardScaler** without a target. k-means relies on distances, so the features
   must share the same scale.

## Step 2: k-means

Add **KMeans** (Unsupervised learning › Clustering) with `n_clusters` = `4`, `n_init` = `10`
and `random_state` = `0`, then run.

![KMeans](../../assets/screenshots/en/tuto-kmeans.png){ .shot }

The table gets a `Cluster` column (0 to 3). The view gives the size of each cluster and the
silhouette coefficient, here 0.77 on a scale from −1 to 1: the closer to 1, the closer each
point is to its own cluster and the farther from the others.

??? question "How to choose the number of clusters when it is unknown?"
    By trying several values of `n_clusters` (2 to 8) and comparing the silhouette, which
    peaks at the right number when groups are clear-cut. On real data there is often no
    single number: the choice depends on the use.

## Step 3: visualise the clusters with PCA

Four dimensions cannot be drawn. Principal component analysis projects the data onto the
directions of greatest variance.

1. Add **PCA** (Unsupervised learning › Decomposing signals in components) on the KMeans
   output, with `n_components` = `2` and **Columns** `x0`, `x1`, `x2`, `x3`, so as not to
   transform `Cluster`.
2. Add a **Scatter plot**: **X axis** `pca0`, **Y axis** `pca1`, **Colour** `Cluster`.

![Clusters projected by PCA](../../assets/screenshots/en/tuto-pca-clusters.png){ .shot }

The four groups appear well separated, each in its own colour. The PCA view gives the
explained variance of each component; the higher it is, the more faithful the projection.

## Step 4: a Gaussian mixture

Add **GaussianMixture** (Unsupervised learning › Gaussian mixture models) on the scaled
table, with `n_components` = `4`, `random_state` = `0` and **Cluster column name**
`Composante`. A Gaussian mixture is a probabilistic model: each group is a normal
distribution with its own shape (an ellipse), and each point gets a probability of belonging
to each group. On this well-separated data, it finds the same groups as k-means.

## Step 5: detect outliers

Add **IsolationForest** (Unsupervised learning › Novelty and outlier detection) on the
scaled table, with `contamination` = `0.03` (an expected 3 % or so of atypical points) and
`random_state` = `0`. Connect a **Scatter plot** to it: **X axis** `x0`, **Y axis** `x1`,
**Colour** `Anomalie` (the default name of the outlier column).

![Outliers](../../assets/screenshots/en/tuto-outliers.png){ .shot }

Points marked `1` lie on the outskirts of the groups. The method builds a forest of trees
that cut the space at random: a point isolated in few cuts is considered atypical. The score
column ranks points from most to least suspicious.

!!! example "In scikit-learn"
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

## Your turn

- [ ] Rerun KMeans with 2, 3, 5 and 6 clusters, noting the silhouette each time.
- [ ] Keep `target`, excluding it only from StandardScaler and KMeans (through their column
  lists), then colour the PCA scatter plot by `target`, then by `Cluster`. Do the clusters
  match the true groups? The cluster numbers themselves are arbitrary.
- [ ] Replace KMeans by **DBSCAN** or **AgglomerativeClustering**.
- [ ] Compare with the **Clustering: k-means and PCA** example, which applies the same
  approach to other data.

## Solution examples

**Open › Examples › Unsupervised: clusters and outliers**, and **Clustering: k-means and
PCA**.

![Solution example](../../assets/screenshots/en/11_non_supervise-canvas.png){ .shot }
