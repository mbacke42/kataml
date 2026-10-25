#!/usr/bin/env python3
"""Captures d'écran de la documentation, générées automatiquement (Playwright).

Démarre KataML sur un espace de travail temporaire, rejoue des scénarios dans
Chromium sans interface, en français puis en anglais, et enregistre les images
dans docs/assets/screenshots/<langue>/.

Usage :
    uv run --group docs python tools/screenshots.py [--lang fr|en|all] [--only nom,…]

Prérequis : uv run --group docs playwright install chromium
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets" / "screenshots"
EXAMPLES = ROOT / "kataml" / "examples"
VIEWPORT = {"width": 1600, "height": 1000}


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_server(workspace: Path) -> tuple[subprocess.Popen, str]:
    port = free_port()
    env = {**os.environ, "KATAML_WORKSPACE": str(workspace)}
    proc = subprocess.Popen([sys.executable, "-m", "kataml", "--no-browser", "--port", str(port)],
                            cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}/"
    for _ in range(120):
        time.sleep(0.5)
        try:
            urllib.request.urlopen(url, timeout=2)
            return proc, url
        except OSError:
            continue
    proc.kill()
    raise RuntimeError("KataML ne démarre pas")


class Shooter:
    def __init__(self, page, url: str, lang: str):
        self.page, self.url, self.lang = page, url, lang
        self.out = OUT / lang
        self.out.mkdir(parents=True, exist_ok=True)

    # -- utilitaires --------------------------------------------------------
    def T(self, fr: str, en: str) -> str:
        return en if self.lang == "en" else fr

    def load(self, example: str | None = None, workflow: dict | None = None):
        """Charge un exemple (ou un workflow) via la sauvegarde automatique du navigateur."""
        wf = workflow or json.loads((EXAMPLES / f"{example}.json").read_text(encoding="utf-8"))
        state = {"wf": wf, "savedName": None}
        self.page.goto(self.url)
        self.page.evaluate("""([lang, state]) => {
            localStorage.clear();
            localStorage.setItem('kataml.lang', lang);
            localStorage.setItem('kataml.theme', 'light');
            localStorage.setItem('kataml.autosave', JSON.stringify(state));
        }""", [self.lang, state])
        self.page.reload()
        self.page.wait_for_selector("#repo-tree .repo-item")
        self.page.wait_for_timeout(600)

    def run_all(self):
        self.page.click('[data-action="run-all"]')
        try:
            self.page.wait_for_function("() => document.querySelector('[data-action=\"run-all\"]').disabled", timeout=3000)
        except Exception:
            pass                       # déjà terminé (résultats en cache)
        self.page.wait_for_function("() => !document.querySelector('[data-action=\"run-all\"]').disabled", timeout=240000)
        self.page.wait_for_timeout(1200)

    def fit(self):
        self.page.click('[data-action="fit"]')
        self.page.wait_for_timeout(300)

    def select(self, node_id: str, wait=900):
        self.page.click(f'#nodes .node[data-id="{node_id}"] .title')
        self.page.wait_for_timeout(wait)

    def tab(self, index_or_text):
        tabs = self.page.locator("#out-tabs .tab")
        if isinstance(index_or_text, int):
            tabs.nth(index_or_text).click()
        else:
            tabs.filter(has_text=index_or_text).first.click()
        self.page.wait_for_timeout(700)

    def bottom(self, height: int):
        self.page.evaluate(f"document.documentElement.style.setProperty('--bottom-h', '{height}px')")
        self.page.wait_for_timeout(300)

    def shot(self, name: str, selector: str | None = None, clip: dict | None = None, full=False):
        path = self.out / f"{name}.png"
        if selector:
            self.page.locator(selector).first.screenshot(path=str(path))
        else:
            self.page.screenshot(path=str(path), clip=clip, full_page=full)
        print(f"  {self.lang}/{name}.png")

    def close_modal(self):
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(200)

    # -- scénarios ----------------------------------------------------------
    def interface(self):
        self.load("01_classification_iris")
        self.run_all()
        self.bottom(330)
        self.fit()
        self.select("n9", wait=1500)
        self.shot("interface-overview")
        self.shot("toolbar", ".topbar")
        self.shot("repository-guide", "#repo")
        self.page.click('[data-repo-mode="api"]')
        self.page.wait_for_timeout(300)
        self.shot("repository-api", "#repo")
        self.page.click('[data-repo-mode="guide"]')
        self.page.fill("#repo-search", self.T("forêt", "forest"))
        self.page.wait_for_timeout(300)
        self.shot("repository-search", "#repo")
        self.page.fill("#repo-search", "")
        # Inspecteur
        self.select("n7")
        self.shot("inspector-config", "#inspector")
        self.page.locator(".insp-tabs button").nth(1).click()
        self.page.wait_for_timeout(300)
        self.shot("inspector-description", "#inspector")
        self.page.locator(".insp-tabs button").nth(0).click()
        # Panneau des sorties
        self.bottom(420)
        self.select("n9")
        self.shot("outputs-view", "#bottom")
        self.select("n8")
        self.tab(0)
        self.shot("outputs-table", "#bottom")
        self.page.locator(".seg button").nth(1).click()
        self.page.wait_for_timeout(700)
        self.shot("outputs-profile", "#bottom")
        self.page.locator(".seg button").nth(0).click()
        self.select("n7")
        self.tab(1)
        self.shot("outputs-model", "#bottom")
        self.bottom(300)
        # Canevas : menu contextuel, ajout rapide
        box = self.page.locator('#nodes .node[data-id="n7"]').bounding_box()
        self.page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 3, button="right")
        self.page.wait_for_timeout(300)
        self.shot("context-menu", clip={"x": box["x"] - 20, "y": box["y"] - 10, "width": 560, "height": 520})
        self.page.keyboard.press("Escape")
        self.page.mouse.click(5, 5)
        wrap = self.page.locator("#canvas-wrap").bounding_box()
        self.page.mouse.dblclick(wrap["x"] + 120, wrap["y"] + wrap["height"] - 260)
        self.page.keyboard.type(self.T("arbre", "tree"))
        self.page.wait_for_timeout(300)
        self.shot("quick-add", clip={"x": wrap["x"] + 90, "y": wrap["y"] + wrap["height"] - 290, "width": 360, "height": 360})
        self.page.keyboard.press("Escape")

    def node_states(self):
        wf = {"name": self.T("États des nœuds", "Node states"), "nodes": [
            {"id": "a", "type": "io.dataset", "x": 0, "y": 0, "label": "", "params": {"dataset": "iris"}},
            {"id": "b", "type": "manip.partition", "x": 250, "y": 0, "label": "", "params": {"stratify": "species"}},
            {"id": "c", "type": "sk.classifier.LogisticRegression", "x": 500, "y": -70, "label": "", "params": {"target": "species"}},
            {"id": "d", "type": "sk.classifier.DecisionTreeClassifier", "x": 500, "y": 40, "label": "", "params": {}},
            {"id": "e", "type": "sk.regressor.Ridge", "x": 500, "y": 150, "label": "", "params": {"target": "species"}},
        ], "edges": [{"from": "a", "fromPort": 0, "to": "b", "toPort": 0}, {"from": "b", "fromPort": 0, "to": "c", "toPort": 0},
                     {"from": "b", "fromPort": 0, "to": "d", "toPort": 0}, {"from": "b", "fromPort": 0, "to": "e", "toPort": 0}],
            "annotations": [], "groups": []}
        self.load(workflow=wf)
        self.select("c")
        self.page.keyboard.press("F7")
        self.page.wait_for_timeout(2500)
        self.select("e")
        self.page.keyboard.press("F7")
        self.page.wait_for_timeout(2500)
        self.page.mouse.click(5, 5)
        self.fit()
        self.page.evaluate("document.querySelectorAll('.node.selected').forEach(n => n.classList.remove('selected'))")
        self.shot("node-states", "#canvas-wrap")

    def components(self):
        self.load("06_frontiere_decision")
        self.fit()
        for i, nid in enumerate(("m1", "m2", "m3", "m4")):
            self.page.click(f'#nodes .node[data-id="{nid}"] .title', modifiers=["Shift"] if i else [])
        self.page.keyboard.press("Control+g")
        self.page.fill("#modal input", self.T("Quatre modèles", "Four models"))
        self.page.locator("#modal .btn.primary").click()
        self.page.wait_for_timeout(500)
        self.fit()
        self.shot("component-collapsed", "#canvas-wrap")
        self.shot("component-inspector", "#inspector")
        self.page.dblclick("#nodes .group-node")
        self.page.wait_for_timeout(400)
        self.fit()
        self.shot("component-expanded", "#canvas-wrap")

    def pipeline(self):
        self.load("04_csv_pretraitement")
        self.run_all()
        self.fit()
        self.shot("pipeline-workflow", "#canvas-wrap")
        self.bottom(460)
        self.select("p1")
        self.shot("pipeline-view", "#bottom")
        # Validation croisée branchée sur un modèle entraîné sur une table normalisée :
        # l'inspecteur propose de créer le Pipeline, qui apparaît contracté.
        N = lambda i, t, x, **p: {"id": i, "type": t, "x": x, "y": 100, "params": p,
                                  "label": self.T(*{"s": ("Normalisation", "Scaling"), "k": ("15 voisins", "15 neighbours")}[i]) if i in "sk" else ""}
        E = lambda a, ap, b, bp: {"from": a, "fromPort": ap, "to": b, "toPort": bp}
        wf = {"name": self.T("Validation croisée", "Cross-validation"), "nodes": [
            N("d", "io.dataset", 0, dataset="iris"),
            N("s", "sk.transformer.StandardScaler", 260, target="species"),
            N("k", "sk.classifier.KNeighborsClassifier", 520, target="species", n_neighbors="15"),
            N("cv", "tune.cross_validation", 780)],
            "edges": [E("d", 0, "s", 0), E("s", 0, "k", 0), E("k", 0, "cv", 0), E("s", 0, "cv", 1)]}
        self.load(workflow=wf)
        self.fit()
        self.select("cv")
        self.shot("cv-hint", ".insp-head")
        self.page.locator(".insp-hint button").click()
        self.page.wait_for_timeout(600)
        self.run_all()
        self.fit()
        self.shot("pipeline-contracted", "#canvas-wrap")

    def dialogs(self):
        self.load("01_classification_iris")
        self.run_all()
        self.page.click('[data-action="open"]')
        self.page.wait_for_selector("#modal .wf-item")
        self.page.wait_for_timeout(300)
        self.shot("dialog-open", "#modal")
        self.close_modal()
        self.page.click('[data-action="export-py"]')
        self.page.wait_for_selector("#modal pre.code")
        self.shot("dialog-export", "#modal")
        self.close_modal()
        self.page.click('[data-action="report"]')
        self.page.wait_for_selector("#modal .rep-node")
        self.shot("dialog-report", "#modal")
        self.page.locator("#modal .btn.primary").click()
        self.page.wait_for_selector("#modal a.btn.primary", timeout=120000)
        href = self.page.locator("#modal a.btn.primary").get_attribute("href")
        self.close_modal()
        report = self.page.context.new_page()
        report.set_viewport_size({"width": 1100, "height": 1400})
        report.goto(self.url.rstrip("/") + href)
        report.wait_for_timeout(1500)
        report.screenshot(path=str(self.out / "report-page.png"))
        print(f"  {self.lang}/report-page.png")
        report.close()
        self.page.click('[data-action="help"]')
        self.page.wait_for_timeout(300)
        self.shot("dialog-help", "#modal")
        self.close_modal()

    def appearance(self):
        self.load("01_classification_iris")
        self.run_all()
        self.select("n9")
        self.page.click('[data-action="appearance"]')
        self.page.wait_for_selector("#modal .swatches")
        self.page.wait_for_timeout(200)
        self.shot("dialog-theme", "#modal")
        # Exemple de personnalisation : bleu, mode sombre, grille.
        self.page.locator("#modal .swatch").nth(2).click()
        self.page.locator("#modal .seg").nth(0).locator("button").nth(2).click()
        self.page.locator("#modal .seg").nth(1).locator("button").nth(1).click()
        self.close_modal()
        self.page.wait_for_timeout(300)
        self.shot("theme-custom")
        self.page.evaluate("localStorage.removeItem('kataml.theme')")

    def blocks(self):
        self.load("01_classification_iris")
        self.page.click('[data-action="blocks"]')
        self.page.wait_for_timeout(400)
        self.page.locator("#modal .btn.primary").click()          # Nouveau bloc
        self.page.wait_for_timeout(300)
        self.page.fill("#modal input", self.T("Écrêtage des extrêmes", "Clip extremes"))
        self.shot("blocks-new", "#modal")
        self.page.locator("#modal .btn.primary").click()          # Créer
        self.page.wait_for_selector("#modal textarea.code-editor", timeout=30000)
        self.page.wait_for_timeout(500)
        self.shot("blocks-editor", "#modal")
        self.page.locator("#modal .modal-foot .btn").first.click()   # Retour à la liste
        self.page.wait_for_timeout(500)
        self.shot("blocks-manager", "#modal")
        self.close_modal()

    def tutorials(self):
        scenes = [
            ("06_frontiere_decision", [("d1", "tuto-boundary-deep"), ("d2", "tuto-boundary-pruned"), ("v1", "tuto-validation-curve")]),
            ("10_fuite_information", [("cv1", "tuto-leak-wrong"), ("cv2", "tuto-leak-right")]),
            ("11_non_supervise", [("k", "tuto-kmeans"), ("v", "tuto-pca-clusters"), ("i", "tuto-outliers")]),
            ("12_comprendre_modele", [("im", "tuto-importance"), ("pd", "tuto-pdp"), ("tr", "tuto-tree")]),
            ("02_regression_diabete", [("n6", "tuto-compare"), ("n8", "tuto-regression-metrics")]),
            ("05_reglage_hyperparametres", [("n4", "tuto-grid"), ("n5", "tuto-learning-curve"), ("n8", "tuto-nested")]),
            ("04_csv_pretraitement", [("n2", "tuto-csv-profile"), ("n12", "tuto-csv-eval")]),
            ("07_texte_avis", [("v1", "tuto-text-tfidf"), ("c1", "tuto-text-compare")]),
            ("09_velos_dates", [("n6", "tuto-dates-pdp")]),
            ("01_classification_iris", [("n9", "tuto-iris-eval"), ("n3", "tuto-iris-scatter"), ("n11", "tuto-iris-cv")]),
        ]
        for example, shots in scenes:
            self.load(example)
            self.run_all()
            self.fit()
            self.shot(f"{example}-canvas", "#canvas-wrap")
            self.bottom(560)
            for nid, name in shots:
                self.select(nid, wait=1300)
                self.shot(name, "#bottom")
            self.bottom(300)

    SCENES = ["interface", "node_states", "components", "pipeline", "dialogs", "appearance", "blocks", "tutorials"]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lang", choices=["fr", "en", "all"], default="all")
    ap.add_argument("--only", default="", help="scénarios séparés par des virgules")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(ROOT / ".build-cache" / "ms-playwright"))
    workspace = Path(tempfile.mkdtemp(prefix="kataml-shots-"))
    proc, url = start_server(workspace)
    scenes = [s for s in args.only.split(",") if s] or Shooter.SCENES
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for lang in (["fr", "en"] if args.lang == "all" else [args.lang]):
                ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=1, color_scheme="light")
                page = ctx.new_page()
                shooter = Shooter(page, url, lang)
                print(f"[{lang}]")
                for scene in scenes:
                    getattr(shooter, scene)()
                ctx.close()
            browser.close()
    finally:
        proc.terminate()
        proc.wait(10)
        shutil.rmtree(workspace, ignore_errors=True)


if __name__ == "__main__":
    main()
