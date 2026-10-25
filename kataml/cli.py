"""Exécution d'un workflow en ligne de commande : ``kataml run workflow.json``."""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path


def run_workflow(path: Path, workspace: Path, report: Path | None = None, script: Path | None = None,
                 notebook: Path | None = None, quiet: bool = False, lang: str = "fr") -> int:
    from .engine import Engine
    from .export import export_notebook, export_python
    from .extension import load_extensions
    from .nodes import REGISTRY
    from .report import build_report, default_order

    wf = json.loads(Path(path).read_text(encoding="utf-8"))
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "data").mkdir(exist_ok=True)
    load_extensions(workspace)
    say = (lambda *a: None) if quiet else (lambda *a: print(*a, flush=True))
    name = wf.get("name") or Path(path).stem
    say(f"Workflow « {name} » : {len(wf.get('nodes', []))} nœuds, espace de travail {workspace}")
    unknown = [n["type"] for n in wf.get("nodes", []) if n["type"] not in REGISTRY]
    if unknown:
        say(f"Types de nœuds inconnus (extension manquante ?) : {', '.join(sorted(set(unknown)))}")
    engine = Engine(workspace)
    failed, broken = 0, set()
    parents = {n["id"]: {e["from"] for e in wf.get("edges", []) if e["to"] == n["id"]} for n in wf.get("nodes", [])}
    t0 = time.perf_counter()
    for i, nid in enumerate(default_order(wf), 1):
        node = next(n for n in wf["nodes"] if n["id"] == nid)
        nt = REGISTRY.get(node["type"])
        label = node.get("label") or (nt.name if nt else node["type"])
        if parents[nid] & broken:
            broken.add(nid)
            say(f"  – [{i:>2}] {label} : ignoré (un nœud amont a échoué)")
            continue
        ok, err, changed = engine.execute(wf, nid)
        if ok:
            secs = changed.get(nid, {}).get("seconds")
            say(f"  ✓ [{i:>2}] {label}" + (f"  ({secs:.2f} s)" if secs else "  (cache)"))
        else:
            failed += 1
            broken.add(nid)
            print(f"  ✗ [{i:>2}] {label} : {err}", flush=True)
    say(f"{'Terminé' if not failed else f'{failed} nœud(s) en échec'} en {time.perf_counter() - t0:.1f} s")
    slug = re.sub(r"[^\w-]+", "_", name)
    if report:
        opts = {**(wf.get("report") or {}), "lang": lang}
        Path(report).write_text(build_report(engine, wf, opts), encoding="utf-8")
        say(f"Rapport : {report}")
    if script:
        Path(script).write_text(export_python(wf, slug), encoding="utf-8")
        say(f"Script Python : {script}")
    if notebook:
        Path(notebook).write_text(export_notebook(wf, slug), encoding="utf-8")
        say(f"Notebook : {notebook}")
    return 1 if failed else 0


def main(args) -> None:
    from .server import default_workspace
    code = run_workflow(args.workflow, (args.workspace or default_workspace()).expanduser().resolve(),
                        args.rapport, args.script, args.notebook, args.quiet, getattr(args, "lang", "fr"))
    sys.exit(code)
