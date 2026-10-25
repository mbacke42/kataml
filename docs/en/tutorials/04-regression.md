# 4. Regression: predicting a value

!!! abstract "Objectives"
    - Build a regression model and read its metrics (R², MAE, RMSE).
    - Compare several models on the same folds.
    - Understand why a single test score can be misleading.

    Prerequisites: [tutorial 1](01-first-workflow.md). Time: 30 min.

## The data

scikit-learn's *diabetes* dataset describes 442 patients by 10 features: age, sex, body mass
index `bmi`, blood pressure `bp` and six blood measurements `s1` to `s6`, already centred and
scaled. The target is a quantitative measure of disease progression one year later; the
model predicts a number rather than a category.

## Step 1: explore

1. Add a **scikit-learn dataset** set to `Diabetes`.
2. Connect a **Correlation matrix** (Visualization) to it. `bmi` and `s5` are the features
   most correlated with `target`, and `s1` and `s2` are strongly correlated with each other.
3. Add a **train_test_split** with a test size of `0.2` and seed `0`. Regression splits are
   not stratified.

## Step 2: two models

| Node | Family | Settings |
|---|---|---|
| **Ridge** | Linear models | target `target`, `alpha` = `1.0` |
| **HistGradientBoostingRegressor** | Ensembles | target `target`, `max_iter` = `150`, `learning_rate` = `0.05`, `max_depth` = `3`, `min_samples_leaf` = `20` |

`Ridge` is a regularised linear regression: it penalises large coefficients to limit
overfitting. *Gradient boosting* builds a sequence of trees, each correcting the errors of
the previous ones, which lets it capture non-linear effects and interactions.

## Step 3: compare

Add **Model comparison** (Model selection and evaluation › Cross-validation), connecting
**Table** to the **Train** output, **Model 1** to Ridge and **Model 2** to gradient boosting,
then run.

![Comparison](../../assets/screenshots/en/tuto-compare.png){ .shot }

| Model | Mean R² (5 folds) | standard deviation |
|---|---|---|
| Gradient boosting | 0.435 | 0.130 |
| Ridge | 0.413 | 0.067 |

The gap between the two models (0.02) is much smaller than their standard deviations: they
are tied. The **Scores per fold** table shows that each one wins on some folds. Ridge is more
stable, and 50 times faster to train.

!!! info "R²"
    The coefficient of determination is 1 for perfect predictions and 0 for a model that
    always predicts the mean; it becomes negative for an even worse model. An R² of 0.43
    means that about 43 % of the variance of progression is explained: the 10 features are
    not enough to predict a patient's course precisely.

## Step 4: evaluate on the test set

Add a **Predictor** (gradient boosting and the **Test** output), then **Regression
metrics**.

![Regression metrics](../../assets/screenshots/en/tuto-regression-metrics.png){ .shot }

The test R² is only 0.19, versus 0.43 in cross-validation. The model is not at fault: the
test set has only 89 patients, and fold 4 of the comparison already gave an R² of 0.20. On so
little data, a single test score varies a lot; the cross-validation mean and standard
deviation give a fairer picture.

The other metrics are in the target's unit:

| Metric | Value | Reading |
|---|---|---|
| MAE (mean absolute error) | 48.6 | average error of 49 points |
| RMSE (root mean squared error) | 64.3 | penalises large errors more |
| Median absolute error | 38.8 | half of the errors are below 39 points |

The predicted vs actual chart and the residuals histogram show whether errors are
systematic, for instance high values underestimated.

??? question "The target ranges from 25 to 346: is an MAE of 49 large?"
    It has to be compared with a naive model. A **DummyRegressor**, which predicts the
    training mean, has an MAE of about 59: the model cuts the error by roughly a fifth, a
    real but modest gain.

## Step 5: find the useful features

Add **permutation_importance** (model: gradient boosting; table: **Test**) and
**partial_dependence** (features `bmi`, `s5`, `bp`). `s5`, `bmi` and `bp` dominate. Partial
dependence shows that predicted progression increases with BMI almost linearly, which
explains why Ridge does as well. [Tutorial 9](09-understanding.md) covers these tools.

!!! example "In scikit-learn"
    ```python
    from sklearn.linear_model import Ridge
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.model_selection import KFold, cross_val_score

    cv = KFold(5, shuffle=True, random_state=0)       # the same folds for all
    for model in (Ridge(alpha=1.0),
                  HistGradientBoostingRegressor(max_iter=150, learning_rate=0.05,
                                                max_depth=3, min_samples_leaf=20)):
        s = cross_val_score(model, X_train, y_train, cv=cv, scoring="r2")
        print(type(model).__name__, s.mean(), s.std())
    ```

## Your turn

- [ ] Add **LinearRegression**, **Lasso** and **RandomForestRegressor** to the comparison,
  which accepts up to 6 models.
- [ ] In the comparison, switch the strategy to `RepeatedKFold` (5 folds, 5 repeats). Do the
  standard deviations shrink? Does the ranking change?
- [ ] Change the split's seed and note the test R² each time. What do you observe?

## Solution example

**Open › Examples › Regression: diabetes**.

![Solution example](../../assets/screenshots/en/02_regression_diabete-canvas.png){ .shot }
