"""Import d'un script Python en workflow, et Lecteur Parquet / Excel.

Lancement : uv run python -m unittest tests.test_py_import -v
"""

import shutil
import tempfile
import unittest
from pathlib import Path

import pandas as pd
from sklearn.datasets import load_iris

from kataml.engine import Engine
from kataml.nodes import REGISTRY
from kataml.py_import import script_to_workflow, scripts_to_workflow

SCRIPT = '''
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

CIBLE = "species"
NUMERIQUES = ["sepal length (cm)", "sepal width (cm)", "petal length (cm)", "petal width (cm)"]

def charger():
    df = pd.read_csv("iris.csv")
    return df.dropna()

def main():
    df = charger()
    X = df.drop(columns=CIBLE)
    y = df[CIBLE]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, stratify=y, random_state=0)
    prep = ColumnTransformer([("num", StandardScaler(), NUMERIQUES)])
    model = Pipeline([("prep", prep), ("clf", LogisticRegression(max_iter=500))])
    model.fit(X_train, y_train)
    print(accuracy_score(y_test, model.predict(X_test)))
    print(cross_val_score(model, X_train, y_train, cv=4).mean())


class SqlReader(Workspace):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        import sqlite3
        con = sqlite3.connect(cls.tmp / "data" / "fleurs.db")
        cls.df.to_sql("iris", con, index=False)
        con.close()

    def read(self, **params):
        wf = {"nodes": [{"id": "s", "type": "io.sql_reader", "params": params}], "edges": []}
        engine = Engine(self.tmp)
        ok, err, _ = engine.execute(wf, "s")
        return ok, err

    def test_query_table_and_errors(self):
        self.assertEqual(self.read(source="fleurs.db", query="SELECT * FROM iris WHERE species = 'setosa'"), (True, None))
        self.assertTrue(self.read(source="fleurs.db", query="iris", limit=10)[0])
        self.assertTrue(self.read(source="fleurs.db")[0])               # une seule table : lue d'office
        ok, err = self.read(source="fleurs.db", query="inconnue")
        self.assertFalse(ok)
        self.assertIn("iris", err)                                      # liste des tables
        ok, err = self.read(source="$KATAML_TEST_PAS_DEFINIE")
        self.assertFalse(ok)
        self.assertIn("KATAML_TEST_PAS_DEFINIE", err)

    def test_script_with_database(self):
        src = (
            'import os\nimport pandas as pd\nfrom sqlalchemy import create_engine\n'
            'URL = os.getenv("DATABASE_URL", "postgresql://u:secret@h/db")\n'
            'COLS = ["species", "petal width (cm)"]\n'
            'cols = ", ".join(f\'"{c}"\' for c in COLS)\n'
            'df = pd.read_sql(f"SELECT {cols} FROM iris", create_engine(URL))\n'
            'masque = df["petal width (cm)"] > 0.5\n'
            'df = df.loc[masque].copy()\n')
        wf, notes = script_to_workflow(src, known_types=set(REGISTRY))
        sql, py = wf["nodes"]
        self.assertEqual(sql["type"], "io.sql_reader")
        self.assertEqual(sql["params"]["source"], "$DATABASE_URL")
        self.assertEqual(sql["params"]["query"], 'SELECT "species", "petal width (cm)" FROM iris')
        self.assertEqual(py["params"]["code"], "out = df.loc[df['petal width (cm)'] > 0.5].copy()\n")
        self.assertTrue(any("DATABASE_URL" in n for n in notes))
        sql["params"]["source"] = "fleurs.db"
        self.run_all(wf)

    def test_library_modules_only_when_imported(self):
        main = "import pandas as pd\nfrom projet.config import CIBLE\ndf = pd.read_csv('iris.csv')\ny = df[CIBLE]\n" \
               "from sklearn.tree import DecisionTreeClassifier\nm = DecisionTreeClassifier().fit(df.drop(columns=CIBLE), y)\n"
        library = [("config.py", "CIBLE = 'species'\n"), ("autre.py", "import pandas as pd\ndf = pd.read_csv('x.csv')\n")]
        wf, _ = scripts_to_workflow([("main.py", main)], known_types=set(REGISTRY), library=library)
        self.assertEqual(len(wf["nodes"]), 2)                           # autre.py n'est pas repris
        self.assertEqual(wf["nodes"][1]["params"]["target"], "species")
        self.assertIn("+1 module", wf["annotations"][0]["text"])


if __name__ == "__main__":
    main()
'''

LIB = '''
COLONNE_CIBLE = "species"
'''
MAIN = '''
import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from monprojet.config import COLONNE_CIBLE
from pathlib import Path
DOSSIER = Path(__file__).parent
df = pd.read_parquet(DOSSIER / "iris.parquet")
clf = DecisionTreeClassifier(max_depth=3).fit(df.drop(columns=COLONNE_CIBLE), df[COLONNE_CIBLE])
'''


class Workspace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="kataml-import-"))
        (cls.tmp / "data").mkdir()
        iris = load_iris(as_frame=True)
        df = iris.frame.drop(columns="target")
        df["species"] = iris.target_names[iris.target]
        df.to_csv(cls.tmp / "data" / "iris.csv", index=False)
        df.to_parquet(cls.tmp / "data" / "iris.parquet", index=False)
        df.to_excel(cls.tmp / "data" / "iris.xlsx", index=False, sheet_name="fleurs")
        cls.df = df

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_all(self, wf):
        engine = Engine(self.tmp)
        for n in wf["nodes"]:
            ok, err, _ = engine.execute(wf, n["id"])
            self.assertTrue(ok, f"{n['id']} ({n['type']}) : {err}")
        return engine


class ImportScript(Workspace):
    def test_script_becomes_runnable_workflow(self):
        wf, notes = script_to_workflow(SCRIPT, "iris.py", known_types=set(REGISTRY))
        types = [n["type"] for n in wf["nodes"]]
        for t in ("io.csv_reader", "manip.missing", "manip.partition", "sk.transformer.StandardScaler",
                  "sk.classifier.LogisticRegression", "compose.pipeline", "apply.predictor",
                  "score.classification", "tune.cross_validation"):
            self.assertIn(t, types)
        part = next(n for n in wf["nodes"] if n["type"] == "manip.partition")
        self.assertEqual(part["params"]["stratify"], "species")
        self.assertEqual(part["params"]["test_size"], 0.3)
        self.assertEqual(wf["annotations"][0]["color"], "jaune")
        self.run_all(wf)

    def test_modules_resolve_constants_and_parquet(self):
        wf, notes = scripts_to_workflow([("main.py", MAIN), ("config.py", LIB)], known_types=set(REGISTRY))
        reader = wf["nodes"][0]
        self.assertEqual((reader["type"], reader["params"]["path"]), ("io.table_reader", "iris.parquet"))
        tree = next(n for n in wf["nodes"] if n["type"] == "sk.classifier.DecisionTreeClassifier")
        self.assertEqual(tree["params"]["target"], "species")
        self.assertEqual(tree["params"]["max_depth"], "3")
        self.run_all(wf)

    def test_unknown_operations_become_python_nodes_or_notes(self):
        src = 'import pandas as pd\ndf = pd.read_csv("iris.csv")\ndf["ratio"] = df["petal length (cm)"] / df["petal width (cm)"]\ndf = df.query("ratio > 2")\n'
        wf, notes = script_to_workflow(src, known_types=set(REGISTRY))
        self.assertEqual([n["type"] for n in wf["nodes"]], ["io.csv_reader", "manip.python", "manip.python"])
        self.run_all(wf)

    def test_invalid_scripts(self):
        with self.assertRaises(ValueError):
            script_to_workflow("def f(:\n  pass")
        with self.assertRaises(ValueError):
            script_to_workflow("print('bonjour')")


class TableReader(Workspace):
    def test_parquet_and_excel(self):
        for path, extra in (("iris.parquet", {}), ("iris.xlsx", {"sheet": "fleurs"}), ("iris.xlsx", {})):
            with self.subTest(path=path, **extra):
                wf = {"nodes": [{"id": "r", "type": "io.table_reader", "params": {"path": path, **extra}}], "edges": []}
                ok, err, _ = Engine(self.tmp).execute(wf, "r")
                self.assertTrue(ok, err)
        wf = {"nodes": [{"id": "r", "type": "io.table_reader", "params": {"path": "iris.csv"}}], "edges": []}
        ok, err, _ = Engine(self.tmp).execute(wf, "r")
        self.assertFalse(ok)
        self.assertIn("Lecteur CSV", err)

    def test_code_export(self):
        code = REGISTRY["io.table_reader"].code
        self.assertEqual(code({"path": "a.parquet"}, [], ["df"]), "df = pd.read_parquet('a.parquet')")
        self.assertEqual(code({"path": "a.xlsx", "sheet": "2"}, [], ["df"]), "df = pd.read_excel('a.xlsx', sheet_name=2)")


if __name__ == "__main__":
    unittest.main()
