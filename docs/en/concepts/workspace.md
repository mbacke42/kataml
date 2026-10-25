# Workspace and files

## The workspace

All KataML data lives in one folder, the **workspace**:

```text
workspace/
  data/        imported files (CSV) and example data
  workflows/   saved workflows (.json)
  components/  reusable components (.json)
  extensions/  custom blocks (.py)
  reports/     generated reports (.html)
  exports/     outputs of the writer nodes (CSV, models)
  openml/      cache of datasets downloaded from OpenML
  .cache/      node results (disk cache)
  theme.css    colour customisation (optional, see Appearance)
```

Its location depends on how KataML is launched:

| Launch | Workspace |
|---|---|
| Linux AppImage | `kataml-workspace/`, next to the `.AppImage` file |
| Windows zip | `workspace/`, next to `KataML.bat` |
| `uv tool install` | `~/kataml` |
| from the repository (`kataml.sh`) | `workspace/` in the repository |
| `--workspace` option or `KATAML_WORKSPACE` variable | the given folder |

If the intended folder is not writable, KataML falls back to `~/kataml`.

## Workflows

A workflow is a JSON file: nodes (type, position, annotation, parameters), connections,
annotations, components and report settings. It is:

- saved automatically in the browser on every change, and restored at next launch;
- saved to `workspace/workflows` with ++ctrl+s++;
- exported or imported as a `.json` file from the **Open** dialog, to send it to
  someone or to version it with Git.

Workflows do not contain the data: a *CSV reader* refers to a file in `workspace/data` (or
an absolute path). To share a workflow, include its data files.

## Data

- Importing a CSV: the *CSV reader*'s **Import** button, or drag the file onto the
  canvas. It is copied to `workspace/data`.
- Downloading a table: the **CSV** button of the output panel, or right-click the node. A
  model downloads in joblib format.
- The **CSV writer** and **Model writer** nodes write to `workspace/exports` (or an
  absolute path) on each run, which is useful on the command line.

## Security and privacy

KataML runs entirely on your machine: no data is sent over the Internet. Only the
*OpenML dataset* node downloads data from openml.org, when you run it.
