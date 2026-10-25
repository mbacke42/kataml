# The Pipeline and data leakage

## Data leakage

An evaluation is only reliable if the test data played no part in training, data
preparation included. Several common practices nevertheless let the test set influence the
model:

- scaling (`StandardScaler`) the whole table before cross-validation, so that the means and
  standard deviations take the test folds into account;
- selecting features (`SelectKBest`) by looking at every row;
- replacing missing values by the median of the whole table.

The resulting score is too optimistic and will not hold on new data.

!!! example "Demonstration (tutorial 2)"
    With a random target and 2,000 noise features, selecting the 20 “best” features on the
    whole table, then evaluating by cross-validation, gives 81 % accuracy. With a Pipeline,
    selection is redone in each fold and the score falls to 52 %, the chance level. See
    [tutorial 2](../tutorials/02-leakage.md).

## `sklearn.pipeline.Pipeline`

A Pipeline chains transformers and a model into a single estimator. When it is fitted, each
step is fitted on the training data only; when it is evaluated by cross-validation, the
whole Pipeline is refitted in each fold.

![Workflow with a Pipeline](../../assets/screenshots/en/pipeline-workflow.png){ .shot }

## The Pipeline node

| Input port | Connect to |
|---|---|
| **Raw table** | the table before preprocessing, with the target |
| **Model** | the output of a training node (or of a transformer, for a transformation Pipeline) |
| **Preprocessing 1, 2, 3** | the *Transformer* outputs, in order of application (optional) |

The node reuses each step's settings and retrains the whole on the raw table. The resulting
Pipeline applies directly to raw test data with the Predictor, with no *Transformer apply*
node. It is evaluated without leakage by **cross_validate**, **Model comparison**,
**learning_curve**, etc. It is tuned with **GridSearchCV / RandomizedSearchCV**, where its
parameters are named `prep1__<transformer>__<parameter>` and `model__<parameter>`; the
Pipeline view lists every tunable parameter.

![Pipeline view](../../assets/screenshots/en/pipeline-view.png){ .shot }

### Creating it from the selection

Select the transformers and the model on the canvas, then right-click › **Create a
Pipeline**. The node is added and connected in the right order (the raw table is the one
feeding the first transformer), then collapsed, as described below.

### Creating it from a cross-validation

When a model trained on the output of a preprocessing step is connected to a
**cross_validate** node, or to a comparison, a hyperparameter search, a learning or
validation curve, that node's inspector warns that the preprocessing will not be redone in
each fold.

![Warning in the inspector](../../assets/screenshots/en/cv-hint.png){ .shot }

The **Create and use the Pipeline** button creates the Pipeline (preprocessing and model),
connects it instead of the model and, if the evaluated table was a transformed one, replaces
it by the raw table.

### Collapsed Pipeline

A Pipeline and its “recipe” nodes (preprocessing and model) form a collapsed
[component](components.md): a single node, with one input (the raw table), one output (the
Pipeline), and the list of its steps as a subtitle.

![Collapsed Pipeline](../../assets/screenshots/en/pipeline-contracted.png){ .shot }

A double-click expands the Pipeline: its steps reappear in a frame to be configured, and
**Collapse** folds it back. A hand-built Pipeline is collapsed with right-click › **Collapse
the Pipeline**, and **Ungroup** makes the nodes independent again.

### Common errors

*“StandardScaler only accepts numeric columns…”*: with no columns chosen, a transformer
applies to all of them, including a text target. Set the target in its **Target** field, or
choose the columns to transform.

*“The preprocessing transforms the target column”*: a transformer set to “all columns”
included the target. Set the target in that transformer.

When the model only used part of the columns produced, the Pipeline automatically adds a
selection step (`select`) that gives it exactly its features.

## Python equivalent

```python
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_validate

pipe = Pipeline([
    ("prep1", ColumnTransformer([("scale", StandardScaler(), columns)], remainder="passthrough")),
    ("model", RandomForestClassifier(n_estimators=200, random_state=0)),
])
scores = cross_validate(pipe, X, y, cv=5)      # the scaler is refitted in each fold
```

KataML's Python export produces this kind of code.
