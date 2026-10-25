# Inspector

The inspector, on the right, shows the selected node: its state, its configuration and its
documentation.

<div class="grid" markdown>

![Configuration](../../assets/screenshots/en/inspector-config.png){ .shot }

![Description](../../assets/screenshots/en/inspector-description.png){ .shot }

</div>

## Header

- The node's name and category (chapter and family of the scikit-learn guide).
- The annotation field, for a free name (“final model”, “Forest 200 trees”…) shown under the node
  name on the canvas, also used in reports and by the model comparison.
- The state (badge), the duration of the last run, and the **Reset** (++f8++) and **Run** (++f7++)
  buttons.
- On error, the full message; on incomplete configuration, the list of what is missing;
  any scikit-learn warnings (convergence…).

## “Configuration” tab

Parameters are grouped:

- **Data**: target column, features, sample weights, columns to transform…
- **Parameters**: options specific to the node.
- **Cross-validation** (evaluation nodes): strategy, number of folds, groups…
- **Hyperparameters** (scikit-learn nodes): every parameter of the class constructor,
  read directly from scikit-learn.

Each change is **applied immediately** (no “OK” button) and puts the node and its
descendants back on hold. ++ctrl+z++ undoes.

### Field types

| Field | Use |
|---|---|
| column list (one) | pick a column of the input table; the pandas type is shown |
| check boxes (several columns) | filter, **All**, **None**, **Num.** (numeric columns); empty = the default shown (often “all other columns”) |
| choice list | values allowed by scikit-learn; the default value is marked |
| switch | boolean parameters |
| “literal” field | a Python value: `100`, `0.5`, `None`, `'auto'`, `[1, 2]`, `(1, 2)`; unrecognised text is taken as a string; suggestions are offered |
| code area | pandas expressions, parameter grids, Markdown, scripts |
| file | file imported into `workspace/data`, **Import** button, or absolute path |

!!! info "Unknown columns"
    To offer columns, the inspector needs to know the input table. If the upstream node
    has not been run yet, a **Load** button runs it; you can also type the names by hand.

### Hyperparameters

- Only **modified** hyperparameters are passed to scikit-learn; a blue edge marks them
  and **default** resets them one by one (a reset-all button resets every one).
- The expected type (taken from the scikit-learn docstring) is shown next to the name;
  the help unfolds with a click.
- Beyond eight hyperparameters, a **filter** field helps find them; technical parameters
  (`verbose`, `n_jobs`, `copy`…) are hidden until the **Advanced** switch is on.
- The **scikit-learn documentation** link opens the official page of the class.

## “Description” tab

Summary of the class (from scikit-learn), role of the node in KataML, input and output
ports (with their type and whether they are optional), and documentation of each
parameter. Clicking a node **in the repository** also shows this description, without
adding it to the workflow.

## Selected component

When a collapsed component is selected, the inspector shows its name (editable), its
overall state, the list of its nodes (a click expands the component and selects the node),
and the **Expand / Collapse**, **Run**, **Save as component** and **Ungroup** buttons.
