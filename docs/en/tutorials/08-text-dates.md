# 8. Text and dates

!!! abstract "Objectives"
    - Turn text into numeric features (TF-IDF) and classify it.
    - Extract date features, with cyclic encoding.
    - Evaluate a model correctly on temporal data.

    Prerequisites: tutorials [2](02-leakage.md) and [4](04-regression.md). Time: 45 min.

## Part A: classifying customer reviews

### The data

`avis.csv` contains 900 short reviews (in French, column `avis`) and their sentiment
(`positif` or `négatif`). Many are mixed (“La livraison était rapide, mais le produit était
cassé”: fast delivery, but broken product), some contain negations (“pas terrible”: not
great; “pas mal”: not bad), and a few labels are wrong, as in any real annotation.

### Step 1: vectorise

A model only works on numbers; the text has to be converted first.

1. Add a **CSV reader** set to `avis.csv`, then a **train_test_split** (test `0.25`,
   stratified by `sentiment`, seed `0`).
2. Add **TfidfVectorizer** (Dataset transformations › Feature extraction) on the training
   set, with **Text column** `avis`, `ngram_range` = `(1, 2)`, `min_df` = `2` and
   `max_features` = `2000`.

![TF-IDF](../../assets/screenshots/en/tuto-text-tfidf.png){ .shot }

Each term of the vocabulary becomes a column: single words and, with
`ngram_range = (1, 2)`, pairs of consecutive words (“pas terrible”, “très déçu”).
`min_df = 2` drops terms found in a single review. The TF-IDF value is high when a term is
frequent in the review but rare across all reviews: “cassé” (broken) weighs more than “le”
(the). The vocabulary has 443 terms here.

??? question "Why are word pairs useful?"
    Taken separately, “pas” and “terrible” are ambiguous, whereas “pas terrible” is clearly
    negative. Bigrams keep part of the word order, and hence negations.

### Step 2: two models in Pipelines

1. Add **LogisticRegression** (`max_iter` = `1000`) and **MultinomialNB** (Supervised
   learning › Naive Bayes), both on the vectorised table, with target `sentiment`.
2. Create a **Pipeline** for each: **Raw table** connected to the **Train** output,
   **Model** to the model, **Preprocessing 1** to the TfidfVectorizer's **Transformer**
   output. The vocabulary is thus relearned in each fold; without a Pipeline, the vocabulary
   and frequencies would take the test into account, which would be leakage.
3. Add **Model comparison** on the training set, with both Pipelines.

![Text comparison](../../assets/screenshots/en/tuto-text-compare.png){ .shot }

| Model | Accuracy (5 folds) |
|---|---|
| Logistic regression Pipeline | 0.895 ± 0.025 |
| Naive Bayes Pipeline | 0.886 ± 0.025 |

The two models are on a par. On the test set (Predictor and Classification metrics),
logistic regression reaches 0.88. Sorting the prediction table by `Prediction (sentiment)`
shows that the errors mostly concern mixed or mislabelled reviews.

## Part B: forecasting bike rentals

### The data

`velos.csv` gathers 6,480 hourly records from a bike-sharing service, January to September
2024: date and time, temperature, humidity (`humidite`) and number of rentals
(`locations`).

### Step 3: date features

A raw date (`2024-03-14 08:00`) cannot be used as is. Add **Date features** (Data
manipulation), with **Date columns** `date`, **Parts to extract** `Month`, `Day of week`,
`Hour`, `Weekend`, and tick **Cyclic encoding (sin/cos)**.

Cyclic encoding adds, for each periodic part, its sine and cosine. The model then sees
11 pm and midnight as neighbours, whereas the numbers 23 and 0 are far apart.

```text
hour  →  angle = 2π · hour / 24  →  (sin, cos)       0 h and 23 h: neighbouring points on the circle
```

### Step 4: split in time

Add a **train_test_split** with a test size of `0.25` and **Shuffle** unticked. The test set
then covers the end of the period, from late July to late September: the model is evaluated
as it will be used, forecasting the future from the past.

!!! warning "Temporal data"
    Shuffling before splitting would put hours neighbouring those of the test set into
    training. The model would interpolate instead of forecasting, and the score would be too
    optimistic. For cross-validation, use the `TimeSeriesSplit` strategy.

### Step 5: model and evaluation

Add **HistGradientBoostingRegressor** with target `locations`, `max_iter` = `300` and
`learning_rate` = `0.08`, then a Predictor on the test set and **Regression metrics**: R²
reaches 0.987 and MAE 12.5 rentals per hour.

??? question "Why is the MAPE (mean relative error) so huge?"
    MAPE divides each error by the actual value. Some night hours have zero rentals, and
    dividing by a value at or near zero blows up the mean. MAPE does not suit targets that
    can be zero; MAE or RMSE are better choices.

### Step 6: the role of the hour in the model

Add **permutation_importance** and **partial_dependence** (features `date_hour`,
`temperature`, `humidite`) on the test set.

![Partial dependence](../../assets/screenshots/en/tuto-dates-pdp.png){ .shot }

Temperature has a strong, almost linear effect: from 12 to 24 °C, predicted rentals increase
by about 38 per hour.

The hour is by far the most important feature, but the information is spread across
`date_hour`, `date_hour_sin` and `date_hour_cos`. The dependence curve of `date_hour` alone
shows the 8 am and 4 to 6 pm peaks, but dampened, because varying `date_hour` while keeping
its sine and cosine fixed matches no real situation. With redundant features, importance and
partial dependence are interpreted per group of features.

!!! example "In scikit-learn"
    ```python
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.pipeline import make_pipeline
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import TimeSeriesSplit, cross_val_score

    text_model = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=2000),
                               LogisticRegression(max_iter=1000))
    text_model.fit(train["avis"], train["sentiment"])

    df["date_hour"] = df["date"].dt.hour
    df["date_hour_sin"] = np.sin(2 * np.pi * df["date_hour"] / 24)
    df["date_hour_cos"] = np.cos(2 * np.pi * df["date_hour"] / 24)
    cross_val_score(model, X, y, cv=TimeSeriesSplit(n_splits=5))
    ```

## Your turn

- [ ] Reviews: set `ngram_range` to `(1, 1)` (single words). Does accuracy drop?
- [ ] Reviews: try **CountVectorizer** instead of TF-IDF with naive Bayes.
- [ ] Bikes: untick cyclic encoding. Does the score change much? Trees can cut the hour into
  intervals; cyclic encoding mostly helps linear models and nearest neighbours.
- [ ] Bikes: replace gradient boosting by **Ridge**, with and without cyclic encoding.
- [ ] Bikes: add a **cross_validate** node with the `TimeSeriesSplit` strategy.

## Solution examples

**Open › Examples › Text: classifying reviews** and **Dates: bike rentals**.

![Solution example (text)](../../assets/screenshots/en/07_texte_avis-canvas.png){ .shot }
![Solution example (dates)](../../assets/screenshots/en/09_velos_dates-canvas.png){ .shot }
