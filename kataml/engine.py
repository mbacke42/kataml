"""Exécution des workflows : ordre topologique, cache mémoire et disque par signature."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import threading
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .nodes import DATA, MODEL, REGISTRY, Ctx, ModelPort, NodeError, _data_path, _jsonable


@dataclass
class Result:
    signature: str
    outputs: list[Any]
    view: list[dict] | None
    messages: list[str] = field(default_factory=list)
    seconds: float = 0.0


class WorkflowError(Exception):
    pass


def _salt() -> str:
    import sklearn

    from . import __version__
    return f"{__version__}|{sklearn.__version__}|{pd.__version__}"


class DiskCache:
    """Résultats des nœuds sur disque, indexés par signature (joblib + métadonnées JSON)."""

    def __init__(self, root: Path, limit_mb: int):
        self.root = root
        self.limit = limit_mb * 1024 * 1024
        self.root.mkdir(parents=True, exist_ok=True)
        self._writes = 0
        self.purge()

    def _paths(self, sig: str) -> tuple[Path, Path]:
        return self.root / f"{sig}.joblib", self.root / f"{sig}.json"

    def meta(self, sig: str) -> dict | None:
        _, m = self._paths(sig)
        try:
            return json.loads(m.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def load(self, sig: str) -> Result | None:
        import joblib
        data, m = self._paths(sig)
        if not (data.exists() and m.exists()):
            return None
        try:
            r = joblib.load(data)
            os.utime(data)
            return r if isinstance(r, Result) else None
        except Exception:
            self.delete(sig)
            return None

    def save(self, r: Result, meta: dict):
        import joblib
        if self.limit <= 0:
            return
        data, m = self._paths(r.signature)
        tmp = data.with_suffix(".tmp")
        try:
            joblib.dump(r, tmp, compress=0)
            tmp.replace(data)
            m.write_text(json.dumps(meta, default=_jsonable), encoding="utf-8")
        except Exception:          # objet non sérialisable : on garde seulement le cache mémoire
            tmp.unlink(missing_ok=True)
            return
        self._writes += 1
        if self._writes % 20 == 0:
            self.purge()

    def delete(self, sig: str):
        for p in self._paths(sig):
            p.unlink(missing_ok=True)

    def clear(self):
        for p in self.root.glob("*.joblib"):
            p.unlink(missing_ok=True)
        for p in self.root.glob("*.json"):
            p.unlink(missing_ok=True)

    def purge(self):
        """Supprime les entrées les plus anciennes au-delà de la taille maximale."""
        files = sorted(self.root.glob("*.joblib"), key=lambda p: p.stat().st_mtime, reverse=True)
        total = 0
        for f in files:
            total += f.stat().st_size
            if total > self.limit:
                self.delete(f.stem)


class Engine:
    def __init__(self, workspace: Path, cache_mb: int | None = None):
        self.workspace = workspace
        self.cache: dict[str, Result] = {}
        self.errors: dict[str, tuple[str, str]] = {}   # node -> (signature, message)
        self.known: dict[str, str] = {}                 # node -> dernière signature connue
        self.lock = threading.RLock()
        self.salt = _salt()
        if cache_mb is None:
            cache_mb = int(os.environ.get("KATAML_CACHE_MB", "1024"))
        self.disk = DiskCache(workspace / ".cache", cache_mb)

    # -- graphe -------------------------------------------------------------
    @staticmethod
    def _index(wf: dict):
        nodes = {n["id"]: n for n in wf.get("nodes", [])}
        incoming: dict[str, dict[int, tuple[str, int]]] = {nid: {} for nid in nodes}
        for e in wf.get("edges", []):
            if e["from"] in nodes and e["to"] in nodes:
                incoming[e["to"]][int(e["toPort"])] = (e["from"], int(e["fromPort"]))
        return nodes, incoming

    def signatures(self, wf: dict) -> dict[str, str | None]:
        """Signature de chaque nœud (None si une entrée obligatoire manque)."""
        nodes, incoming = self._index(wf)
        sigs: dict[str, str | None] = {}
        visiting: set[str] = set()

        def sig(nid):
            if nid in sigs:
                return sigs[nid]
            if nid in visiting:
                raise WorkflowError("Le workflow contient un cycle.")
            visiting.add(nid)
            node = nodes[nid]
            nt = REGISTRY.get(node["type"])
            if nt is None:
                sigs[nid] = None
                return None
            parts = [self.salt, node["type"], json.dumps(node.get("params", {}), sort_keys=True, default=str),
                     getattr(nt, "source_hash", "")]
            ok = True
            for i in range(len(nt.inputs)):
                src = incoming[nid].get(i)
                if src is None:
                    if i not in nt.optional_inputs:
                        ok = False
                    parts.append("-")
                    continue
                s = sig(src[0])
                if s is None:
                    ok = False
                parts.append(f"{s}:{src[1]}")
                if nt.uses_labels:
                    parts.append(nodes[src[0]].get("label") or "")
            if node["type"] == "io.csv_reader":
                path = _data_path(self.workspace, node.get("params", {}).get("path") or "")
                parts.append(str(path.stat().st_mtime) if path.is_file() else "missing")
            visiting.discard(nid)
            sigs[nid] = hashlib.sha1("|".join(parts).encode()).hexdigest() if ok else None
            return sigs[nid]

        for nid in nodes:
            sig(nid)
        self.known.update({k: v for k, v in sigs.items() if v})
        return sigs

    def status(self, wf: dict) -> dict[str, dict]:
        sigs = self.signatures(wf)
        out = {}
        for nid, s in sigs.items():
            r = self.cache.get(nid)
            if s and r and r.signature == s:
                out[nid] = self._state(r)
            elif s and nid in self.errors and self.errors[nid][0] == s:
                out[nid] = {"state": "error", "message": self.errors[nid][1]}
            elif s and (meta := self.disk.meta(s)):
                out[nid] = {"state": "executed", **meta}
            else:
                out[nid] = {"state": "idle"}
        return out

    @staticmethod
    def _meta(r: Result) -> dict:
        return {"seconds": round(r.seconds, 3), "messages": r.messages,
                "outputs": [describe(o) for o in r.outputs], "has_view": bool(r.view)}

    def _state(self, r: Result) -> dict:
        return {"state": "executed", **self._meta(r)}

    # -- exécution ----------------------------------------------------------
    def execute(self, wf: dict, target: str) -> tuple[bool, str | None, dict[str, dict]]:
        """Exécute ``target`` et ses prédécesseurs. Renvoie (succès, erreur, états modifiés)."""
        with self.lock:
            nodes, incoming = self._index(wf)
            if target not in nodes:
                raise WorkflowError("Nœud inconnu.")
            sigs = self.signatures(wf)
            changed: dict[str, dict] = {}
            try:
                self._run(target, nodes, incoming, sigs, changed)
            except NodeError as e:
                return False, str(e), changed
            return True, None, changed

    def _cached(self, nid: str, sig: str | None) -> Result | None:
        r = self.cache.get(nid)
        if r and r.signature == sig:
            return r
        if sig and (r := self.disk.load(sig)):
            self.cache[nid] = r
            return r
        return None

    def _run(self, nid, nodes, incoming, sigs, changed) -> Result:
        r = self._cached(nid, sigs.get(nid))
        if r:
            return r
        node = nodes[nid]
        nt = REGISTRY.get(node["type"])
        if nt is None:
            raise NodeError(f"Type de nœud inconnu : {node['type']}")
        inputs, labels = [], []
        for i, (pname, _) in enumerate(nt.inputs):
            src = incoming[nid].get(i)
            if src is None:
                if i in nt.optional_inputs:
                    inputs.append(None)
                    labels.append(None)
                    continue
                msg = f"Port d'entrée « {pname} » non connecté."
                changed[nid] = {"state": "error", "message": msg}
                raise NodeError(msg)
            try:
                up = self._run(src[0], nodes, incoming, sigs, changed)
            except NodeError:
                changed.setdefault(nid, {"state": "idle"})
                raise
            inputs.append(up.outputs[src[1]] if src[1] < len(up.outputs) else None)
            labels.append(nodes[src[0]].get("label") or None)
        ctx = Ctx(inputs=inputs, workspace=self.workspace, node_id=nid, input_labels=labels)
        params = self._params(nt, node.get("params", {}))
        t0 = time.perf_counter()
        try:
            outputs = nt.run(ctx, params) or []
        except NodeError as e:
            self._fail(nid, sigs, str(e), changed)
            raise
        except Exception as e:  # erreur inattendue : message court + trace en console
            traceback.print_exc()
            msg = f"{type(e).__name__} : {e}"
            self._fail(nid, sigs, msg, changed)
            raise NodeError(msg) from e
        r = Result(sigs.get(nid) or "", outputs, ctx.view, ctx.messages, time.perf_counter() - t0)
        self.cache[nid] = r
        self.errors.pop(nid, None)
        changed[nid] = self._state(r)
        if r.signature:
            self.disk.save(r, self._meta(r))
        return r

    def _fail(self, nid, sigs, msg, changed):
        self.cache.pop(nid, None)
        self.errors[nid] = (sigs.get(nid) or "", msg)
        changed[nid] = {"state": "error", "message": msg}

    @staticmethod
    def _params(nt, given: dict) -> dict:
        params = {}
        for spec in nt.params:
            name = spec["name"]
            if spec.get("group") == "Hyperparamètres":
                if name in given and given[name] not in (None, ""):
                    params[name] = given[name]
                continue
            params[name] = given.get(name, spec.get("default"))
        return params

    def reset(self, ids=None):
        with self.lock:
            if ids is None:
                self.cache.clear()
                self.errors.clear()
                self.disk.clear()
                return
            for i in ids:
                r = self.cache.pop(i, None)
                self.errors.pop(i, None)
                for sig in {getattr(r, "signature", None), self.known.get(i)} - {None}:
                    self.disk.delete(sig)

    def result(self, nid) -> Result:
        r = self._cached(nid, self.known.get(nid)) or self.cache.get(nid)
        if r is None:
            raise NodeError("Ce nœud n'est pas exécuté.")
        return r

    def input_columns(self, wf: dict, nid: str, run: bool = False) -> list[list[dict] | None]:
        """Colonnes disponibles sur chaque port d'entrée (pour les formulaires)."""
        nodes, incoming = self._index(wf)
        node = nodes.get(nid)
        if node is None or node["type"] not in REGISTRY:
            return []
        nt = REGISTRY[node["type"]]
        sigs = self.signatures(wf)
        res = []
        for i in range(len(nt.inputs)):
            src = incoming[nid].get(i)
            if src is None:
                res.append(None)
                continue
            r = self._cached(src[0], sigs.get(src[0]))
            if r is None and run and sigs.get(src[0]):
                with self.lock:
                    try:
                        r = self._run(src[0], nodes, incoming, sigs, {})
                    except NodeError:
                        r = None
            o = r.outputs[src[1]] if r and src[1] < len(r.outputs) else None
            if isinstance(o, pd.DataFrame):
                res.append([{"name": str(c), "dtype": str(t)} for c, t in o.dtypes.items()])
            elif isinstance(o, ModelPort):
                # Port modèle : on propose les variables du modèle.
                res.append([{"name": str(c), "dtype": "variable"} for c in o.features])
            else:
                res.append(None)
        return res

    def all_input_columns(self, wf: dict) -> dict[str, list]:
        """Colonnes connues (résultats en cache, sans calcul) des nœuds qui ont des paramètres de colonnes."""
        out = {}
        for node in wf.get("nodes", []):
            nt = REGISTRY.get(node["type"])
            if nt and any(p.get("type") in ("column", "columns") for p in nt.params):
                out[node["id"]] = self.input_columns(wf, node["id"])
        return out


def describe(o) -> dict:
    if isinstance(o, pd.DataFrame):
        return {"kind": DATA, "rows": int(o.shape[0]), "cols": int(o.shape[1])}
    if isinstance(o, ModelPort):
        return {"kind": MODEL, "name": o.name, "model_kind": o.kind}
    return {"kind": "none"}


# --------------------------------------------------------------------------
# Service : opérations de l'API, résultats sérialisables (JSON / octets)
# --------------------------------------------------------------------------

def table_page(df: pd.DataFrame, offset: int, limit: int, sort: str | None, desc: bool) -> dict:
    if sort and sort in map(str, df.columns):
        col = next(c for c in df.columns if str(c) == sort)
        df = df.sort_values(col, ascending=not desc, kind="stable")
    part = df.iloc[offset: offset + limit]
    cols = [{"name": str(c), "dtype": str(df[c].dtype)} for c in df.columns]
    rows = json.loads(part.to_json(orient="values", date_format="iso", default_handler=str))
    return {"columns": cols, "rows": rows, "index": [_jsonable(i) for i in part.index],
            "total": int(len(df)), "offset": offset}


def column_profile(s: pd.Series) -> dict:
    num = pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s)
    out = {"name": str(s.name), "dtype": str(s.dtype), "missing": int(s.isna().sum()),
           "unique": int(s.nunique()), "numeric": bool(num)}
    v = s.dropna()
    if num and len(v):
        counts, edges = np.histogram(v, bins=12)
        out.update(min=_jsonable(v.min()), max=_jsonable(v.max()), mean=_jsonable(v.mean()),
                   std=_jsonable(v.std()), hist=counts.tolist(), edges=edges.tolist())
    elif len(v):
        vc = v.astype(str).value_counts().head(6)
        out.update(top=[[k, int(n)] for k, n in vc.items()])
    return out


class EngineService:
    """Façade du moteur utilisée par le serveur, en direct ou dans un processus séparé."""

    def __init__(self, workspace: Path):
        from .extension import load_extensions
        load_extensions(workspace)
        self.engine = Engine(workspace)

    def reload_extensions(self):
        from .extension import extensions_info, reload_local_extensions
        reload_local_extensions(self.engine.workspace)
        return {"extensions": extensions_info()}

    def set_bundled(self, key, enabled):
        from .extension import set_bundled
        # L'interface a déjà persisté le choix dans le processus serveur.
        set_bundled(self.engine.workspace, key, enabled, persist=False)
        return {"ok": True}

    def report(self, wf, options=None):
        from .report import build_report
        return build_report(self.engine, wf, options or {})

    def status(self, wf):
        return {"states": self.engine.status(wf)}

    def execute(self, wf, node):
        ok, err, changed = self.engine.execute(wf, node)
        return {"ok": ok, "error": err, "states": changed}

    def reset(self, nodes=None):
        self.engine.reset(nodes)
        return {"ok": True}

    def columns(self, wf, node, run=False):
        return {"ports": self.engine.input_columns(wf, node, run)}

    def columns_all(self, wf):
        return {"columns": self.engine.all_input_columns(wf)}

    def port(self, node, port=0, offset=0, limit=100, sort=None, desc=False):
        r = self.engine.result(node)
        if port >= len(r.outputs):
            raise NodeError("Port inexistant.")
        o = r.outputs[port]
        if isinstance(o, pd.DataFrame):
            return {"kind": "data", **table_page(o, int(offset), min(int(limit), 1000), sort, bool(desc))}
        if isinstance(o, ModelPort):
            return {"kind": "model", "summary": o.summary()}
        return {"kind": "none"}

    def profile(self, node, port=0):
        o = self.engine.result(node).outputs[int(port)]
        if not isinstance(o, pd.DataFrame):
            raise NodeError("Pas une table.")
        return {"columns": [column_profile(o[c]) for c in o.columns[:200]]}

    def view(self, node):
        r = self.engine.result(node)
        return {"blocks": r.view or [], "messages": r.messages, "seconds": r.seconds}

    def download(self, node, port, name):
        o = self.engine.result(node).outputs[int(port)]
        name = re.sub(r"[^\w\-]+", "_", name or "sortie") or "sortie"
        if isinstance(o, pd.DataFrame):
            return o.to_csv(index=False).encode("utf-8"), f"{name}.csv", "text/csv; charset=utf-8"
        if isinstance(o, ModelPort):
            import joblib
            buf = io.BytesIO()
            joblib.dump(o.estimator, buf)
            return buf.getvalue(), f"{name}.joblib", "application/octet-stream"
        raise NodeError("Rien à télécharger.")
