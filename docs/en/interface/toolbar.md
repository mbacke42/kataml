# Toolbar

![Toolbar](../../assets/screenshots/en/toolbar.png){ .shot }

## Workflow name

The field on the left holds the workflow name; click to edit it. An orange dot signals
changes not yet saved to the workspace (the browser, for its part, saves automatically and
continuously).

## Buttons

| Button | Shortcut | Action |
|---|---|---|
| **New** | | empty workflow (asks for confirmation if changes are unsaved) |
| **Open** | | open a saved workflow, an example or a tutorial, or import a `.json` file |
| **Data** | | project data (CSV, Parquet, Excel, SQLite) and library of Python scripts to convert into workflows |
| **Save** | ++ctrl+s++ | save to `workspace/workflows` (++ctrl+shift+s++: save under another name) |
| ↶ / ↷ | ++ctrl+z++ / ++ctrl+y++ | undo / redo (structure, parameters, positions) |
| **Annotation** | ++a++ | add a note on the canvas |
| **Export** | | equivalent Python script or Jupyter notebook |
| **Report** | ++ctrl+p++ | generate an HTML report (see [Reports](../reports.md)) |
| **Arrange** | ++l++ | lay out the graph automatically (the selection, or the whole workflow) |
| **Reset** | | clear all results (and the cache) |
| **Run all** | ++shift+f7++ | run every configured node |
| **Stop** | | interrupt the running computation (visible during execution) |

On medium-sized screens, secondary buttons only show their icon: their label appears on
hover.

## Open

![“Open” dialog](../../assets/screenshots/en/dialog-open.png){ .shot }

The dialog lists **your workflows** (`workspace/workflows` folder) and the **examples**
shipped with KataML, which serve as solutions for the [tutorials](../tutorials/index.md).
The **Import a .json file** button loads a workflow received from elsewhere; **Export the
current workflow** saves it as a file.

### Import a Python script

**Import a Python script (.py)** rebuilds the workflow from a pandas / scikit-learn script:
each file read, split, transformer, model, prediction, metric or cross-validation becomes a
connected node. The script is not run, only analysed.

- If the script imports its own modules (`from myproject.config import TARGET`), select
  them at the same time: their constants and functions are used.
- Unrecognised pandas operations (`df["x"] = …`, `df.query(…)`) become **Python script**
  nodes that reproduce them.
- A yellow note on the canvas lists what could not be inferred (file, computed target
  column…): complete those nodes in the inspector, then run.

## Data and scripts

The **Data** button opens a two-part window.

- **Data** (`workspace/data`): CSV, Parquet, Excel files and SQLite databases. **To canvas**
  creates the reader matching the format; **Import** adds files (or drop them in the window).
- **Scripts** (`workspace/scripts`): the project's Python script library. **Add** `.py`
  files, **New** to start from a commented template, **View / edit** to edit them. Tick the
  script(s) to convert, then **Create the workflow**: the other scripts are used as modules
  when imported.

**Import a project folder** takes a whole folder: scripts join the library (`.venv`, `.git`,
cache folders… are ignored) and data files are located; only those read by the workflow are
imported at conversion time.

### Databases

The **SQL reader** node reads a SQLite database (`.db`, `.sqlite`) from `workspace/data`,
opened read-only, or a PostgreSQL / MySQL database from its connection URL, e.g.
`postgresql+psycopg://user@localhost:5432/db`. These databases need a driver:
`uv pip install sqlalchemy "psycopg[binary]"` (PostgreSQL) or `uv pip install sqlalchemy pymysql`
(MySQL), in the KataML folder.

!!! tip "Password"
    Write `$DATABASE_URL` instead of the URL: it is read from the environment variable of
    the same name (`export DATABASE_URL=…` before starting KataML), and no password is saved
    in the workflow.

## Export to Python

![Python export](../../assets/screenshots/en/dialog-export.png){ .shot }

KataML translates the workflow into pandas / scikit-learn code, node by node, in
execution order:

- **Script** `.py`: standalone, runnable with `python my_workflow.py`;
- **Notebook** `.ipynb`: one cell per node, preceded by a title; annotations become text
  cells.

Reading the export of a workflow you have built shows how each node is written in
scikit-learn.

## Stopping a computation

Computations run in a separate process. **Stop** interrupts it immediately (even in the
middle of a long training) then restarts it; results already obtained are kept thanks to
the cache. See [Execution and cache](../concepts/execution.md).
