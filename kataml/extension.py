"""Système d'extensions de KataML.

Une extension ajoute des nœuds. Deux façons de la fournir :

* un fichier ``.py`` déposé dans ``<espace de travail>/extensions/`` ;
* un paquet Python installé qui déclare un point d'entrée dans le groupe
  ``kataml.extensions`` (``[project.entry-points."kataml.extensions"]``).

Le module de l'extension importe l'API publique ci-dessous et déclare ses nœuds
avec ``register``. Il peut définir ``KATAML_EXTENSION = {"name": …, "version": …,
"description": …}``. Exemple minimal::

    from kataml.extension import DATA, P, register

    @register("ext.demo.doubler", "Doubler une colonne", inputs=[("Table", DATA)],
              outputs=[("Table", DATA)], params=[P("column", "Colonne", "column", "", port=0)])
    def doubler(ctx, p):
        df = ctx.data().copy()
        df[p["column"]] = df[p["column"]] * 2
        return [df]

Voir docs/EXTENSIONS.md pour le détail.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import os
import sys
import traceback
from importlib.metadata import entry_points
from pathlib import Path

from . import __version__
from .nodes import (  # noqa: F401  (API publique réexportée)
    CAT_APPLY, CAT_COMPOSE, CAT_EXPLAIN, CAT_IO, CAT_MANIP, CAT_SCORE, CAT_TUNE, CAT_VIEW,
    DATA, MODEL, REGISTRY, Ctx, ModelPort, NodeError, P, check_columns, ensure_numeric,
    parse_literal, py, resolve_features, table_block,
)
from .nodes import register as _register

CAT_EXTENSIONS = "Extensions"
GROUP = "kataml.extensions"

#: Extensions chargées : [{"name", "version", "description", "source", "nodes", "error"}]
LOADED: list[dict] = []
_sources_done: set[str] = set()


def register(type_: str, name: str, category: str = CAT_EXTENSIONS, description: str = "", **kw):
    """Déclare un nœud (même signature que le registre interne).

    ``inputs`` / ``outputs`` : listes de ``(nom, DATA | MODEL)`` ; ``params`` : liste de ``P(...)`` ;
    la fonction décorée reçoit ``(ctx, p)`` et renvoie la liste des sorties. ``code`` (optionnel) :
    fonction ``(p, ins, outs) -> str`` pour l'export Python ; ``has_view=True`` si le nœud
    alimente une vue via ``ctx.add_view(...)``.
    """
    existing = REGISTRY.get(type_)
    if existing is not None and existing.extension is None:
        raise ValueError(f"Le type « {type_} » appartient à KataML et ne peut pas être remplacé.")
    kw.setdefault("color", "ext")
    return _register(type_, name, category, description or name, **kw)


def _load(source: str, loader, meta_default: dict, fingerprint: str = ""):
    before = set(REGISTRY)
    info = {"name": meta_default.get("name"), "version": meta_default.get("version", ""),
            "description": "", "source": source, "nodes": [], "error": None}
    try:
        module = loader()
        if callable(module) and not hasattr(module, "__file__"):
            module = module() or module           # point d'entrée de type fonction
        meta = getattr(module, "KATAML_EXTENSION", {}) or {}
        info.update({k: v for k, v in meta.items() if k in ("name", "version", "description")})
    except Exception as e:
        info["error"] = f"{type(e).__name__} : {e}"
        traceback.print_exc()
    new = sorted(set(REGISTRY) - before)
    for t in new:
        REGISTRY[t].extension = info["name"]
        # Empreinte du code : un bloc modifié invalide ses résultats en cache.
        REGISTRY[t].source_hash = fingerprint or info.get("version", "")
    info["nodes"] = new
    LOADED.append(info)
    status = f"erreur ({info['error']})" if info["error"] else f"{len(new)} nœud(s)"
    print(f"Extension « {info['name']} » : {status}", flush=True)


def load_extensions(workspace: Path | None = None) -> list[dict]:
    """Charge les extensions (une seule fois par source). Désactivable : KATAML_NO_EXTENSIONS=1."""
    if os.environ.get("KATAML_NO_EXTENSIONS"):
        return LOADED
    try:
        eps = entry_points(group=GROUP)
    except TypeError:                      # Python < 3.10
        eps = entry_points().get(GROUP, [])
    for ep in eps:
        key = f"ep:{ep.name}"
        if key not in _sources_done:
            _sources_done.add(key)
            dist = getattr(ep, "dist", None)
            _load(f"paquet {ep.value}", ep.load, {"name": ep.name},
                  fingerprint=f"{ep.value}@{getattr(dist, 'version', '')}")
    if workspace is not None:
        folder = Path(workspace) / "extensions"
        for f in sorted(folder.glob("*.py")) if folder.is_dir() else []:
            key = f"file:{f.resolve()}"
            if key in _sources_done or f.name.startswith("_"):
                continue
            _sources_done.add(key)

            def loader(f=f):
                name = f"kataml_ext_{f.stem}"
                spec = importlib.util.spec_from_file_location(name, f)
                module = importlib.util.module_from_spec(spec)
                sys.modules[name] = module
                spec.loader.exec_module(module)
                return module

            import hashlib
            digest = hashlib.sha1(f.read_bytes()).hexdigest()[:12]
            _load(f"fichier {f.name}", loader, {"name": f.stem}, fingerprint=digest)
    if workspace is not None:
        for key, on in bundled_state(workspace).items():
            if on and key in _bundled_by_key() and not _bundled_loaded(key):
                _load_bundled(key)
    return LOADED


def reload_local_extensions(workspace: Path) -> list[dict]:
    """Recharge les extensions fichiers de l'espace de travail (après modification)."""
    local = [x for x in LOADED if x["source"].startswith("fichier ")]
    for info in local:
        for t in info["nodes"]:
            REGISTRY.pop(t, None)
        sys.modules.pop(f"kataml_ext_{Path(info['source'][8:]).stem}", None)
        LOADED.remove(info)
    for key in [k for k in _sources_done if k.startswith("file:")]:
        _sources_done.discard(key)
    return load_extensions(workspace)


def extensions_info() -> list[dict]:
    return [dict(x) for x in LOADED]


# --------------------------------------------------------------------------
# Extensions « fournies » (embarquées dans le paquet, activables à la demande)
# --------------------------------------------------------------------------

def _bundled_by_key() -> dict:
    from .contrib import BUNDLED
    return {b["key"]: b for b in BUNDLED}


def _state_file(workspace) -> Path:
    return Path(workspace) / "extensions.json"


def bundled_state(workspace) -> dict:
    """{clé: activée} lu depuis workspace/extensions.json."""
    try:
        return dict(json.loads(_state_file(workspace).read_text(encoding="utf-8")).get("bundled", {}))
    except (OSError, ValueError, AttributeError):
        return {}


def _bundled_source(key: str) -> str:
    return f"fourni:{key}"


def _bundled_loaded(key: str) -> bool:
    return any(x["source"] == _bundled_source(key) for x in LOADED)


def _load_bundled(key: str):
    meta = _bundled_by_key()[key]
    _load(_bundled_source(key), lambda: importlib.import_module(meta["module"]),
          {"name": meta["name"]}, fingerprint=f"contrib:{key}@{__version__}")


def _unload_bundled(key: str):
    meta = _bundled_by_key().get(key)
    for info in [x for x in LOADED if x["source"] == _bundled_source(key)]:
        for t in info["nodes"]:
            REGISTRY.pop(t, None)
        LOADED.remove(info)
    if meta:
        sys.modules.pop(meta["module"], None)


def list_bundled(workspace) -> list[dict]:
    """État des extensions fournies pour l'interface (clé, nom, description, activée)."""
    from .contrib import BUNDLED
    state = bundled_state(workspace)
    return [{"key": b["key"], "name": b["name"], "description": b["description"],
             "enabled": bool(state.get(b["key"], False)), "loaded": _bundled_loaded(b["key"])}
            for b in BUNDLED]


def set_bundled(workspace, key: str, enabled: bool, persist: bool = True) -> list[dict]:
    """Active ou désactive une extension fournie (chargement/déchargement immédiat)."""
    if key not in _bundled_by_key():
        raise NodeError(f"Extension fournie inconnue : {key}")
    if persist:
        state = bundled_state(workspace)
        state[key] = bool(enabled)
        try:
            _state_file(workspace).write_text(json.dumps({"bundled": state}, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
    if enabled and not _bundled_loaded(key):
        _load_bundled(key)
    elif not enabled and _bundled_loaded(key):
        _unload_bundled(key)
    return list_bundled(workspace)


# --------------------------------------------------------------------------
# Modèles de blocs (création depuis l'interface)
# --------------------------------------------------------------------------

INPUT_PRESETS = {
    "none": ("[]", ""),
    "table": ('[("Table", DATA)]', 'df = ctx.data(0).copy()'),
    "two_tables": ('[("Table", DATA), ("Table 2", DATA)]', 'df = ctx.data(0).copy()\n    df2 = ctx.data(1)'),
    "table_model": ('[("Modèle", MODEL), ("Table", DATA)]', 'm = ctx.model(0)          # m.estimator, m.features, m.target\n    df = ctx.data(1).copy()'),
}


def slugify(name: str) -> str:
    import re
    import unicodedata
    s = unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s or "bloc"


def block_template(name: str, description: str = "", inputs: str = "table", code: str | None = None,
                   category: str = "Mes blocs", slug: str | None = None) -> tuple[str, str]:
    """Renvoie (nom de fichier, source Python) d'un nouveau bloc."""
    slug = slug or slugify(name)
    ins, prelude = INPUT_PRESETS.get(inputs, INPUT_PRESETS["table"])
    description = description or f"Bloc personnalisé « {name} »."
    if code is not None:
        # Conversion d'un nœud Script Python : son code s'exécute avec df / df2 et produit `out`.
        body = (f"    import numpy as np\n    import pandas as pd\n"
                f"    env = {{\"np\": np, \"pd\": pd, \"df\": ctx.data(0).copy(),\n"
                f"           \"df2\": ctx.inputs[1].copy() if len(ctx.inputs) > 1 and ctx.inputs[1] is not None else None}}\n"
                f"    exec(CODE, env)\n"
                f"    out = env.get(\"out\")\n"
                f"    if not isinstance(out, pd.DataFrame):\n"
                f"        raise NodeError(\"Le code doit affecter un DataFrame à la variable `out`.\")\n"
                f"    return [out]\n")
        code_const = f"\nCODE = {code.rstrip()!r}\n"
        params = ""
        ins = '[("Table", DATA), ("Table 2 (optionnelle)", DATA)]'
        optional = "\n    optional_inputs=[1],"
    else:
        body = (f"    {prelude}\n"
                f"    col, facteur = p[\"colonne\"], p[\"facteur\"]\n"
                f"    if not col:\n"
                f"        raise NodeError(\"Choisissez une colonne.\")\n"
                f"    check_columns(df, [col])\n"
                f"    # Votre code ici. Exemple : une nouvelle colonne.\n"
                f"    df[f\"{{col}}_x{{facteur:g}}\"] = df[col] * facteur\n"
                f"    return [df]\n") if inputs in ("table", "two_tables", "table_model") else (
                "    import pandas as pd\n    # Bloc source : produit une table.\n"
                "    return [pd.DataFrame({\"x\": range(10)})]\n")
        port = 1 if inputs == "table_model" else 0
        params = (f'\n        P("colonne", "Colonne", "column", "", port={port}, required=True),\n'
                  f'        P("facteur", "Facteur", "float", 2.0, "Valeur multiplicative."),\n    '
                  if inputs != "none" else "")
        code_const = ""
        optional = ""
    source = f'''"""Bloc KataML : {name}.

Fichier chargé automatiquement depuis workspace/extensions/. Après modification,
cliquez sur « Recharger » dans le gestionnaire « Mes blocs ».

Types de paramètres : str, int, float, bool, choice (choices=[…]), column, columns,
code, literal. Le paramètre ``port`` d'une colonne indique la table d'entrée utilisée.
"""

from kataml.extension import DATA, MODEL, NodeError, P, check_columns, register

KATAML_EXTENSION = {{"name": {slug!r}, "version": "1.0", "description": {description!r}}}
{code_const}

@register(
    "ext.{slug}", {name!r}, {category!r},
    {description!r},
    inputs={ins},
    outputs=[("Table", DATA)],
    params=[{params}],{optional}
)
def run(ctx, p):
{body}'''
    return f"{slug}.py", source
