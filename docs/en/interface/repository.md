# Node repository

The repository, on the left, holds every available node. It can be browsed in two ways and
filtered by a search.

<div class="grid" markdown>

![“Guide” view](../../assets/screenshots/en/repository-guide.png){ .shot }

![“API” view](../../assets/screenshots/en/repository-api.png){ .shot }

</div>

## “Guide” view: the scikit-learn chapters

By default, nodes are organised like the
[scikit-learn user guide](https://scikit-learn.org/stable/user_guide.html): one
**category** per chapter, then **families** that follow its sections.

| Category | Content | Example families |
|---|---|---|
| **Essentials** | a selection of the most useful nodes to get started | |
| **Dataset loading** | reading and writing (CSV, scikit-learn datasets, OpenML, models) | |
| **Data manipulation (pandas)** | filters, computed columns, split, sort, joins, dates, Python script | |
| **Visualization** | statistics, scatter plots, histograms, correlations, box plots | |
| **Dataset transformations** | chapter 6 of the guide | Preprocessing data, Imputation of missing values, Feature extraction, Kernel approximation, Random projection, Pipelines and composite estimators |
| **Supervised learning** | chapter 1 | Linear models, Support vector machines, Nearest neighbors, Decision trees, Ensembles, Multiclass and multioutput, Feature selection, Probability calibration, Neural network models… |
| **Unsupervised learning** | chapter 2 | Clustering, Gaussian mixture models, Decomposing signals in components, Manifold learning, Covariance estimation, Novelty and outlier detection, Density estimation |
| **Prediction** | apply a model (`predict`) or a transformer (`transform`) | |
| **Model selection and evaluation** | chapter 3 | Cross-validation, Tuning the hyper-parameters, Tuning the decision threshold, Metrics and scoring, Validation curves |
| **Inspection** | chapter 4 | Partial dependence, Permutation feature importance, Model visualization |
| **Report** | text blocks for reports | |
| **My components** | your saved node groups ([Components](../concepts/components.md)) | |
| **My blocks** | your Python nodes ([Custom blocks](../blocks.md)) | |

!!! info "Where each estimator lives"
    As in scikit-learn, each estimator appears in only one place: for example
    `SelectKBest` is in *Supervised learning › Feature selection* (section 1.13 of the
    guide), `PCA` in *Unsupervised learning › Decomposing signals in components*
    (section 2.5). Search remains the fastest way to find a node.

## “API” view: the Python modules

The **API** button groups nodes by module: `sklearn.linear_model`, `sklearn.ensemble`,
`sklearn.model_selection`… KataML's own nodes (reading, manipulation, visualisation) are
filed under `kataml`. Handy when you already know scikit-learn, or to find a node seen in
a script.

## Search

![Search for “forest”](../../assets/screenshots/en/repository-search.png){ .shot }

The search field filters live, in both languages: class names (`RandomForest`, `pca`),
English or French words (“forest”, “scaling”, “outliers”, “forêt”), modules (`ensemble`).
Results are shown with their family. ++enter++ adds the first result; ++escape++ clears
the search.

## Adding a node

- **Drag and drop** a node from the repository onto the canvas. Dropped onto an existing
  node, it is automatically connected to its first compatible output.
- **Double-click** in the repository: the node is added to the right of the selected node
  and connected to it.
- **Click** once on a repository node to show its description in the inspector, without
  adding it.

You can also add a node directly from the canvas, see [Quick add](canvas.md#quick-add).

## The “My blocks” button

At the top of the repository, **My blocks** opens the custom block manager: create a node
in Python, edit it, reload it. See [Custom blocks](../blocks.md).
