# Interface tour

KataML's interface opens in the browser. It is organised in five areas.

![The five areas of the interface](../../assets/screenshots/en/interface-overview.png){ .shot }

| Area | Role | Detailed page |
|---|---|---|
| **Toolbar** (top) | workflow name, files, undo, export, report, execution | [Toolbar](toolbar.md) |
| **Node repository** (left) | every available node, organised along the scikit-learn user guide, with search | [Node repository](repository.md) |
| **Canvas** (centre) | the workflow: nodes, connections, annotations, components | [Canvas](canvas.md) |
| **Inspector** (right) | configuration and documentation of the selected node | [Inspector](inspector.md) |
| **Output panel** (bottom) | tables, models and views of the selected node | [Outputs](outputs.md) |

The splitters between areas can be dragged with the mouse: widen the inspector to read
the hyperparameter help, or enlarge the output panel for charts. The chosen sizes are
remembered.

## The work cycle

1. **Add** nodes from the repository (drag and drop or double-click).
2. **Connect** an output to an input: triangular ports carry tables, square ports carry
   models.
3. **Configure** each node in the inspector: its light turns from red to orange.
4. **Run** (++f7++ or **Run all**): the light turns green.
5. **Inspect** the results in the output panel, by clicking a node or one of its outputs.

Any configuration change puts the affected node and those depending on it back on hold;
the others keep their results (see [Execution and cache](../concepts/execution.md)).

## Language and appearance

At the top right: **?** opens the help (++f1++), **EN / FR** switches language (the
interface reloads), the palette opens the [Appearance](appearance.md) dialog (mode, main
colour, canvas background), the moon / sun icon switches between light and dark, and **⏻**
stops KataML.
