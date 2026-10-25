# Command line

## Launching the interface

```bash
kataml [--port 8765] [--host 127.0.0.1] [--workspace FOLDER] [--no-browser]
```

See [Installation › Launch options](installation.md#launch-options). From the repository,
`./kataml.sh` (or `kataml.bat`) accepts the same options.

## Running a workflow without the interface

```bash
kataml run workflow.json [--rapport report.html] [--script script.py]
                           [--notebook notebook.ipynb] [--workspace FOLDER]
                           [--lang fr|en] [-q]
```

| Option | Effect |
|---|---|
| `workflow.json` | the workflow to run (saved or exported from the interface) |
| `--rapport FILE` | generates the [HTML report](reports.md), with the settings saved in the workflow |
| `--script FILE` | exports the equivalent Python script |
| `--notebook FILE` | exports the Jupyter notebook |
| `--workspace FOLDER` | workspace: data for CSV readers, cache, custom blocks |
| `--lang en` | report in English |
| `-q`, `--quiet` | only show errors |

All nodes run in graph order. A failing node is reported, and the nodes depending on it are
skipped; other branches carry on:

```text
Workflow « Classification des iris » : 14 nœuds, espace de travail /home/me/kataml
  ✓ [ 1] Introduction  (cache)
  ✓ [ 2] Iris  (0.01 s)
  ✓ [ 5] 75 % / 25 %  (0.03 s)
  ✓ [ 7] Forêt aléatoire  (0.56 s)
  ✓ [11] CV 5 plis  (3.23 s)
  …
Terminé en 5.1 s
Rapport : report.html
```

(The console messages are in French.) The **exit code** is 0 if everything succeeded, 1
otherwise: the command fits into a script, a `Makefile` or a continuous integration job.

The disk cache is shared with the interface: nodes already computed (same parameters, same
data) are not recomputed.

## Usage examples

=== "Weekly report"

    A workflow reads `sales.csv` (in `workspace/data`); a scheduled task replaces the file
    then regenerates the report:

    ```bash
    kataml run sales.json --rapport "reports/sales-$(date +%F).html" --lang en -q
    ```

=== "Grading labs"

    Run every submitted workflow and produce a report for each:

    ```bash
    for f in submissions/*.json; do
      kataml run "$f" --rapport "${f%.json}.html" --lang en -q || echo "Failed: $f"
    done
    ```

=== "Moving to code"

    ```bash
    kataml run study.json --script study.py --notebook study.ipynb
    python study.py
    ```

## Environment variables

| Variable | Effect |
|---|---|
| `KATAML_WORKSPACE` | default workspace |
| `KATAML_CACHE_MB` | maximum disk cache size, in MB (1024 by default) |
| `KATAML_NO_EXTENSIONS=1` | load no installed extension (diagnostics) |
