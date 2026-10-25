---
name: kataml-extension
description: Write a KataML extension (custom block/node) in Python. Use when the user wants to add a new node to KataML, create or edit a block, package blocks for distribution, or asks how KataML's register/ctx/P API, views and Python export work. Covers the public API, parameter and view/chart shapes, testing with the engine, and both delivery paths (workspace file, pip package).
---

# Writing a KataML extension

A KataML extension adds one or more **nodes** (blocks) to the visual workbench. A node is a
Python function decorated with `register`. It receives the node's inputs and parameters and
returns its outputs. The repository placement, configuration form, status light, result
cache, table display and report integration all come for free.

Work from the real examples in this repository: `kataml/contrib/eda.py` (six analysis
blocks, with views and Python export) and `extensions/kataml-exemple/` (a distributable
package). Mirror their style.

## The two ways a user ships an extension

- **A `.py` file in `workspace/extensions/`** — loaded automatically at startup, editable in
  the app under **My blocks**. Best for one project or personal use. A single file may hold
  several `@register` nodes.
- **A pip-installed package** with an entry point — for distributing to others (see the end
  of this file).

(First-party extensions bundled with the app live in `kataml/contrib/` and are toggled by a
checkbox; users writing their own use the two paths above.)

## Minimal node

```python
from kataml.extension import DATA, NodeError, P, check_columns, register

# Optional metadata shown in "My blocks".
KATAML_EXTENSION = {"name": "mes_blocs", "version": "1.0", "description": "..."}

@register(
    "ext.mes_blocs.log",          # unique id; always prefix with ext.<namespace>.
    "Logarithme",                 # display name
    "Manipulation",               # repository category (existing label or a new one)
    "Ajoute log(1 + x) aux colonnes choisies.",   # description (one or two sentences)
    inputs=[("Table", DATA)],     # input ports: DATA (a table) or MODEL (a fitted model)
    outputs=[("Table", DATA)],    # output ports
    params=[
        P("columns", "Colonnes", "columns", [], port=0, required=True),
        P("suffix", "Suffixe", "str", "_log"),
    ],
)
def log1p(ctx, p):
    import numpy as np
    df = ctx.data(0).copy()                 # never mutate the input: copy first
    check_columns(df, p["columns"])          # raises a clear error if a column is missing
    for c in p["columns"]:
        df[c + p["suffix"]] = np.log1p(df[c])
    return [df]                              # one value per output port, in order
```

The function returns a **list** with one entry per output port: a `pandas.DataFrame` for a
`DATA` port. Order matches `outputs`.

## Public API (`from kataml.extension import ...`)

- `register`, `DATA`, `MODEL`, `P`, `NodeError`
- helpers: `check_columns(df, cols)`, `ensure_numeric(df, cols)`, `resolve_features(df, feats, exclude=())`,
  `table_block(df, title=None)`, `py(value)` (Python-literal repr for the code export),
  `parse_literal(text)`
- types: `Ctx`, `ModelPort`
- category constants: `CAT_IO`, `CAT_MANIP`, `CAT_VIEW`, `CAT_SCORE`, `CAT_TUNE`, `CAT_APPLY`,
  `CAT_COMPOSE`, `CAT_EXPLAIN`, `CAT_EXTENSIONS`. You may also pass a plain string category
  (a new label creates a new repository group).

`register(type_, name, category, description, *, inputs=(), outputs=(), params=(), code=None,
has_view=False, color="ext", keywords="", doc_url=None, optional_inputs=())`.

- `has_view=True` when the node calls `ctx.add_view(...)`.
- `optional_inputs=[1]` marks input port 1 as optional (the node runs without it).
- `keywords` improves repository search.

## Parameters — `P(name, label, type, default=None, help="", **kw)`

| `type` | Control | Useful kwargs |
|---|---|---|
| `"str"`, `"int"`, `"float"` | text field | `allow_empty=True`, `min=`, `max=` |
| `"bool"` | switch | |
| `"choice"` | dropdown | `choices=[...]`, `choice_labels={value: label}` |
| `"multichoice"` | checkboxes | `choices=[...]` |
| `"column"` / `"columns"` | pick one / several columns of an input table | `port=0` (which input the columns come from) |
| `"code"` | multi-line text area | `rows=8` |
| `"literal"` | a Python value (`[1, 2]`, `None`, `'text'`) | |
| `"file"` | a file name from `workspace/data` (with an import button) | |

`required=True` keeps the node red until the parameter is set. Read values with
`p.get("name")` or `p["name"]`; `columns`/`multichoice` default to a list, scalars to their
default.

## Context — `ctx`

- `ctx.data(i)` — input port `i` as a `DataFrame`.
- `ctx.model(i)` — input port `i` as a `ModelPort`: `.estimator` (the fitted scikit-learn
  object), `.features` (list of columns), `.target`, `.classes`, and `.kind`: one of
  `"classifier"`, `"regressor"`, `"cluster"`, `"transformer"`, `"embedding"`, `"outlier"`,
  `"covariance"`, `"density"`, `"neighbors"`. Check `.kind` before using the estimator.
- `ctx.add_view(block, ...)` — attach one or more view blocks (needs `has_view=True`).
- `ctx.messages.append("...")` — a note shown in the inspector.
- `raise NodeError("...")` — a clear, user-facing error on the node. Validate inputs and
  raise `NodeError` rather than letting raw exceptions through.

## Views (for `ctx.add_view`)

- **Metrics tiles**: `{"type": "metrics", "items": [{"label": "...", "value": 0.97}]}`
  (value may be a number or a short string).
- **Table**: `table_block(df, "Titre")`.
- **Charts**: `{"type": "chart", "chart": "<kind>", "title": "...", ...}`. Supported kinds and
  their fields:
  - `"hbar"` / `"bar"`: `"labels": [str], "values": [number]`
  - `"histogram"`: `"edges": [...], "series": [{"name": str, "counts": [int]}], "xlabel", "ylabel"`
  - `"scatter"`: `"x": [...], "y": [...], "xlabel", "ylabel"`, optional `"diagonal": True`, `"groups": [...]`
  - `"line"`: `"series": [{"name": str, "x": [...], "y": [...]}], "xlabel", "ylabel"`, optional `"domain": [0, 1]`
  - `"heatmap"`: `"labels": [str], "ylabels": [str], "matrix": [[...]], "xlabel", "ylabel", "annot": True`
  - `"groupedbar"`: `"labels": [str], "series": [{"name": str, "values": [...]}]`
  - `"box"`: `"boxes": [{"label": str, "lo": x, "q1": x, "median": x, "q3": x, "hi": x, "outliers": [...]}]`
  - any chart accepts an optional `"height"` in pixels.
- **Text**: `{"type": "text", "text": "...", "title": "...", "mono": True}` (`mono` for
  preformatted output) or `{"type": "markdown", "text": "...", "title": "..."}`.

All series/coordinate values must be JSON-plain (Python `int`/`float`/`str`); convert NumPy
scalars with `float(...)` / `int(...)` and arrays with `.tolist()`.

## Python export (optional but recommended)

`register(..., code=lambda p, ins, outs: "...")` returns the equivalent code for the "export
to script / notebook" feature. `ins` and `outs` are the variable names of the input and
output ports. The exported script already imports `pandas as pd`, `numpy as np`, and
`from sklearn import datasets, metrics`. Use `py(value)` to embed parameter values:

```python
code=lambda p, ins, outs: (
    f"{outs[0]} = {ins[0]}.copy()\n"
    f"for _c in {py(p.get('columns') or [])}:\n"
    f"    {outs[0]}[_c + {py(p.get('suffix', '_log'))}] = np.log1p({outs[0]}[_c])"),
```

Keep it a faithful, readable equivalent. If a node has no reasonable export, omit `code`.

## Testing a node

Import the module (that registers its nodes) and drive the engine on a temporary workspace.
A node runs only after its upstream nodes, so execute them in order.

```python
import tempfile
from pathlib import Path
from kataml.engine import Engine
import mes_blocs  # the module with your @register nodes

ws = Path(tempfile.mkdtemp()); (ws / "data").mkdir()
wf = {"nodes": [
    {"id": "d", "type": "io.dataset", "params": {"dataset": "iris"}, "x": 0, "y": 0, "label": ""},
    {"id": "n", "type": "ext.mes_blocs.log", "params": {"columns": ["petal length (cm)"]}, "x": 1, "y": 0, "label": ""},
], "edges": [{"from": "d", "fromPort": 0, "to": "n", "toPort": 0}]}
e = Engine(ws)
for node in wf["nodes"]:
    ok, err, _ = e.execute(wf, node["id"])
    assert ok, err
print(e.result("n").outputs[0].columns)
```

Also check the Python export runs: write `export_python(wf, "t")` (from `kataml.export`) to a
file and run it with the same Python.

## Rules that matter

- **Prefix ids** `ext.<namespace>.<node>`. An id cannot replace a built-in node, and it is
  stored inside saved workflows, so keep it stable.
- **Copy inputs** (`ctx.data(i).copy()`); never mutate a received table.
- **Be deterministic**: the cache assumes the same node, inputs and parameters give the same
  result. Expose any randomness as a seed parameter. (Editing a block's code invalidates its
  cached results automatically.)
- **Fail clearly** with `NodeError`; validate columns and numeric types up front
  (`check_columns`, `ensure_numeric`).
- **Missing values**: keep them missing. In particular, `astype(str)` turns `NaN` into the
  text `"nan"` under pandas 2; use `s.where(s.isna(), s.astype(str))` when you need text.
- **No NaN or infinity in views**: views are sent as strict JSON. Replace a non-finite
  metric with a string such as `"—"`; tables built with `table_block` are converted for you.
- **Labels are displayed as written**: KataML translates only its own nodes, so write
  names, labels and messages in your users' language.
- A block runs with the user's rights. Keep dependencies to `pandas`, `numpy` and
  `scikit-learn` unless the user asks otherwise.

## Distributing as a package

Lay out a package that declares the entry point KataML reads at startup:

```toml
# pyproject.toml
[project]
name = "mes-blocs"
version = "1.0.0"
dependencies = ["kataml"]

[project.entry-points."kataml.extensions"]
mes_blocs = "mes_blocs"          # the module imported at startup
```

Install it beside KataML (`pip install ./mes-blocs`, or
`uv tool install kataml --with ./mes-blocs`). Installed extensions appear in **My blocks**.
See `extensions/kataml-exemple/` for a complete, minimal template.
