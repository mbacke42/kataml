"""Export d'un workflow en script Python ou en notebook Jupyter."""

from __future__ import annotations

import json

from .engine import Engine, WorkflowError
from .nodes import DATA, REGISTRY

HEADER_DOC = '''"""Workflow « {name} » exporté depuis KataML.

Script autonome : python {fname}
Dépendances : pandas, scikit-learn.
"""
'''

IMPORTS = '''import joblib
import numpy as np
import pandas as pd
from sklearn import datasets, metrics
from sklearn.base import clone, is_classifier
from sklearn.compose import ColumnTransformer
from sklearn.inspection import permutation_importance
from sklearn.model_selection import (
    GridSearchCV, GroupKFold, GroupShuffleSplit, KFold, LeaveOneGroupOut, LeaveOneOut,
    RandomizedSearchCV, RepeatedKFold, RepeatedStratifiedKFold, ShuffleSplit, StratifiedGroupKFold,
    StratifiedKFold, StratifiedShuffleSplit, TimeSeriesSplit,
    cross_validate, learning_curve, train_test_split, validation_curve,
)
from sklearn.pipeline import Pipeline, make_pipeline'''

HELPERS = '''

def colonnes(cols):
    """Étape de Pipeline qui ne garde que les colonnes indiquées."""
    return ColumnTransformer([("select", "passthrough", list(cols))], remainder="drop",
                             verbose_feature_names_out=False).set_output(transform="pandas")'''


def _sections(wf: dict):
    """Renvoie (imports, [(titre, code)]) dans l'ordre d'exécution."""
    nodes, incoming = Engine._index(wf)
    order, seen = [], set()

    def visit(nid, stack=()):
        if nid in seen:
            return
        if nid in stack:
            raise WorkflowError("Le workflow contient un cycle.")
        for src, _ in incoming[nid].values():
            visit(src, stack + (nid,))
        seen.add(nid)
        order.append(nid)

    # Ordre stable : de gauche à droite sur le canevas.
    for nid in sorted(nodes, key=lambda i: (nodes[i].get("x", 0), nodes[i].get("y", 0))):
        visit(nid)

    imports: dict[str, set[str]] = {}
    extra: list[str] = []
    var: dict[tuple[str, int], str] = {}
    sections = []
    for idx, nid in enumerate(order, 1):
        node = nodes[nid]
        nt = REGISTRY.get(node["type"])
        if nt is None:
            continue
        label = node.get("label") or nt.name
        title = f"[{idx}] {label}" + (f" ({nt.name})" if node.get("label") else "")
        outs = []
        for j, (_, kind) in enumerate(nt.outputs):
            v = f"{'df' if kind == DATA else 'model'}_{idx}" + (f"_{j + 1}" if len(nt.outputs) > 1 else "")
            var[(nid, j)] = v
            outs.append(v)
        ins = [var.get(incoming[nid][i]) if i in incoming[nid] else None for i in range(len(nt.inputs))]
        if any(v is None for i, v in enumerate(ins) if i not in nt.optional_inputs):
            sections.append((title, "# Entrée non connectée : nœud ignoré."))
            continue
        if getattr(nt, "sk_import", None):
            mod, cls = nt.sk_import
            imports.setdefault(mod, set()).add(cls)
        extra += [e for e in getattr(nt, "extra_imports", []) if e not in extra]
        params = Engine._params(nt, node.get("params", {}))
        try:
            code = nt.code(params, ins, outs) if nt.code else f"# (pas d'équivalent Python pour {nt.name})"
        except Exception as e:  # ne bloque pas l'export
            code = f"# Export impossible pour ce nœud : {e}"
        sections.append((title, code))
    lines = [IMPORTS] + [f"from {m} import {', '.join(sorted(c))}" for m, c in sorted(imports.items())] + extra
    return "\n".join(lines) + HELPERS, sections


def export_python(wf: dict, name: str = "workflow") -> str:
    head, sections = _sections(wf)
    body = "\n\n".join(f"# --- {t}\n{c}" for t, c in sections)
    return HEADER_DOC.format(name=name, fname=f"{name}.py") + "\n" + head + "\n\n\n" + body + "\n"


def _cell(kind: str, text: str) -> dict:
    lines = text.splitlines(keepends=True)
    cell = {"cell_type": kind, "metadata": {}, "source": lines}
    if kind == "code":
        cell.update(execution_count=None, outputs=[])
    return cell


def export_notebook(wf: dict, name: str = "workflow") -> str:
    """Notebook Jupyter (nbformat 4) : une cellule par nœud, annotations en Markdown."""
    head, sections = _sections(wf)
    notes = sorted(wf.get("annotations") or [], key=lambda a: (a.get("y", 0), a.get("x", 0)))
    intro = f"# {wf.get('name') or name}\n\nWorkflow exporté depuis KataML : une cellule par nœud, dans l'ordre d'exécution."
    cells = [_cell("markdown", intro)]
    for a in notes:
        first, *rest = (a.get("text") or "").split("\n")
        cells.append(_cell("markdown", f"**{first.strip()}**" + ("\n\n" + "\n".join(rest) if rest else "")))
    cells.append(_cell("code", head))
    for title, code in sections:
        cells.append(_cell("markdown", f"### {title}"))
        cells.append(_cell("code", code))
    nb = {"cells": cells, "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
    for i, c in enumerate(nb["cells"]):
        c["id"] = f"cell-{i}"
    return json.dumps(nb, ensure_ascii=False, indent=1)
