# Nodes, ports and models

## Nodes

A node receives inputs, applies an operation set by its parameters and produces outputs.
There are two families.

Nodes generated from scikit-learn each correspond to an estimator (`LogisticRegression`,
`StandardScaler`, `KMeans`, `IsolationForest`…). Their hyperparameters, types, default
values and help are read from scikit-learn at startup, and so follow the installed version.

KataML's own nodes cover reading and writing files, table manipulation with pandas, charts,
evaluation, cross-validation, model inspection, the Pipeline and reports.

The [node reference](../reference/index.md) describes all of them.

## Ports

| Port | Shape | Content |
|---|---|---|
| table | triangle | a `pandas.DataFrame` |
| model | square | a fitted scikit-learn estimator, with its features (`features`), its target and its classes |

Besides the scikit-learn object, a model port carries the list of expected columns and the
name of the target. The *Predictor* therefore needs no configuration: it applies the model
to the right columns and names the prediction `Prediction (target)`.

## Estimator roles

| Role | Training node | Outputs | Application |
|---|---|---|---|
| classifier, regressor | target and features | model | **Predictor** (`predict`, `predict_proba`) |
| clustering, Gaussian mixture | features | table with the cluster label, model | Predictor (if `predict` exists) |
| transformer (preprocessing, decomposition…) | columns to transform | transformed table, transformer | **Transformer apply** (`transform`) |
| outlier detection | features | table with an *Anomalie* column (1/0) and a score, model | Predictor (novelties) |
| covariance, density, neighbours | features | enriched table (Mahalanobis distance, log-density, neighbours), model | none |
| meta-estimator (voting, stacking, one-vs-rest, RFE, multi-output…) | models connected as inputs | model | Predictor |

## Fit on one table, apply to another

In supervised learning, the model is fitted (`fit`) on training data, then applied
(`predict`, `transform`) to data it has never seen. In KataML, this reads:

```
train_test_split ─ Train ─▶ Training node ─ Model ─▶ Predictor ─▶ Evaluation
                 └ Test ──────────────────────────────────▲
```

Likewise, a transformer fitted on the training set (*Transformer* output) is applied to the
test set with *Transformer apply*: scaling then uses the training means rather than those of
the test set. The [Pipeline](pipeline.md) automates these sequences.

## Target and features

Supervised nodes ask for a target column. Left empty, the **Features** list means all other
columns. Features must be numeric; a text column triggers a message suggesting to encode it
(`OneHotEncoder`, `OrdinalEncoder`) or to exclude it.

Transformers act on the chosen columns (all but the target if the list is empty) and keep
the others, like `ColumnTransformer(remainder="passthrough")`. Setting the target in a
transformer excludes it from the transformation; it is required for supervised transformers
(`SelectKBest`, `LinearDiscriminantAnalysis`…).

## Base estimators and meta-estimators

Some estimators contain others: `BaggingClassifier(estimator=…)`,
`VotingClassifier(estimators=[…])`, `RFE(estimator=…)`, `MultiOutputRegressor(estimator=…)`.
In KataML, the model output of a training node is connected to their base estimator or
“Model 1, 2…” ports. That node's settings are reused (`clone`) and the whole is retrained.
