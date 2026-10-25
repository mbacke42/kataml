"""Rapports HTML autonomes : schéma du workflow, sections par nœud, annexes.

Le fichier produit embarque les données des vues (JSON) et le moteur de rendu de
l'interface (ui.js, charts.js, blocks.js, report_view.js) : il s'ouvre hors ligne,
dans n'importe quel navigateur, et s'imprime en PDF.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

from . import __version__
from .engine import Engine, describe
from .nodes import REGISTRY, _jsonable

STATIC = Path(__file__).parent / "static"
NODE_W, NODE_H = 184, 64

FAMILY_COLORS = {
    "io": "#eb6834", "manip": "#d39200", "view": "#2a78d6", "learner": "#14966a", "regressor": "#008300",
    "cluster": "#4a3aa7", "transformer": "#0f8fa8", "apply": "#c2477a", "score": "#d64545", "tune": "#7a5bd6",
    "compose": "#256abf", "explain": "#b8860b", "report": "#52514e", "ext": "#8a6bbf",
}
STATE_COLORS = {"executed": "#0ca30c", "error": "#d03b3b", "idle": "#e39b00"}


def node_color(nt) -> str:
    if nt is None:
        return "#898781"
    if nt.type.startswith("io."):
        return FAMILY_COLORS["io"]
    if nt.type.startswith("manip."):
        return FAMILY_COLORS["manip"]
    if nt.type.startswith("sk.regressor."):
        return FAMILY_COLORS["regressor"]
    return FAMILY_COLORS.get(nt.color, "#898781")


def default_order(wf: dict) -> list[str]:
    """Ordre de lecture : ordre d'exécution, de gauche à droite."""
    nodes, incoming = Engine._index(wf)
    order, seen = [], set()

    def visit(nid, stack=()):
        if nid in seen or nid in stack:
            return
        for src, _ in incoming[nid].values():
            visit(src, stack + (nid,))
        seen.add(nid)
        order.append(nid)

    for nid in sorted(nodes, key=lambda i: (nodes[i].get("x", 0), nodes[i].get("y", 0))):
        visit(nid)
    return order


def included_by_default(node: dict) -> bool:
    nt = REGISTRY.get(node["type"])
    return bool(nt and (nt.has_view or node["type"] == "report.text"))


def node_name(nt, lang: str) -> str:
    from .i18n import NODES
    return NODES.get(nt.type, (nt.name,))[0] if lang == "en" else nt.name


def section_label(nt, lang: str) -> str:
    from . import taxonomy
    section, _ = taxonomy.classify(nt.type, nt.module, nt.kind)
    return taxonomy.label(taxonomy.SECTIONS, section, lang) if section else nt.category


def diagram_svg(wf: dict, states: dict, lang: str = "fr") -> str:
    nodes = [dict(n) for n in wf.get("nodes", []) if n.get("type") in REGISTRY]
    if not nodes:
        return ""
    # Workflows écrits à la main : positions par défaut, en ligne dans l'ordre d'exécution.
    rank = {nid: k for k, nid in enumerate(default_order(wf))}
    for n in nodes:
        n.setdefault("x", rank.get(n["id"], 0) * (NODE_W + 80))
        n.setdefault("y", 0)
    by_id = {n["id"]: n for n in nodes}
    notes = wf.get("annotations") or []
    xs = [n["x"] for n in nodes] + [a["x"] for a in notes]
    ys = [n["y"] for n in nodes] + [a["y"] for a in notes]
    x2 = [n["x"] + NODE_W for n in nodes] + [a["x"] + a.get("w", 280) for a in notes]
    y2 = [n["y"] + NODE_H for n in nodes] + [a["y"] + a.get("h", 100) for a in notes]
    pad = 24
    x0, y0, w, h = min(xs) - pad, min(ys) - pad, max(x2) - min(xs) + 2 * pad, max(y2) - min(ys) + 2 * pad
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {w} {h}" class="diagram" '
           f'role="img" aria-label="Schéma du workflow">']
    for a in notes:
        first, *rest = (a.get("text") or "").split("\n")
        out.append(f'<rect x="{a["x"]}" y="{a["y"]}" width="{a.get("w", 280)}" height="{a.get("h", 100)}" rx="10" '
                   f'fill="#fbf3d8" stroke="#eadfb8"/>')
        out.append(f'<text x="{a["x"] + 12}" y="{a["y"] + 22}" class="dn-t">{html.escape(first[:60])}</text>')
        for k, line in enumerate(rest[:3]):
            out.append(f'<text x="{a["x"] + 12}" y="{a["y"] + 40 + 16 * k}" class="dn-l">{html.escape(line[:70])}</text>')

    def port(n, kind, i):
        nt = REGISTRY[n["type"]]
        count = len(nt.inputs if kind == "in" else nt.outputs)
        return (n["x"] + (0 if kind == "in" else NODE_W), n["y"] + NODE_H * (i + 1) / (count + 1))

    for e in wf.get("edges", []):
        a, b = by_id.get(e["from"]), by_id.get(e["to"])
        if not a or not b:
            continue
        (ax, ay), (bx, by) = port(a, "out", e["fromPort"]), port(b, "in", e["toPort"])
        dx = max(40, abs(bx - ax) / 2)
        out_kind = REGISTRY[a["type"]].outputs[e["fromPort"]][1] if e["fromPort"] < len(REGISTRY[a["type"]].outputs) else "data"
        dash = ' stroke-dasharray="6 4"' if out_kind == "model" else ""
        out.append(f'<path d="M{ax},{ay} C{ax + dx},{ay} {bx - dx},{by} {bx},{by}" fill="none" '
                   f'stroke="{"#6d8fbf" if out_kind == "model" else "#a3a29b"}" stroke-width="2"{dash}/>')
    for n in nodes:
        nt = REGISTRY[n["type"]]
        color = node_color(nt)
        state = (states.get(n["id"]) or {}).get("state", "idle")
        x, y = n["x"], n["y"]
        label = n.get("label") or f"#{n['id'].lstrip('n')}"
        out.append(f'<g><rect x="{x}" y="{y}" width="{NODE_W}" height="{NODE_H}" rx="11" fill="#fff" stroke="#dcdbd4"/>'
                   f'<rect x="{x + 10}" y="{y + 10}" width="28" height="28" rx="7" fill="{color}"/>'
                   f'<text x="{x + 48}" y="{y + 24}" class="dn-n">{html.escape(node_name(nt, lang)[:24])}</text>'
                   f'<text x="{x + 48}" y="{y + 40}" class="dn-l">{html.escape(label[:26])}</text>'
                   f'<circle cx="{x + 54}" cy="{y + 52}" r="4" fill="{STATE_COLORS.get(state, "#c3c2b7")}"/></g>')
    out.append("</svg>")
    return "".join(out)


@lru_cache(maxsize=1)
def _bundle() -> str:
    """Concatène les modules du rendu en un script autonome (sans import/export)."""
    parts = ["const LANG = globalThis.KATAML_LANG || \"fr\";"]
    for name in ("ui.js", "i18n.js", "charts.js", "blocks.js", "report_view.js"):
        src = (STATIC / "js" / name).read_text(encoding="utf-8")
        src = re.sub(r"^import [^;]+;\s*$", "", src, flags=re.M)
        src = re.sub(r"^export (?=(async )?function|const|let|class)", "", src, flags=re.M)
        parts.append(f"// --- {name}\n{src}")
    return "(() => {\n" + "\n".join(parts) + "\nrenderReport();\n})();"


@lru_cache(maxsize=1)
def _styles() -> str:
    css = (STATIC / "css" / "app.css").read_text(encoding="utf-8")
    return css + REPORT_CSS


def _theme_css(workspace: Path, accent: str | None) -> str:
    """Personnalisation du rapport : theme.css de l'espace de travail, puis couleur choisie."""
    css = ""
    f = Path(workspace) / "theme.css"
    if f.is_file():
        css += f.read_text(encoding="utf-8", errors="replace").replace("</", "<\\/")
    if accent and re.fullmatch(r"#[0-9a-fA-F]{6}", accent):
        css += f"\n:root {{ --accent: {accent}; }}"
    return f"\n<style>{css}</style>" if css else ""


REPORT_CSS = """
/* --- Rapport --- */
html, body { height: auto; }
body { overflow: auto; background: #f4f4f2; }
.report { max-width: 980px; margin: 0 auto; padding: 40px 32px 60px; background: var(--panel); min-height: 100vh;
  box-shadow: 0 0 0 1px var(--line); }
.report header { border-bottom: 2px solid var(--text); padding-bottom: 18px; margin-bottom: 26px; }
.report h1 { font-size: 30px; letter-spacing: -.02em; margin: 0 0 6px; }
.report .subtitle { color: var(--text-2); font-size: 15px; }
.report .meta { display: flex; flex-wrap: wrap; gap: 6px 18px; margin-top: 12px; font-size: 12px; color: var(--muted); }
.report h2 { font-size: 19px; margin: 0 0 4px; letter-spacing: -.01em; }
.report .section { padding: 22px 0; border-top: 1px solid var(--line); break-inside: avoid-page; }
.report .section .sub { color: var(--muted); font-size: 12px; margin-bottom: 12px; }
.report .section .view { padding: 0; }
.report .toc { columns: 2; font-size: 13px; margin: 0 0 26px; padding-left: 20px; }
.report .toc a { color: var(--text-2); }
.report .diagram-box { border: 1px solid var(--line); border-radius: 12px; padding: 12px; margin-bottom: 26px; background: var(--canvas); }
.report .diagram { width: 100%; height: auto; max-height: 520px; }
.report .diagram text { font-family: var(--font); }
.report .dn-n { font-size: 12.5px; font-weight: 620; fill: #17171a; }
.report .dn-l { font-size: 11px; fill: #8a8990; }
.report .dn-t { font-size: 12.5px; font-weight: 650; fill: #17171a; }
.report .warn { padding: 10px 12px; border-radius: 8px; background: #fdecec; color: #8c2020; font-size: 13px; }
.report pre.code { white-space: pre-wrap; font: 11.5px/1.5 var(--mono); background: var(--panel-2); border: 1px solid var(--line);
  border-radius: 10px; padding: 14px; }
.report footer { margin-top: 40px; color: var(--muted); font-size: 12px; text-align: center; }
.report .notes { background: #fbf3d8; border-radius: 10px; padding: 12px 16px; margin-bottom: 18px; white-space: pre-wrap; }
.markdown h3, .markdown h4, .markdown h5 { margin: 14px 0 6px; }
.markdown p { margin: 0 0 10px; line-height: 1.6; }
.markdown blockquote { margin: 0 0 10px; padding: 4px 12px; border-left: 3px solid var(--line-strong); color: var(--text-2); }
.toolbar-print { position: fixed; top: 14px; right: 14px; }
@media print {
  body { background: #fff; }
  .report { box-shadow: none; max-width: none; padding: 0; }
  .toolbar-print, .chart-tip { display: none !important; }
  .report .section { break-inside: auto; }
  .vblock, .metrics, .chart { break-inside: avoid; }
  @page { margin: 16mm 14mm; }
}
"""


def build_report(engine: Engine, wf: dict, options: dict) -> str:
    """HTML autonome du rapport. ``options`` : title, author, order, diagram, code, tables, notes, lang."""
    from .export import export_python
    from .i18n import text as tr, translate_payload
    lang = options.get("lang") or "fr"
    nodes = {n["id"]: n for n in wf.get("nodes", [])}
    states = engine.status(wf)
    order = [i for i in (options.get("order") or default_order(wf)) if i in nodes]
    if not options.get("order"):
        order = [i for i in order if nodes[i].get("report", included_by_default(nodes[i]))]
    rows = int(options.get("table_rows", 10) or 0) if options.get("tables", True) else 0
    sections = []
    for nid in order:
        node = nodes[nid]
        nt = REGISTRY.get(node["type"])
        sec = {"id": nid, "type": node_name(nt, lang) if nt else node["type"],
               "category": section_label(nt, lang) if nt else "",
               "label": node.get("label") or "", "state": (states.get(nid) or {}).get("state", "idle"),
               "blocks": [], "message": None}
        if node["type"] == "report.text":
            p = node.get("params", {})
            sec.update(markdown=True, blocks=[{"type": "markdown", "title": None, "text": p.get("text") or ""}],
                       title=p.get("title") or "")
            sections.append(sec)
            continue
        if sec["state"] == "error":
            sec["message"] = states[nid].get("message")
        try:
            r = engine.result(nid)
            sec["blocks"] = r.view or []
            sec["seconds"] = round(r.seconds, 2)
            if rows:
                for k, o in enumerate(r.outputs):
                    if isinstance(o, pd.DataFrame) and not r.view:
                        head = o.head(rows)
                        sec["blocks"].append({"type": "table", "title": tr(f"{nt.outputs[k][0]} ({len(o)} lignes × {o.shape[1]} colonnes, aperçu)") if lang == "en" else f"{nt.outputs[k][0]} ({len(o)} lignes × {o.shape[1]} colonnes, aperçu)",
                                              "columns": [str(c) for c in head.columns],
                                              "rows": json.loads(head.to_json(orient="values", default_handler=str))})
                        break
            sec["outputs"] = [describe(o) for o in r.outputs]
        except Exception:
            if sec["state"] != "error":
                sec["message"] = ("Node not executed when the report was generated." if lang == "en"
                                  else "Nœud non exécuté au moment de la génération du rapport.")
        sections.append(sec)
    import sklearn
    payload = {
        "title": options.get("title") or wf.get("name") or "Rapport",
        "workflow": wf.get("name") or "",
        "author": options.get("author") or "",
        "date": dt.datetime.now().strftime("%d/%m/%Y %H:%M"),
        "versions": f"KataML {__version__} · scikit-learn {sklearn.__version__} · pandas {pd.__version__}",
        "lang": lang,
        "diagram": diagram_svg(wf, states, lang) if options.get("diagram", True) else "",
        "notes": [a.get("text", "") for a in sorted(wf.get("annotations") or [], key=lambda a: (a.get("y", 0), a.get("x", 0)))]
                 if options.get("notes", True) else [],
        "sections": sections,
        "code": export_python(wf, re.sub(r"[^\w-]+", "_", wf.get("name") or "workflow")) if options.get("code") else "",
    }
    payload = translate_payload(payload, lang)
    data = json.dumps(payload, default=_jsonable, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="{lang}" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(payload['title'])}</title>
<style>{_styles()}</style>{_theme_css(engine.workspace, options.get("accent"))}
</head>
<body>
<div id="report" class="report"></div>
<script type="application/json" id="report-data">{data}</script>
<script>globalThis.KATAML_LANG = {json.dumps(lang)};</script>
<script>{_bundle()}</script>
</body>
</html>
"""
