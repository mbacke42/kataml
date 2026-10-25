"""Extensions fournies : activation (case à cocher) et exécution des blocs d'analyse exploratoire."""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from kataml import extension
from kataml.engine import Engine
from kataml.export import export_python
from kataml.nodes import REGISTRY

N = lambda i, t, **p: {"id": i, "type": t, "params": p, "x": 0, "y": 0, "label": ""}  # noqa: E731
E = lambda a, ap, b, bp: {"from": a, "fromPort": ap, "to": b, "toPort": bp}  # noqa: E731


class BundledExtensions(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp(prefix="kataml-eda-"))
        (self.ws / "data").mkdir()

    def tearDown(self):
        extension._unload_bundled("eda")        # ne pas laisser fuiter entre les tests
        shutil.rmtree(self.ws, ignore_errors=True)

    def run_all(self, wf):
        e = Engine(self.ws)
        for n in wf["nodes"]:
            ok, err, _ = e.execute(wf, n["id"])
            self.assertTrue(ok, f"{n['id']} ({n['type']}) : {err}")
        return e

    def test_toggle_enables_disables_and_persists(self):
        self.assertNotIn("ext.eda.overview", REGISTRY)           # désactivé par défaut
        extension.set_bundled(self.ws, "eda", True)
        self.assertIn("ext.eda.overview", REGISTRY)
        self.assertEqual(REGISTRY["ext.eda.overview"].extension, "eda")  # marqué extension (exclu du test i18n)
        self.assertTrue(json.loads((self.ws / "extensions.json").read_text())["bundled"]["eda"])
        state = {b["key"]: b for b in extension.list_bundled(self.ws)}
        self.assertTrue(state["eda"]["enabled"] and state["eda"]["loaded"])
        self.assertFalse(state["exemple"]["enabled"])
        extension.set_bundled(self.ws, "eda", False)
        self.assertNotIn("ext.eda.overview", REGISTRY)
        self.assertFalse(json.loads((self.ws / "extensions.json").read_text())["bundled"]["eda"])

    def test_load_extensions_respects_saved_state(self):
        (self.ws / "extensions.json").write_text('{"bundled": {"eda": true}}', encoding="utf-8")
        extension.load_extensions(self.ws)
        self.assertIn("ext.eda.target", REGISTRY)

    def test_blocks_on_iris(self):
        extension.set_bundled(self.ws, "eda", True)
        wf = {"nodes": [
            N("d", "io.dataset", dataset="iris"),
            N("ov", "ext.eda.overview"), N("fr", "ext.eda.frequencies", column="species"),
            N("tg", "ext.eda.target", target="species"), N("di", "ext.eda.distributions"),
            N("ou", "ext.eda.outliers"),
        ], "edges": [E("d", 0, "ov", 0), E("d", 0, "fr", 0), E("d", 0, "tg", 0),
                     E("d", 0, "di", 0), E("d", 0, "ou", 0)]}
        e = self.run_all(wf)
        self.assertEqual(len(e.result("ov").outputs[0]), 5)
        self.assertEqual(set(e.result("fr").outputs[0]["effectif"]), {50})
        self.assertEqual(e.result("tg").outputs[0].iloc[0]["variable"], "petal length (cm)")
        self.assertEqual(len(e.result("di").outputs[0]), 4)
        self.assertEqual(len(e.result("ou").outputs[0]), 4)

    def test_missing_and_outliers_on_dirty_data(self):
        extension.set_bundled(self.ws, "eda", True)
        rng = np.random.default_rng(0)
        df = pd.DataFrame({"age": rng.integers(18, 70, 60).astype(float),
                           "ville": rng.choice(["Paris", "Lyon", "Nice"], 60),
                           "revenu": rng.normal(2000, 500, 60)})
        df.loc[rng.choice(60, 10, replace=False), "age"] = np.nan
        df.loc[0, "revenu"] = 99999.0
        df.to_csv(self.ws / "data" / "clients.csv", index=False)
        wf = {"nodes": [
            N("c", "io.csv_reader", path="clients.csv"),
            N("ms", "ext.eda.missing"), N("ou", "ext.eda.outliers", columns=["revenu"]),
        ], "edges": [E("c", 0, "ms", 0), E("c", 0, "ou", 0)]}
        e = self.run_all(wf)
        self.assertEqual(int(e.result("ms").outputs[0].set_index("colonne").loc["age", "manquants"]), 10)
        self.assertGreaterEqual(int(e.result("ou").outputs[0].set_index("variable").loc["revenu", "nb_extrêmes"]), 1)

    def test_export_runs(self):
        extension.set_bundled(self.ws, "eda", True)
        wf = {"nodes": [
            N("d", "io.dataset", dataset="iris"),
            N("ov", "ext.eda.overview"), N("fr", "ext.eda.frequencies", column="species"),
            N("di", "ext.eda.distributions"), N("ou", "ext.eda.outliers"), N("ms", "ext.eda.missing"),
        ], "edges": [E("d", 0, "ov", 0), E("d", 0, "fr", 0), E("d", 0, "di", 0),
                     E("d", 0, "ou", 0), E("d", 0, "ms", 0)]}
        self.run_all(wf)
        import subprocess
        script = self.ws / "t.py"
        script.write_text(export_python(wf, "t"), encoding="utf-8")
        proc = subprocess.run([sys.executable, str(script)], cwd=self.ws, capture_output=True, text=True, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])


if __name__ == "__main__":
    unittest.main()
