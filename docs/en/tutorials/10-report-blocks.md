# 10. Report, export and custom block

!!! abstract "Objectives"
    - Produce an annotated HTML report from a workflow.
    - Export the workflow to a Python script or a Jupyter notebook.
    - Write a node in Python.

    Prerequisites: [tutorial 1](01-first-workflow.md). Time: 40 min.

This tutorial uses the **Open › Examples › Iris classification** example.

## Part A: the report

### Step 1: comment with text blocks

The example contains two **Report text** nodes (category **Report**), titled
“Introduction” and “Conclusion”. Having no ports, they compute nothing: they carry a section
title and a Markdown text (`##` headings, lists, bold, italics, links). Add a third one,
“Method”, that justifies the use of the Pipeline:

```markdown
## Method

Scaling and the random forest are combined in a **Pipeline**,
evaluated by 5-fold cross-validation on the training data.
```

### Step 2: generate the report

Click **Report** (++ctrl+p++).

![Report dialog](../../assets/screenshots/en/dialog-report.png){ .shot }

The dialog asks for a title and, optionally, an author. Four options control the workflow
diagram, annotations, table previews for nodes without a view, and the Python script
appendix. The **Content and order of sections** list offers each node as a section: tick
those to include and order them with the ↑ ↓ arrows, placing “Method” after
“Introduction”.

**Generate report** runs the nodes that have not run yet, then saves a file to
`workspace/reports`.

![Report](../../assets/screenshots/en/report-page.png){ .shot }

The report is a standalone HTML file. It opens offline in any browser, its charts stay
interactive on hover, and it prints cleanly to PDF (++ctrl+p++ in the browser). The choices
made in the dialog are saved with the workflow. See [Reports](../reports.md).

## Part B: moving to code

**Export** shows the workflow's Python code, with syntax highlighting. The **Copy** button
and the **Script `….py`** button give a script that redoes the workflow with pandas and
scikit-learn only, in execution order, one section per node. The **Notebook `….ipynb`**
button produces a notebook with one cell per node, preceded by its title; canvas annotations
become text cells. The workflow's `.json` file is exported from **Open**.

![Export dialog](../../assets/screenshots/en/dialog-export.png){ .shot }

The script uses the scikit-learn objects behind the nodes (`Pipeline`, `cross_validate`,
`DecisionBoundaryDisplay`…). An analysis can thus be built in the interface, then continued
in Python.

The command line runs a workflow without the interface and produces the same files:

```bash
kataml run iris.json --rapport report.html --script iris.py --notebook iris.ipynb --lang en
```

See [Command line](../cli.md).

## Part C: writing a node

This part creates a “Clipping” node that brings the extreme values of numeric columns back
to chosen quantiles (*winsorisation*), an operation missing from the catalogue.

### Step 1: create the block

1. At the top of the repository, click **My blocks**, then **New block**.
2. Fill in **Name** `Clipping`, **Description** “Limits values to the chosen quantiles”,
   **Inputs** *One table*, then click **Create**.

![My blocks](../../assets/screenshots/en/blocks-new.png){ .shot }

A commented Python file opens in the built-in editor.

### Step 2: write the code

Keep the file header (docstring, `import`, `KATAML_EXTENSION`) and replace the
`@register(…)` decorator and the `run` function by:

```python
@register(
    "ext.clipping",
    "Clipping",
    "Mes blocs",
    "Limits the values of numeric columns to the chosen quantiles (winsorisation).",
    inputs=[("Table", DATA)],
    outputs=[("Table", DATA)],
    params=[
        P("columns", "Columns (empty = all numeric)", "columns", [], port=0),
        P("low", "Low quantile", "float", 0.01),
        P("high", "High quantile", "float", 0.99),
    ],
)
def clipping(ctx, p):
    df = ctx.data(0).copy()
    cols = p["columns"] or list(df.select_dtypes("number").columns)
    check_columns(df, cols)
    if not 0 <= p["low"] < p["high"] <= 1:
        raise NodeError("Need 0 ≤ low quantile < high quantile ≤ 1.")
    for c in cols:
        df[c] = df[c].clip(df[c].quantile(p["low"]), df[c].quantile(p["high"]))
    return [df]
```

Click **Save and reload** (++ctrl+s++). The message “Saved and reloaded: 1 node(s).” confirms
loading; a syntax error would be shown under the editor.

![Block editor](../../assets/screenshots/en/blocks-editor.png){ .shot }

### Step 3: use the block

The **Clipping** node appears in the repository, in the **My blocks** category. Placed
between a CSV reader and a Statistics node, it behaves like a built-in node: configuration
form, state light, cache, output table. The `columns` parameter type automatically offers the
input table's columns; choose them so as not to clip the target.

!!! tip "From a Python script"
    A **Python script** node is turned into a block with right-click › **Convert into a
    reusable block**.

Views, model inputs, Python export and distribution as packages are described in
[Custom blocks](../blocks.md).

## Your turn

- [ ] Add a view to the block showing how many values were clipped: declare
  `has_view=True` in `register`, then call
  `ctx.add_view({"type": "metrics", "items": [{"label": "Clipped values", "value": n}]})`.
- [ ] Generate the report of [tutorial 3](03-csv-cleaning.md) with the Python script
  appendix, and print it to PDF.
- [ ] Export a workflow to a notebook and run it in Jupyter
  (`uvx --with scikit-learn --with pandas jupyter lab`).
