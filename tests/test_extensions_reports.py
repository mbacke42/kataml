"""Blocs personnalisés (extensions), rapports HTML et exécution en ligne de commande."""

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from kataml import extension as ext
from kataml.engine import Engine
from kataml.nodes import REGISTRY
from kataml.report import build_report

ROOT = Path(__file__).resolve().parents[1]
N = lambda i, t, x=0, **p: {"id": i, "type": t, "params": p, "x": x, "y": 0, "label": ""}  # noqa: E731
E = lambda a, ap, b, bp: {"from": a, "fromPort": ap, "to": b, "toPort": bp}  # noqa: E731


class Extensions(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp(prefix="kataml-ext-"))
        (self.ws / "extensions").mkdir()

    def tearDown(self):
        ext.reload_local_extensions(Path(tempfile.mkdtemp()))   # décharge les blocs du test
        shutil.rmtree(self.ws, ignore_errors=True)

    def test_templates_load_and_run(self):
        for kind in ("table", "two_tables", "table_model", "none"):
            fname, src = ext.block_template(f"Bloc {kind}", inputs=kind)
            (self.ws / "extensions" / fname).write_text(src)
        fname, src = ext.block_template("Converti", code="out = df.head(4)")
        (self.ws / "extensions" / fname).write_text(src)
        infos = ext.reload_local_extensions(self.ws)
        local = [x for x in infos if x["source"].startswith("fichier ")]
        self.assertEqual(len(local), 5)
        self.assertTrue(all(not x["error"] for x in local), local)
        wf = {"nodes": [N("d", "io.dataset", dataset="iris"),
                        N("b", "ext.bloc_table", colonne="sepal length (cm)", facteur=3.0),
                        N("c", "ext.converti")],
              "edges": [E("d", 0, "b", 0), E("d", 0, "c", 0)]}
        e = Engine(self.ws)
        self.assertTrue(e.execute(wf, "b")[0])
        self.assertIn("sepal length (cm)_x3", e.result("b").outputs[0].columns)
        self.assertTrue(e.execute(wf, "c")[0])
        self.assertEqual(len(e.result("c").outputs[0]), 4)

    def test_errors_reload_and_cache_invalidation(self):
        f = self.ws / "extensions" / "mon_bloc.py"
        f.write_text(ext.block_template("Mon bloc")[1])
        ext.reload_local_extensions(self.ws)
        wf = {"nodes": [N("d", "io.dataset", dataset="iris"), N("b", "ext.mon_bloc", colonne="sepal width (cm)")],
              "edges": [E("d", 0, "b", 0)]}
        e = Engine(self.ws)
        self.assertTrue(e.execute(wf, "b")[0])
        self.assertEqual(e.status(wf)["b"]["state"], "executed")
        # Code modifié : le résultat en cache n'est plus valable.
        f.write_text(f.read_text().replace("* facteur", "* facteur * 10"))
        ext.reload_local_extensions(self.ws)
        self.assertEqual(e.status(wf)["b"]["state"], "idle")
        # Fichier cassé : erreur signalée, nœud retiré, le reste fonctionne.
        f.write_text("ceci n'est pas du python")
        info = next(x for x in ext.reload_local_extensions(self.ws) if x["source"] == "fichier mon_bloc.py")
        self.assertTrue(info["error"])
        self.assertNotIn("ext.mon_bloc", REGISTRY)

    def test_cannot_override_builtin(self):
        with self.assertRaises(ValueError):
            ext.register("io.dataset", "Pirate")(lambda ctx, p: [])

    def test_sample_package(self):
        path = ROOT / "extensions" / "kataml-exemple" / "kataml_exemple" / "__init__.py"

        def loader():
            spec = importlib.util.spec_from_file_location("kataml_exemple", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module

        ext._load("paquet test", loader, {"name": "exemple"})
        try:
            wf = {"nodes": [N("d", "io.dataset", dataset="diabetes"), N("w", "ext.exemple.winsorize", low=0.05, high=0.95)],
                  "edges": [E("d", 0, "w", 0)]}
            e = Engine(self.ws)
            ok, err, _ = e.execute(wf, "w")
            self.assertTrue(ok, err)
            out = e.result("w").outputs[0]
            self.assertLessEqual(out["bmi"].max(), e.result("d").outputs[0]["bmi"].quantile(0.95) + 1e-9)
        finally:
            for t in ("ext.exemple.winsorize", "ext.exemple.frequency"):
                REGISTRY.pop(t, None)


class Reports(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp(prefix="kataml-report-"))

    def tearDown(self):
        shutil.rmtree(self.ws, ignore_errors=True)

    def workflow(self):
        return {"name": "Démo rapport", "nodes": [
            N("t", "report.text", -300, title="Introduction", text="## But\n\nClasser les **iris**."),
            N("d", "io.dataset", 0, dataset="iris"), N("p", "manip.partition", 250, stratify="species"),
            N("m", "sk.classifier.LogisticRegression", 500, target="species", max_iter="500"),
            N("pr", "apply.predictor", 750), N("sc", "score.classification", 1000)],
            "edges": [E("d", 0, "p", 0), E("p", 0, "m", 0), E("m", 0, "pr", 0), E("p", 1, "pr", 1), E("pr", 0, "sc", 0)],
            "annotations": [{"x": 0, "y": -150, "w": 300, "h": 90, "text": "Note\nTexte"}]}

    def test_build_report(self):
        wf = self.workflow()
        e = Engine(self.ws)
        for n in wf["nodes"]:
            e.execute(wf, n["id"])
        html = build_report(e, wf, {"author": "Équipe", "code": True})
        data = json.loads(html.split('id="report-data">')[1].split("</script>")[0].replace("<\\/", "</"))
        titles = [s.get("title") or s["type"] for s in data["sections"]]
        self.assertEqual(titles[0], "Introduction")            # le texte vient en premier (à gauche)
        self.assertIn("Évaluation classification", titles)
        self.assertTrue(data["diagram"].startswith("<svg"))
        self.assertIn("Pipeline", data["code"] + "LogisticRegression")
        self.assertEqual(data["author"], "Équipe")
        self.assertNotIn("import {", html)                     # bundle autonome

    def test_theme(self):
        wf = {"name": "Thème", "nodes": [N("t", "report.text", 0, title="T", text="x")], "edges": []}
        e = Engine(self.ws)
        self.assertNotIn("--accent: #123456", build_report(e, wf, {}))
        (self.ws / "theme.css").write_text(":root { --c-io: #abcdef; }", encoding="utf-8")
        html = build_report(e, wf, {"accent": "#123456"})
        self.assertIn("--c-io: #abcdef", html)                # theme.css de l'espace de travail
        self.assertIn("--accent: #123456", html)              # couleur choisie dans l'interface
        self.assertNotIn("evil", build_report(e, wf, {"accent": "red;}evil{"}))

    def test_cli_run(self):
        wf_path = self.ws / "wf.json"
        wf_path.write_text(json.dumps(self.workflow()), encoding="utf-8")
        report = self.ws / "r.html"
        proc = subprocess.run([sys.executable, "-m", "kataml", "run", str(wf_path), "--workspace", str(self.ws / "w"),
                               "--rapport", str(report), "--script", str(self.ws / "s.py")],
                              capture_output=True, text=True, timeout=300)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertTrue(report.read_text().startswith("<!doctype html>"))
        self.assertIn("Terminé", proc.stdout)
        bad = json.loads(wf_path.read_text())
        bad["nodes"][3]["params"]["target"] = "absente"
        wf_path.write_text(json.dumps(bad))
        proc = subprocess.run([sys.executable, "-m", "kataml", "run", str(wf_path), "--workspace", str(self.ws / "w"), "-q"],
                              capture_output=True, text=True, timeout=300)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("absente", proc.stdout)


if __name__ == "__main__":
    unittest.main()
