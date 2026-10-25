# Tutorials

The ten tutorials go from the first prediction to the report and the custom block; each
takes 20 to 45 minutes. They build on one another, but every page lists its prerequisites.

| # | Tutorial | Concepts | Solution example |
|---|---|---|---|
| 1 | [First workflow](01-first-workflow.md) | nodes, connections, train / test, evaluation | Iris classification |
| 2 | [Evaluating without cheating](02-leakage.md) | cross-validation, data leakage, Pipeline | Information leakage |
| 3 | [Cleaning a CSV file](03-csv-cleaning.md) | missing values, categorical features, imbalanced classes | CSV: cleaning and encoding |
| 4 | [Regression](04-regression.md) | regression metrics, model comparison, evaluation variance | Regression: diabetes |
| 5 | [Overfitting](05-overfitting.md) | complexity, decision boundaries, validation curve | Decision boundaries and overfitting |
| 6 | [Tuning hyperparameters](06-tuning.md) | grid search, learning curve, nested validation | Hyperparameter tuning |
| 7 | [Unsupervised learning](07-unsupervised.md) | clustering, Gaussian mixtures, PCA, outliers | Unsupervised: clusters and outliers; Clustering: k-means and PCA |
| 8 | [Text and dates](08-text-dates.md) | TF-IDF, date features, cyclic encoding, time series | Text: classifying reviews; Dates: bike rentals |
| 9 | [Understanding a model](09-understanding.md) | permutation importance, partial dependence, trees | Understanding a model |
| 10 | [Report and custom block](10-report-blocks.md) | HTML report, Python export, writing a node | Iris classification |

## Page layout

Each tutorial starts with its objectives and prerequisites, then builds the workflow node by
node, with a screenshot at the key steps. The “In scikit-learn” boxes give the equivalent
Python code. Questions have their answer folded under the title; the “Your turn” section
suggests variations to try alone. The complete workflow is in **Open › Examples**.

The figures quoted were obtained with the random seeds given (`random_state`); they may vary
slightly from one scikit-learn version to another. **Open** only replaces the current
workflow after confirmation, and that workflow is saved automatically: the solution example
can be opened without losing your work.

For classroom use, annotations (++a++) let you write instructions on the canvas, and every
example exports to a Jupyter notebook. In the English interface, the examples' node
annotations (“Iris”, “75 % / 25 %”…) stay as written in the workflow files.
