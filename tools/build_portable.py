#!/usr/bin/env python3
"""Construit les versions portables de KataML : AppImage Linux et zip Windows.

Les deux paquets sont produits depuis Linux, sans runner Windows :

* un Python « relocalisable » (python-build-standalone, celui qu'utilise uv) est
  téléchargé pour chaque plateforme ;
* les wheels officielles de KataML, scikit-learn, pandas… sont installées
  dedans avec ``uv pip install --target --python-platform`` ;
* le tout est nettoyé, précompilé (.pyc) puis empaqueté.

Usage :
    uv run --no-project python tools/build_portable.py [--target linux|windows|all] [--smoke-test]

Prérequis : uv dans le PATH, accès réseau (téléchargements depuis GitHub et PyPI).
Bibliothèque standard uniquement.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import stat
import subprocess
import sys
import tarfile
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Versions figées pour des builds reproductibles.
PBS_RELEASE = "20261009"
PYTHON_VERSION = "3.13.16"
PY_MINOR = "3.13"
PBS_URL = ("https://github.com/astral-sh/python-build-standalone/releases/download/"
           f"{PBS_RELEASE}/cpython-{PYTHON_VERSION}+{PBS_RELEASE}-{{triple}}-install_only_stripped.tar.gz")
APPIMAGETOOL_URL = ("https://github.com/AppImage/appimagetool/releases/download/"
                    "continuous/appimagetool-x86_64.AppImage")

TARGETS = {
    "linux": {"triple": "x86_64-unknown-linux-gnu", "uv_platform": "x86_64-manylinux_2_28",
              "site": f"lib/python{PY_MINOR}/site-packages", "stdlib": f"lib/python{PY_MINOR}"},
    "windows": {"triple": "x86_64-pc-windows-msvc", "uv_platform": "x86_64-pc-windows-msvc",
                "site": "Lib/site-packages", "stdlib": "Lib"},
}

# Modules de la bibliothèque standard inutiles pour KataML.
STDLIB_PRUNE = ["test", "idlelib", "tkinter", "turtledemo", "ensurepip", "lib2to3", "pydoc_data", "turtle.py"]
SITE_PRUNE = ["pip", "pip-*.dist-info", ".lock", "*.whl"]
USER_AGENT = "kataml-build (+https://gitlab.com/fredbl/kataml)"


def log(msg: str):
    print(f"[build] {msg}", flush=True)


def run(cmd, **kw):
    log("$ " + " ".join(str(c) for c in cmd))
    subprocess.run([str(c) for c in cmd], check=True, **kw)


def project_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return re.search(r'^version\s*=\s*"([^"]+)"', text, re.M).group(1)


def fetch(url: str, dest: Path) -> Path:
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    log(f"téléchargement {url}")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f, 1 << 20)
    tmp.rename(dest)
    return dest


def build_wheel(work: Path) -> Path:
    out = work / "wheel"
    shutil.rmtree(out, ignore_errors=True)
    run(["uv", "build", "--wheel", "--out-dir", out, ROOT])
    return next(out.glob("kataml-*.whl"))


def python_runtime(target: str, cache: Path, dest: Path) -> Path:
    """Extrait le Python standalone de la plateforme dans ``dest/python``."""
    archive = fetch(PBS_URL.format(triple=TARGETS[target]["triple"]),
                    cache / f"cpython-{PYTHON_VERSION}-{target}.tar.gz")
    shutil.rmtree(dest / "python", ignore_errors=True)
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as tar:
        tar.extractall(dest, filter="tar" if sys.version_info >= (3, 12) else None)
    return dest / "python"


def install_packages(target: str, pyroot: Path, wheel: Path):
    site = pyroot / TARGETS[target]["site"]
    run(["uv", "pip", "install", "--quiet", "--no-cache", "--target", site,
         "--python-platform", TARGETS[target]["uv_platform"], "--python-version", PY_MINOR,
         "--only-binary", ":all:", wheel])
    # uv --target crée un dossier bin/ pour les scripts : inutile ici.
    shutil.rmtree(site / "bin", ignore_errors=True)


def prune(target: str, pyroot: Path):
    stdlib = pyroot / TARGETS[target]["stdlib"]
    site = pyroot / TARGETS[target]["site"]
    removed = 0
    for name in STDLIB_PRUNE:
        for p in stdlib.glob(name):
            removed += _rm(p)
    for pat in SITE_PRUNE:
        for p in site.glob(pat):
            removed += _rm(p)
    # Suites de tests des dépendances (pandas, scipy, numpy, sklearn…).
    for p in list(site.rglob("tests")):
        if p.is_dir() and p.parent != site:
            removed += _rm(p)
    for p in list(pyroot.rglob("__pycache__")):
        removed += _rm(p)
    for pat in ("*.pyi", "*.pxd", "*.pyx", "*.c", "*.h"):
        for p in site.rglob(pat):
            removed += _rm(p)
    log(f"nettoyage {target} : {removed / 1e6:.0f} Mo retirés")


def _rm(p: Path) -> int:
    if not p.exists():
        return 0
    if p.is_dir():
        size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
        shutil.rmtree(p)
    else:
        size = p.stat().st_size
        p.unlink()
    return size


def precompile(host_python: Path, target: str, pyroot: Path):
    """Précompile en .pyc (l'AppImage est en lecture seule : pas de cache à l'exécution)."""
    lib = pyroot / TARGETS[target]["stdlib"]
    run([host_python, "-m", "compileall", "-q", "-j", "0", "--invalidation-mode", "unchecked-hash",
         "-s", pyroot, "-p", "<kataml>", lib], stdout=subprocess.DEVNULL)


def dir_size(p: Path) -> float:
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) / 1e6


# --------------------------------------------------------------------------
# Linux : AppImage
# --------------------------------------------------------------------------

APPRUN = """#!/bin/sh
# Lanceur de l'AppImage KataML.
HERE="$(dirname "$(readlink -f "$0")")"
if [ -z "$KATAML_WORKSPACE" ]; then
  if [ -n "$APPIMAGE" ]; then
    # Espace de travail à côté du fichier .AppImage.
    KATAML_WORKSPACE="$(dirname "$APPIMAGE")/kataml-workspace"
  else
    KATAML_WORKSPACE="$HOME/kataml"
  fi
fi
export KATAML_WORKSPACE
unset PYTHONHOME PYTHONPATH
exec "$HERE/usr/python/bin/python3" -I -m kataml "$@"
"""

DESKTOP = """[Desktop Entry]
Type=Application
Name=KataML
Comment=Workflows de machine learning visuels avec scikit-learn
Exec=kataml
Icon=kataml
Categories=Education;Science;DataVisualization;
Terminal=false
"""


def build_linux(work: Path, cache: Path, wheel: Path, out: Path, version: str) -> tuple[Path, Path]:
    appdir = work / "KataML.AppDir"
    shutil.rmtree(appdir, ignore_errors=True)
    pyroot = python_runtime("linux", cache, appdir / "usr")
    install_packages("linux", pyroot, wheel)
    prune("linux", pyroot)
    precompile(pyroot / "bin" / "python3", "linux", pyroot)
    (appdir / "AppRun").write_text(APPRUN, encoding="utf-8")
    (appdir / "AppRun").chmod(0o755)
    (appdir / "kataml.desktop").write_text(DESKTOP, encoding="utf-8")
    shutil.copy(ROOT / "kataml" / "static" / "img" / "logo.svg", appdir / "kataml.svg")
    shutil.copy(appdir / "kataml.svg", appdir / ".DirIcon")
    log(f"AppDir : {dir_size(appdir):.0f} Mo")

    tool = fetch(APPIMAGETOOL_URL, cache / "appimagetool-x86_64.AppImage")
    tool.chmod(tool.stat().st_mode | stat.S_IEXEC)
    image = out / f"KataML-{version}-x86_64.AppImage"
    env = {**os.environ, "ARCH": "x86_64", "APPIMAGE_EXTRACT_AND_RUN": "1"}
    run([tool, "--no-appstream", appdir, image], env=env, stdout=subprocess.DEVNULL)
    log(f"→ {image.name} ({image.stat().st_size / 1e6:.0f} Mo)")
    return image, pyroot / "bin" / "python3"


# --------------------------------------------------------------------------
# Windows : zip portable
# --------------------------------------------------------------------------

LAUNCHER_BAT = r"""@echo off
REM Lance KataML. Fermez cette fenetre (ou utilisez le bouton Quitter) pour l'arreter.
title KataML
cd /d "%~dp0"
set "KATAML_WORKSPACE=%~dp0workspace"
set PYTHONHOME=
set PYTHONPATH=
"%~dp0python\python.exe" -I -m kataml %*
if errorlevel 1 pause
"""

README_WIN = """KataML {version} — version portable pour Windows (64 bits)
=============================================================

Lancement : double-cliquez sur « KataML.bat ».
Le navigateur s'ouvre sur l'interface. Pour arrêter, utilisez le bouton
« Quitter » (en haut à droite) ou fermez la fenêtre noire.

Aucune installation n'est nécessaire : Python et scikit-learn sont inclus
dans le dossier « python ». Vos données, workflows et exports sont rangés
dans le dossier « workspace », à côté de ce fichier. Le dossier complet
peut être déplacé ou copié sur une clé USB.

Au premier lancement, Windows SmartScreen peut afficher « Windows a protégé
votre ordinateur » : cliquez sur « Informations complémentaires » puis
« Exécuter quand même ».

Projet : https://gitlab.com/fredbl/kataml
"""


def build_windows(work: Path, cache: Path, wheel: Path, out: Path, version: str, host_python: Path) -> Path:
    name = f"KataML-{version}-windows-x64"
    base = work / name
    shutil.rmtree(base, ignore_errors=True)
    pyroot = python_runtime("windows", cache, base)
    install_packages("windows", pyroot, wheel)
    prune("windows", pyroot)
    precompile(host_python, "windows", pyroot)
    (base / "KataML.bat").write_bytes(LAUNCHER_BAT.replace("\n", "\r\n").encode("ascii"))
    (base / "LISEZ-MOI.txt").write_bytes(README_WIN.format(version=version).replace("\n", "\r\n").encode("utf-8-sig"))
    (base / "workspace").mkdir()
    log(f"dossier Windows : {dir_size(base):.0f} Mo")
    archive = out / f"{name}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in sorted(base.rglob("*")):
            arc = Path(name) / f.relative_to(base)
            if f.is_dir():
                if not any(f.iterdir()):
                    z.writestr(str(arc).replace(os.sep, "/") + "/", "")
                continue
            z.write(f, arc)
    log(f"→ {archive.name} ({archive.stat().st_size / 1e6:.0f} Mo)")
    return archive


# --------------------------------------------------------------------------
# Test de fumée : démarre l'AppImage et exécute un mini-workflow via l'API
# --------------------------------------------------------------------------

def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def smoke_test(image: Path, work: Path):
    port = free_port()
    ws = work / "smoke-workspace"
    shutil.rmtree(ws, ignore_errors=True)
    env = {**os.environ, "APPIMAGE_EXTRACT_AND_RUN": "1", "KATAML_WORKSPACE": str(ws)}
    log(f"test de fumée sur le port {port}")
    proc = subprocess.Popen([str(image), "--no-browser", "--port", str(port)], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    base = f"http://127.0.0.1:{port}"
    try:
        token = None
        for _ in range(120):
            time.sleep(1)
            if proc.poll() is not None:
                raise RuntimeError("KataML s'est arrêté :\n" + proc.stdout.read())
            try:
                html = urllib.request.urlopen(base + "/", timeout=2).read().decode()
                token = re.search(r'name="kataml-token" content="([^"]+)"', html).group(1)
                break
            except OSError:
                continue
        if not token:
            raise RuntimeError("le serveur ne répond pas")

        def api(path, body=None):
            req = urllib.request.Request(base + "/api/" + path, data=json.dumps(body or {}).encode(),
                                         headers={"X-KataML-Token": token, "Content-Type": "application/json"})
            return json.loads(urllib.request.urlopen(req, timeout=120).read())

        wf = {"nodes": [
            {"id": "a", "type": "io.dataset", "params": {"dataset": "iris"}},
            {"id": "b", "type": "sk.classifier.RandomForestClassifier", "params": {"target": "species"}},
            {"id": "c", "type": "apply.predictor", "params": {}},
            {"id": "d", "type": "score.classification", "params": {}},
        ], "edges": [
            {"from": "a", "fromPort": 0, "to": "b", "toPort": 0},
            {"from": "b", "fromPort": 0, "to": "c", "toPort": 0},
            {"from": "a", "fromPort": 0, "to": "c", "toPort": 1},
            {"from": "c", "fromPort": 0, "to": "d", "toPort": 0},
        ]}
        res = api("execute", {"workflow": wf, "node": "d"})
        if not res.get("ok"):
            raise RuntimeError(f"échec du workflow : {res}")
        examples = api("workflows")["examples"]
        if not api("report", {"workflow": {**wf, "name": "fumée"}, "options": {}}).get("name"):
            raise RuntimeError("la génération de rapport a échoué")
        # Annulation : un calcul long est interrompu (processus de calcul relancé).
        import threading
        slow = {"nodes": wf["nodes"][:1] + [{"id": "s", "type": "manip.python",
                                             "params": {"code": "import time\ntime.sleep(60)\nout = df"}}],
                "edges": [{"from": "a", "fromPort": 0, "to": "s", "toPort": 0}]}
        box = {}
        th = threading.Thread(target=lambda: box.update(r=api("execute", {"workflow": slow, "node": "s"})))
        th.start()
        time.sleep(2)
        if not api("cancel")["ok"]:
            raise RuntimeError("l'annulation n'a pas été prise en compte")
        th.join(30)
        if not box.get("r", {}).get("cancelled"):
            raise RuntimeError(f"annulation inattendue : {box}")
        if api("status", {"workflow": wf})["states"]["d"]["state"] != "executed":
            raise RuntimeError("le cache n'a pas été relu après l'annulation")
        api("shutdown")
        proc.wait(timeout=20)
        if not (ws / "data" / "clients.csv").exists():
            raise RuntimeError("les données d'exemple n'ont pas été copiées dans l'espace de travail")
        log(f"test de fumée réussi ({len(examples)} exemples, workflow exécuté, annulation vérifiée)")
    finally:
        if proc.poll() is None:
            proc.kill()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--target", choices=["linux", "windows", "all"], default="all")
    ap.add_argument("--out", type=Path, default=ROOT / "dist")
    ap.add_argument("--work", type=Path, default=ROOT / "build")
    ap.add_argument("--cache", type=Path, default=ROOT / ".build-cache")
    ap.add_argument("--smoke-test", action="store_true", help="démarre l'AppImage et exécute un workflow")
    args = ap.parse_args()

    if not shutil.which("uv"):
        sys.exit("uv est requis : https://docs.astral.sh/uv/")
    version = project_version()
    args.out.mkdir(parents=True, exist_ok=True)
    args.work.mkdir(parents=True, exist_ok=True)
    log(f"KataML {version} · Python {PYTHON_VERSION} (python-build-standalone {PBS_RELEASE})")
    wheel = build_wheel(args.work)

    # Le Python Linux sert aussi à précompiler la version Windows (même version mineure).
    host_python = None
    if args.target in ("linux", "all"):
        image, host_python = build_linux(args.work, args.cache, wheel, args.out, version)
        if args.smoke_test:
            smoke_test(image, args.work)
    if args.target in ("windows", "all"):
        if host_python is None:
            host_python = python_runtime("linux", args.cache, args.work / "host") / "bin" / "python3"
        build_windows(args.work, args.cache, wheel, args.out, version, host_python)

    for f in sorted(args.out.iterdir()):
        log(f"dist/{f.name}  {f.stat().st_size / 1e6:.0f} Mo")


if __name__ == "__main__":
    main()
