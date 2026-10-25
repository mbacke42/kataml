# 3. Cleaning a CSV file

!!! abstract "Objectives"
    - Import your own data and profile it.
    - Handle missing values and categorical features.
    - Choose a metric suited to imbalanced classes.

    Prerequisites: tutorials [1](01-first-workflow.md) and [2](02-leakage.md). Time: 45 min.

## The data

`clients.csv`, shipped with the examples, describes 800 customers of a fictitious operator:
region (`region`), plan (`offre`), age, income (`revenu`), seniority (`anciennete`), number
of support calls (`appels_support`), and the target `resilie` (churned: `oui` / `non`). The
aim is to predict churn in order to contact customers at risk.

## Step 1: read and profile

1. Click **New**, then add a **CSV reader** (category **Dataset loading**). In **File**,
   choose `clients.csv`. Your own data is added with the **Import** button, or by dragging
   the file onto the canvas.
2. Left empty, the column separator is detected automatically. For a file using `;` and a
   decimal comma, set **Decimal separator** to `,`.
3. Connect a **Statistics** node and run.

![Data profile](../../assets/screenshots/en/tuto-csv-profile.png){ .shot }

The profile shows 158 missing values (53 for `age`, 79 for `revenu`, 26 for `anciennete`),
two text columns, `region` (5 values) and `offre` (3), and an imbalanced target: about 28 %
churn.

??? question "Why not drop incomplete rows?"
    The **Drop missing rows** node (`dropna`) would do it, but we would lose almost one
    customer in five, and customers with incomplete data are not necessarily like the
    others. Above all, the model will have to predict for new customers, who will have
    missing values too: it has to learn to fill them in.

## Step 2: split first

Add a **train_test_split** with **Test size** `0.25`, **Stratify by** `resilie` and
**Random state** `1`. All the following steps learn on the **Train** output.

## Step 3: prepare the columns

Chain three transformers from the **Dataset transformations** category, each one receiving
the previous one's **Transformed table**:

| Node | Settings | Role |
|---|---|---|
| **SimpleImputer** (Imputation of missing values) | columns `age`, `revenu`, `anciennete`; `strategy` = `median` | replaces each missing value by the column median, computed on the training set |
| **OneHotEncoder** (Preprocessing data) | columns `region`, `offre`; `handle_unknown` = `ignore` | creates one 0/1 column per category |
| **StandardScaler** (Preprocessing data) | target `resilie` | centres and scales the numeric columns, except the target |

Columns not chosen are kept unchanged. After encoding, the table contains columns
`region_Est`, `region_Nord`, and so on.

!!! warning "The target in transformers"
    Set to “all columns”, a transformer would also process the target. Set it in the
    transformer's **Target** field to exclude it.

## Step 4: model and Pipeline

1. Add **LogisticRegression** on the StandardScaler output, with target `resilie`,
   `max_iter` = `1000` and `class_weight` = `'balanced'`.
2. Select the three transformers and the model, then right-click › **Create a Pipeline**.
   Its raw table is the **Train** output of the split. The Pipeline appears collapsed, its
   four steps combined into one node; a double-click shows them.
3. Add a **Predictor**, with **Model** connected to the Pipeline and **Table** to the raw
   **Test** output: the Pipeline imputes, encodes and scales by itself. Finish with
   **Classification metrics** and **ROC curve**.

![Evaluation](../../assets/screenshots/en/tuto-csv-eval.png){ .shot }

## Step 5: read the evaluation

Accuracy is only 58 %, whereas a model always answering “non” would reach 72 %. The
confusion matrix qualifies this: the model detects 35 churners out of 56 (62 % recall), at
the cost of false alarms, while the “always non” model detects none.

The `class_weight='balanced'` setting gives more weight to the rare class, so the model
looks for churners instead of favouring the majority answer. Balanced accuracy (mean of
per-class recalls) is 0.59, above the 0.5 of chance. AUC (0.65) measures the ability to rank
customers from most to least at risk, independently of the decision threshold.

This data is weakly predictive, which is common in practice.

??? question "Which metric to choose?"
    The one that reflects the cost of errors. If contacting a customer is cheap and losing
    one is expensive, favour recall of the “oui” class; to compare models independently of
    the threshold, AUC or average precision. Accuracy alone is misleading as soon as classes
    are imbalanced.

## Step 6: tune the regularisation

Add **GridSearchCV / RandomizedSearchCV**, with **Model (configuration)** connected to the
Pipeline and **Table** to the **Train** output, and the following grid:

```json
{ "model__C": [0.01, 0.1, 1, 10] }
```

Set **Scoring** to `roc_auc`. The `model__` prefix refers to the Pipeline's model step; the
Pipeline view lists every tunable parameter. The four values give a cross-validated AUC
close to 0.74: regularisation changes little, the data is the limiting factor.

!!! example "In scikit-learn"
    ```python
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from sklearn.pipeline import make_pipeline
    from sklearn.linear_model import LogisticRegression

    prep = ColumnTransformer([
        ("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()),
         ["age", "revenu", "anciennete", "appels_support"]),
        ("cat", OneHotEncoder(handle_unknown="ignore"), ["region", "offre"]),
    ])
    pipe = make_pipeline(prep, LogisticRegression(max_iter=1000, class_weight="balanced"))
    ```

## Your turn

- [ ] Add a **DummyClassifier** (Supervised learning) and compare it with the Pipeline using
  **Model comparison**, with scoring `balanced_accuracy` then `accuracy`.
- [ ] Remove `class_weight`. What happens to accuracy, churn recall and AUC? Why does AUC
  barely change?
- [ ] Try **HistGradientBoostingClassifier**, which accepts missing values without
  imputation.

## Solution example

**Open › Examples › CSV: cleaning and encoding**.

![Solution example](../../assets/screenshots/en/04_csv_pretraitement-canvas.png){ .shot }
