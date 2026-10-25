"""Serveur HTTP local (bibliothèque standard uniquement) et API JSON."""

from __future__ import annotations

import gzip
import json
import mimetypes
import os
import re
import secrets
import shutil
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

import pandas as pd

from . import __version__, sk_catalog
from .engine import EngineService, WorkflowError
from .export import export_notebook, export_python
from .nodes import REGISTRY, NodeError, _jsonable, catalog
from .worker import Cancelled, EngineProcess
from . import extension as ext

STATIC = Path(__file__).parent / "static"
EXAMPLES = Path(__file__).parent / "examples"
SAFE_NAME = re.compile(r"^[\w\-. ()àâäéèêëîïôöùûüç]+$", re.IGNORECASE)


class App:
    def __init__(self, workspace: Path):
        self.workspace = workspace
        for d in ("data", "workflows", "exports", "components"):
            (workspace / d).mkdir(parents=True, exist_ok=True)
        self.copy_example_data()
        (workspace / "extensions").mkdir(exist_ok=True)
        (workspace / "reports").mkdir(exist_ok=True)
        (workspace / "scripts").mkdir(exist_ok=True)
        ext.load_extensions(workspace)
        # Moteur dans un processus séparé (annulation possible), sauf KATAML_INPROCESS=1.
        self.engine = InProcess(workspace) if os.environ.get("KATAML_INPROCESS") else EngineProcess(workspace)
        self.token = secrets.token_urlsafe(24)
        self.public = False
        self.build_catalog()

    def build_catalog(self):
        self._catalogs: dict[str, bytes] = {}

    def catalog_gz(self, lang: str) -> bytes:
        from . import taxonomy
        lang = "en" if lang == "en" else "fr"
        if lang not in self._catalogs:
            self._catalogs[lang] = gzip.compress(json.dumps({
                "nodes": catalog(lang), "version": __version__, "extensions": ext.extensions_info(),
                "sklearn": sk_catalog.sklearn_version(), "pandas": pd.__version__, "lang": lang,
                "category_order": taxonomy.section_order(lang),
            }, default=_jsonable, ensure_ascii=False, allow_nan=False).encode())
        return self._catalogs[lang]

    def reload_extensions(self) -> list[dict]:
        ext.reload_local_extensions(self.workspace)
        self.engine.call("reload_extensions")
        self.build_catalog()
        return ext.extensions_info()

    def set_bundled(self, key: str, enabled: bool) -> list[dict]:
        bundled = ext.set_bundled(self.workspace, key, enabled)   # persiste + (dé)charge côté serveur
        self.engine.call("set_bundled", key=key, enabled=enabled)  # idem côté moteur
        self.build_catalog()
        return bundled

    def copy_example_data(self):
        """Copie dans l'espace de travail les données d'exemple manquantes."""
        for f in (EXAMPLES / "data").glob("*"):
            dest = self.workspace / "data" / f.name
            if not dest.exists():
                shutil.copyfile(f, dest)


def _safe_file(base: Path, name: str, suffix: str | None = None) -> Path:
    name = Path(name).name
    if not name or not SAFE_NAME.match(name):
        raise NodeError("Nom de fichier invalide.")
    if suffix and not name.endswith(suffix):
        name += suffix
    return base / name


class InProcess:
    """Moteur dans le processus du serveur (tests, débogage) : pas d'annulation."""

    def __init__(self, workspace: Path):
        self.service = EngineService(workspace)

    def call(self, method, **kwargs):
        return getattr(self.service, method)(**kwargs)

    def cancel(self) -> bool:
        return False

    def close(self):
        pass


class Handler(BaseHTTPRequestHandler):
    app: App
    server_version = "KataML"

    def log_request(self, code="-", size="-"):
        if isinstance(code, int) and code >= 400 or str(code).startswith(("4", "5")):
            super().log_request(code, size)

    # -- sécurité : requêtes locales uniquement, jeton anti-CSRF --------------
    def _host_ok(self) -> bool:
        if self.app.public:
            return True
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]")
        return host in ("127.0.0.1", "localhost", "::1")

    def _token_ok(self, query) -> bool:
        tok = self.headers.get("X-KataML-Token") or (query.get("token") or [""])[0]
        return secrets.compare_digest(tok, self.app.token)

    # -- réponses ------------------------------------------------------------
    def _send(self, status, body: bytes, ctype: str, extra=None, gz=False):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if gz:
            self.send_header("Content-Encoding", "gzip")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, status=200):
        from . import i18n
        if self.headers.get("X-KataML-Lang") == "en":
            obj = i18n.translate_payload(obj, "en")
        body = json.dumps(obj, default=_jsonable, ensure_ascii=False, allow_nan=False).encode()
        if len(body) > 20000 and "gzip" in (self.headers.get("Accept-Encoding") or ""):
            self._send(status, gzip.compress(body, 5), "application/json; charset=utf-8", gz=True)
        else:
            self._send(status, body, "application/json; charset=utf-8")

    def _error(self, msg, status=400):
        self._json({"error": msg}, status)

    def _body(self) -> bytes:
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    # -- routage -------------------------------------------------------------
    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def _dispatch(self, method):
        if not self._host_ok():
            return self._error("Hôte non autorisé.", 403)
        url = urlparse(self.path)
        q = parse_qs(url.query)
        if not url.path.startswith("/api/"):
            return self._static(url.path) if method == "GET" else self._error("Introuvable", 404)
        if not self._token_ok(q):
            return self._error("Jeton invalide.", 403)
        route = getattr(self, f"api_{url.path[5:].replace('/', '_')}", None)
        if route is None:
            return self._error("Route inconnue.", 404)
        try:
            data = {}
            if method == "POST" and url.path != "/api/upload":
                raw = self._body()
                data = json.loads(raw or b"{}")
            route(data, q)
        except (NodeError, WorkflowError) as e:
            self._error(str(e))
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._error(f"{type(e).__name__} : {e}", 500)

    def _static(self, path):
        if path in ("/", "/index.html"):
            html = (STATIC / "index.html").read_text(encoding="utf-8")
            html = html.replace("__KATAML_TOKEN__", self.app.token)
            return self._send(200, html.encode(), "text/html; charset=utf-8",
                              {"Content-Security-Policy": "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'"})
        if path == "/theme.css":
            # Personnalisation de l'interface : workspace/theme.css (feuille vide s'il n'existe pas).
            t = self.app.workspace / "theme.css"
            return self._send(200, t.read_bytes() if t.is_file() else b"", "text/css; charset=utf-8")
        f = (STATIC / path.lstrip("/")).resolve()
        if not str(f).startswith(str(STATIC.resolve())) or not f.is_file():
            return self._error("Introuvable", 404)
        ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype.endswith(("javascript", "json", "svg+xml")):
            ctype += "; charset=utf-8"
        self._send(200, f.read_bytes(), ctype)

    # -- API -----------------------------------------------------------------
    def api_catalog(self, data, q):
        self._send(200, self.app.catalog_gz(q.get("lang", ["fr"])[0]), "application/json; charset=utf-8", gz=True)

    def api_status(self, data, q):
        self._json(self.app.engine.call("status", wf=data["workflow"]))

    def api_execute(self, data, q):
        try:
            self._json(self.app.engine.call("execute", wf=data["workflow"], node=data["node"]))
        except Cancelled as e:
            self._json({"ok": False, "cancelled": True, "error": str(e),
                        "states": {data["node"]: {"state": "idle"}}})

    def api_cancel(self, data, q):
        self._json({"ok": self.app.engine.cancel()})

    def api_reset(self, data, q):
        self._json(self.app.engine.call("reset", nodes=data.get("nodes")))

    def api_columns(self, data, q):
        self._json(self.app.engine.call("columns", wf=data["workflow"], node=data["node"], run=bool(data.get("run"))))

    def api_columns_all(self, data, q):
        self._json(self.app.engine.call("columns_all", wf=data["workflow"]))

    def api_port(self, data, q):
        self._json(self.app.engine.call("port", node=data["node"], port=int(data.get("port", 0)),
                                        offset=int(data.get("offset", 0)), limit=int(data.get("limit", 100)),
                                        sort=data.get("sort"), desc=bool(data.get("desc"))))

    def api_profile(self, data, q):
        self._json(self.app.engine.call("profile", node=data["node"], port=int(data.get("port", 0))))

    def api_view(self, data, q):
        self._json(self.app.engine.call("view", node=data["node"]))

    def api_download(self, data, q):
        body, fn, ctype = self.app.engine.call("download", node=q.get("node", [""])[0],
                                               port=int(q.get("port", ["0"])[0]), name=q.get("name", ["sortie"])[0])
        self._send(200, body, ctype, {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(fn)}"})

    def api_upload(self, data, q):
        name = q.get("name", [""])[0]
        dest = _safe_file(self.app.workspace / "data", name)
        n = int(self.headers.get("Content-Length") or 0)
        if n > 2 * 1024 ** 3:
            raise NodeError("Fichier trop volumineux.")
        with open(dest, "wb") as f:
            remaining = n
            while remaining > 0:
                chunk = self.rfile.read(min(1 << 20, remaining))
                if not chunk:
                    break
                f.write(chunk)
                remaining -= len(chunk)
        self._json({"ok": True, "name": dest.name})

    def api_files(self, data, q):
        d = self.app.workspace / "data"
        files = sorted((f for f in d.iterdir() if f.is_file()), key=lambda f: f.name.lower())
        self._json({"files": [{"name": f.name, "size": f.stat().st_size} for f in files]})

    def api_workflows(self, data, q):
        d = self.app.workspace / "workflows"
        mine = sorted((f.stem for f in d.glob("*.json")), key=str.lower)
        examples = []
        en = self.headers.get("X-KataML-Lang") == "en"
        for f in sorted(EXAMPLES.glob("*.json")):
            try:
                meta = json.loads(f.read_text(encoding="utf-8"))
                name = (en and meta.get("name_en")) or meta.get("name", f.stem)
                desc = (en and meta.get("description_en")) or meta.get("description", "")
                examples.append({"id": f.stem, "name": name, "description": desc})
            except Exception:
                pass
        self._json({"workflows": mine, "examples": examples})

    def api_workflow_load(self, data, q):
        if data.get("example"):
            f = _safe_file(EXAMPLES, data["example"], ".json")
            self.app.copy_example_data()
        else:
            f = _safe_file(self.app.workspace / "workflows", data["name"], ".json")
        if not f.is_file():
            raise NodeError("Workflow introuvable.")
        self._json({"workflow": json.loads(f.read_text(encoding="utf-8"))})

    def api_workflow_save(self, data, q):
        f = _safe_file(self.app.workspace / "workflows", data["name"], ".json")
        f.write_text(json.dumps(data["workflow"], ensure_ascii=False, indent=1), encoding="utf-8")
        self._json({"ok": True, "name": f.stem})

    def api_import_script(self, data, q):
        """Reconstruit un workflow à partir de scripts Python (jamais exécutés).

        ``files`` : scripts envoyés ; ``scripts`` : noms de scripts de workspace/scripts.
        Les autres scripts de la bibliothèque servent de modules s'ils sont importés.
        Renvoie aussi les fichiers de données utilisés par le schéma mais absents de workspace/data.
        """
        from .py_import import scripts_to_workflow
        files = [(str(f.get("name") or "script.py"), str(f.get("source") or "")) for f in data.get("files") or []]
        lib_dir = self.app.workspace / "scripts"
        for name in data.get("scripts") or []:
            f = _safe_file(lib_dir, name, ".py")
            if not f.is_file():
                raise NodeError(f"Script introuvable : {name}")
            files.append((f.name, f.read_text(encoding="utf-8", errors="replace")))
        chosen = {n for n, _ in files}
        library = [(f.name, f.read_text(encoding="utf-8", errors="replace"))
                   for f in sorted(lib_dir.glob("*.py")) if f.name not in chosen and f.stat().st_size < 2_000_000]
        if sum(len(src) for _, src in files) > 5_000_000:
            raise NodeError("Scripts trop volumineux (5 Mo au plus).")
        try:
            wf, notes = scripts_to_workflow(files, known_types=set(REGISTRY), library=library)
        except ValueError as e:
            raise NodeError(str(e)) from e
        missing = []
        for n in wf["nodes"]:
            path = (n.get("params") or {}).get("path") if n["type"] in ("io.csv_reader", "io.table_reader") else \
                (n.get("params") or {}).get("source") if n["type"] == "io.sql_reader" else None
            if path and "://" not in path and not path.startswith("$") and path not in missing \
                    and not (self.app.workspace / "data" / Path(path).name).exists() and not Path(path).expanduser().is_absolute():
                missing.append(path)
        self._json({"workflow": wf, "notes": notes, "missing_data": missing})

    # -- Bibliothèque de scripts (workspace/scripts) ---------------------------
    def api_scripts(self, data, q):
        d = self.app.workspace / "scripts"
        files = sorted(d.glob("*.py"), key=lambda f: f.name.lower())
        self._json({"folder": str(d), "scripts": [
            {"name": f.name, "size": f.stat().st_size, "mtime": f.stat().st_mtime,
             "main": "__main__" in f.read_text(encoding="utf-8", errors="replace")[:2_000_000]} for f in files]})

    def api_script_read(self, data, q):
        f = _safe_file(self.app.workspace / "scripts", data["file"], ".py")
        if not f.is_file():
            raise NodeError("Script introuvable.")
        self._json({"file": f.name, "source": f.read_text(encoding="utf-8", errors="replace")})

    def api_script_save(self, data, q):
        source = str(data.get("source") or "")
        if len(source) > 2_000_000:
            raise NodeError("Script trop volumineux (2 Mo au plus).")
        f = _safe_file(self.app.workspace / "scripts", data["file"], ".py")
        f.write_text(source, encoding="utf-8")
        self._json({"file": f.name})

    def api_script_delete(self, data, q):
        f = _safe_file(self.app.workspace / "scripts", data["file"], ".py")
        f.unlink(missing_ok=True)
        self._json({"ok": True})

    def api_data_delete(self, data, q):
        f = _safe_file(self.app.workspace / "data", data["file"])
        f.unlink(missing_ok=True)
        self._json({"ok": True})

    def api_export(self, data, q):
        name = data.get("name") or "workflow"
        if data.get("format") == "ipynb":
            self._json({"code": export_notebook(data["workflow"], name)})
        else:
            self._json({"code": export_python(data["workflow"], name)})

    # Composants réutilisables (groupes de nœuds enregistrés).
    def api_components(self, data, q):
        out = []
        for f in sorted((self.app.workspace / "components").glob("*.json"), key=lambda f: f.stem.lower()):
            try:
                c = json.loads(f.read_text(encoding="utf-8"))
                out.append({"id": f.stem, "name": c.get("name", f.stem), "description": c.get("description", ""),
                            "nodes": len(c.get("nodes", []))})
            except (OSError, ValueError):
                pass
        self._json({"components": out})

    def api_component_load(self, data, q):
        f = _safe_file(self.app.workspace / "components", data["id"], ".json")
        if not f.is_file():
            raise NodeError("Composant introuvable.")
        self._json({"component": json.loads(f.read_text(encoding="utf-8"))})

    def api_component_save(self, data, q):
        comp = data["component"]
        f = _safe_file(self.app.workspace / "components", comp.get("name") or "composant", ".json")
        f.write_text(json.dumps(comp, ensure_ascii=False, indent=1), encoding="utf-8")
        self._json({"ok": True, "id": f.stem})

    def api_component_delete(self, data, q):
        f = _safe_file(self.app.workspace / "components", data["id"], ".json")
        f.unlink(missing_ok=True)
        self._json({"ok": True})

    # Rapports HTML (enregistrés dans workspace/reports).
    def api_report(self, data, q):
        import datetime as dt
        wf = data["workflow"]
        options = {**(data.get("options") or {}), "lang": self.headers.get("X-KataML-Lang") or "fr"}
        html_doc = self.app.engine.call("report", wf=wf, options=options)
        stem = ext.slugify(wf.get("name") or "rapport")
        name = f"{stem}-{dt.datetime.now():%Y%m%d-%H%M%S}.html"
        (self.app.workspace / "reports" / name).write_text(html_doc, encoding="utf-8")
        self._json({"name": name})

    def api_reports(self, data, q):
        files = sorted((self.app.workspace / "reports").glob("*.html"), key=lambda f: f.stat().st_mtime, reverse=True)
        self._json({"reports": [{"name": f.name, "size": f.stat().st_size} for f in files[:30]]})

    def api_report_file(self, data, q):
        f = _safe_file(self.app.workspace / "reports", q.get("name", [""])[0])
        if f.suffix != ".html" or not f.is_file():
            raise NodeError("Rapport introuvable.")
        extra = {"Content-Security-Policy": "default-src 'none'; script-src 'unsafe-inline'; "
                                            "style-src 'unsafe-inline'; img-src data:"}
        if q.get("download", ["0"])[0] == "1":
            extra["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(f.name)}"
        self._send(200, f.read_bytes(), "text/html; charset=utf-8", extra)

    # Blocs personnalisés (extensions fichiers de workspace/extensions).
    def _ext_dir(self) -> Path:
        return self.app.workspace / "extensions"

    def api_extensions(self, data, q):
        files = sorted(self._ext_dir().glob("*.py"), key=lambda f: f.name.lower())
        self._json({"extensions": ext.extensions_info(), "folder": str(self._ext_dir()),
                    "bundled": ext.list_bundled(self.app.workspace),
                    "files": [{"name": f.name, "size": f.stat().st_size} for f in files]})

    def api_bundled_set(self, data, q):
        self._json({"bundled": self.app.set_bundled(data["key"], bool(data.get("enabled")))})

    def api_extensions_reload(self, data, q):
        self._json({"extensions": self.app.reload_extensions()})

    def api_extension_new(self, data, q):
        name = data.get("name") or "Mon bloc"
        base = slug = ext.slugify(name)
        i = 2
        while (self._ext_dir() / f"{slug}.py").exists() or f"ext.{slug}" in REGISTRY:
            slug, i = f"{base}_{i}", i + 1
        fname, source = ext.block_template(name, data.get("description") or "", data.get("inputs") or "table",
                                           data.get("code"), data.get("category") or "Mes blocs", slug=slug)
        (self._ext_dir() / fname).write_text(source, encoding="utf-8")
        self._json({"file": fname, "extensions": self.app.reload_extensions()})

    def api_extension_read(self, data, q):
        f = _safe_file(self._ext_dir(), data["file"])
        if f.suffix != ".py" or not f.is_file():
            raise NodeError("Fichier introuvable.")
        self._json({"file": f.name, "source": f.read_text(encoding="utf-8")})

    def api_extension_save(self, data, q):
        f = _safe_file(self._ext_dir(), data["file"], ".py")
        f.write_text(data["source"], encoding="utf-8")
        self._json({"file": f.name, "extensions": self.app.reload_extensions()})

    def api_extension_delete(self, data, q):
        f = _safe_file(self._ext_dir(), data["file"], ".py")
        f.unlink(missing_ok=True)
        self._json({"extensions": self.app.reload_extensions()})

    def api_shutdown(self, data, q):
        self._json({"ok": True})
        threading.Thread(target=self.app.httpd.shutdown, daemon=True).start()

    def api_info(self, data, q):
        self._json({"workspace": str(self.app.workspace), "version": __version__,
                    "sklearn": sk_catalog.sklearn_version()})

    def api_update(self, data, q):
        from . import update
        self._json(update.check(self.app.workspace))


def default_workspace() -> Path:
    """Dossier de travail par défaut.

    Depuis une copie du dépôt (lanceur kataml.sh) : ./workspace à côté du code.
    Une fois installé (uv tool install) : ~/kataml, ou $KATAML_WORKSPACE.
    """
    import os
    if os.environ.get("KATAML_WORKSPACE"):
        return Path(os.environ["KATAML_WORKSPACE"]).expanduser()
    source_root = Path(__file__).resolve().parent.parent
    if (source_root / "pyproject.toml").is_file() and (source_root / "kataml.sh").is_file():
        return source_root / "workspace"
    return Path.home() / "kataml"


def serve(host="127.0.0.1", port=8765, workspace: Path | None = None, open_browser=True):
    workspace = (workspace or default_workspace()).expanduser().resolve()
    print("KataML : chargement du catalogue scikit-learn…", flush=True)
    try:
        app = App(workspace)
    except OSError as e:
        # Dossier non inscriptible (application dans un dossier système, clé verrouillée…).
        fallback = Path.home() / "kataml"
        print(f"Impossible d'utiliser {workspace} ({e.strerror}) : repli sur {fallback}", flush=True)
        workspace = fallback
        app = App(workspace)
    app.public = host not in ("127.0.0.1", "localhost", "::1")
    Handler.app = app
    if app.public:
        print("ATTENTION : interface accessible depuis le réseau. Le nœud « Script Python » "
              "permet d'exécuter du code sur cette machine.", flush=True)
    httpd = None
    for p in range(port, port + 20):
        try:
            httpd = ThreadingHTTPServer((host, p), Handler)
            port = p
            break
        except OSError:
            continue
    if httpd is None:
        raise SystemExit("Aucun port libre trouvé.")
    httpd.daemon_threads = True
    app.httpd = httpd
    url = f"http://{'127.0.0.1' if host in ('0.0.0.0', '') else host}:{port}/"
    print(f"KataML {__version__} · scikit-learn {sk_catalog.sklearn_version()} · {len(REGISTRY)} nœuds")
    print(f"Espace de travail : {workspace}")
    print(f"Interface : {url}   (Ctrl+C pour quitter)", flush=True)
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt de KataML.")
    finally:
        httpd.server_close()
        app.engine.close()
