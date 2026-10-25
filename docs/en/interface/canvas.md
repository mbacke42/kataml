# Canvas

The canvas holds the workflow: nodes linked by connections, annotations and, where used,
components (node groups).

## Anatomy of a node

![Node states](../../assets/screenshots/en/node-states.png){ .shot }

Each node shows:

- a coloured icon for its family (data, manipulation, model, evaluation…);
- its name (the node type) and, below, its annotation (a free name given in the inspector,
  or its number);
- a traffic light and an information line: size of the tables produced (`150 × 5`),
  “trained model”, duration, or the first configuration problem;
- its ports: inputs on the left, outputs on the right.

| Light | Meaning |
|---|---|
| 🔴 red | to configure: a required parameter or an input is missing (the message says which); or a run-time error (✕ badge, message in the inspector) |
| 🟠 orange | configured, ready to run |
| 🟢 green | executed: results are available |
| 🔵 blinking | running or queued |

On hover, a ▶ button runs the node (with what precedes it if needed).

## Ports and connections

A triangular port carries a table (a pandas DataFrame), a square port a model (a fitted
scikit-learn estimator, with its features and its target). Model connections are drawn as
blue dashed lines.

To connect, **drag from an output port to an input port** of the same type; incompatible
ports fade during the gesture. An input accepts only one connection: connecting a new one
replaces the old one. Dragging from an already connected input detaches the connection so
you can move it. Cycles are impossible.

A **single click on an output port** of an executed node shows that output in the bottom
panel. A connection is selected with a click and deleted with ++delete++.

Semi-transparent ports are **optional** (for example “Table 2” of the Python script, or
the base estimator of `BaggingClassifier`).

## Quick add

![Quick add](../../assets/screenshots/en/quick-add.png){ .shot }

Double-clicking the canvas background opens a floating search that offers every node;
++up++, ++down++ and ++enter++ are used to choose. A connection released in empty space
opens the same search, limited to nodes compatible with the starting port, and the new node
is connected automatically.

## Selecting, moving, editing

| Gesture | Effect |
|---|---|
| click on a node | select (shows configuration and outputs) |
| ++shift++ or ++ctrl++ + click | add to / remove from the selection |
| ++shift++ + drag the background | rectangle selection |
| drag a node | move (the whole selection; snaps to a 10 px grid, ++alt++ to disable) |
| drag the background, middle click, or ++space++ + drag | pan the canvas |
| wheel, pinch | zoom (towards the pointer) |
| double-click on a node | open its configuration |
| ++delete++ | delete the selection |
| ++ctrl+c++ / ++ctrl+v++ / ++ctrl+d++ | copy / paste / duplicate (internal connections are kept) |
| ++ctrl+a++ | select all |
| ++f++ | fit the whole workflow in view |

The zoom bar, at the bottom right, also offers −, +, 100 % and “fit”.

## Context menus

![Node context menu](../../assets/screenshots/en/context-menu.png){ .shot }

Right-click opens a menu that depends on the element clicked:

- on a node: run, run downstream, reset, configure, show the view or an output,
  download an output (CSV or joblib model), copy, duplicate, delete; with several nodes
  selected: group as component, create a Pipeline, arrange the selection; on a Python
  script: convert into a reusable block;
- on a connection: delete it;
- on an annotation: edit the text, change the colour, delete;
- on the background: add a node, an annotation, paste, select all, fit.

## Annotations

An annotation (**Annotation** button or ++a++ key) is a coloured note placed on the
canvas: lab instructions, explanation of a step… **Double-click** to edit the text (the
first line is shown in bold), drag the bottom-right corner to resize it. Annotations are
included in reports and in exported notebooks.

## Automatic layout

**Arrange** (++l++) lays out the graph in layers from left to right, each node one column
after its deepest predecessor, limiting crossings. Applied to a selection, it only arranges
that selection. A collapsed component counts as a single node. The operation can be undone
with ++ctrl+z++.

## Components

Several nodes can be grouped into a **component** (++ctrl+g++), collapsed into a single
node with ports, expanded on demand, and saved for reuse. See
[Components](../concepts/components.md).

## Creating a Pipeline from the selection

Select transformers (up to three) and **one** supervised model, then right-click ›
**Create a Pipeline**: KataML adds a Pipeline node connected to the raw table, the model
and the transformers in the right order, then **collapses** it with its steps into a single
node (double-click to expand it). An existing Pipeline is collapsed with right-click ›
**Collapse the Pipeline**. See [The Pipeline](../concepts/pipeline.md).

## Dropping a file

Drag a **CSV** file from your file manager onto the canvas: it is copied to
`workspace/data` and a *CSV reader* node is created. A **Parquet** or **Excel** file
creates a *Parquet / Excel reader* node. A workflow **.json** file is opened directly, and
one or more **.py** scripts are converted into a workflow (see
[Import a Python script](toolbar.md#import-a-python-script)).
