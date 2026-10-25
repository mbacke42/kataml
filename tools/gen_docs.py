#!/usr/bin/env python3
"""Génère la référence des nœuds de la documentation à partir du catalogue de KataML.

Écrit docs/<langue>/reference/*.md (français et anglais) : une page par chapitre du
guide scikit-learn, une fiche par nœud (ports, paramètres, hyperparamètres, lien
vers la documentation officielle). À relancer après toute évolution des nœuds ;
la CI le fait avant chaque construction du site.

Usage : uv run --group docs python tools/gen_docs.py
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kataml import __version__, sk_catalog, taxonomy  # noqa: E402
from kataml.nodes import catalog  # noqa: E402

TXT = {
    "fr": {
        "title": "Référence des nœuds", "inputs": "Entrées", "outputs": "Sorties", "params": "Paramètres",
        "hyper": "Hyperparamètres", "none": "aucune", "name": "Nom", "label": "Libellé", "type": "Type",
        "default": "Défaut", "help": "Description", "doc": "Documentation scikit-learn", "module": "Module",
        "id": "Identifiant", "count": "nœuds", "table": "table", "model": "modèle", "optional": "optionnelle",
        "family_other": "Autres", "hp_note": "Hyperparamètres lus dans scikit-learn {v} (signature et docstring de la classe).",
        "intro": ("Cette référence est générée automatiquement à partir du catalogue de KataML {k} "
                  "(scikit-learn {v}) et décrit les nœuds de cette version. Ils sont "
                  "classés comme dans le dépôt de l'interface (vue « Guide »), selon les chapitres du "
                  "[guide utilisateur de scikit-learn](https://scikit-learn.org/stable/user_guide.html)."),
        "section": "Chapitre", "nodes": "Nœuds", "excluded": "Estimateurs scikit-learn non proposés comme nœuds",
        "excluded_intro": "Chaque estimateur de scikit-learn est disponible, sauf ceux-ci, pour la raison indiquée :", "values": "valeurs :",
        "estimator": "Estimateur", "reason": "Raison",
    },
    "en": {
        "title": "Node reference", "inputs": "Inputs", "outputs": "Outputs", "params": "Parameters",
        "hyper": "Hyperparameters", "none": "none", "name": "Name", "label": "Label", "type": "Type",
        "default": "Default", "help": "Description", "doc": "scikit-learn documentation", "module": "Module",
        "id": "Identifier", "count": "nodes", "table": "table", "model": "model", "optional": "optional",
        "family_other": "Other", "hp_note": "Hyperparameters read from scikit-learn {v} (class signature and docstring).",
        "intro": ("This reference is generated automatically from the catalogue of KataML {k} "
                  "(scikit-learn {v}) and describes the nodes of this version. They are organised "
                  "as in the interface repository (“Guide” view), following the chapters of the "
                  "[scikit-learn user guide](https://scikit-learn.org/stable/user_guide.html)."),
        "section": "Chapter", "nodes": "Nodes", "excluded": "scikit-learn estimators not offered as nodes",
        "excluded_intro": "Every scikit-learn estimator is available except these, for the stated reason:", "values": "values:",
        "estimator": "Estimator", "reason": "Reason",
    },
}

EXCLUDED_EN = {
    "nœud dédié « Pipeline »": "dedicated “Pipeline” node",
    "nœud dédié « Recherche d'hyperparamètres »": "dedicated “GridSearchCV / RandomizedSearchCV” node",
    "utilisé par chaque transformeur (colonnes choisies) et par le Pipeline": "used by every transformer (chosen columns) and by the Pipeline",
    "remplacé par l'enchaînement de transformeurs dans un Pipeline": "replaced by chaining transformers in a Pipeline",
    "n'agit que sur la cible ; les classifieurs acceptent des étiquettes texte": "acts on the target only; classifiers accept text labels",
    "n'agit que sur la cible": "acts on the target only", "n'agit que sur la cible (multi-étiquette)": "acts on the target only (multi-label)",
    "attend une fonction Python : utiliser le nœud Script Python ou un bloc personnalisé": "expects a Python function: use the Python script node or a custom block",
    "agit sur une matrice de noyau, pas sur une table": "acts on a kernel matrix, not a table",
    "extraction d'imagettes (images)": "patch extraction (images)", "entrée sous forme de dictionnaires": "dictionary input",
    "entrée sous forme de dictionnaires ou de listes de chaînes": "dictionary or string-list input",
    "exige un dictionnaire d'atomes fourni en paramètre": "requires a dictionary of atoms as a parameter",
    "utilitaire interne (estimateur figé)": "internal utility (frozen estimator)",
    "biclustering d'une matrice (lignes et colonnes)": "biclustering of a matrix (rows and columns)",
    "nœud dédié « TfidfVectorizer » (catégorie Extraction de caractéristiques)": "dedicated “TfidfVectorizer” node (Feature extraction)",
    "nœud dédié « CountVectorizer »": "dedicated “CountVectorizer” node", "nœud dédié « HashingVectorizer »": "dedicated “HashingVectorizer” node",
}


def slug(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def cell(v) -> str:
    s = "" if v is None else str(v)
    return s.replace("|", "\\|").replace("\n", " ").strip()


def node_card(sp: dict, t: dict) -> str:
    lines = [f"### {sp['name']} {{ #{slug(sp['type'])} }}", ""]
    meta = [f"**{t['id']}** : `{sp['type']}`", f"**{t['module']}** : `{sp['module']}`"]
    if sp.get("doc_url"):
        meta.append(f"[{t['doc']} ↗]({sp['doc_url']})")
    lines += [" · ".join(meta), ""]
    for para in (sp.get("description") or "").split("\n\n"):
        if para.strip():
            lines += [cell(para), ""]

    def ports(items, optional=()):
        if not items:
            return t["none"]
        return ", ".join(f"{p['name']} ({t['table'] if p['kind'] == 'data' else t['model']}"
                         + (f", {t['optional']}" if i in optional else "") + ")" for i, p in enumerate(items))
    lines += [f"- **{t['inputs']}** : {ports(sp['inputs'], sp.get('optional_inputs') or [])}",
              f"- **{t['outputs']}** : {ports(sp['outputs'])}", ""]
    params = [p for p in sp["params"] if p.get("group") != "Hyperparamètres"]
    hps = [p for p in sp["params"] if p.get("group") == "Hyperparamètres"]
    if params:
        lines += [f"| {t['label']} | {t['name']} | {t['type']} | {t['default']} | {t['help']} |", "|---|---|---|---|---|"]
        for p in params:
            default = p.get("default")
            if p.get("choice_labels") and isinstance(default, str) and default in p["choice_labels"]:
                default = p["choice_labels"][default]
            choices = ""
            if p.get("choices") and p["type"] in ("choice", "multichoice") and len(p["choices"]) <= 14:
                choices = " (" + t["values"] + " " + ", ".join(f"`{c}`" for c in p["choices"] if c != "") + ")"
            lines.append(f"| {cell(p['label'])} | `{p['name']}` | {p['type']} | {cell(default)} | {cell(p.get('help'))}{cell(choices)} |")
        lines.append("")
    if hps:
        lines += [f"??? note \"{t['hyper']} ({len(hps)})\"", ""]
        lines += [f"    | {t['name']} | {t['type']} | {t['default']} | {t['help']} |", "    |---|---|---|---|"]
        for p in hps:
            lines.append(f"    | `{p['name']}` | {cell(p.get('typeinfo')) or p['type']} | `{cell(p.get('default_repr'))}` | {cell(p.get('help'))[:400]} |")
        lines += ["", f"    {t['hp_note'].format(v=sk_catalog.sklearn_version())}", ""]
    return "\n".join(lines)


def generate(lang: str):
    t = TXT[lang]
    out = ROOT / "docs" / lang / "reference"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.md"):
        old.unlink()
    specs = [s for s in catalog(lang) if not s.get("extension")]
    by_section = defaultdict(list)
    for sp in specs:
        by_section[sp["section"]].append(sp)
    index = [f"# {t['title']}", "", t["intro"].format(k=__version__, v=sk_catalog.sklearn_version()), "",
             f"| {t['section']} | {t['nodes']} |", "|---|---|"]
    for key in taxonomy.SECTIONS:
        items = by_section.get(key)
        if not items:
            continue
        title = taxonomy.label(taxonomy.SECTIONS, key, lang)
        fname = f"{key.replace('_', '-')}.md"
        index.append(f"| [{title}]({fname}) | {len(items)} |")
        families = defaultdict(list)
        for sp in items:
            families[sp.get("family") or ""].append(sp)
        page = [f"# {title}", "", f"{len(items)} {t['count']}.", ""]
        order = sorted(families, key=lambda f: (f == "", f))
        for fam in order:
            if fam:
                page += [f"## {fam}", ""]
            elif len(order) > 1:
                page += [f"## {t['family_other']}", ""]
            for sp in sorted(families[fam], key=lambda s: s["name"].lower()):
                page += [node_card(sp, t), "---", ""]
        (out / fname).write_text("\n".join(page), encoding="utf-8")
    index += ["", f"## {t['excluded']} {{ #excluded }}", "", t["excluded_intro"], "", f"| {t['estimator']} | {t['reason']} |", "|---|---|"]
    for name, reason in sorted(sk_catalog.NOT_AS_NODES.items()):
        index.append(f"| `{name}` | {EXCLUDED_EN.get(reason, reason) if lang == 'en' else reason} |")
    (out / "index.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    print(f"docs/{lang}/reference : {len(specs)} nœuds")


if __name__ == "__main__":
    for lang in ("fr", "en"):
        generate(lang)
