# Cross-validation

## Principle

A single train / test split gives a score that depends on the luck of that split.
Cross-validation divides the table into folds; the model is trained several times, each
time tested on a different fold. This gives a mean and a standard deviation of the score,
much more reliable than a single value.

## Nodes involved

| Node | Role |
|---|---|
| **cross_validate** | training and test scores per fold, for one or more metrics |
| **cross_val_predict** | prediction of each row by a model that has not seen it, to connect to the evaluation nodes |
| **Model comparison** | up to 6 models evaluated on the same folds, with ranking and spread |
| **permutation_test_score** | comparison of the score with the one obtained on shuffled targets (p-value) |
| **GridSearchCV / RandomizedSearchCV** | hyperparameter search; “Search” output for nested validation |
| **learning_curve**, **validation_curve** | score as a function of data size or of a hyperparameter |

All of them take a model (configuration) and a table as input: the model's settings are
reused (`clone`) and it is retrained on each fold. With a Pipeline as input, data
preparation is relearned in each fold too.

## Strategies

The **Cross-validation** group of these nodes offers every strategy of
`sklearn.model_selection`:

| Strategy | Use |
|---|---|
| **Automatic** | `StratifiedKFold` for classification (class proportions preserved), `KFold` otherwise |
| `KFold`, `StratifiedKFold` | general case |
| `RepeatedKFold`, `RepeatedStratifiedKFold` | several repetitions of k folds with different splits, for a more stable estimate |
| `ShuffleSplit`, `StratifiedShuffleSplit` | independent random draws of training and test sets |
| `GroupKFold`, `StratifiedGroupKFold`, `GroupShuffleSplit`, `LeaveOneGroupOut` | grouped data (several rows per patient, customer, site…): a group must never be on both sides |
| `TimeSeriesSplit` | time series: the future is always predicted from the past |
| `LeaveOneOut` | very small datasets (one model per row, hence costly) |

The related parameters are the number of folds (`n_splits`), the number of repeats, the test
size (ShuffleSplit strategies), the groups column (group strategies), shuffling and the
seed.

!!! warning "Grouped and temporal data"
    If the same person appears on several rows, a plain `KFold` puts some of them in
    training and others in test; the model recognises the person and the score is too
    optimistic. A group strategy is then needed. For dated data, use `TimeSeriesSplit`, and a
    split without shuffling.

## Nested cross-validation

The best score of a hyperparameter search is optimistic: the settings were kept because they
did well on those particular folds. To estimate the performance of the whole procedure
(“tune, then train”), two loops are nested. The inner loop is the search itself, with the
split strategy of the **GridSearchCV / RandomizedSearchCV** node; it chooses the settings.
The outer loop is a **cross_validate** node that evaluates the whole search on folds it has
never seen.

In KataML, connect the **Search (configuration)** output of the search node to a
**cross_validate** node (or to a model comparison, a learning curve…), with the same table.
The search is redone in each outer fold, and the view shows the hyperparameters chosen in
each fold. The **Best model** output, by contrast, passes a frozen setting, whose
re-evaluation gives an optimistic score.

```text
Pipeline ──▶ GridSearchCV ── Search (configuration) ──▶ cross_validate
             (inner loop: choose)                       (outer loop: evaluate)
```

!!! note "Groups"
    The outer loop can use a group strategy, but the inner search cannot; choose another
    strategy for it.

See [tutorial 6](../tutorials/06-tuning.md).

## Metrics

The **Metrics** parameter accepts every name from `sklearn.metrics.get_scorer_names()`:
`accuracy`, `balanced_accuracy`, `f1_macro`, `roc_auc`, `r2`, `neg_root_mean_squared_error`…
Left empty, it means the model's default score: accuracy for classification, R² for
regression. Error metrics are negative (`neg_…`), so that a larger value is always better.
