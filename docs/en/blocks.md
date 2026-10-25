# Writing your own blocks

A KataML block (node) is a Python function decorated with `register`. It receives the
node's inputs and parameters, and returns the list of its outputs. Everything else comes
automatically: place in the repository, configuration form, state light, cache, table
display, reports.

## Where extensions come from

At startup, KataML gathers blocks from three sources into the same repository:

| Source | For whom | Activation |
|---|---|---|
| **Files** `workspace/extensions/*.py` | prototyping, personal use | loaded automatically; created and edited in **My blocks** |
| **Bundled extensions** (shipped with the app) | ready-to-use first-party blocks | **checkbox** in **My blocks** (disabled by default) |
| **Python packages** (entry point `kataml.extensions`) | distributing to other users | installed with `pip`/`uv`, loaded automatically |

The three coexist. `KATAML_NO_EXTENSIONS=1` disables them all (diagnostics). A block runs
with the user's rights: only enable extensions you trust.

To write an extension **with an AI assistant**, a dedicated skill is provided in the
repository (`.claude/skills/kataml-extension/`): it gives the agent all the API and
conventions it needs.

## Creating a block

1. **From the interface**: **My blocks** button (at the top of the repository), then
   **New block**. A commented file is created in `workspace/extensions/` and opens in the
   built-in editor; **Save and reload** (Ctrl+S) updates it immediately. Errors (syntax,
   import…) are shown under the editor.
2. **From a Python script**: right-click a “Python script” node, then **Convert into a
   reusable block**. Its code becomes a repository block.
3. **As a Python package**, to distribute blocks to other users: see below.

Files in `workspace/extensions/` are also loaded by the portable builds (AppImage, Windows
zip) and by `kataml run`. [Tutorial 10](tutorials/10-report-blocks.md) walks through a
complete example.

## Anatomy of a block

```python
from kataml.extension import DATA, MODEL, NodeError, P, check_columns, register

KATAML_EXTENSION = {"name": "my_blocks", "version": "1.0", "description": "…"}

@register(
    "ext.my_blocks.log",            # unique identifier (ext. prefix recommended)
    "Logarithm",                    # displayed name
    "Data manipulation",            # repository category (existing or new)
    "Adds log(1 + x) for the chosen columns.",
    inputs=[("Table", DATA)],       # input ports: DATA (table) or MODEL (model)
    outputs=[("Table", DATA)],
    params=[
        P("columns", "Columns", "columns", [], port=0, required=True),
        P("suffix", "Suffix", "str", "_log"),
    ],
)
def log1p(ctx, p):
    import numpy as np
    df = ctx.data(0).copy()          # input #0 as a DataFrame
    check_columns(df, p["columns"])
    for c in p["columns"]:
        df[c + p["suffix"]] = np.log1p(df[c])
    return [df]                      # one value per output port
```

### Parameters (`P(name, label, type, default, help, …)`)

| Type | Control | Useful options |
|---|---|---|
| `str`, `int`, `float` | input field | `allow_empty=True` |
| `bool` | switch | |
| `choice` | drop-down list | `choices=[…]`, `choice_labels={…}` |
| `multichoice` | check boxes | `choices=[…]` |
| `column` / `columns` | column(s) of the input table | `port=0` (input index) |
| `code` | multi-line text area | `rows=8` |
| `literal` | Python value (`[1, 2]`, `None`, `'text'`) | |

`required=True` keeps the node red while the parameter is empty.

### Context (`ctx`)

- `ctx.data(i)`: table of input `i`; `ctx.model(i)`: model of input `i` (`m.estimator`,
  `m.features`, `m.target`, `m.kind`);
- `ctx.add_view(block, …)`: adds a view (with `has_view=True` in `register`). Available
  blocks: `{"type": "metrics", "items": [{"label", "value"}]}`,
  `{"type": "chart", "chart": "bar" | "hbar" | "line" | "scatter" | "histogram" | …}`,
  `table_block(df, "title")`, `{"type": "text", "text": "…"}`,
  `{"type": "markdown", "text": "…"}`;
- `ctx.messages.append("…")`: warning shown in the inspector;
- `raise NodeError("…")`: clear error shown on the node.

### Python export

`register(..., code=lambda p, ins, outs: "…")` provides the equivalent code for the script
or notebook export (`ins` / `outs`: variable names).

## Bundled extensions

Two first-party extensions are **shipped with KataML**, so they are present in the portable
builds too, with nothing to install: **Exploratory data analysis** (six blocks: overview,
missing values, frequencies, relationship with the target, distributions, outliers) and
**Example (preparation)** (winsorizing, frequency encoding). They are **disabled by default**:
enable them with a checkbox in **My blocks**, section “Bundled extensions”. The choice is
saved in `workspace/extensions.json`.

## Distributing blocks in a package

The repository's `extensions/kataml-exemple/` folder is a minimal template (two blocks) for
publishing your own blocks as a package. You only need to declare an entry point in
`pyproject.toml`:

```toml
[project.entry-points."kataml.extensions"]
my_blocks = "my_package"          # module imported when KataML starts
```

Installation alongside KataML:

```bash
uv tool install git+https://gitlab.com/fredbl/kataml.git --with ./my-package
```

or, in KataML's environment, `pip install ./my-package`. Installed extensions are listed
in **My blocks**. `KATAML_NO_EXTENSIONS=1` disables them all (diagnostics).

## Good practice

- Prefix identifiers (`ext.my_package.…`): an identifier cannot replace a built-in node,
  and it is stored in workflows.
- Do not modify the tables you receive: work on a copy (`.copy()`).
- Stay deterministic (random seeds as parameters): the cache assumes that the same node,
  with the same inputs and parameters, produces the same result. Changing a block's code
  automatically invalidates its cached results.
- A block runs with the user's rights: only install trusted extensions.
