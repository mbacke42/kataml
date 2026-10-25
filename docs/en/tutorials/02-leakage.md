# 2. Evaluating without cheating: data leakage

!!! abstract "Objectives"
    - See that an evaluation can be wrong while the approach looks correct.
    - Understand data leakage between training and test.
    - Use the **Pipeline** node to avoid it.

    Prerequisites: [tutorial 1](01-first-workflow.md). Time: 30 min.

## The experiment

The data in this tutorial contains nothing to learn: 100 rows, 2,000 random features and a
random 0/1 target. On new data, no model can exceed 50 % accuracy. A common approach is
applied anyway, and we measure what it reports.

## Step 1: generate random data

1. Click **New**, then add a **Python script** node (category **Data manipulation**). This
   node runs pandas code and expects an input table even if it does not use it: connect a
   **scikit-learn dataset** (iris, for instance).
2. In **Code**, write:

    ```python
    import numpy as np
    rng = np.random.default_rng(0)
    # 100 rows, 2,000 purely random features, random target.
    out = pd.DataFrame(rng.normal(size=(100, 2000)), columns=[f'x{i}' for i in range(2000)])
    out['target'] = rng.integers(0, 2, size=100)
    ```

3. Run: the node produces a `100 × 2001` table.

## Step 2: the leaky approach

With 2,000 features for 100 rows, we start by keeping the features that look useful.

1. Add **SelectKBest** (Supervised learning › Feature selection), connected to the script,
   with **Target** `target` and `k` = `20`. When run, it keeps the 20 features most related
   to the target (ANOVA test).
2. Add **LogisticRegression** on its **Transformed table**, with **Target column**
   `target`.
3. Add **cross_validate**, connecting **Model (configuration)** to the logistic regression
   and **Table** to SelectKBest's transformed table, then run.

![Leaky cross-validation](../../assets/screenshots/en/tuto-leak-wrong.png){ .shot }

Cross-validation reports 81 % accuracy on pure noise, although the model has learnt nothing
real.

??? question "Where is the mistake?"
    SelectKBest chose its 20 features by looking at all 100 rows, including those that later
    serve as test in each fold. Among 2,000 random features, some correlate with the target
    by chance on these particular 100 rows, and the selection found them using the test
    answers. Cross-validation only retrains the logistic regression: the selection has
    already seen the test.

## Step 3: the right approach with a Pipeline

The whole chain (selection and model) must be relearned on each training fold, without ever
seeing the test fold.

1. Add a **Pipeline** node (Dataset transformations › Pipelines and composite estimators).
2. Connect **Raw table** to the script output (the data before selection), **Model** to the
   logistic regression and **Preprocessing 1** to SelectKBest's **Transformer** output.

    !!! tip "Shortcuts"
        Selecting SelectKBest and the logistic regression (++shift++ + click), then
        right-click › **Create a Pipeline** makes the three connections; the Pipeline
        appears collapsed with its steps, and a double-click expands it. You can also select
        the first cross_validate node: the inspector flags the leak and offers **Create and
        use the Pipeline**.

3. Add a second **cross_validate**, with **Model (configuration)** connected to the Pipeline
   and **Table** to the script output, then run.

![Leak-free cross-validation](../../assets/screenshots/en/tuto-leak-right.png){ .shot }

The score falls to 52 %, the chance level. Each fold now redoes the selection on its own
training data only, and the selected features are worthless on the test.

!!! example "In scikit-learn"
    ```python
    from sklearn.pipeline import make_pipeline
    from sklearn.feature_selection import SelectKBest
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score

    # Wrong: the selection sees the whole dataset
    X_sel = SelectKBest(k=20).fit_transform(X, y)
    cross_val_score(LogisticRegression(), X_sel, y, cv=5).mean()      # ≈ 0.81

    # Right: the selection is redone in each fold
    pipe = make_pipeline(SelectKBest(k=20), LogisticRegression())
    cross_val_score(pipe, X, y, cv=5).mean()                          # ≈ 0.52
    ```

## Steps that belong in the Pipeline

Any step that learns something from the data (scaling, imputation, feature selection, PCA,
encoding…) is part of the model and must be fitted on the training data only. The Pipeline
guarantees this, in cross-validation as in hyperparameter search, and then applies directly
to raw data. Leakage is strongest with many features and few rows; on real data it is less
visible than here, but it biases the evaluation in the same way.

See also: [The Pipeline](../concepts/pipeline.md).

## Your turn

- [ ] Vary `k` (5, 50, 200) in SelectKBest. How do the two scores change?
- [ ] Replace the random target by one related to a feature:
  `out['target'] = (out['x0'] + rng.normal(scale=0.5, size=100) > 0).astype(int)`.
  Do the two approaches still give different results?
- [ ] Add a **permutation_test_score** on the Pipeline. What is the p-value?

## Solution example

**Open › Examples › Information leakage**.

![Solution example](../../assets/screenshots/en/10_fuite_information-canvas.png){ .shot }
