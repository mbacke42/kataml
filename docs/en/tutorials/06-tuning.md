# 6. Tuning hyperparameters

!!! abstract "Objectives"
    - Search for the best hyperparameters with `GridSearchCV`.
    - Read a learning curve to tell whether more data would help.
    - Understand why the best score of a search is optimistic, and run a nested
      cross-validation.

    Prerequisites: tutorials [2](02-leakage.md) and [5](05-overfitting.md). Time: 40 min.

## Data and model

The `Breast cancer` **scikit-learn dataset** describes 569 tumours by 30 image measurements;
the target is benign or malignant (37 % malignant). The model is a support vector machine
(`SVC`, RBF kernel). This model is very sensitive to feature scale: it is preceded by a
**StandardScaler** (target `target`), and both are combined in a **Pipeline** whose raw table
is the dataset.

Two hyperparameters govern the RBF-kernel SVC. `C` sets the cost of training errors: a large
value gives a boundary that hugs the data, a small value a smoother, more regularised
boundary. `gamma` sets the reach of each point's influence: the larger it is, the more local
that influence and the more irregular the boundary.

## Step 1: locate `C` with a validation curve

Add a **validation_curve** node, with **Model** connected to the Pipeline and **Table** to
the dataset. Set **Hyperparameter** to `model__C`, **Values tested** to
`[0.001, 0.01, 0.1, 1, 10, 100, 1000]` and tick **Log scale**.

| `C` | training | validation |
|---|---|---|
| 0.001 to 0.01 | 0.627 | 0.627 |
| 0.1 | 0.956 | 0.949 |
| 1 | 0.987 | 0.977 |
| 100 to 1000 | 1.000 | 0.963 |

??? question "Why exactly 0.627 for small values of `C`?"
    It is the proportion of benign tumours: over-regularised, the model predicts “benign”
    for every tumour. This is an extreme case of underfitting.

## Step 2: grid search

Add **GridSearchCV / RandomizedSearchCV**, with **Model (configuration)** connected to the
Pipeline and **Table** to the dataset, and the following **Parameter grid**:

```json
{
  "model__C": [0.1, 1, 10, 100],
  "model__gamma": ["scale", 0.01, 0.001]
}
```

Set **Scoring** to `roc_auc` and 5 folds. Each of the 12 combinations (4 × 3) is evaluated by
cross-validation, 60 fits in total.

![Grid search](../../assets/screenshots/en/tuto-grid.png){ .shot }

The best combination is `C = 10`, `gamma = 0.01`, with an AUC of 0.996. The top six
combinations lie between 0.994 and 0.996; these gaps of at most 0.002 are well below the
between-fold standard deviation (0.005) and are not significant. Keeping the most
regularised of them (here `C = 1`, `gamma = "scale"`, second in the ranking) is a reasonable
choice.

The **Best model** output is the Pipeline retrained on all the data with these settings;
**Results** holds the full `cv_results_` table.

!!! tip "Larger grids"
    With many hyperparameters, the **Randomised (RandomizedSearchCV)** **Search strategy**,
    with a set number of **Iterations**, explores a large space much more efficiently for
    the same cost.

## Step 3: the effect of data size

Add a **learning_curve** node, with **Model** connected to the best model and **Table** to
the dataset.

![Learning curve](../../assets/screenshots/en/tuto-learning-curve.png){ .shot }

The validation score goes from 0.94 with 45 examples to 0.98 with 455, then levels off, and
the gap with training stays small. Collecting more data would bring almost nothing; to
progress, better features would be needed.

??? question "What would the curve of a data-starved model look like?"
    The validation curve would still be rising on the right and stay well below the training
    curve: each additional example would improve the model.

## Step 4: evaluate the tuned model

Connect a **cross_validate** node to the best model: it gives an AUC of 0.996 and an
accuracy of 0.979. This score is slightly optimistic, because the hyperparameters were
chosen for doing well on these same folds; it is a mild form of data leakage. Two methods
avoid it.

The first is to split first: the search runs on the training set only, then the Predictor
and the evaluation run on the test set, which played no part in any choice.

The second is nested cross-validation: the search is redone inside each fold of an outer
cross-validation. Connect a second **cross_validate** node to the third output of the search
node, **Search (configuration)**, and to the same table.

![Nested cross-validation](../../assets/screenshots/en/tuto-nested.png){ .shot }

| Evaluation | Accuracy | AUC |
|---|---|---|
| CV of the best model (optimistic) | 0.979 | 0.996 |
| Nested CV | 0.975 | 0.995 |

The nested view also lists the hyperparameters chosen in each fold: `C = 10` four times,
`C = 1` once. It therefore evaluates the tuning procedure (“search for the best `C` on this
grid”) rather than one setting, and its score is the one to report as expected performance.

The optimism stays small in this example (12 combinations with very close scores). It grows
with the number of combinations tried and the scarcity of data, as the third exercise below
shows.

!!! example "In scikit-learn"
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
    nested = cross_validate(GridSearchCV(pipe, grid, cv=5), X, y, cv=5)   # nested
    ```

## Your turn

- [ ] Apply the first method: stratified train_test_split, search on the training set,
  evaluation on the test set.
- [ ] Add `"model__kernel": ["rbf", "linear"]` to the grid. How many combinations are tried?
  Does the linear kernel do as well?
- [ ] Generate purely random data with a **Python script**, as in [tutorial 2](02-leakage.md)
  but with 60 rows and 50 features (`size=(60, 50)`, `range(50)`, `size=60`). Build a
  Pipeline of **SelectKBest** (target `target`) and **KNeighborsClassifier**, then search
  over the grid
  `{"prep1__SelectKBest__k": [1, 2, 3, 5, 10, 20, 50], "model__n_neighbors": [1, 3, 5, 7, 9, 15]}`.
  Compare the search's best score (about 0.68) with the nested validation score (about
  0.57, close to chance). What do you notice in the hyperparameters chosen in each fold?
- [ ] Redo the search in randomised mode, with 8 iterations and more values of `C`
  (`[0.1, 0.3, 1, 3, 10, 30, 100]`).

## Solution example

**Open › Examples › Hyperparameter tuning**.

![Solution example](../../assets/screenshots/en/05_reglage_hyperparametres-canvas.png){ .shot }
