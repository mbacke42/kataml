# Execution, cache and cancellation

## Running

| Scope | Command | Effect |
|---|---|---|
| one node | ++f7++, the ▶ button on hover, or **Run** in the inspector | runs the node, after those it depends on if they have not run yet |
| the whole workflow | **Run all** (++shift+f7++) | runs every configured node; incomplete nodes (red light) and their descendants are skipped, with a message |
| a node and what follows | right-click › *Run downstream* | runs the node and everything that depends on it |

During execution, queued and running nodes blink, and an animated line travels along the
connections leading to the running node. An error stops the nodes that depend on the failing
node; other branches carry on.

## The cache

Each node has a signature, computed from its type, its parameters, the signatures of its
inputs and, for a *CSV reader*, the file modification date. As long as the signature does
not change, the result is reused. Changing a parameter therefore only puts that node and its
descendants back on hold, and undoing the change (++ctrl+z++) instantly recovers the previous
result.

Results are also saved to disk, in `workspace/.cache`: after restarting KataML, nodes already
computed stay green. This cache is limited to 1 GB (`KATAML_CACHE_MB` variable) and the
oldest results are removed beyond that. **Reset** in the toolbar empties it completely;
**Reset** in the inspector, or ++f8++, clears the results of a node and its descendants.

!!! note "Reproducibility"
    The cache assumes that a node gives the same result for the same inputs. Setting the
    `random_state` parameters (random seed) makes results reproducible, and model
    comparisons fair.

## Interrupting a computation

Computations run in a process separate from the server. The interface therefore stays
responsive during training, and tables or views can be consulted. The **Stop** button
interrupts the computation even in the middle of a `fit` lasting several minutes: the process
is stopped then restarted, and results already obtained are read back from the disk cache.

## Warnings and errors

scikit-learn warnings (convergence not reached, deprecated parameter…) are shown in the
inspector without blocking execution. Error messages name the cause and a possible fix:
column not found (with the list of available columns), non-numeric features, missing values
(with the nodes that can handle them), invalid parameter…
