# Release history

## Development version

- **Import a Python script**: the “Import a Python script (.py)” button of the “Open” dialog
  (or dropping a `.py` on the canvas) rebuilds the workflow from a pandas / scikit-learn
  script. The script is **never run**: it is analysed. Data loading, `dropna`, `drop`,
  `train_test_split`, estimators, `Pipeline`, `ColumnTransformer`, `fit` / `predict`,
  metrics and cross-validation are recognised; the script's functions are followed, and
  unrecognised pandas operations become “Python script” nodes. Also select the modules the
  script imports: their constants (target name, columns…) and functions are used. A note on
  the canvas lists what remains to be checked.
- **Parquet / Excel reader**: new node reading `.parquet`, `.xlsx`, `.xls` and `.feather`
  files (Excel sheet of your choice). Dropping such a file on the canvas creates this node.
  `pyarrow` and `openpyxl` join the dependencies.
- **SQL reader**: reads a SQLite database from `workspace/data` (read-only) or a PostgreSQL /
  MySQL database from its connection URL. Writing `$DATABASE_URL` reads the URL from an
  environment variable, so no password is saved in the workflow. A query, a table name, or
  nothing (when there is a single table). Script import converts `pd.read_sql(…)`, including
  a query built with an f-string and a URL read with `os.getenv`.
- **“Data and scripts” window** (“Data” button): the files of `workspace/data` (add to the
  canvas with the right reader, remove) and a **script library** (`workspace/scripts`): add,
  write from a template, edit, then tick the scripts to convert into a workflow. The other
  scripts of the library are used as modules when imported.
- **Import a project folder**: scripts join the library (`.venv`, `.git`, cache folders… are
  ignored) and only the data files read by the workflow are imported. After a conversion,
  KataML lists missing data files and offers to import them.
- **Faster computation on large datasets**: above 10,000 rows, cross-validation,
  out-of-fold predictions, hyperparameter search, curves and permutations use all processor
  cores (`--jobs` option, `KATAML_N_JOBS` variable). Out-of-fold predictions no longer train
  the model twice when the probabilities already give the predicted class. `--cache-mb`
  option to enlarge the result cache.
- **Encoders and text columns**: with no columns chosen, OneHotEncoder, OrdinalEncoder and
  TargetEncoder only take text columns, and scalers / PCA only numeric columns (instead of
  all, which failed on text). The columns used are listed in the node messages. A
  transformer that needs the target (TargetEncoder, SelectKBest…) says so clearly when the
  “Target” field is empty.
- Script import handles preparation code better: intermediate variables (masks, dates),
  pandas chains and two-table operations (`df` and `df2`) become readable “Python script”
  nodes.

## 0.5.8 (16 October 2026)

- The first-party extensions (exploratory data analysis, preparation example) are now
  **shipped with the application**, so they are present in the portable builds with nothing
  to install. Enable them with a **checkbox** in “My blocks”, section “Bundled extensions”
  (disabled by default; the choice is saved in `workspace/extensions.json`).
- The **exploratory-data-analysis** blocks (overview, missing values, frequencies,
  relationship with the target, distributions, outliers) are thus available everywhere, and
  translated into English like the rest of the interface.
- A skill for AI assistants (`.claude/skills/kataml-extension/`) describes the API and the
  conventions for writing your own extensions; the blocks guide presents the three sources of
  extensions.
- Fixes: **Unite columns** no longer fails on a missing value (it counts as empty text);
  **Split a column** and **Explode a list** keep missing values instead of producing the text
  “nan”; **Pivot** restricts itself by default to numeric columns with “mean”, “median” or
  “sum”, and explains the error otherwise; **Agreement** shows “—” for an undefined measure
  (constant column) instead of breaking the view; infinite values in tables are shown as
  missing; error messages of the new nodes are translated.

## 0.5.7 (16 October 2026)

- First version of the exploratory-data-analysis blocks, as an extension (see 0.5.8 for
  their bundling and checkbox activation).

## 0.5.6 (15 October 2026)

- The interface shows a dismissible banner when a newer version has been published as a
  release. The check queries GitLab at most once a day, with no personal data (generic
  User-Agent), fails silently when offline, and can be disabled with the environment variable
  `KATAML_NO_UPDATE_CHECK=1`.

## 0.5.5 (15 October 2026)

- Seven data-reshaping nodes (grammar of data, in pandas), in the **Manipulation** category:
  **Unpivot to long** and **Pivot to wide** to move between wide and long formats; **Split a
  column** and **Unite columns** to split or recombine text; **Explode a list** to get one row
  per element; **Deduplicate** and **Fill values** (ffill/bfill).
- They complement the existing nodes (filtering, aggregation, join, concatenation) for
  shaping a dataset before training.

## 0.5.4 (15 October 2026)

- Two new evaluation nodes. **Agreement between two columns** measures the association
  between two categorical columns (contingency table, Cramér's V, adjusted Rand index,
  mutual information, V-measure, Fowlkes–Mallows); it also compares a clustering to a ground
  truth, and adds raw agreement and Cohen's kappa when both columns use the same categories.
  **Clustering quality** evaluates a clustering without ground truth: silhouette (overall and
  per cluster), Calinski–Harabasz and Davies–Bouldin.
- **Classification metrics** now also reports Jaccard, the Hamming and 0-1 losses, and, when
  the Predictor provides probabilities, log loss and top-2 accuracy.
- **Regression metrics** now also reports the D² (absolute error) score and, on positive
  targets, MSLE/RMSLE and the Poisson and Gamma deviances.

## 0.5.3 (14 October 2026)

- After a dataset change, columns that no longer exist in a node's input are removed from
  its configuration, instead of staying displayed as “missing”; a message lists the removed
  columns, and Ctrl+Z undoes the operation. During a run, this cleanup happens before each
  node, and a node that is no longer configured is not run.
- The inspector's column lists update after each run, without having to reselect the node.

## 0.5.2 (11 October 2026)

- The **GridSearchCV / RandomizedSearchCV** node has a third output, **Search
  (configuration)**. Connected to a cross-validation (or a comparison, a curve…), it gives a
  nested cross-validation, whose view lists the hyperparameters chosen in each fold.
- The “Hyperparameter tuning” example and tutorial 6 compare the two evaluations.

## 0.5.1 (11 October 2026)

- “Create a Pipeline” combines the Pipeline and its steps into a single collapsed node, with
  the list of steps as a subtitle; a double-click expands it. An existing Pipeline is
  collapsed with right-click › “Collapse the Pipeline”.
- The inspector of cross-validation nodes flags a model trained on a transformed table and
  offers “Create and use the Pipeline”.
- When a transformer receives a text column (often the target), the error message names the
  offending columns and gives the fix.

## 0.5.0 (11 October 2026)

- Katanime becomes KataML (*Keen-edged Analytics Toolkit for Applied Machine Learning*):
  Python package and command `kataml`, `KATAML_*` environment variables, `kataml.extensions`
  extension group, `~/kataml` workspace. New repository: <https://gitlab.com/fredbl/kataml>.
- New main colour, teal.
- Themes: “Appearance” dialog (automatic, light or dark mode, seven main colours or a custom
  one, canvas background) and a `theme.css` file in the workspace to redefine the colours of
  the interface and reports.

## 0.4.1 (11 October 2026)

- Documentation in English and French, published on GitLab Pages, with automatic
  screenshots and a node reference generated from scikit-learn.
- Ten tutorials and three new examples (information leakage, unsupervised, understanding a
  model).
- “Text” example fixed: the `note` column of the reviews file gave the model the answer; the
  new data is more realistic.
- English translations completed.

## 0.4.0 (11 October 2026)

- Every public scikit-learn estimator is available as a node (classifiers, regressors,
  clustering, transformers, outliers, covariance, density, neighbours, embeddings,
  meta-estimators); exceptions are justified and a test checks coverage.
- The node repository follows the scikit-learn user guide (*Guide* view), or the API modules
  (*API* view).
- Optional English interface, with names close to scikit-learn's; bilingual reports and
  command line.
- Every cross-validation strategy (groups, time series, repeats).

## 0.3.0 (10 October 2026)

- Standalone HTML reports: diagram, node views, Markdown “Report text” blocks, script
  appendix; PDF printing; command-line generation.
- Custom blocks (“My blocks”): nodes written in Python in the built-in editor, conversion of
  a Python script into a block, distribution of extensions as packages.

## 0.2.0 (10 October 2026)

- Leak-free Pipeline; meta-estimators (voting, stacking, bagging…).
- Model comparison, permutation test, validation curve.
- Decision boundaries, trees, partial dependence.
- Jupyter notebook export, cancellation of running computations, disk cache.
- Reusable components, automatic graph layout.
- Text (TF-IDF), date features, OpenML datasets.

## 0.1.0 (10 October 2026)

- Node canvas, inspector, output panel, nodes generated from scikit-learn.
- CSV reading, pandas manipulations, charts, evaluation, hyperparameter search.
- Python script export.
- Portable builds (AppImage, Windows zip) and installation with uv.
