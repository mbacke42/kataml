# Output panel

The bottom panel shows the results of the selected node. Its tabs match the node's
**outputs** (one per output port), preceded by the **View** when the node produces one.
The arrow on the right collapses or expands the panel; its height is set with the
splitter.

## View

![View of an evaluation](../../assets/screenshots/en/outputs-view.png){ .shot }

The view gathers what the node has to show: indicators (metrics), charts, summary tables,
text. Charts are interactive: hovering shows exact values; curves have a crosshair. The
main types:

| Chart | Nodes |
|---|---|
| confusion matrix, heat map | Classification metrics, Correlation matrix, covariance |
| bars, horizontal bars | importances, coefficients, model comparison, cluster sizes |
| histograms, box plots | Statistics, Histogram, residuals, outlier scores |
| scatter plots | Scatter plot, predicted vs actual, outliers, embeddings |
| curves with standard deviation bands | ROC, precision-recall, calibration, learning and validation curves, partial dependence |
| decision map | DecisionBoundaryDisplay |
| tree | plot_tree / export_text |

## Table

![Table](../../assets/screenshots/en/outputs-table.png){ .shot }

- 100 rows per page, navigation at the bottom; the total number of rows and columns is
  shown.
- Clicking a **header** sorts (ascending, descending, then original order); the pandas type
  of each column is shown under its name.
- Missing values appear as greyed *NaN*; the original index is kept.
- **CSV** downloads the full table.

## Profile

![Column profile](../../assets/screenshots/en/outputs-profile.png){ .shot }

The **Profile** button replaces the table by one card per column: type, number of
distinct and missing values, histogram and statistics (numeric) or most frequent values
(text). Ideal for a first look at unknown data.

## Model

![Model](../../assets/screenshots/en/outputs-model.png){ .shot }

For a model port: estimator, kind (classifier, regressor, clustering, transformer…),
target, features used, classes, output columns (transformers), effective hyperparameters,
**learned attributes** (`coef_`, `feature_importances_`, `n_iter_`…) and Python
representation. **joblib** downloads the model, which can be reloaded in any script with
`joblib.load()`.
