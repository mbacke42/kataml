"""Tests de bout en bout : exécution des exemples et de l'export Python.

Lancement : uv run python -m unittest discover tests
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from kataml.engine import Engine
from kataml.export import export_notebook, export_python
from kataml.nodes import REGISTRY

EXAMPLES = Path(__file__).resolve().parents[1] / "kataml" / "examples"


class ExampleWorkflows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="kataml-test-"))
        (cls.tmp / "data").mkdir()
        for f in (EXAMPLES / "data").glob("*"):
            shutil.copy(f, cls.tmp / "data" / f.name)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_examples_execute_and_export(self):
        files = sorted(EXAMPLES.glob("*.json"))
        self.assertGreaterEqual(len(files), 5)
        for f in files:
            with self.subTest(example=f.stem):
                wf = json.loads(f.read_text(encoding="utf-8"))
                for n in wf["nodes"]:
                    self.assertIn(n["type"], REGISTRY, n["type"])
                engine = Engine(self.tmp)
                for n in wf["nodes"]:
                    ok, err, _ = engine.execute(wf, n["id"])
                    self.assertTrue(ok, f"{n['id']} ({n['type']}) : {err}")
                status = engine.status(wf)
                self.assertTrue(all(s["state"] == "executed" for s in status.values()))
                script = self.tmp / f"{f.stem}.py"
                script.write_text(export_python(wf, f.stem), encoding="utf-8")
                proc = subprocess.run([sys.executable, str(script)], cwd=self.tmp / "data",
                                      capture_output=True, text=True, timeout=300)
                self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])

    def test_cache_and_invalidation(self):
        wf = {"nodes": [{"id": "a", "type": "io.dataset", "params": {"dataset": "wine"}},
                        {"id": "b", "type": "manip.sampling", "params": {"frac": 0.5}}],
              "edges": [{"from": "a", "fromPort": 0, "to": "b", "toPort": 0}]}
        e = Engine(self.tmp)
        self.assertTrue(e.execute(wf, "b")[0])
        self.assertEqual(e.status(wf)["b"]["state"], "executed")
        wf["nodes"][1]["params"]["frac"] = 0.2
        st = e.status(wf)
        self.assertEqual(st["a"]["state"], "executed")
        self.assertEqual(st["b"]["state"], "idle")

    def test_errors_are_reported(self):
        wf = {"nodes": [{"id": "a", "type": "io.dataset", "params": {"dataset": "iris"}},
                        {"id": "b", "type": "sk.classifier.LogisticRegression", "params": {"target": "absente"}}],
              "edges": [{"from": "a", "fromPort": 0, "to": "b", "toPort": 0}]}
        ok, err, states = Engine(self.tmp).execute(wf, "b")
        self.assertFalse(ok)
        self.assertIn("absente", err)
        self.assertEqual(states["b"]["state"], "error")

    def test_string_features_give_helpful_message(self):
        wf = {"nodes": [{"id": "a", "type": "io.dataset", "params": {"dataset": "iris"}},
                        {"id": "b", "type": "sk.regressor.LinearRegression", "params": {"target": "sepal length (cm)"}}],
              "edges": [{"from": "a", "fromPort": 0, "to": "b", "toPort": 0}]}
        ok, err, _ = Engine(self.tmp).execute(wf, "b")
        self.assertFalse(ok)
        self.assertIn("OneHotEncoder", err)


if __name__ == "__main__":
    unittest.main()
