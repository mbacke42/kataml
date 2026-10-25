# 1. First workflow: classifying irises

!!! abstract "Objectives"
    - Build a complete workflow: data, training, prediction, evaluation.
    - Understand why data is split into training and test sets.
    - Read a confusion matrix and a cross-validation.

    Prerequisites: KataML installed ([Installation](../installation.md)). Time: 30 min.

## The data

The *iris* dataset describes 150 flowers of three species (*setosa*, *versicolor*,
*virginica*) by four measurements: length and width of the sepals and petals. The task is to
predict the species from the measurements. This is supervised classification: the model
learns from examples whose answer is known.

## Step 1: load the data

1. Click **New** in the toolbar.
2. In the repository, **Dataset loading** category, drag **scikit-learn dataset** onto the
   canvas (or double-click the canvas background and type “dataset”).
3. The node is selected. In the inspector, set **Dataset** to `Iris`. The light turns
   orange: the node is ready.
4. Press ++f7++. The light turns green and the information line reads `150 × 5`.

The bottom panel shows the table. The **Profile** button shows one card per column:
distribution of the measurements, and three species of 50 flowers each.

??? question "Why is the `species` column of text type?"
    It is the target, a category rather than a measurement. scikit-learn classifiers accept
    text labels directly.

## Step 2: look at the data

1. Drag a connection from the node's output (the triangle on the right) and release it in
   empty space. Quick add then only offers nodes that accept a table. Type “scatter” and
   pick **Scatter plot**, which is connected automatically.
2. Set **X axis** `petal length (cm)`, **Y axis** `petal width (cm)`, **Colour**
   `species`, then run (++f7++).

![Iris scatter plot](../../assets/screenshots/en/tuto-iris-scatter.png){ .shot }

*setosa* is clearly apart; *versicolor* and *virginica* overlap a little, and the model
should sometimes confuse them.

## Step 3: split training and test

Evaluated on the data used to train it, a model always looks good, since it may have learnt
that data by heart. To estimate its performance on flowers it has never seen, part of the
data is kept aside.

1. Add **train_test_split** (category **Data manipulation**) and connect it to the dataset.
2. Set **Test size** `0.25`, **Stratify by** `species` (same species proportions on both
   sides) and **Random state** `42`.
3. Run. The node has two outputs, **Train** (112 rows) and **Test** (38 rows); clicking
   each output port shows the corresponding table.

## Step 4: train a model

1. In the repository, **Supervised learning › Ensembles**, drag
   **RandomForestClassifier**. A random forest makes many decision trees vote.
2. Connect the **Train** output of the split to its input.
3. In the inspector, set **Target column** to `species` and leave **Features** empty (all
   other columns). Under **Hyperparameters**, set `n_estimators` to `200` and
   `random_state` to `0`.
4. Run. The output is a model (square port); clicking it shows its parameters and learned
   attributes (`feature_importances_`…).

!!! info "Hyperparameters"
    Hyperparameters are the model's settings, fixed before training. The inspector's
    **Description** tab reproduces the scikit-learn help for each one, with a link to the
    official documentation. A field left empty keeps the scikit-learn default.

## Step 5: predict and evaluate

1. Add **Predictor** (category **Prediction**). Connect the **Model** output to its
   **Model** input, and the **Test** output of the split to its **Table** input.
2. Run: the test table gets a `Prediction (species)` column.
3. Connect **Classification metrics** (category **Model selection and evaluation**) to it
   and run.

![Evaluation](../../assets/screenshots/en/tuto-iris-eval.png){ .shot }

Accuracy is about 89 %: 34 flowers correctly classified out of 38. The confusion matrix
(rows: true species, columns: predicted species) locates the errors, all between
*versicolor* and *virginica*, as the scatter plot suggested.

??? question "Why is there no error on *setosa*?"
    Its petals are much smaller than those of the other two species: a single rule (“petal
    length < 2.5 cm”) is enough to recognise it.

## Step 6: a finer estimate by cross-validation

With 38 test flowers, one or two more errors move accuracy by 3 to 5 points.
Cross-validation repeats training and evaluation on five different splits.

1. Add **cross_validate** (category **Model selection and evaluation**).
2. Connect the **Model** output to **Model (configuration)** and the **Train** output to
   **Table**. The model is retrained on each fold, with the same settings.
3. Under **Metrics**, tick `accuracy` and `f1_macro`, then run.

![Cross-validation](../../assets/screenshots/en/tuto-iris-cv.png){ .shot }

Cross-validation gives 0.94 ± 0.04. The test score (0.89) lies within that range; it was
only less certain. The training score is 1.0 on every fold, because the forest recognises
the flowers it has seen perfectly: only the test score tells how good the model is.

!!! example "In scikit-learn"
    ```python
    from sklearn.datasets import load_iris
    from sklearn.model_selection import train_test_split, cross_validate
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, confusion_matrix

    df = load_iris(as_frame=True).frame            # KataML renames target to species
    X, y = df.drop(columns="target"), df["target"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, stratify=y, random_state=42)
    model = RandomForestClassifier(n_estimators=200, random_state=0).fit(X_train, y_train)
    y_pred = model.predict(X_test)
    print(accuracy_score(y_test, y_pred), confusion_matrix(y_test, y_pred))
    print(cross_validate(model, X_train, y_train, cv=5, scoring=["accuracy", "f1_macro"]))
    ```
    **Export** produces this code for any workflow.

## Your turn

- [ ] Replace the forest by **KNeighborsClassifier** (Supervised learning › Nearest
  neighbors), connecting it in place of the forest: an input accepts only one connection,
  and the new one replaces the old one. Does the score change?
- [ ] Use only the sepals (**Features** `sepal length (cm)` and `sepal width (cm)`). What
  happens to accuracy, and what does it say about these features?
- [ ] Change the split's seed (`1`, `2`, `3`…), noting the test accuracy each time, then
  compare its spread with the cross-validation standard deviation.

## Solution example

**Open › Examples › Iris classification** contains this workflow with a few additions:
scaling and the forest are combined in a Pipeline (the subject of the next tutorial), a ROC
curve and a decision boundary complete the evaluation, and **Report text** blocks prepare a
report (tutorial 10).

![Solution example](../../assets/screenshots/en/01_classification_iris-canvas.png){ .shot }
