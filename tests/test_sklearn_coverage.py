"""Couverture de scikit-learn : chaque estimateur est un nœud, ou une absence justifiée."""

import json
import subprocess
import sys
import tempfile
import unittest
import warnings
from pathlib import Path

from sklearn.utils.discovery import all_estimators

from kataml import sk_catalog
from kataml.engine import Engine
from kataml.export import export_python
from kataml.nodes import REGISTRY

N = lambda i, t, **p: {"id": i, "type": t, "params": p, "x": 0, "y": 0, "label": ""}  # noqa: E731
E = lambda a, ap, b, bp: {"from": a, "fromPort": ap, "to": b, "toPort": bp}  # noqa: E731


class Coverage(unittest.TestCase):
    def test_every_estimator_is_covered(self):
        names = {t.split(".")[-1] for t in REGISTRY}
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            missing = [n for n, _ in all_estimators() if n not in names and n not in sk_catalog.NOT_AS_NODES]
        self.assertEqual(missing, [], "Estimateurs ni disponibles ni justifiés")

    def test_new_families_run_and_export(self):
        ws = Path(tempfile.mkdtemp(prefix="kataml-cov-"))
        wf = {"nodes": [
            N("d", "io.dataset", dataset="iris"), N("g", "manip.expression", name="groupe", expr="index % 10"),
            N("p", "manip.partition", stratify="species"),
            N("iso", "sk.outlier.IsolationForest", random_state="0"),
            N("lof", "sk.outlier.LocalOutlierFactor", novelty=True), N("predo", "apply.predictor"),
            N("gmm", "sk.cluster.GaussianMixture", n_components="3", random_state="0"),
            N("cov", "sk.covariance.LedoitWolf"), N("kde", "sk.density.KernelDensity"),
            N("nn", "sk.neighbors.NearestNeighbors", n_neighbors="3"),
            N("mds", "sk.transformer.MDS", n_components="2", random_state="0", target="species"),
            N("isot", "sk.regressor.IsotonicRegression", target="petal width (cm)", features=["petal length (cm)"]),
            N("tree", "sk.classifier.DecisionTreeClassifier", target="species", max_depth="3"),
            N("bag", "sk.classifier.BaggingClassifier", target="species", n_estimators="10", random_state="0"),
            N("w", "sk.classifier.LogisticRegression", target="species", sample_weight="sepal width (cm)", max_iter="500"),
            N("cvg", "tune.cross_validation", cv_strategy="group", groups="groupe"),
            N("cvt", "tune.cross_validation", cv_strategy="time_series", cv=4),
            N("cmp", "tune.compare", cv_strategy="repeated_stratified", cv=3, n_repeats=2),
            N("oof", "tune.cross_val_predict"), N("sc", "score.classification"),
            N("perm", "tune.permutation_test", n_permutations=15),
            N("lin", "io.dataset", dataset="linnerud"),
            N("rid", "sk.regressor.Ridge", target="Weight", features=["Chins", "Situps", "Jumps"]),
            N("mo", "meta.MultiOutputRegressor", targets=["Weight", "Waist", "Pulse"]),
            N("pmo", "apply.predictor"),
        ], "edges": [
            E("d", 0, "g", 0), E("g", 0, "p", 0), E("p", 0, "iso", 0), E("p", 0, "lof", 0), E("lof", 1, "predo", 0),
            E("p", 1, "predo", 1), E("p", 0, "gmm", 0), E("p", 0, "cov", 0), E("p", 0, "kde", 0), E("p", 0, "nn", 0),
            E("p", 0, "mds", 0), E("p", 0, "isot", 0), E("p", 0, "tree", 0), E("p", 0, "bag", 0), E("tree", 0, "bag", 1),
            E("p", 0, "w", 0), E("tree", 0, "cvg", 0), E("p", 0, "cvg", 1), E("tree", 0, "cvt", 0), E("p", 0, "cvt", 1),
            E("p", 0, "cmp", 0), E("tree", 0, "cmp", 1), E("bag", 0, "cmp", 2),
            E("bag", 0, "oof", 0), E("p", 0, "oof", 1), E("oof", 0, "sc", 0), E("tree", 0, "perm", 0), E("p", 0, "perm", 1),
            E("lin", 0, "rid", 0), E("lin", 0, "mo", 0), E("rid", 0, "mo", 1), E("mo", 0, "pmo", 0), E("lin", 0, "pmo", 1),
        ]}
        e = Engine(ws)
        for n in wf["nodes"]:
            ok, err, _ = e.execute(wf, n["id"])
            self.assertTrue(ok, f"{n['id']} ({n['type']}) : {err}")
        self.assertIn("Anomalie", e.result("iso").outputs[0].columns)
        self.assertIn("Prediction (Pulse)", e.result("pmo").outputs[0].columns)
        script = ws / "t.py"
        script.write_text(export_python(wf, "t"), encoding="utf-8")
        proc = subprocess.run([sys.executable, str(script)], cwd=ws, capture_output=True, text=True, timeout=300)
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])


if __name__ == "__main__":
    unittest.main()
