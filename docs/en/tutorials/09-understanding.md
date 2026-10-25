# 9. Understanding a model

!!! abstract "Objectives"
    - Measure feature importance by permutation and know its limits.
    - Read a partial dependence curve.
    - Draw a tree and a decision boundary.

    Prerequisites: tutorials [1](01-first-workflow.md) and [5](05-overfitting.md). Time: 40 min.

## The model under study

Build the following workflow: **scikit-learn dataset** `Breast cancer` (569 tumours, 30
measurements, target `benign` or `malignant`), **train_test_split** (test `0.25`,
stratified by `target`, seed `0`), **RandomForestClassifier** (`n_estimators` = `200`,
`random_state` = `0`), then a Predictor and Classification metrics on the test set. Accuracy
is 0.958: a single malignant tumour missed out of 53, and five false alarms.

A forest of 200 trees cannot be read directly. scikit-learn's inspection tools
(`sklearn.inspection`) examine its decisions from several angles.

## Step 1: feature importance

Add **permutation_importance** (Inspection), with **Model** connected to the forest,
**Table** to the **Test** output and **Repeats** `10`.

![Permutation importance](../../assets/screenshots/en/tuto-importance.png){ .shot }

The method shuffles one column of the test set at random, which breaks its link with the
target, and measures the resulting drop in score. An important feature makes the score
fall; a useless one leaves it unchanged. The operation is repeated, hence the error bars.

The drops observed are very small (under 0.01): no feature is indispensable, although the
model does use these measurements. The 30 features are highly correlated, since the radius,
perimeter and area of a tumour vary together. When `worst perimeter` is scrambled, the
forest finds the same information in `worst radius` or `worst area`.

!!! warning "Limits of permutation importance"
    - With correlated features, importance is shared between them or vanishes: a low
      importance does not mean a feature is useless.
    - It is computed on the test set; on the training set, it also measures what the model
      has learnt by heart.
    - Impurity-based importance (`feature_importances_`, visible in the forest's **Model**
      tab) favours features with many distinct values; permutation importance is more
      reliable.

??? question "How to measure the importance of a group of correlated features?"
    By removing the whole group (Column filter) and comparing cross-validation scores with
    and without it. Correlated features can also be clustered, keeping only one per group
    before interpreting.

## Step 2: direction of the effect

Importance measures the size of an effect, not its direction. Add **partial_dependence**
(Inspection), with **Model** connected to the forest, **Table** to the **Test** output and
**Features** `worst area`, `worst concave points`, `mean texture`.

![Partial dependence](../../assets/screenshots/en/tuto-pdp.png){ .shot }

Each curve shows the mean predicted probability of malignancy as one feature varies, the
others keeping their observed values. For `worst area`, it goes from 0.35 to 0.53: the
larger the tumour, the more the model leans towards “malignant”, with a marked threshold.
The effect of `mean texture` is weak. Correlations dampen the effects here too, since an
area that grows at constant radius does not exist in reality.

## Step 3: read a tree

Add **plot_tree / export_text** (Inspection), with **Model** connected to the forest,
**Tree index** `0` and **Displayed depth** `3`.

![A tree of the forest](../../assets/screenshots/en/tuto-tree.png){ .shot }

The chart gives the rules of the first of the 200 trees: each node tests a feature, each
leaf gives a class and its proportion. The full tree has 8 levels and 19 leaves, and the
forest makes 200 such trees vote, each trained on a different sample. A single tree is easy
to read; the forest, more accurate, can no longer be read directly. This is the usual
trade-off between interpretability and performance.

## Step 4: the decision boundary in two dimensions

Add **DecisionBoundaryDisplay**, with **Model** connected to the forest, **Table** to the
**Test** output, **X axis** `worst area` and **Y axis** `worst concave points`. Since the
model uses 30 features, the other 28 are fixed at their median to draw in two dimensions;
the list of these values appears under the map. The map shows how the decision depends on
the two chosen measurements, all else being equal.

!!! example "In scikit-learn"
    ```python
    from sklearn.inspection import permutation_importance, PartialDependenceDisplay
    from sklearn.tree import plot_tree

    r = permutation_importance(forest, X_test, y_test, n_repeats=10, random_state=0)
    PartialDependenceDisplay.from_estimator(
        forest, X_test, ["worst area", "worst concave points", "mean texture"])
    plot_tree(forest.estimators_[0], max_depth=3, feature_names=X.columns)
    ```

## Shapley values

Shapley values (`shap` library) explain each individual prediction. They are not part of
scikit-learn, but can be added as a [custom block](../blocks.md) if `shap` is installed in
the same environment. Permutation importance and partial dependence cover most global
explanation needs.

## Your turn

- [ ] Compute importance on the training set instead of the test set. What changes?
- [ ] Replace the forest by a depth-3 **DecisionTreeClassifier** and compare accuracy and
  readability.
- [ ] Keep only the 10 `mean …` features (Column filter). Does permutation importance become
  clearer?
- [ ] Add **LogisticRegression** in a Pipeline with StandardScaler and examine its
  coefficients in the **Model** tab. What does their sign mean?

## Solution example

**Open › Examples › Understanding a model**.

![Solution example](../../assets/screenshots/en/12_comprendre_modele-canvas.png){ .shot }
