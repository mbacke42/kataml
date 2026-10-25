"""Traduction anglaise : spécifications des nœuds, vues, messages et erreurs.

Le moteur produit ses textes en français ; en anglais, ils sont traduits au moment
de l'envoi (catalogue, vues, messages), à partir de ce dictionnaire. Les noms des
nœuds anglais reprennent autant que possible ceux de scikit-learn.
Les données (contenu des tables, noms de colonnes) ne sont jamais traduites.
"""

from __future__ import annotations

import copy
import re

# Noms et descriptions des nœuds propres à KataML.
NODES = {
    "io.csv_reader": ("CSV reader (read_csv)", "Reads a CSV (or TSV) file into a pandas table. Import a file with the “Import” button: it is copied into workspace/data. An absolute path also works. The separator is detected automatically when left empty."),
    "io.table_reader": ("Parquet / Excel reader (read_parquet / read_excel)", "Reads a Parquet (.parquet), Excel (.xlsx, .xls), Feather or JSON file into a pandas table. The format is inferred from the extension. Drop the file on the canvas or use “Import”: it is copied into workspace/data. An absolute path also works. For Excel, the first sheet is used when the field is empty."),
    "io.sql_reader": ("SQL reader (read_sql)", "Runs a SQL query and returns the result as a table. The database is either a SQLite file (.db, .sqlite) in workspace/data or a SQLAlchemy connection URL, e.g. postgresql+psycopg://user:password@localhost:5432/db or mysql+pymysql://user@host/db. To avoid saving a password in the workflow, write $DATABASE_URL: the URL is read from that environment variable. The query can be just a table name; left empty, the only table of the database is read (otherwise the list of tables is shown). SQLite databases are opened read-only."),
    "io.dataset": ("scikit-learn dataset (load_* / make_*)", "Loads a dataset shipped with scikit-learn (no download) or generates a synthetic one (make_classification, make_moons…). The target is placed in the “target” column (“species” for iris, with class names)."),
    "io.csv_writer": ("CSV writer (to_csv)", "Writes the input table to a CSV file (by default in workspace/exports). Any table can also be downloaded from the output panel."),
    "io.model_writer": ("Model writer (joblib.dump)", "Serialises the model with joblib, the standard scikit-learn format. The file can be reloaded in any Python script with joblib.load()."),
    "io.openml": ("OpenML dataset (fetch_openml)", "Downloads a dataset from openml.org (sklearn.datasets.fetch_openml), by name or numeric id. Examples: titanic, adult, credit-g, diabetes, blood-transfusion-service-center, wine-quality-red. Files are cached in workspace/openml: a connection is only needed the first time."),
    "manip.column_filter": ("Column filter", "Keeps or removes a selection of columns."),
    "manip.row_filter": ("Row filter (query)", "Filters rows with a pandas DataFrame.query expression, e.g. `age > 30 and sex == \"F\"` or `` `petal length (cm)` < 2 `` (backticks for names containing spaces)."),
    "manip.expression": ("New column (eval)", "Computes a column from a DataFrame.eval expression, e.g. `weight / height ** 2`. An existing column with the same name is replaced."),
    "manip.missing": ("Drop missing rows (dropna)", "Removes rows containing missing values (in all columns or a selection). To impute instead of dropping, use SimpleImputer, KNNImputer or IterativeImputer."),
    "manip.partition": ("train_test_split", "Splits the table into a training and a test set with sklearn.model_selection.train_test_split. Stratifying on the target keeps class proportions in both parts."),
    "manip.sampling": ("Sampling (sample)", "Draws a random sample of rows (number or fraction)."),
    "manip.sorter": ("Sort (sort_values)", "Sorts rows by one or more columns."),
    "manip.types": ("Type conversion (astype)", "Converts column types: numeric (invalid values become NaN), text, category, boolean or date."),
    "manip.groupby": ("Aggregation (groupby)", "Groups rows and aggregates columns (mean, sum, count…)."),
    "manip.join": ("Join (merge)", "Joins two tables on key columns (pandas.merge)."),
    "manip.concat": ("Concatenation (concat)", "Stacks the rows of two tables (pandas.concat)."),
    "manip.melt": ("Unpivot to long (melt)", "Goes from wide to long format (pandas.melt): the chosen columns become two columns, one for the variable name and one for its value, while the identifier columns are repeated. Useful when column headers are actually values (one column per year, for instance)."),
    "manip.pivot": ("Pivot to wide (pivot_table)", "Goes from long to wide format (pandas.pivot_table): the values of a column become columns. An aggregation function combines any duplicates. This is the inverse of “Unpivot to long”."),
    "manip.separate": ("Split a column (str.split)", "Splits a text column into several columns on a separator (str.split). Useful when a column encodes several variables, e.g. “2024-F” → year and sex."),
    "manip.unite": ("Unite columns", "Joins several columns into a single text column, separated by a separator. This is the inverse of “Split a column”."),
    "manip.explode": ("Explode a list (explode)", "Turns a column of lists (or of delimited text) into one row per element (pandas.explode), repeating the other columns."),
    "manip.distinct": ("Deduplicate (drop_duplicates)", "Removes duplicate rows (pandas.drop_duplicates), considering all columns or a selection."),
    "manip.fill": ("Fill values (ffill / bfill)", "Fills missing values by carrying the last known value forward (ffill) or the next one backward (bfill). For statistical imputation, use SimpleImputer (Preprocessing category)."),
    "manip.rename": ("Rename columns", "Renames columns, one mapping per line: `old -> new`."),
    "manip.python": ("Python script", "Runs free Python code. The input table is available as `df` (and `df2` if the second port is connected); assign the result to `out`. pandas (pd), numpy (np) and sklearn are imported."),
    "manip.dates": ("Date features", "Extracts numeric features from one or more date columns: year, month, day of week, hour, weekend… Cyclic encoding (sine / cosine) tells the model that December is close to January. Unrecognised values become missing."),
    "view.statistics": ("Statistics (describe)", "Descriptive statistics per column (DataFrame.describe): count, mean, standard deviation, quantiles, missing values, categories."),
    "view.scatter": ("Scatter plot", "Scatter plot of two numeric columns, coloured by a third one."),
    "view.histogram": ("Histogram", "Distribution of a column: histogram for a numeric variable, bar chart of counts for a categorical one. Optional grouping by a categorical column."),
    "view.correlation": ("Correlation matrix", "Pairwise correlations between numeric columns (Pearson, Spearman or Kendall)."),
    "view.boxplot": ("Box plot", "Box plots of numeric columns, optionally by group."),
    "view.table": ("Table view", "Shows the full table (paginated and sortable) in the output panel."),
    "apply.predictor": ("Predictor (predict / predict_proba)", "Applies a fitted model (classification, regression, clustering or outlier detection with predict) to a table. Adds a “Prediction (target)” column and, optionally, the probability of each class (predict_proba), needed for the ROC curve."),
    "apply.transformer": ("Transformer apply (transform)", "Applies an already fitted transformer (model output of a preprocessing node) to a new table, typically the test set: the transformation learnt on the training set is reused without information leakage."),
    "score.classification": ("Classification metrics", "Compares the true and predicted columns: confusion matrix, accuracy, precision, recall, F1, Cohen's kappa, MCC, Jaccard, Hamming and 0-1 losses (sklearn.metrics). With the Predictor's probabilities, adds log loss and top-2 accuracy. Columns are detected automatically after a Predictor."),
    "score.concordance": ("Agreement between two columns", "Measures the association between two categorical columns: contingency table, Cramér's V, adjusted Rand index, mutual information (adjusted, normalized), V-measure (homogeneity, completeness) and Fowlkes–Mallows (sklearn.metrics). Also compares a clustering to a ground truth (two labelings). When both columns use the same categories, raw agreement and Cohen's kappa are added."),
    "score.clustering": ("Clustering quality", "Quality of a clustering without ground truth, from the features and the cluster column: silhouette coefficient (overall and per cluster), Calinski–Harabasz index (higher is better) and Davies–Bouldin index (lower is better) (sklearn.metrics). To compare the clustering to a known label, use “Agreement between two columns”."),
    "score.regression": ("Regression metrics", "Regression metrics: R², MAE, RMSE, MAPE, median error, explained variance, D² (absolute error). On positive targets, adds MSLE/RMSLE and the Poisson and Gamma deviances. The view shows predicted vs true values and the distribution of residuals."),
    "score.roc": ("ROC curve (roc_curve)", "One-vs-rest ROC curves and area under the curve for each class, from the “P (target=class)” probability columns produced by the Predictor. Also shows the precision-recall curve."),
    "score.calibration": ("Calibration curve (calibration_curve)", "Compares predicted probabilities with observed frequencies (sklearn.calibration.calibration_curve): a well-calibrated model follows the diagonal. Uses the “P (target=class)” columns of the Predictor and shows the Brier score (lower is better)."),
    "score.importance": ("permutation_importance", "Permutation importance (sklearn.inspection.permutation_importance): drop of the score when each feature is shuffled. Works with any supervised model; preferably computed on the test set."),
    "tune.cross_validation": ("cross_validate", "Evaluates a model configuration by cross-validation (sklearn.model_selection.cross_validate). Connect the output of a learner or a Pipeline: its hyperparameters, features and target are reused, and the model is refitted on each fold. All scikit-learn strategies are available: k-fold, repeated, grouped, time series, leave-one-out…"),
    "tune.cross_val_predict": ("cross_val_predict", "Predicts each row with a model that did not see it during training (sklearn.model_selection.cross_val_predict). The resulting table can be connected to evaluation nodes (confusion matrix, ROC, residuals…) to evaluate on the whole table without a separate test set."),
    "tune.permutation_test": ("permutation_test_score", "Is the model better than chance? The model is evaluated by cross-validation, then re-evaluated many times after shuffling the target (sklearn.model_selection.permutation_test_score). The p-value is the proportion of “chance” scores at least as good."),
    "tune.grid_search": ("GridSearchCV / RandomizedSearchCV", "Exhaustive (GridSearchCV) or randomised (RandomizedSearchCV) search with cross-validation. The grid is a Python dictionary, e.g. {\"n_estimators\": [50, 100, 200], \"max_depth\": [None, 5, 10]}. The “Best model” output is the best estimator refitted on the whole table. The “Search (configuration)” output passes the search itself: connected to a cross-validation, it gives a nested cross-validation (the search is redone in each outer fold)."),
    "tune.learning_curve": ("learning_curve", "Training and validation score as a function of the training set size (sklearn.model_selection.learning_curve): diagnoses over- or underfitting."),
    "tune.validation_curve": ("validation_curve", "Training and cross-validation score as a function of a hyperparameter (sklearn.model_selection.validation_curve). The gap between the two curves shows where overfitting begins. Examples: max_depth with [1, 2, 4, 8, 16, None], C with [0.01, 0.1, 1, 10, 100]. For a Pipeline, prefix the name: model__C."),
    "tune.compare": ("Model comparison", "Evaluates several models by cross-validation on the same folds and ranks them. Connect 1 to 6 outputs of learners or Pipelines (same target): each configuration is refitted on each fold. The displayed name is the upstream node's annotation, or else the estimator name."),
    "compose.pipeline": ("Pipeline", "Chains one or more preprocessing steps and a model into a single sklearn.pipeline.Pipeline, refitted on raw data. Connect the raw table (before preprocessing), the model (output of a learner) and, in order, the transformers. Their settings are reused but everything is refitted together. The Pipeline applies directly to raw test data with the Predictor. Above all, cross-validation and hyperparameter search then refit the preprocessing on each fold: the correct way to evaluate without information leakage. Parameters are named prep1__…, model__… (see the view)."),
    "explain.decision_boundary": ("DecisionBoundaryDisplay", "Map of the model's predictions in the plane of two features: each coloured area is a predicted class (or a predicted value for regression), with the table's points on top. Intensity shows the confidence (maximum probability) when available. Ideal with make_moons or make_circles to see under- or overfitting. Other features are fixed at their median (or mode)."),
    "explain.tree": ("plot_tree / export_text", "Draws a decision tree: condition of each node, number of samples, impurity and majority class (or mean value). For a forest or boosting, choose the index of the tree. Rules are also given as text (sklearn.tree.export_text)."),
    "explain.partial_dependence": ("partial_dependence", "Average effect of a feature on the prediction, all other features being averaged out (sklearn.inspection.partial_dependence). For classification, one curve per class (predicted probability)."),
    # Extensions fournies (kataml/contrib), activables dans « Mes blocs ».
    "ext.eda.overview": ("Overview", "Table profile: for each column, its type, missing values, cardinality, constant columns and sample values. Also gives the number of rows, columns and duplicates, and the share of missing cells."),
    "ext.eda.missing": ("Missing values", "Number and share of missing values per column, and co-occurrence patterns of missing values (correlation of missingness indicators: two columns often missing together have a value close to 1)."),
    "ext.eda.frequencies": ("Categorical frequencies (value_counts)", "Table and chart of the counts of the categories of a categorical column (value_counts). If no column is chosen, the first non-numeric column is used."),
    "ext.eda.target": ("Relationship with the target", "Ranks the features by strength of association with a target column, in [0,1]: Cramér's V (categorical–categorical), correlation ratio η (categorical–numeric) or |Pearson correlation| (numeric–numeric). Spots the features most related to the target before modelling."),
    "ext.eda.distributions": ("Distributions", "Histogram of each numeric feature (up to twelve) and a table of shape statistics (mean, standard deviation, skewness, kurtosis) to spot asymmetries and heavy tails."),
    "ext.eda.outliers": ("Outliers (IQR)", "Counts, for each numeric feature, the values outside [Q1 − k·IQR, Q3 + k·IQR] (Tukey's rule, k = 1.5 by default): a first screening of atypical values."),
    "ext.exemple.winsorize": ("Winsorizing", "Brings the extreme values of the chosen columns back to the given quantiles (for example 1% and 99%): outliers weigh less on models sensitive to extremes (linear regression, k-means…)."),
    "ext.exemple.frequency": ("Frequency encoding", "Replaces each category of a categorical variable by its relative frequency in the table: a compact alternative to one-hot encoding for variables with many categories."),
    "report.text": ("Report text", "Text block (Markdown) for the report: introduction, interpretation, conclusion… Place it on the canvas near the nodes it comments on: the report follows the workflow order (editable in the “Report” dialog). Syntax: # title, **bold**, *italic*, `code`, - list, > quote, [link](https://…)."),
}

# Libellés, ports, aides et choix (correspondance exacte).
PHRASES = {
    # Groupes de paramètres
    "Données": "Data", "Hyperparamètres": "Hyperparameters", "Paramètres": "Parameters", "Validation croisée": "Cross-validation",
    # Ports
    "Table": "Table", "Modèle": "Model", "Transformeur": "Transformer", "Table transformée": "Transformed table",
    "Table vectorisée": "Vectorized table", "Table + clusters": "Table + clusters", "Table + anomalies": "Table + outliers",
    "Table + distance de Mahalanobis": "Table + Mahalanobis distance", "Table + log-densité": "Table + log-density",
    "Table + voisins": "Table + neighbors", "Table + prédictions": "Table + predictions", "Table + probabilités": "Table + probabilities",
    "Apprentissage": "Train", "Test": "Test", "Table retenue": "Kept rows", "Table rejetée": "Rejected rows",
    "Gauche": "Left", "Droite": "Right", "Table 1": "Table 1", "Table 2": "Table 2", "Table 2 (optionnelle)": "Table 2 (optional)",
    "Statistiques": "Statistics", "Corrélations": "Correlations", "Métriques": "Metrics", "Matrice de confusion": "Confusion matrix",
    "AUC": "AUC", "Calibration": "Calibration", "Importances": "Importances", "Scores par pli": "Scores per fold",
    "Scores permutés": "Permuted scores", "Meilleur modèle": "Best model", "Résultats": "Results", "Recherche (configuration)": "Search (configuration)", "Courbe": "Curve",
    "Classement": "Ranking", "Dépendances": "Dependences", "Modèle (configuration)": "Model (configuration)",
    "Estimateur de base": "Base estimator", "Estimateur de base (optionnel)": "Base estimator (optional)",
    "Modèle final (optionnel)": "Final estimator (optional)", "Table brute": "Raw table", "Pipeline": "Pipeline",
    "Prétraitement 1": "Preprocessing 1", "Prétraitement 2": "Preprocessing 2", "Prétraitement 3": "Preprocessing 3",
    **{f"Modèle {i}": f"Model {i}" for i in range(1, 7)},
    # Libellés de paramètres
    "Colonne cible": "Target column", "Colonnes cibles": "Target columns",
    "Variables explicatives (vide = toutes les autres)": "Features (empty = all other columns)",
    "Variables explicatives (vide = toutes sauf les cibles)": "Features (empty = all but the targets)",
    "Variables (vide = toutes les numériques)": "Features (empty = all numeric columns)",
    "Variables (vide = 3 premières)": "Features (empty = first 3)", "Poids des observations (sample_weight)": "Sample weights (sample_weight)",
    "Colonne numérique de poids, facultative.": "Optional numeric weight column.",
    "Nom de la colonne de cluster": "Cluster column name", "Nom de la colonne d'anomalie": "Outlier column name",
    "Colonnes à transformer (vide = toutes sauf la cible)": "Columns to transform (empty = all but the target)",
    "Cible (transformeurs supervisés uniquement)": "Target (supervised transformers only)",
    "Requise par ex. pour SelectKBest ou LinearDiscriminantAnalysis. Reste dans la table.": "Required e.g. by SelectKBest or LinearDiscriminantAnalysis. Stays in the table.",
    "Colonne de texte": "Text column", "Fichier": "File", "Feuille (Excel)": "Sheet (Excel)", "Colonnes à transformer (vide = toutes les colonnes texte)": "Columns to transform (empty = all text columns)", "Colonnes à transformer (vide = toutes les colonnes numériques)": "Columns to transform (empty = all numeric columns)", "Base de données": "Database", "Requête SQL ou nom de table": "SQL query or table name", "Nombre maximal de lignes (0 = toutes)": "Maximum number of rows (0 = all)", "Séparateur": "Separator", "Séparateur décimal": "Decimal separator",
    "Première ligne = en-têtes": "First row = header", "Encodage": "Encoding", "Valeurs manquantes supplémentaires": "Extra missing values",
    "Nom d'un fichier de workspace/data ou chemin absolu.": "Name of a file in workspace/data or absolute path.",
    "Vide = détection automatique (, ; tabulation |).": "Empty = automatic detection (, ; tab |).", "Ex. : NA, ?, -": "E.g.: NA, ?, -",
    "Jeu de données": "Dataset", "Nombre d'échantillons (générateurs)": "Number of samples (generators)",
    "Nombre de variables (classification/régression)": "Number of features (classification/regression)",
    "Bruit (générateurs)": "Noise (generators)", "Nombre de classes / centres": "Number of classes / centers",
    "Graine aléatoire": "Random state", "Fichier de sortie": "Output file", "Écrire l'index": "Write index",
    "Colonnes": "Columns", "Mode": "Mode", "Expression": "Expression", "Syntaxe DataFrame.query.": "DataFrame.query syntax.",
    "Nom de la colonne": "Column name", "Colonnes à vérifier (vide = toutes)": "Columns to check (empty = all)",
    "Proportion de test": "Test size", "Entre 0 et 1, ou un nombre de lignes entier.": "Between 0 and 1, or an integer number of rows.",
    "Stratifier selon": "Stratify by", "Mélanger": "Shuffle", "Fraction (0–1)": "Fraction (0–1)",
    "Ignorée si un nombre de lignes est donné.": "Ignored if a number of rows is given.", "Nombre de lignes": "Number of rows",
    "Avec remise": "With replacement", "Croissant": "Ascending", "Type cible": "Target type", "Grouper par": "Group by",
    "Colonnes à agréger (vide = toutes)": "Columns to aggregate (empty = all)", "Fonction": "Function",
    "Clé(s) gauche": "Left key(s)", "Clé(s) droite": "Right key(s)", "Type": "Type", "Réindexer": "Reset index",
    "Correspondances": "Mappings", "Une ligne par colonne : ancien -> nouveau": "One line per column: old -> new", "Code": "Code",
    # Remise en forme (grammaire des données)
    "Colonnes d'identifiants (conservées)": "Identifier columns (kept)",
    "Colonnes à dépivoter (vide = toutes les autres)": "Columns to unpivot (empty = all others)",
    "Nom de la colonne de variable": "Variable column name", "Nom de la colonne de valeur": "Value column name",
    "Colonnes d'index (lignes)": "Index columns (rows)", "Colonne(s) étalée(s) en colonnes": "Column(s) spread into columns",
    "Colonne(s) de valeurs (vide = toutes les autres)": "Value column(s) (empty = all others)",
    "Fonction d'agrégation (doublons)": "Aggregation function (duplicates)",
    "Colonne à scinder": "Column to split", "Vide = espaces.": "Empty = whitespace.",
    "Noms des colonnes (séparés par des virgules ; vide = automatique)": "Column names (comma-separated; empty = automatic)",
    "Colonnes à réunir": "Columns to unite", "Supprimer les colonnes d'origine": "Drop the original columns",
    "Colonne à éclater": "Column to explode", "Séparateur (si la colonne est du texte)": "Separator (if the column is text)",
    "Vide = la colonne contient déjà des listes.": "Empty = the column already holds lists.",
    "Colonnes à considérer (vide = toutes)": "Columns to consider (empty = all)", "Garder": "Keep",
    "Première occurrence": "First occurrence", "Dernière occurrence": "Last occurrence",
    "Colonnes (vide = toutes)": "Columns (empty = all)", "Sens": "Direction",
    "Vers l'avant (ffill)": "Forward (ffill)", "Vers l'arrière (bfill)": "Backward (bfill)",
    # Extensions fournies : ports et paramètres
    "Profil": "Profile", "Manquants par colonne": "Missing values per column", "Effectifs": "Counts",
    "Associations": "Associations", "Statistiques de forme": "Shape statistics", "Valeurs extrêmes": "Outliers",
    "Modalités affichées": "Categories shown", "Variables (vide = toutes les autres)": "Features (empty = all others)",
    "Facteur IQR (k)": "IQR factor (k)", "Colonnes (vide = toutes les numériques)": "Columns (empty = all numeric)",
    "Quantile bas": "Lower quantile", "Quantile haut": "Upper quantile", "Colonnes catégorielles": "Categorical columns",
    "Colonnes de dates": "Date columns", "Éléments à extraire": "Parts to extract", "Encodage cyclique (sin/cos)": "Cyclic encoding (sin/cos)",
    "Supprimer la colonne d'origine": "Drop the original column", "Nom ou identifiant": "Name or id", "Version": "Version",
    "Numéro de version, ou « active » pour la dernière.": "Version number, or “active” for the latest.",
    "Axe X": "X axis", "Axe Y": "Y axis", "Couleur": "Colour", "Points max.": "Max points", "Colonne": "Column",
    "Nombre de classes": "Number of bins", "Méthode": "Method", "Colonnes (vide = numériques)": "Columns (empty = numeric)",
    "Standardiser (z-score)": "Standardize (z-score)", "Ajouter les probabilités": "Add probabilities",
    "Ajouter les probabilités (classification)": "Add probabilities (classification)",
    "Nom de la colonne (vide = automatique)": "Column name (empty = automatic)",
    "Colonne réelle (auto si vide)": "True column (auto if empty)", "Colonne prédite (auto si vide)": "Predicted column (auto if empty)",
    "Première colonne": "First column", "Deuxième colonne": "Second column", "Colonne de clusters (auto si vide)": "Cluster column (auto if empty)",
    "Table de contingence": "Contingency table", "Silhouette par cluster": "Silhouette per cluster",
    "Nombre de classes de probabilité": "Number of probability bins", "Découpage": "Strategy", "Répétitions": "Repeats",
    "Score": "Scoring", "Vide = score par défaut du modèle. Ex. 'f1_macro', 'r2'.": "Empty = model's default score. E.g. 'f1_macro', 'r2'.",
    "Métriques ": "Scoring", "Vide = score par défaut (exactitude ou R²).": "Empty = default score (accuracy or R²).",
    "Stratégie": "Strategy", "Nombre de plis (k)": "Number of folds (n_splits)", "Répétitions (stratégies répétées)": "Repeats (repeated strategies)",
    "Part de test (stratégies ShuffleSplit)": "Test size (ShuffleSplit strategies)",
    "Colonne de groupes (stratégies par groupes)": "Groups column (group strategies)",
    "Les lignes d'un même groupe (patient, client, site…) restent du même côté de la séparation.": "Rows of the same group (patient, customer, site…) stay on the same side of the split.",
    "Nombre de permutations": "Number of permutations", "Métrique": "Scoring", "Grille de paramètres": "Parameter grid",
    "Stratégie de recherche": "Search strategy", "Itérations (aléatoire)": "Iterations (randomised)", "Nombre de tailles": "Number of sizes",
    "Hyperparamètre": "Hyperparameter", "Nom exact du paramètre (voir la vue du modèle).": "Exact parameter name (see the model view).",
    "Valeurs testées": "Values tested", "Liste Python, ex. [1, 2, 4, 8, None].": "Python list, e.g. [1, 2, 4, 8, None].",
    "Échelle logarithmique": "Log scale", "Axe X (vide = 1re variable)": "X axis (empty = 1st feature)",
    "Axe Y (vide = 2e variable)": "Y axis (empty = 2nd feature)", "Résolution de la grille": "Grid resolution",
    "Points affichés max.": "Max displayed points", "Profondeur affichée": "Displayed depth",
    "Indice de l'arbre (forêts, boosting)": "Tree index (forests, boosting)", "Points par courbe": "Points per curve",
    "Titre de la section": "Section title", "Facultatif.": "Optional.", "Texte (Markdown)": "Text (Markdown)",
    # Choix
    "(par défaut)": "(default)", "Garder la sélection": "Keep selection", "Retirer la sélection": "Remove selection",
    "Numérique": "Numeric", "Texte": "Text", "Catégorie": "Category", "Booléen": "Boolean", "Date / heure": "Date / time",
    "Interne": "Inner", "Complète": "Outer", "Grille exhaustive (GridSearchCV)": "Exhaustive grid (GridSearchCV)",
    "Aléatoire (RandomizedSearchCV)": "Randomised (RandomizedSearchCV)", "Intervalles égaux": "Uniform", "Effectifs égaux (quantiles)": "Quantile",
    "Année": "Year", "Trimestre": "Quarter", "Mois": "Month", "Jour du mois": "Day of month", "Jour de la semaine (0 = lundi)": "Day of week (0 = Monday)",
    "Jour de l'année": "Day of year", "Semaine ISO": "ISO week", "Heure": "Hour", "Minute": "Minute", "Week-end (0/1)": "Weekend (0/1)",
    "Automatique (StratifiedKFold en classification, sinon KFold)": "Automatic (StratifiedKFold for classification, else KFold)",
    "GroupKFold (par groupes)": "GroupKFold (groups)", "StratifiedGroupKFold (par groupes)": "StratifiedGroupKFold (groups)",
    "GroupShuffleSplit (par groupes)": "GroupShuffleSplit (groups)", "LeaveOneGroupOut (par groupes)": "LeaveOneGroupOut (groups)",
    "TimeSeriesSplit (séries temporelles)": "TimeSeriesSplit (time series)",
    "Iris (classification, 150×4, 3 classes)": "Iris (classification, 150×4, 3 classes)",
    "Vins (classification, 178×13, 3 classes)": "Wine (classification, 178×13, 3 classes)",
    "Cancer du sein (classification binaire, 569×30)": "Breast cancer (binary classification, 569×30)",
    "Chiffres manuscrits (classification, 1797×64)": "Digits (classification, 1797×64)",
    "Diabète (régression, 442×10)": "Diabetes (regression, 442×10)", "Linnerud (régression multi-sorties, 20×3)": "Linnerud (multi-output regression, 20×3)",
    "Générateur : classification": "Generator: classification", "Générateur : régression": "Generator: regression",
    "Générateur : nuages gaussiens (blobs)": "Generator: Gaussian blobs", "Générateur : deux lunes": "Generator: two moons",
    "Générateur : cercles concentriques": "Generator: concentric circles", "oui": "yes", "non": "no",
}

# Vues, messages et erreurs (correspondance exacte).
VIEW = {
    "Lignes": "Rows", "Colonnes": "Columns", "Valeurs manquantes": "Missing values", "Doublons": "Duplicates",
    "Résumé par colonne": "Summary per column", "Distributions": "Distributions", "Variables": "Features",
    "Exactitude (apprentissage)": "Accuracy (training)", "R² (apprentissage)": "R² (training)", "Classes": "Classes",
    "Clusters": "Clusters", "Silhouette": "Silhouette", "Bruit (-1)": "Noise (-1)", "Taille des clusters": "Cluster sizes",
    "Modèle": "Model", "Colonnes en entrée": "Input columns", "Colonnes en sortie": "Output columns",
    "Variance expliquée par composante": "Explained variance per component", "Ratio": "Ratio",
    "Scores des variables (scores_)": "Feature scores (scores_)", "Importance des variables (feature_importances_)": "Feature importances (feature_importances_)",
    "Coefficients (coef_)": "Coefficients (coef_)", "|Coefficients| moyens (coef_)": "Mean |coefficients| (coef_)",
    "Exactitude": "Accuracy", "Exactitude équilibrée": "Balanced accuracy", "Précision (macro)": "Precision (macro)",
    "Rappel (macro)": "Recall (macro)", "F1 (macro)": "F1 (macro)", "F1 (pondéré)": "F1 (weighted)", "Kappa de Cohen": "Cohen's kappa",
    "Perte de Hamming": "Hamming loss", "Perte 0-1": "Zero-one loss", "Log-loss": "Log loss", "Exactitude top-2": "Top-2 accuracy",
    "V de Cramér": "Cramér's V", "Indice de Rand ajusté": "Adjusted Rand index", "Indice de Rand": "Rand index",
    "Information mutuelle ajustée": "Adjusted mutual information", "Information mutuelle normalisée": "Normalized mutual information",
    "Information mutuelle": "Mutual information", "V-mesure": "V-measure", "Homogénéité": "Homogeneity", "Complétude": "Completeness",
    "Fowlkes–Mallows": "Fowlkes–Mallows", "Accord brut": "Raw agreement", "Table de contingence": "Contingency table",
    "Calinski–Harabasz": "Calinski–Harabasz", "Davies–Bouldin": "Davies–Bouldin", "Silhouette moyenne par cluster": "Mean silhouette per cluster",
    "Silhouette par cluster": "Silhouette per cluster", "cluster": "cluster", "silhouette": "silhouette", "taille": "size",
    # Extensions fournies : vues
    "Cellules manquantes": "Missing cells", "Profil par colonne": "Profile per column",
    "Colonnes avec manquants": "Columns with missing values", "Lignes complètes": "Complete rows",
    "Valeurs manquantes par colonne (%)": "Missing values per column (%)",
    "Co-occurrence des manquants": "Co-occurrence of missing values", "Modalités": "Categories", "Manquants": "Missing",
    "Cible numérique": "Numeric target", "Cible catégorielle": "Categorical target",
    "Association à la cible (0–1)": "Association with the target (0–1)", "Variables classées": "Ranked features",
    "Total extrêmes": "Total outliers", "Valeurs extrêmes par variable": "Outliers per feature",
    "Bornes et comptage": "Bounds and counts",
    "% manquants": "% missing", "constante": "constant", "exemples": "examples", "variable": "feature",
    "asymétrie": "skewness", "aplatissement": "kurtosis", "bas": "low", "haut": "high",
    "nb_extrêmes": "n_outliers", "% extrêmes": "% outliers",
    "Matrice de confusion": "Confusion matrix", "Prédit": "Predicted", "Réel": "True", "Rapport par classe": "Per-class report",
    "classe": "class", "précision": "precision", "rappel": "recall", "effectif": "support", "métrique": "metric", "valeur": "value",
    "Erreur absolue médiane": "Median absolute error", "Variance expliquée": "Explained variance", "Erreur max": "Max error",
    "D² (erreur absolue)": "D² (absolute error)", "Déviance de Poisson": "Poisson deviance", "Déviance Gamma": "Gamma deviance",
    "Prédit vs réel": "Predicted vs true", "Distribution des résidus (prédit − réel)": "Residuals distribution (predicted − true)",
    "Résidu": "Residual", "Résidus": "Residuals", "Effectif": "Count", "Courbe ROC": "ROC curve",
    "Taux de faux positifs": "False positive rate", "Taux de vrais positifs": "True positive rate", "Précision-rappel": "Precision-recall",
    "Rappel": "Recall", "Précision": "Precision", "Importance par permutation": "Permutation importance",
    "Synthèse": "Summary", "mesure": "measure", "Plis": "Folds", "Score par pli": "Score per fold",
    # En-têtes des tableaux de vue (statistiques, comparaison de modèles) et séries.
    "colonne": "column", "non_nuls": "non_null", "manquants": "missing", "uniques": "unique",
    "moyenne": "mean", "écart_type": "std", "médiane": "median", "rang": "rank", "modèle": "model",
    "score moyen": "mean score", "écart-type": "std", "temps d'ajustement (s)": "fit time (s)",
    "prédiction": "prediction",
    "pli": "fold",
    "Meilleur score (CV)": "Best score (CV)", "Combinaisons testées": "Combinations tested", "Meilleurs paramètres": "Best parameters",
    "Classement": "Ranking", "Courbe d'apprentissage": "Learning curve", "Taille du jeu d'apprentissage": "Training set size",
    "Score": "Score", "Apprentissage": "Training", "Validation": "Validation", "Étapes": "Steps",
    "Paramètres réglables (pour la recherche d'hyperparamètres)": "Tunable parameters (for hyperparameter search)",
    "paramètre": "parameter", "Variables candidates": "Candidate features", "Variables retenues": "Selected features",
    "Hyperparamètres choisis dans chaque pli (validation imbriquée)": "Hyperparameters chosen in each fold (nested validation)",
    "Validation croisée imbriquée : la recherche d'hyperparamètres est refaite dans chaque pli externe ; le score évalue la procédure de réglage complète.":
        "Nested cross-validation: the hyperparameter search is redone in each outer fold; the score evaluates the whole tuning procedure.",
    "Validation croisée imbriquée : la recherche interne utilise une stratégie par groupes, non prise en charge ici. Choisissez une autre stratégie dans la recherche (la validation externe peut, elle, être par groupes).":
        "Nested cross-validation: the inner search uses a group strategy, which is not supported here. Choose another strategy in the search (the outer validation can use groups).",
    "Rang d'élimination (1 = retenue)": "Elimination rank (1 = selected)", "Meilleur modèle": "Best model",
    "Modèles comparés": "Models compared", "Dispersion des scores par pli": "Score spread per fold", "Autres variables fixées": "Other features fixed",
    "Arbre de décision": "Decision tree", "Profondeur": "Depth", "Feuilles": "Leaves", "Nœuds": "Nodes", "Règles": "Rules",
    "Meilleure valeur": "Best value", "Score de validation": "Validation score", "Probabilité": "Probability", "Prédiction": "Prediction",
    "Courbe de calibration": "Calibration curve", "Probabilité prédite (moyenne)": "Mean predicted probability",
    "Fréquence observée": "Observed frequency", "Distribution des probabilités prédites": "Distribution of predicted probabilities",
    "Documents": "Documents", "Termes": "Terms", "Termes les plus fréquents (nombre de documents)": "Most frequent terms (number of documents)",
    "Description": "Description", "Sortie standard": "Standard output", "Anomalies": "Outliers", "Proportion": "Proportion",
    "Anomalies (2 premières variables)": "Outliers (first 2 features)", "Distribution des scores": "Score distribution",
    "Score (bas = atypique)": "Score (low = atypical)", "Matrice de covariance estimée": "Estimated covariance matrix",
    "Distribution de la log-densité": "Log-density distribution", "Log-densité": "Log-density", "log-densité": "log-density",
    "Dimensions en sortie": "Output dimensions", "Plongement (2 premières dimensions)": "Embedding (first 2 dimensions)",
    "Score du modèle": "Model score", "Score moyen au hasard": "Mean chance score", "p-valeur": "p-value",
    "Scores obtenus en mélangeant la cible": "Scores obtained by shuffling the target", "permutations": "permutations",
    "Valeurs écrêtées par colonne": "Clipped values per column", "anomalie": "outlier", "normal": "normal",
    # Erreurs et messages fréquents
    "Ce nœud n'est pas exécuté.": "This node has not been executed.", "Choisissez la colonne cible.": "Choose the target column.",
    "La colonne cible contient des valeurs manquantes.": "The target column contains missing values.",
    "Un modèle supervisé est requis.": "A supervised model is required.",
    "Un modèle supervisé (classification ou régression) est requis.": "A supervised model (classification or regression) is required.",
    "Ce modèle est un transformeur : utilisez « Appliquer un transformeur ».": "This model is a transformer: use “Transformer apply”.",
    "Ce modèle n'est pas un transformeur : utilisez le « Prédicteur ».": "This model is not a transformer: use the “Predictor”.",
    "Expression vide.": "Empty expression.", "Branchez au moins deux modèles.": "Connect at least two models.",
    "Branchez au moins un modèle.": "Connect at least one model.", "Cette stratégie demande une colonne de groupes.": "This strategy needs a groups column.",
    "Choisissez au moins deux colonnes cibles.": "Choose at least two target columns.", "Choisissez la colonne de texte.": "Choose the text column.",
    "Choisissez la colonne réelle et la colonne prédite.": "Choose the true and predicted columns.",
    "Il faut au moins deux colonnes numériques.": "At least two numeric columns are needed.", "Il faut au moins deux variables.": "At least two features are needed.",
    "La grille doit être un dictionnaire non vide.": "The grid must be a non-empty dictionary.",
    "La régression isotonique n'utilise qu'une seule variable : choisissez-la.": "Isotonic regression uses a single feature: choose it.",
    "Le script doit affecter un DataFrame à la variable `out`.": "The script must assign a DataFrame to the `out` variable.",
    "Les modèles mélangent classification et régression.": "The models mix classification and regression.",
    "Exécution interrompue.": "Run interrupted.", "Rien à télécharger.": "Nothing to download.", "Port inexistant.": "No such port.",
    "Donnez au moins deux valeurs, sous forme de liste.": "Give at least two values, as a list.",
    "L'estimateur de base doit être un modèle supervisé.": "The base estimator must be a supervised model.",
    # Messages des nœuds de métriques, de remise en forme et des extensions fournies
    "Choisissez les deux colonnes à comparer.": "Choose the two columns to compare.",
    "Aucune ligne sans valeur manquante dans les deux colonnes.": "No row without missing values in both columns.",
    "Choisissez la colonne de clusters.": "Choose the cluster column.",
    "Aucune variable numérique pour évaluer le clustering.": "No numeric feature to evaluate the clustering.",
    "La silhouette demande entre 2 clusters et n−1 lignes : vérifiez la colonne de clusters.":
        "The silhouette needs between 2 clusters and n−1 rows: check the cluster column.",
    "Choisissez au moins une colonne d'index et une colonne à étaler.": "Choose at least one index column and one column to spread.",
    "Aucune colonne de valeurs numérique : choisissez les colonnes de valeurs, ou la fonction « first » ou « count ».":
        "No numeric value column: choose the value columns, or the “first” or “count” function.",
    "Choisissez au moins une colonne à réunir.": "Choose at least one column to unite.",
    "La table ne contient aucune colonne.": "The table has no column.",
    "Aucune association calculable (données insuffisantes).": "No association can be computed (not enough data).",
    "Aucune variable numérique à représenter.": "No numeric feature to plot.",
    "Aucune variable numérique à analyser.": "No numeric feature to analyse.",
    "Les quantiles doivent vérifier 0 ≤ bas < haut ≤ 1.": "Quantiles must satisfy 0 ≤ low < high ≤ 1.",
    "Les données contiennent des valeurs manquantes. Ajoutez un nœud SimpleImputer ou « Lignes incomplètes » en amont, ou choisissez un estimateur qui les gère (HistGradientBoosting…).":
        "The data contains missing values. Add a SimpleImputer or “Drop missing rows” node upstream, or choose an estimator that handles them (HistGradientBoosting…).",
}

PATTERNS = [
    (r"^(\S+) a besoin de la colonne à prédire : .*$",
     lambda m: f"{m[1]} needs the column to predict: choose it in the “Target (supervised transformers only)” field. "
               "It is not transformed and stays in the table."),
    (r"^Aucune colonne (texte|numérique) à transformer dans la table(?: \(hors cible « (.+) »\))?\.$",
     lambda m: f"No {'text' if m[1] == 'texte' else 'numeric'} column to transform in the table"
               + (f" (apart from the target “{m[2]}”)." if m[2] else ".")),
    (r"^Colonnes choisies automatiquement : (.+)$", lambda m: f"Columns chosen automatically: {m[1]}"),
    (r"^(\S+) n'accepte que des colonnes numériques\. (Les colonnes choisies incluent|Aucune colonne n'étant choisie, toutes sont transformées, y compris) (la colonne texte|les colonnes texte) (.+?)\. Si c'est la colonne à prédire.*$",
     lambda m: (f"{m[1]} only accepts numeric columns. "
                + ("The chosen columns include" if m[2].startswith("Les") else "No column being chosen, all are transformed, including")
                + (" the text column " if m[3].startswith("la") else " the text columns ")
                + m[4].replace("« ", "“").replace(" »", "”")
                + ". If it is the column to predict, set it in the “Target” field; otherwise choose the "
                  "“Columns to transform” or encode these columns first (OneHotEncoder, OrdinalEncoder).")),
    (r"^Port d'entrée « (.+) » non connecté\.$", r"Input port “\1” is not connected."),
    (r"^Colonnes non numériques : (.+)\. Encodez-les \(OneHotEncoder, OrdinalEncoder\) ou excluez-les des variables\.$",
     r"Non-numeric columns: \1. Encode them (OneHotEncoder, OrdinalEncoder) or exclude them from the features."),
    (r"^(Colonne|Colonne cible|Variable du modèle|Colonne du transformeur|Colonne de groupes|Colonne de poids) introuvable\(s\) : (.+?)\. Colonnes disponibles : (.+)$",
     r"Column(s) not found: \2. Available columns: \3"),
    (r"^Fichier introuvable : (.+)$", r"File not found: \1"), (r"^Expression invalide : (.+)$", r"Invalid expression: \1"),
    (r"^Paramètre invalide : (.+)$", r"Invalid parameter: \1"), (r"^Paramètres inconnus pour (.+?) : (.+?)\. Paramètres réglables : (.+)$",
     r"Unknown parameters for \1: \2. Tunable parameters: \3"), (r"^Paramètre inconnu « (.+) »\. Possibles : (.+)$", r"Unknown parameter “\1”. Possible: \2"),
    (r"^Grille invalide \(dictionnaire Python attendu\) : (.+)$", r"Invalid grid (Python dictionary expected): \1"),
    (r"^Valeurs invalides \(liste Python attendue\) : (.+)$", r"Invalid values (Python list expected): \1"),
    (r"^(.+) ne sait pas prédire de nouvelles données \(pas de méthode predict\)\.$", r"\1 cannot predict new data (no predict method)."),
    (r"^(.+) ne fait pas de prédiction : son résultat est dans sa table de sortie\.$", r"\1 does not predict: its result is in its output table."),
    (r"^Le prétraitement (\d+) \((.+)\) transforme la colonne cible « (.+) » : indiquez-la comme cible dans ce nœud pour l'exclure\.$",
     r"Preprocessing \1 (\2) transforms the target column “\3”: set it as the target in that node to exclude it."),
    (r"^Les modèles n'ont pas la même cible : (.+)\.$", r"The models do not share the same target: \1."),
    (r"^(\d+) lignes supprimées$", r"\1 rows dropped"), (r"^Écrit : (.+)$", r"Written: \1"),
    (r"^(\d+) lignes écrites dans (.+)$", r"\1 rows written to \2"), (r"^Modèle écrit dans (.+)$", r"Model written to \1"),
    (r"^(.+) \(moyenne ± écart-type\)$", r"\1 (mean ± std)"), (r"^Pli (\d+)$", r"Fold \1"), (r"^AUC (.+)$", r"AUC \1"),
    (r"^Brier (.+)$", r"Brier \1"), (r"^Score moyen \((.+)\) ± écart-type$", r"Mean score (\1) ± std"),
    (r"^Score \((.+)\)$", r"Score (\1)"), (r"^Corrélation \((.+)\)$", r"Correlation (\1)"),
    (r"^Frontière de décision \((.+)\)$", r"Decision boundary (\1)"), (r"^Dépendance partielle : (.+)$", r"Partial dependence: \1"),
    (r"^Courbe de validation \((.+)\)$", r"Validation curve (\1)"), (r"^Réel \((.+)\)$", r"True (\1)"),
    (r"^Score \(modèle : (.+)\)$", r"Score (model: \1)"),
    (r"^(.+) \((\d+) lignes × (\d+) colonnes, aperçu\)$", r"\1 (\2 rows × \3 columns, preview)"),
    (r"^Workflow « (.+) » exporté depuis KataML\.$", r"Workflow “\1” exported from KataML."),
    (r"^La fonction « (.+) » demande des colonnes numériques, ce que ne sont pas : (.+)\. Choisissez la fonction « first » ou « count », ou d'autres colonnes de valeurs\.$",
     r"The “\1” function needs numeric columns, which these are not: \2. Choose the “first” or “count” function, or other value columns."),
    (r"^Effectifs — (.+) \(jusqu'à (\d+)\)$", r"Counts — \1 (up to \2)"),
    (r"^Extension fournie inconnue : (.+)$", r"Unknown bundled extension: \1"),
]
_PATTERNS = [(re.compile(a), b) for a, b in PATTERNS]


def text(s: str) -> str:
    if not isinstance(s, str) or not s:
        return s
    if s in VIEW:
        return VIEW[s]
    if s in PHRASES:
        return PHRASES[s]
    for rx, rep in _PATTERNS:
        if rx.match(s):
            return rx.sub(rep, s)
    return s


def translate_spec(spec: dict, lang: str) -> dict:
    if lang != "en":
        return spec
    spec = copy.deepcopy(spec)
    name, desc = NODES.get(spec["type"], (None, None))
    if name:
        spec["name"], spec["description"] = name, desc
    elif spec.get("description_en"):
        spec["description"] = spec["description_en"]
    for port in spec["inputs"] + spec["outputs"]:
        port["name"] = PHRASES.get(port["name"], port["name"])
    for p in spec["params"]:
        p["label"] = PHRASES.get(p["label"], p["label"])
        if p.get("help"):
            p["help"] = PHRASES.get(p["help"], p["help"])
        if p.get("group"):
            p["group_label"] = PHRASES.get(p["group"], p["group"])
        if p.get("choice_labels"):
            p["choice_labels"] = {k: PHRASES.get(v, v) for k, v in p["choice_labels"].items()}
    return spec


def _blocks(blocks: list) -> list:
    out = []
    for b in blocks or []:
        b = dict(b)
        for k in ("title", "xlabel", "ylabel", "clabel", "label"):
            if k in b:
                b[k] = text(b[k])
        if b.get("type") == "metrics":
            b["items"] = [{**it, "label": text(it.get("label"))} for it in b.get("items", [])]
        if b.get("type") == "table":
            b["columns"] = [text(c) for c in b.get("columns", [])]
        if isinstance(b.get("labels"), list) and b.get("chart") in ("groupedbar", "bar"):
            b["labels"] = [text(x) if isinstance(x, str) else x for x in b["labels"]]
        if "series" in b:
            b["series"] = [{**s, "name": text(s.get("name"))} for s in b["series"]]
        if b.get("chart") == "scatter" and b.get("groups"):
            b["groups"] = [text(g) for g in b["groups"]]
        out.append(b)
    return out


def translate_payload(obj, lang: str):
    """Traduit les champs textuels d'une réponse d'API (sans toucher aux données des tables)."""
    if lang != "en" or not isinstance(obj, dict):
        return obj
    obj = dict(obj)
    for k in ("error", "message"):
        if isinstance(obj.get(k), str):
            obj[k] = text(obj[k])
    if isinstance(obj.get("messages"), list):
        obj["messages"] = [text(m) for m in obj["messages"]]
    if isinstance(obj.get("blocks"), list):
        obj["blocks"] = _blocks(obj["blocks"])
    if isinstance(obj.get("states"), dict):
        obj["states"] = {nid: translate_payload(st, lang) for nid, st in obj["states"].items()}
    if isinstance(obj.get("sections"), list):
        obj["sections"] = [{**s, "blocks": _blocks(s.get("blocks")), "message": text(s.get("message"))} for s in obj["sections"]]
    return obj
