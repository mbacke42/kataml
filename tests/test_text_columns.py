"""Encodeurs et colonnes texte : TargetEncoder, OneHotEncoder, StandardScaler sans sélection.

Lancement : uv run python -m unittest tests.test_text_columns -v
"""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from kataml.engine import Engine
from kataml.export import export_python


class TextColumns(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="kataml-text-"))
        (cls.tmp / "data").mkdir()
        rng = np.random.default_rng(0)
        n = 600
        pd.DataFrame({
            "ORIGIN": rng.choice(["ATL", "JFK", "LAX", "ORD"], n), "DEST": rng.choice(["SFO", "DEN"], n),
            "CARRIER": rng.choice(["AA", "DL", "UA"], n), "DISTANCE": rng.integers(100, 3000, n),
            "RETARD_15": rng.integers(0, 2, n),
        }).to_csv(cls.tmp / "data" / "vols.csv", index=False)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def wf(self, *nodes):
        reader = {"id": "r", "type": "io.csv_reader", "params": {"path": "vols.csv"}}
        nodes = [reader, *nodes]
        edges = [{"from": a["id"], "fromPort": 0, "to": b["id"], "toPort": 0} for a, b in zip(nodes, nodes[1:])]
        return {"name": "test", "nodes": nodes, "edges": edges}

    def run_all(self, wf):
        engine = Engine(self.tmp)
        results = [engine.execute(wf, n["id"]) for n in wf["nodes"]]
        return engine, results

    def test_target_encoder_needs_target(self):
        wf = self.wf({"id": "t", "type": "sk.transformer.TargetEncoder", "params": {}})
        _, res = self.run_all(wf)
        ok, err, _ = res[-1]
        self.assertFalse(ok)
        self.assertIn("Cible", err)

    def test_encoders_and_scaler_choose_their_columns(self):
        wf = self.wf(
            {"id": "t", "type": "sk.transformer.TargetEncoder", "params": {"columns": ["ORIGIN", "DEST"], "target": "RETARD_15"}},
            {"id": "o", "type": "sk.transformer.OneHotEncoder", "params": {"target": "RETARD_15"}},      # vide = texte
            {"id": "s", "type": "sk.transformer.StandardScaler", "params": {"target": "RETARD_15"}},    # vide = numérique
            {"id": "m", "type": "sk.classifier.LogisticRegression", "params": {"target": "RETARD_15"}},
        )
        engine, res = self.run_all(wf)
        for n, (ok, err, _) in zip(wf["nodes"], res):
            self.assertTrue(ok, f"{n['id']} : {err}")
        script = self.tmp / "vols_text.py"
        script.write_text(export_python(wf, "vols_text"), encoding="utf-8")
        proc = subprocess.run([sys.executable, str(script)], cwd=self.tmp / "data", capture_output=True, text=True, timeout=300)
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])

    def test_no_text_column(self):
        wf = self.wf({"id": "d", "type": "manip.column_filter", "params": {"columns": ["DISTANCE", "RETARD_15"]}},
                     {"id": "o", "type": "sk.transformer.OneHotEncoder", "params": {"target": "RETARD_15"}})
        _, res = self.run_all(wf)
        ok, err, _ = res[-1]
        self.assertFalse(ok)
        self.assertIn("Aucune colonne texte", err)


if __name__ == "__main__":
    unittest.main()
