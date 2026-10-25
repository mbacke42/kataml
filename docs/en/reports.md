# Reports

A report presents a workflow and its results as a readable document: to hand in a lab, to
document a study, to share an analysis with someone who does not have KataML.

## Generating a report

**Report** button in the toolbar, or ++ctrl+p++.

![Report dialog](../assets/screenshots/en/dialog-report.png){ .shot }

| Setting | Effect |
|---|---|
| **Title**, **Author** | report header (default title: the workflow name) |
| **Workflow diagram** | drawing of the graph, nodes coloured by state |
| **Annotations** | the canvas notes, as boxes |
| **Table previews** | for nodes without a view (manipulations), the first 10 rows of the table produced |
| **Python script appendix** | the exported code, at the end of the report |
| **Content and order of sections** | the nodes to include (check boxes) and their order (↑ ↓) |

By default, nodes producing a **view** (evaluations, charts, inspection…) and **Report
text** blocks are ticked, in execution order.

**Generate report** first runs the ticked nodes that have not run yet, then saves the file
to `workspace/reports`. A window offers to **open** it in a new tab or to **download** it.
The five latest reports are listed at the bottom of the dialog.

Settings are saved **with the workflow**: the next generation, from the interface or the
[command line](cli.md), reuses the same selection.

## Report content

![Report](../assets/screenshots/en/report-page.png){ .shot }

1. **Header**: title, author, date, versions of KataML, scikit-learn and pandas (useful
   for reproducibility).
2. Clickable **table of contents**.
3. **Workflow diagram** and **annotations**.
4. One **section per node**: name (annotation) and type, then its full view: indicators,
   interactive charts, tables. A failing node shows its message.
5. **Appendix**: the equivalent Python script (if requested).

## Commenting: “Report text” blocks

The **Report text** node (category **Report**) has no input or output. It carries a
section title and a Markdown text:

```markdown
## Goal

Predict the species of an iris from **four measurements**.

- 150 flowers, 50 per species;
- evaluation by 5-fold cross-validation.

Source: [scikit-learn](https://scikit-learn.org/stable/datasets/toy_dataset.html#iris-dataset).
```

Supported: headings (`#` to `####`), paragraphs, bulleted and numbered lists, **bold**,
*italics*, `code`, links and quotes. Place these blocks in the section order to introduce,
explain and conclude.

## A standalone file

The report is a single HTML file that contains everything it needs: chart data, styles and
display code. It opens offline in any browser, without KataML; its charts keep showing
values on hover; it prints cleanly to PDF (++ctrl+p++ in the browser, with a print-friendly
layout); and it can be e-mailed or uploaded to a learning platform like any other file.

!!! tip "Language"
    The report is written in the interface language. On the command line: `--lang en`.
