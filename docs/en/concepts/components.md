# Components (node groups)

A **component** groups several nodes into one unit: the canvas stays readable, and a
useful processing chain can be reused from one workflow to another.

## Grouping

Select at least two nodes, then ++ctrl+g++ (or right-click › **Group as component**) and
give it a name. The component appears **collapsed**: a single node, drawn as a stack to
remind you it contains several.

![Collapsed component](../../assets/screenshots/en/component-collapsed.png){ .shot }

## A component's ports

Its ports are computed automatically:

- inputs: the inputs of its nodes that are not fed from inside the group (connected to
  the outside, or free);
- outputs: the outputs of its nodes that are used outside, or not used at all.

Connections work as with an ordinary node; internally, they link the group's nodes.
Clicking an output of the component shows the output of the corresponding node.

## Expanding, collapsing, ungrouping

- A double-click on the component expands it: its nodes reappear in a dashed frame
  bearing its name. The frame is moved by its title; **Collapse** folds it back.
- **Ungroup** (right-click or inspector) removes the group and keeps the nodes.
- **Run** runs all its nodes; its light summarises their state (green if all are
  executed, red if one is failing or incomplete).

![Expanded component](../../assets/screenshots/en/component-expanded.png){ .shot }

A component's inspector lists its nodes: a click expands the component and selects the
node to configure it.

![Component inspector](../../assets/screenshots/en/component-inspector.png){ .shot }

## Collapsed Pipelines

A collapsed Pipeline is a special component: it groups the Pipeline node and its steps,
only shows the raw table as input and the Pipeline as output, and carries its steps as a
subtitle. See [The Pipeline](pipeline.md#collapsed-pipeline).

## Reusable components

Right-click › **Save as reusable component**: the group (its nodes, their settings and
their internal connections) is saved to `workspace/components`. It appears in the
repository, in the **My components** category: drag it or double-click it to insert it,
already collapsed, into any workflow. Right-click a component in the repository to delete
it.

!!! tip "Component ideas"
    A standard data preparation (imputation + encoding + scaling), a trio of models to
    compare, an evaluation battery (predictor + metrics + ROC + calibration)…
