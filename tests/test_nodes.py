"""Nœuds de composition, d'explicabilité et de données (v0.2)."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from kataml.engine import Engine
from kataml.export import export_notebook

N = lambda i, t, **p: {"id": i, "type": t, "params": p, "x": 0, "y": 0, "label": ""}  # noqa: E731
E = lambda a, ap, b, bp: {"from": a, "fromPort": ap, "to": b, "toPort": bp}  # noqa: E731


class NewNodes(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp(prefix="kataml-nodes-"))
        (self.ws / "data").mkdir()

    def tearDown(self):
        shutil.rmtree(self.ws, ignore_errors=True)

    def run_all(self, wf):
        e = Engine(self.ws)
        for n in wf["nodes"]:
            ok, err, _ = e.execute(wf, n["id"])
            self.assertTrue(ok, f"{n['id']} ({n['type']}) : {err}")
        return e

    def test_composition_and_explainability(self):
        wf = {"nodes": [
            N("d", "io.dataset", dataset="iris"), N("p", "manip.partition", stratify="species"),
            N("s", "sk.transformer.StandardScaler", target="species"),
            N("lr", "sk.classifier.LogisticRegression", target="species"), N("pipe", "compose.pipeline"),
            N("pred", "apply.predictor"), N("cv", "tune.cross_validation"),
            N("rf", "sk.classifier.RandomForestClassifier", target="species", n_estimators="30"),
            N("vote", "meta.VotingClassifier", voting="soft"), N("stack", "meta.StackingClassifier"),
            N("ovr", "meta.OneVsRestClassifier"), N("rfe", "meta.RFE", n_features_to_select="2"),
            N("cmp", "tune.compare"), N("db", "explain.decision_boundary"), N("tree", "explain.tree"),
            N("vc", "tune.validation_curve", param="model__C", values="[0.1, 1, 10]"),
            N("pdp", "explain.partial_dependence"), N("cal", "score.calibration"),
            N("gs", "tune.grid_search", grid='{"model__C": [0.1, 1]}'),
        ], "edges": [
            E("d", 0, "p", 0), E("p", 0, "s", 0), E("s", 0, "lr", 0),
            E("p", 0, "pipe", 0), E("lr", 0, "pipe", 1), E("s", 1, "pipe", 2),
            E("pipe", 0, "pred", 0), E("p", 1, "pred", 1), E("pipe", 0, "cv", 0), E("p", 0, "cv", 1),
            E("p", 0, "rf", 0), E("p", 0, "vote", 0), E("rf", 0, "vote", 1), E("pipe", 0, "vote", 2),
            E("p", 0, "stack", 0), E("rf", 0, "stack", 1), E("pipe", 0, "stack", 2),
            E("p", 0, "ovr", 0), E("rf", 0, "ovr", 1), E("p", 0, "rfe", 0), E("rf", 0, "rfe", 1),
            E("p", 0, "cmp", 0), E("rf", 0, "cmp", 1), E("pipe", 0, "cmp", 2), E("vote", 0, "cmp", 3),
            E("rf", 0, "db", 0), E("p", 1, "db", 1), E("rf", 0, "tree", 0),
            E("pipe", 0, "vc", 0), E("p", 0, "vc", 1), E("pipe", 0, "pdp", 0), E("p", 1, "pdp", 1),
            E("pred", 0, "cal", 0), E("pipe", 0, "gs", 0), E("p", 0, "gs", 1),
        ]}
        e = self.run_all(wf)
        # Le Pipeline s'applique aux données brutes de test.
        pred = e.result("pred").outputs[0]
        self.assertIn("Prediction (species)", pred.columns)
        self.assertEqual(len(e.result("cmp").outputs[0]), 3)
        self.assertEqual(e.result("rfe").outputs[1].output_columns.__len__(), 3)  # 2 variables + cible
        nb = json.loads(export_notebook({**wf, "annotations": [{"text": "Titre\nTexte"}]}, "t"))
        self.assertEqual(nb["nbformat"], 4)
        self.assertGreater(len(nb["cells"]), len(wf["nodes"]))
        # Cache disque : un nouveau moteur retrouve tous les résultats.
        st = Engine(self.ws).status(wf)
        self.assertTrue(all(s["state"] == "executed" for s in st.values()))

    def test_pipeline_rejects_transformed_target(self):
        wf = {"nodes": [N("d", "io.dataset", dataset="diabetes"), N("s", "sk.transformer.StandardScaler"),
                        N("m", "sk.regressor.Ridge", target="target"), N("pipe", "compose.pipeline")],
              "edges": [E("d", 0, "s", 0), E("s", 0, "m", 0), E("d", 0, "pipe", 0), E("m", 0, "pipe", 1), E("s", 1, "pipe", 2)]}
        e = Engine(self.ws)
        ok, err, _ = e.execute(wf, "pipe")
        self.assertFalse(ok)
        self.assertIn("cible", err)

    def test_nested_cross_validation(self):
        wf = {"nodes": [N("d", "io.dataset", dataset="iris"),
                        N("m", "sk.classifier.KNeighborsClassifier", target="species"),
                        N("g", "tune.grid_search", grid='{"n_neighbors": [1, 5, 15]}', cv=3),
                        N("cv", "tune.cross_validation", cv=4)],
              "edges": [E("d", 0, "m", 0), E("m", 0, "g", 0), E("d", 0, "g", 1), E("g", 2, "cv", 0), E("d", 0, "cv", 1)]}
        e = self.run_all(wf)
        out = e.result("cv").outputs[0]
        self.assertEqual(len(out), 4)                                   # plis externes
        self.assertIn("choisi · n_neighbors", out.columns)             # réglage refait dans chaque pli
        self.assertTrue(set(out["choisi · n_neighbors"]) <= {"1", "5", "15"})
        titles = [b.get("title") for b in e.result("cv").view]
        self.assertIn("Hyperparamètres choisis dans chaque pli (validation imbriquée)", titles)
        # Recherche interne par groupes : refusée avec un message clair.
        wf["nodes"][2]["params"].update(cv_strategy="group", groups="species")
        ok, err, _ = Engine(self.ws).execute(wf, "cv")
        self.assertFalse(ok)
        self.assertIn("imbriquée", err)

    def test_transformer_on_text_column_explains(self):
        e = Engine(self.ws)
        for params, scope in (({}, "Aucune colonne n'étant choisie"), ({"columns": ["species", "sepal width (cm)"]}, "Les colonnes choisies")):
            wf = {"nodes": [N("d", "io.dataset", dataset="iris"), N("s", "sk.transformer.StandardScaler", **params)],
                  "edges": [E("d", 0, "s", 0)]}
            ok, err, _ = e.execute(wf, "s")
            self.assertFalse(ok)
            self.assertIn(scope, err)
            self.assertIn("« species »", err)
            self.assertIn("Cible", err)
            from kataml.i18n import text
            self.assertIn("“species”", text(err))
            self.assertTrue(text(err).startswith("StandardScaler only accepts numeric columns."))

    def test_text_and_dates(self):
        pd.DataFrame({
            "avis": ["très bon film", "nul et ennuyeux", None, "excellent jeu", "mauvais scénario", "bon moment"] * 10,
            "note": [1, 0, 1, 1, 0, 1] * 10,
            "date": pd.date_range("2024-01-01", periods=60, freq="37h").astype(str),
        }).to_csv(self.ws / "data" / "avis.csv", index=False)
        wf = {"nodes": [
            N("r", "io.csv_reader", path="avis.csv"),
            N("dt", "manip.dates", columns=["date"], parts=["month", "hour", "is_weekend"], cyclic=True),
            N("v", "text.TfidfVectorizer", column="avis"), N("lr", "sk.classifier.LogisticRegression", target="note"),
            N("pipe", "compose.pipeline"), N("cv", "tune.cross_validation", cv=3),
        ], "edges": [E("r", 0, "dt", 0), E("dt", 0, "v", 0), E("v", 0, "lr", 0), E("dt", 0, "pipe", 0),
                     E("lr", 0, "pipe", 1), E("v", 1, "pipe", 2), E("pipe", 0, "cv", 0), E("dt", 0, "cv", 1)]}
        e = self.run_all(wf)
        cols = e.result("dt").outputs[0].columns
        self.assertIn("date_hour_sin", cols)
        self.assertNotIn("date", cols)
        self.assertIn("bon", e.result("v").outputs[0].columns)

    def test_concordance_and_clustering_metrics(self):
        wf = {"nodes": [
            N("d", "io.dataset", dataset="iris"),
            N("km", "sk.cluster.KMeans", n_clusters="3", random_state="0", n_init="10"),
            N("conc", "score.concordance", col1="Cluster", col2="species"),
            N("qual", "score.clustering", labels="Cluster"),
            N("lr", "sk.classifier.LogisticRegression", target="species", max_iter="500"),
            N("pred", "apply.predictor", proba=True), N("sc", "score.classification"),
        ], "edges": [
            E("d", 0, "km", 0), E("km", 0, "conc", 0), E("km", 0, "qual", 0),
            E("d", 0, "lr", 0), E("lr", 0, "pred", 0), E("d", 0, "pred", 1), E("pred", 0, "sc", 0),
        ]}
        e = self.run_all(wf)
        # Concordance : association invariante au nommage des catégories (clusters vs espèces).
        conc = e.result("conc").outputs[0].set_index("métrique")["valeur"]
        self.assertGreater(conc["V de Cramér"], 0.8)
        self.assertGreater(conc["Indice de Rand ajusté"], 0.6)
        self.assertNotIn("Kappa de Cohen", conc.index)       # catégories disjointes : pas d'accord brut
        self.assertEqual(len(e.result("conc").outputs[1]), 3)  # table de contingence : 3 clusters
        # Qualité du clustering : silhouette, Calinski–Harabasz, Davies–Bouldin.
        qual = e.result("qual").outputs[0].set_index("métrique")["valeur"]
        self.assertEqual(set(qual.index), {"Silhouette", "Calinski–Harabasz", "Davies–Bouldin"})
        self.assertEqual(len(e.result("qual").outputs[1]), 3)  # une ligne par cluster
        # Classification enrichie (C) : log-loss et top-2 grâce aux probabilités.
        sc = e.result("sc").outputs[0].set_index("métrique")["valeur"]
        for m in ("Jaccard (macro)", "Perte de Hamming", "Perte 0-1", "Log-loss", "Exactitude top-2"):
            self.assertIn(m, sc.index)
        # Deux colonnes aux mêmes catégories : accord brut et kappa ajoutés.
        wf2 = {"nodes": [
            N("d", "io.dataset", dataset="iris"),
            N("lr", "sk.classifier.LogisticRegression", target="species", max_iter="500"),
            N("pred", "apply.predictor"),
            N("conc", "score.concordance", col1="species", col2="Prediction (species)"),
        ], "edges": [E("d", 0, "lr", 0), E("lr", 0, "pred", 0), E("d", 0, "pred", 1), E("pred", 0, "conc", 0)]}
        m2 = self.run_all(wf2).result("conc").outputs[0]["métrique"].tolist()
        self.assertIn("Accord brut", m2)
        self.assertIn("Kappa de Cohen", m2)

    def test_regression_extra_metrics(self):
        wf = {"nodes": [
            N("d", "io.dataset", dataset="diabetes"),
            N("rid", "sk.regressor.Ridge", target="target"),
            N("pred", "apply.predictor"), N("sr", "score.regression"),
        ], "edges": [E("d", 0, "rid", 0), E("rid", 0, "pred", 0), E("d", 0, "pred", 1), E("pred", 0, "sr", 0)]}
        mets = self.run_all(wf).result("sr").outputs[0]["métrique"].tolist()
        # D² toujours présent ; cibles positives (diabetes) -> MSLE et déviances présentes.
        for m in ("D² (erreur absolue)", "MSLE", "RMSLE", "Déviance de Poisson", "Déviance Gamma"):
            self.assertIn(m, mets)

    def test_reshape_grammar(self):
        pd.DataFrame({
            "ville": ["Paris", "Lyon"], "2022": [10, 5], "2023": [12, 7], "2024": [15, 9],
        }).to_csv(self.ws / "data" / "ventes.csv", index=False)
        pd.DataFrame({
            "code": ["2024-F", "2024-M", "2023-F", "2024-F"], "tags": ["a;b", "b;c", "a", "a;b"],
        }).to_csv(self.ws / "data" / "codes.csv", index=False)
        wf = {"nodes": [
            N("v", "io.csv_reader", path="ventes.csv"),
            N("melt", "manip.melt", id_vars=["ville"], var_name="année", value_name="ventes"),
            N("piv", "manip.pivot", index=["ville"], columns=["année"], values=["ventes"], aggfunc="sum"),
            N("c", "io.csv_reader", path="codes.csv"),
            N("sep", "manip.separate", column="code", sep="-", into="année,sexe", drop=True),
            N("uni", "manip.unite", columns=["année", "sexe"], name="code2", sep="-", drop=False),
            N("exp", "manip.explode", column="tags", sep=";"),
            N("dis", "manip.distinct", columns=["tags"], keep="first"),
        ], "edges": [
            E("v", 0, "melt", 0), E("melt", 0, "piv", 0),
            E("c", 0, "sep", 0), E("sep", 0, "uni", 0), E("c", 0, "exp", 0), E("exp", 0, "dis", 0),
        ]}
        e = self.run_all(wf)
        # melt : 2 villes × 3 années = 6 lignes, colonnes année/ventes.
        melt = e.result("melt").outputs[0]
        self.assertEqual(len(melt), 6)
        self.assertEqual(list(melt.columns), ["ville", "année", "ventes"])
        # pivot : retour au format large, une ligne par ville, colonnes aplaties.
        piv = e.result("piv").outputs[0]
        self.assertEqual(len(piv), 2)
        self.assertIn("ventes / 2024", piv.columns)
        # separate : deux nouvelles colonnes, colonne d'origine retirée.
        sep = e.result("sep").outputs[0]
        self.assertEqual(list(sep.columns), ["tags", "année", "sexe"])
        self.assertEqual(sep.loc[0, "sexe"], "F")
        # unite : colonne reconstruite identique au code d'origine.
        self.assertEqual(e.result("uni").outputs[0].loc[1, "code2"], "2024-M")
        # explode : 'a;b' -> 2 lignes ; distinct : combinaisons code/tags uniques.
        self.assertEqual(len(e.result("exp").outputs[0]), 7)
        self.assertEqual(len(e.result("dis").outputs[0]), 3)

    def test_edge_cases_missing_and_constant(self):
        import json
        import subprocess
        import sys
        import numpy as np
        from kataml.export import export_python
        from kataml.nodes import _jsonable
        pd.DataFrame({
            "const": ["x"] * 6, "b": ["u", "v"] * 3, "k": ["A", "A", "B", "B", "C", "C"], "num": [1, 2, 3, 4, 5, 6],
            "txt": ["1-a", None, "3-c", "4-d", "5-e", "6-f"], "lst": ["p;q", None, "r", "s", "t", "u"],
            "t2": ["m", None, None, "n", "o", "p"],
        }).to_csv(self.ws / "data" / "t.csv", index=False)
        wf = {"nodes": [
            N("r", "io.csv_reader", path="t.csv"),
            N("conc", "score.concordance", col1="const", col2="b"),        # colonne constante : V de Cramér non défini
            N("piv", "manip.pivot", index=["k"], columns=["b"]),             # valeurs par défaut : numériques seulement
            N("sep", "manip.separate", column="txt", sep="-", into="n,l"),
            N("uni", "manip.unite", columns=["txt", "t2"], name="u", sep="_", drop=False),
            N("exp", "manip.explode", column="lst", sep=";"),
        ], "edges": [E("r", 0, x, 0) for x in ("conc", "piv", "sep", "uni", "exp")]}
        e = self.run_all(wf)
        # Vue sérialisable en JSON strict, comme le fait le serveur.
        json.dumps(e.result("conc").view, default=_jsonable, allow_nan=False)
        self.assertIn("num / u", e.result("piv").outputs[0].columns)
        # Les manquants restent manquants (pas de texte « nan »).
        sep = e.result("sep").outputs[0]
        self.assertTrue(sep.loc[1, ["n", "l"]].isna().all())
        u = e.result("uni").outputs[0]["u"]
        self.assertEqual(u[0], "1-a_m")
        self.assertEqual(u[2], "3-c_")                                     # une partie manquante : texte vide
        self.assertTrue(pd.isna(u[1]))                                      # toutes manquantes : manquant
        lst = e.result("exp").outputs[0]["lst"]
        self.assertEqual(lst.tolist()[:2], ["p", "q"])
        self.assertEqual(int(lst.isna().sum()), 1)
        self.assertNotIn("nan", lst.dropna().tolist())
        # Pivot : fonction numérique sur une colonne texte -> message clair.
        wf["nodes"][2]["params"].update(values=["txt"], aggfunc="mean")
        ok, err, _ = Engine(self.ws).execute(wf, "piv")
        self.assertFalse(ok)
        self.assertIn("first", err)
        wf["nodes"][2]["params"].update(values=[], aggfunc="mean")
        # Infinis : None dans les tables (JSON strict).
        self.assertIsNone(_jsonable(np.float64("inf")))
        self.assertIsNone(_jsonable(float("-inf")))
        # L'export reproduit ces traitements sans erreur.
        script = self.ws / "t.py"
        script.write_text(export_python(wf, "t").replace("'t.csv'", repr(str(self.ws / "data" / "t.csv"))), encoding="utf-8")
        proc = subprocess.run([sys.executable, str(script)], cwd=self.ws, capture_output=True, text=True, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])


if __name__ == "__main__":
    unittest.main()
