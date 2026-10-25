"""Calcul sur plusieurs cœurs et prédictions hors pli sans double entraînement.

Lancement : uv run python -m unittest tests.test_performance -v
"""

import os
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd
from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.svm import SVC

from kataml import nodes


class Cores(unittest.TestCase):
    def test_setting(self):
        with mock.patch.dict(os.environ, {"KATAML_N_JOBS": "-1"}):
            self.assertEqual(nodes.n_jobs(50_000), -1)
            self.assertIsNone(nodes.n_jobs(500))              # petit jeu : un seul cœur
        with mock.patch.dict(os.environ, {"KATAML_N_JOBS": "1"}):
            self.assertIsNone(nodes.n_jobs(50_000))
        with mock.patch.dict(os.environ, {"KATAML_N_JOBS": "4"}):
            self.assertEqual(nodes.n_jobs(50_000), 4)

    def test_argmax_models(self):
        self.assertTrue(nodes._argmax_predicts(RandomForestClassifier()))
        self.assertFalse(nodes._argmax_predicts(SVC(probability=True)))   # predict ≠ argmax(proba)

    def test_out_of_fold_predictions_unchanged(self):
        X, y = make_classification(n_samples=12_000, n_features=8, random_state=0)
        df = pd.DataFrame(X, columns=[f"x{i}" for i in range(8)])
        df["y"] = np.where(y == 1, "oui", "non")
        est = RandomForestClassifier(n_estimators=20, random_state=0)
        model = nodes.ModelPort(est.fit(df.drop(columns="y"), df["y"]), "classifier", "RandomForestClassifier",
                                list(df.columns[:-1]), "y", classes=list(est.classes_))
        ctx = nodes.Ctx([model, df], Path("."), "test")
        wf_out = nodes.REGISTRY["tune.cross_val_predict"].run(
            ctx, {"cv_strategy": "stratified", "cv": 3, "shuffle": True, "random_state": 0, "proba": True})[0]
        cv = StratifiedKFold(3, shuffle=True, random_state=0)
        ref = cross_val_predict(RandomForestClassifier(n_estimators=20, random_state=0), df.drop(columns="y"), df["y"], cv=cv)
        self.assertTrue((wf_out["Prediction (y)"].to_numpy() == ref).all())


if __name__ == "__main__":
    unittest.main()
