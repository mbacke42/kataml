# Frequently asked questions

## Using KataML

??? question "A node stays red: what should I do?"
    Read its information line, or the inspector: the message names the missing required
    parameter (“Parameter “Target column” required”) or the unconnected input. After a
    run-time error, the full message is shown in the inspector.

??? question "“Features must be numeric”"
    scikit-learn models only accept numbers. Encode text columns (**OneHotEncoder**,
    **OrdinalEncoder**), vectorise free text (**TfidfVectorizer**), extract date parts
    (**Date features**), or exclude these columns from **Features**. See
    [tutorial 3](tutorials/03-csv-cleaning.md).

??? question "“StandardScaler only accepts numeric columns”"
    With no columns chosen, a transformer applies to every column, including the target if
    it is text (`species`…). Set the target in its **Target** field, choose the **Columns to
    transform**, or encode text columns first (**OneHotEncoder**). The message names the
    offending columns.

??? question "How do I cross-validate StandardScaler + a model?"
    Combine them in a **Pipeline** and connect it to the cross-validation, with the raw
    table: see [The Pipeline](concepts/pipeline.md). If you connect the model directly, the
    cross-validation inspector offers **Create and use the Pipeline**.

??? question "How do I run a nested cross-validation?"
    Connect the **Search (configuration)** output of the **GridSearchCV /
    RandomizedSearchCV** node to a **cross_validate** node: see
    [Nested cross-validation](concepts/cross-validation.md#nested-cross-validation).

??? question "“Missing values”"
    Most estimators reject `NaN`. Use **SimpleImputer** (or **KNNImputer**,
    **IterativeImputer**) in a Pipeline, drop the rows with **Drop missing rows**, or pick
    a model that accepts them (**HistGradientBoostingClassifier / Regressor**).

??? question "The result does not change when I edit my CSV file"
    The cache takes the file's modification date into account: rerun the CSV reader. If
    the file was replaced by a copy with the same date, use **Reset** (++f8++) on the node.

??? question "My training score is 100 %, is that good?"
    Not in itself: it is often the sign of a model that has learnt by heart. Only the score
    on unseen data (test set, cross-validation) matters. See
    [tutorial 5](tutorials/05-overfitting.md).

??? question "What is the difference between train_test_split and cross-validation?"
    The split makes **one** train / test division: simple, but the test score depends on
    the luck of the split. Cross-validation makes **several** and gives a mean and a
    standard deviation. Both are often combined: cross-validation on the training set to
    choose, final test to confirm.

??? question "A computation takes too long"
    **Stop** (toolbar) interrupts it immediately. Reduce the data size (**Sampling**), the
    number of folds, the grid size (or switch to randomised search), or set `n_jobs` = `-1`
    on models that offer it to use every core.

??? question "Where are my files?"
    In the workspace, whose path is printed in the terminal at startup (“Espace de
    travail : …”); the **My blocks** dialog also shows the blocks folder. See
    [Workspace](concepts/workspace.md).

## scikit-learn

??? question "Is all of scikit-learn available?"
    Every public scikit-learn estimator is a node, except those that make no sense as a
    standalone node; each exception is justified in the
    [reference](reference/index.md#excluded) (for example `GridSearchCV` is a dedicated
    node, so is `Pipeline`). An automated test checks this coverage against each
    scikit-learn version.

??? question "Which scikit-learn version is used?"
    The one in the environment: it is shown at the bottom of the repository, in the
    terminal at startup and in report headers. Nodes, their hyperparameters and their help
    are read from scikit-learn at startup: they follow the installed version.

??? question "Can I use XGBoost, LightGBM, SHAP…?"
    Not directly: KataML only depends on scikit-learn and pandas. But a
    [custom block](blocks.md) can use any library installed in the same environment (for
    example `uv tool install … --with xgboost`).

## Installation and security

??? question "Is an Internet connection required?"
    No, except to install KataML and for the **OpenML dataset** node (first download of a
    dataset). scikit-learn's built-in datasets are included. The interface also queries GitLab
    at most once a day to report a newer version; this call fails silently when offline and can
    be disabled (see below).

??? question "Is my data sent anywhere?"
    No. The server runs on your machine and only listens on `127.0.0.1`; requests must
    carry a token generated at startup. Your tables and workflows never leave your machine.
    The only outgoing request is the version check: a call to GitLab's public API with a
    generic User-Agent (the tool's name and the project URL) and no personal data. To disable
    it, start KataML with the environment variable `KATAML_NO_UPDATE_CHECK=1`.

??? question "Can I install KataML on a server for a class?"
    It can be done with `--host 0.0.0.0`, but it is not advisable outside a trusted network: the
    Python script node and custom blocks run code on the server, and all users would share
    the same workspace. Prefer one installation per workstation (portable builds or uv).

??? question "Port 8765 is already in use"
    KataML automatically takes the next free port (and prints it). You can also choose:
    `kataml --port 9000`.

??? question "The browser does not open"
    Open the address printed in the terminal (it contains the access token). With
    `--no-browser`, this is the expected behaviour.
