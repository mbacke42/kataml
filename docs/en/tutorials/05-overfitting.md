# 5. Overfitting and decision boundaries

!!! abstract "Objectives"
    - Visualise what a model has learnt through its decision boundary.
    - Recognise overfitting and underfitting.
    - Choose a model's complexity with a validation curve.

    Prerequisites: [tutorial 1](01-first-workflow.md). Time: 30 min.

## The data

Add a **scikit-learn dataset** set to `Generator: two moons` (`make_moons`), with **Number of
samples** `400`, **Noise** `0.3` and **Random state** `0`. The table has two features, `x0`
and `x1`, and a 0/1 target. The noise mixes the two classes near the boundary: a model can
only classify everything correctly by learning that noise.

Add a **train_test_split**: test `0.3`, stratified by `target`, seed `0`.

## Step 1: an unconstrained tree

1. Add **DecisionTreeClassifier** (Supervised learning › Decision trees) on the training
   set, with target `target` and `random_state` `0`, and no other setting.
2. Add **DecisionBoundaryDisplay** (Inspection), with **Model** connected to the tree and
   **Table** to the **Test** output, then run.

![Deep tree](../../assets/screenshots/en/tuto-boundary-deep.png){ .shot }

The map colours each point of the plane by predicted class; the dots are the test data. The
tree has cut the plane into a multitude of small rectangles, including isolated islands: it
has learnt every training point, noise included, and its training accuracy is 100 %.

## Step 2: a pruned tree

Duplicate the tree (++ctrl+d++), set `max_depth` to `3` and connect a second decision
boundary to it.

![Depth-3 tree](../../assets/screenshots/en/tuto-boundary-pruned.png){ .shot }

The boundary comes down to a few large rectangles: it is coarser, but no longer follows the
noise. A **plot_tree / export_text** node connected to this model shows 7 leaves and readable
rules (`x1 <= 0.09`…).

## Step 3: compare four models

Add **KNeighborsClassifier** (`n_neighbors` = `15`) and **SVC** (RBF kernel by default), each
with its decision boundary, then **Model comparison** with the four models and the **Train**
output.

| Model | Accuracy (5 folds) |
|---|---|
| RBF SVM | 0.893 ± 0.054 |
| 15 neighbours | 0.889 ± 0.071 |
| Tree (depth 3) | 0.886 ± 0.040 |
| Deep tree | 0.861 ± 0.063 |

The deep tree, perfect on the training set, is the worst on new data: this is overfitting.
The smooth boundaries of the SVM and of the 15 neighbours follow the shape of the moons.

??? question "What happens with `n_neighbors` = 1?"
    With a single neighbour, each training point imposes its class around it and the
    boundary becomes very irregular, like the deep tree's. With 200 neighbours it becomes
    almost straight instead: the model is too simple for the shape of the moons, which is
    underfitting.

## Step 4: the validation curve

To choose `max_depth`, add a **validation_curve** node, with **Model (configuration)**
connected to the deep tree and **Table** to the **Train** output. Set **Hyperparameter** to
`max_depth` and **Values tested** to `[1, 2, 3, 4, 6, 8, 12, None]`.

![Validation curve](../../assets/screenshots/en/tuto-validation-curve.png){ .shot }

The chart draws two curves, each with its standard deviation band. The training score rises
to 1.0 as depth increases. The validation score peaks around 0.89 at depth 2 or 3, then
drops (0.84 at depth 6). The widening gap between the two curves is the signature of
overfitting; on the left (depth 1), both scores are low, which indicates underfitting.

```text
             underfitting        sweet spot          overfitting
score        both low            best validation     train / validation gap
complexity   low ─────────────────────────────────────────────────── high
```

!!! example "In scikit-learn"
    ```python
    from sklearn.model_selection import validation_curve
    from sklearn.inspection import DecisionBoundaryDisplay
    from sklearn.tree import DecisionTreeClassifier

    depths = [1, 2, 3, 4, 6, 8, 12, None]
    train, valid = validation_curve(DecisionTreeClassifier(random_state=0), X_train, y_train,
                                    param_name="max_depth", param_range=depths, cv=5)
    tree = DecisionTreeClassifier(max_depth=3, random_state=0).fit(X_train, y_train)
    DecisionBoundaryDisplay.from_estimator(tree, X_test)
    ```

## Your turn

- [ ] Plot the validation curve of `n_neighbors` for k-nearest neighbours
  (`[1, 3, 5, 10, 15, 30, 60, 120]`). Where is the underfitting?
- [ ] Plot the one of `C` for the SVC (`[0.01, 0.1, 1, 10, 100, 1000]`, log scale).
- [ ] Reduce **Noise** to `0.1`. Do the gaps between models shrink?
- [ ] Try `min_samples_leaf` = `10` on the deep tree, instead of `max_depth`.

## Solution example

**Open › Examples › Decision boundaries and overfitting**.

![Solution example](../../assets/screenshots/en/06_frontiere_decision-canvas.png){ .shot }
