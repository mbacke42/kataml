"""Registre des nœuds KataML.

Un nœud est décrit par une spécification (ports, paramètres, aide) envoyée à
l'interface, une fonction ``run(ctx, p)`` qui renvoie la liste des sorties et,
optionnellement, une fonction ``code(p, ins, outs)`` qui produit l'équivalent
en script Python (export « vers scikit-learn pur »).
"""

from __future__ import annotations

import ast
import inspect
import io
import json
import re
import textwrap
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
from sklearn import datasets as skdatasets
from sklearn import metrics as skm
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import (
    GridSearchCV, KFold, StratifiedKFold, cross_validate, train_test_split,
)

from . import sk_catalog

DATA, MODEL = "data", "model"

CAT_IO = "Entrées / Sorties"
CAT_MANIP = "Manipulation"
CAT_VIEW = "Visualisation"
CAT_SCORE = "Évaluation"
CAT_TUNE = "Validation & réglage"
CAT_APPLY = "Application de modèles"
CAT_COMPOSE = "Pipelines & ensembles"
CAT_EXPLAIN = "Explicabilité"


class NodeError(Exception):
    """Erreur destinée à l'utilisateur (message affiché tel quel)."""


@dataclass
class ModelPort:
    """Objet circulant sur un port « modèle »."""
    estimator: Any
    kind: str                      # classifier | regressor | cluster | transformer
    name: str
    features: list[str] = field(default_factory=list)
    target: str | None = None
    classes: list | None = None
    output_columns: list[str] | None = None
    fitted: bool = True

    def final_estimator(self):
        """Estimateur « utile » : dernière étape d'un Pipeline, transformeur d'un ColumnTransformer."""
        est = self.estimator
        while True:
            if hasattr(est, "steps"):
                est = est.steps[-1][1]
            elif isinstance(est, ColumnTransformer) and est.transformers:
                est = est.transformers_[0][1] if hasattr(est, "transformers_") else est.transformers[0][1]
            else:
                return est

    def summary(self) -> dict:
        est = self.estimator
        inner = self.final_estimator()
        params = {k: repr(v) for k, v in inner.get_params(deep=False).items()}
        attrs = {}
        for a in sorted(vars(inner)):
            if a.endswith("_") and not a.startswith("_"):
                v = getattr(inner, a)
                attrs[a] = _short_repr(v)
        return {
            "name": self.name, "kind": self.kind, "features": self.features,
            "target": self.target,
            "classes": [_jsonable(c) for c in self.classes] if self.classes is not None else None,
            "output_columns": self.output_columns, "params": params,
            "attributes": attrs, "repr": repr(est), "fitted": self.fitted,
            "steps": [name for name, _ in est.steps] if hasattr(est, "steps") else None,
        }


@dataclass
class Ctx:
    inputs: list[Any]
    workspace: Path
    node_id: str
    view: list[dict] | None = None
    messages: list[str] = field(default_factory=list)
    input_labels: list[str | None] = field(default_factory=list)

    def label(self, i: int) -> str | None:
        return self.input_labels[i] if i < len(self.input_labels) else None

    def data(self, i: int = 0) -> pd.DataFrame:
        v = self.inputs[i]
        if not isinstance(v, pd.DataFrame):
            raise NodeError(f"Le port d'entrée {i + 1} attend une table.")
        return v

    def model(self, i: int = 0) -> ModelPort:
        v = self.inputs[i]
        if not isinstance(v, ModelPort):
            raise NodeError(f"Le port d'entrée {i + 1} attend un modèle.")
        return v

    def add_view(self, *blocks: dict):
        self.view = (self.view or []) + list(blocks)


@dataclass
class NodeType:
    type: str
    name: str
    category: str
    description: str
    inputs: list[tuple[str, str]]
    outputs: list[tuple[str, str]]
    params: list[dict]
    run: Callable
    code: Callable | None = None
    family: str | None = None
    doc_url: str | None = None
    has_view: bool = False
    color: str = "data"
    keywords: str = ""
    optional_inputs: list[int] = field(default_factory=list)
    uses_labels: bool = False      # la signature dépend des noms des nœuds amont
    extension: str | None = None   # nom de l'extension qui fournit le nœud
    module: str | None = None      # module scikit-learn d'origine (nœuds générés)
    kind: str | None = None        # rôle : classifier, regressor, cluster, transformer…
    description_en: str = ""       # description anglaise (nœuds générés depuis scikit-learn)

    def spec(self) -> dict:
        return {
            "type": self.type, "name": self.name, "category": self.category,
            "family": self.family, "description": self.description,
            "inputs": [{"name": n, "kind": k} for n, k in self.inputs],
            "outputs": [{"name": n, "kind": k} for n, k in self.outputs],
            "params": self.params, "doc_url": self.doc_url,
            "has_view": self.has_view, "color": self.color, "keywords": self.keywords,
            "optional_inputs": self.optional_inputs, "extension": self.extension,
            "description_en": self.description_en,
        }


REGISTRY: dict[str, NodeType] = {}


def register(type_, name, category, description, inputs=(), outputs=(), params=(),
             code=None, has_view=False, color="data", family=None, doc_url=None, keywords="",
             optional_inputs=(), uses_labels=False):
    def deco(fn):
        REGISTRY[type_] = NodeType(
            type_, name, category, textwrap.dedent(description).strip(),
            list(inputs), list(outputs), list(params), fn, code, family, doc_url,
            has_view, color, keywords, list(optional_inputs), uses_labels,
        )
        return fn
    return deco


# --------------------------------------------------------------------------
# Utilitaires
# --------------------------------------------------------------------------

def P(name, label, type_, default=None, help="", **kw) -> dict:
    d = {"name": name, "label": label, "type": type_, "default": default, "help": help}
    d.update(kw)
    return d


def _jsonable(v):
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        f = float(v)
        return f if np.isfinite(f) else None   # NaN et ±inf : JSON strict
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, float) and not np.isfinite(v):
        return None
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    return str(v)


def _short_repr(v) -> str:
    if isinstance(v, np.ndarray):
        with np.printoptions(precision=4, threshold=12, edgeitems=3, suppress=True):
            r = f"array{v.shape} " + np.array2string(v, max_line_width=100)
    else:
        r = repr(v)
    return r if len(r) < 400 else r[:400] + "…"


PARALLEL_MIN_ROWS = 10_000


def n_jobs(rows: int | None = None) -> int | None:
    """Nombre de cœurs pour les calculs répétés (validation croisée, recherche, permutations).

    Variable d'environnement KATAML_N_JOBS (option --jobs) : -1 = tous les cœurs (défaut),
    1 = un seul (comportement d'origine), N = N cœurs. En dessous de PARALLEL_MIN_ROWS lignes,
    le calcul reste sur un cœur : lancer les processus coûterait plus que le gain.
    """
    import os
    if rows is not None and rows < PARALLEL_MIN_ROWS:
        return None
    try:
        n = int(os.environ.get("KATAML_N_JOBS", "-1"))
    except ValueError:
        return -1
    return None if n in (0, 1) else n


def parse_literal(value):
    """Convertit une saisie utilisateur en valeur Python (littéral ou chaîne brute)."""
    if not isinstance(value, str):
        return value
    s = value.strip()
    if s == "":
        return None
    try:
        return ast.literal_eval(s)
    except (ValueError, SyntaxError):
        return s


def check_columns(df: pd.DataFrame, cols, what="Colonne"):
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise NodeError(f"{what} introuvable(s) : {', '.join(map(str, missing))}. "
                        f"Colonnes disponibles : {', '.join(map(str, df.columns[:30]))}")


def resolve_features(df: pd.DataFrame, features, exclude=()) -> list[str]:
    feats = list(features or [])
    if not feats:
        feats = [c for c in df.columns if c not in exclude]
    check_columns(df, feats)
    return feats


def ensure_numeric(df: pd.DataFrame, cols):
    bad = [c for c in cols if not (pd.api.types.is_numeric_dtype(df[c]) or pd.api.types.is_bool_dtype(df[c]))]
    if bad:
        raise NodeError(
            "Colonnes non numériques : " + ", ".join(map(str, bad[:10]))
            + ". Encodez-les (OneHotEncoder, OrdinalEncoder) ou excluez-les des variables."
        )


def py(v) -> str:
    return repr(v)


def table_block(df: pd.DataFrame, title=None, max_rows=200) -> dict:
    d = df.head(max_rows)
    return {
        "type": "table", "title": title,
        "columns": [str(c) for c in d.columns],
        "rows": [[_jsonable(x) for x in row] for row in d.itertuples(index=False)],
    }


def detect_prediction_column(df: pd.DataFrame) -> str | None:
    for c in df.columns:
        if str(c).startswith("Prediction"):
            return c
    return None


def detect_target_from_prediction(df: pd.DataFrame, pred_col) -> str | None:
    m = re.match(r"Prediction \((.+)\)$", str(pred_col or ""))
    if m and m.group(1) in df.columns:
        return m.group(1)
    return None


# --------------------------------------------------------------------------
# Entrées / sorties
# --------------------------------------------------------------------------

def _data_path(ctx_or_ws, path: str) -> Path:
    ws = ctx_or_ws.workspace if isinstance(ctx_or_ws, Ctx) else ctx_or_ws
    p = Path(path).expanduser()
    if not p.is_absolute():
        for cand in (ws / "data" / p, Path.cwd() / p, ws / p):
            if cand.exists():
                return cand
        return ws / "data" / p
    return p


@register(
    "io.csv_reader", "Lecteur CSV", CAT_IO,
    """
    Lit un fichier CSV (ou TSV) dans une table pandas.

    Déposez un fichier via le bouton « Importer » : il est copié dans
    workspace/data. Un chemin absolu fonctionne aussi. Le séparateur est
    détecté automatiquement si le champ est laissé vide.
    """,
    outputs=[("Table", DATA)],
    params=[
        P("path", "Fichier", "file", "", "Nom d'un fichier de workspace/data ou chemin absolu.", required=True),
        P("sep", "Séparateur", "str", "", "Vide = détection automatique (, ; tabulation |)."),
        P("decimal", "Séparateur décimal", "choice", ".", choices=[".", ","]),
        P("header", "Première ligne = en-têtes", "bool", True),
        P("encoding", "Encodage", "choice", "utf-8", choices=["utf-8", "latin-1", "cp1252", "utf-16"]),
        P("na_values", "Valeurs manquantes supplémentaires", "str", "", "Ex. : NA, ?, -"),
    ],
    keywords="fichier lire import csv tsv",
)
def csv_reader(ctx: Ctx, p):
    path = _data_path(ctx, p.get("path") or "")
    if not p.get("path") or not path.exists():
        raise NodeError(f"Fichier introuvable : {p.get('path') or '(non renseigné)'}")
    sep = p.get("sep") or None
    if sep == "\\t":
        sep = "\t"
    na = [s.strip() for s in (p.get("na_values") or "").split(",") if s.strip()] or None
    df = pd.read_csv(
        path, sep=sep, engine="python" if sep is None else "c",
        decimal=p.get("decimal") or ".", header=0 if p.get("header", True) else None,
        encoding=p.get("encoding") or "utf-8", na_values=na,
    )
    if not p.get("header", True):
        df.columns = [f"col{i}" for i in range(df.shape[1])]
    return [df]


def _code_csv_reader(p, ins, outs):
    args = [py(p.get("path"))]
    sep = p.get("sep")
    args.append(f"sep={py(sep)}" if sep else "sep=None, engine='python'")
    if p.get("decimal", ".") != ".":
        args.append(f"decimal={py(p['decimal'])}")
    if not p.get("header", True):
        args.append("header=None")
    if p.get("encoding", "utf-8") != "utf-8":
        args.append(f"encoding={py(p['encoding'])}")
    return f"{outs[0]} = pd.read_csv({', '.join(args)})"


REGISTRY["io.csv_reader"].code = _code_csv_reader


# Formats lus par le Lecteur Parquet / Excel : extension -> (fonction pandas, dépendance).
TABLE_FORMATS = {
    ".parquet": ("read_parquet", "pyarrow"), ".pq": ("read_parquet", "pyarrow"),
    ".xlsx": ("read_excel", "openpyxl"), ".xlsm": ("read_excel", "openpyxl"), ".xls": ("read_excel", "xlrd"),
    ".feather": ("read_feather", "pyarrow"), ".json": ("read_json", None),
}


def _table_format(path: str):
    fmt = TABLE_FORMATS.get(Path(path).suffix.lower())
    if fmt is None:
        raise NodeError(f"Format non reconnu : « {Path(path).suffix or path} ». Formats acceptés : "
                        + ", ".join(sorted(TABLE_FORMATS)) + " (pour un CSV, utilisez le Lecteur CSV).")
    return fmt


@register(
    "io.table_reader", "Lecteur Parquet / Excel", CAT_IO,
    """
    Lit un fichier Parquet (.parquet), Excel (.xlsx, .xls), Feather ou JSON
    dans une table pandas. Le format est déduit de l'extension.

    Déposez le fichier sur le canevas ou via « Importer » : il est copié dans
    workspace/data. Un chemin absolu fonctionne aussi. Pour Excel, la feuille
    est la première si le champ est vide.
    """,
    outputs=[("Table", DATA)],
    params=[
        P("path", "Fichier", "file", "", "Nom d'un fichier de workspace/data ou chemin absolu.", required=True),
        P("sheet", "Feuille (Excel)", "str", "", "Nom ou numéro (0 = première). Vide = première feuille."),
        P("header", "Première ligne = en-têtes", "bool", True),
    ],
    keywords="fichier lire import parquet excel xlsx xls feather json read_parquet read_excel",
)
def table_reader(ctx: Ctx, p):
    path = _data_path(ctx, p.get("path") or "")
    if not p.get("path") or not path.exists():
        raise NodeError(f"Fichier introuvable : {p.get('path') or '(non renseigné)'}")
    func, dep = _table_format(str(path))
    try:
        if func == "read_excel":
            sheet = p.get("sheet")
            sheet = 0 if sheet in (None, "") else (int(sheet) if str(sheet).strip().isdigit() else sheet)
            df = pd.read_excel(path, sheet_name=sheet, header=0 if p.get("header", True) else None)
        else:
            df = getattr(pd, func)(path)
    except ImportError as e:
        raise NodeError(f"La lecture de ce format demande le paquet « {dep} » : "
                        f"installez-le (uv pip install {dep}) puis relancez KataML.") from e
    except (ValueError, KeyError) as e:
        raise NodeError(f"Lecture impossible : {e}") from e
    if func == "read_excel" and not p.get("header", True):
        df.columns = [f"col{i}" for i in range(df.shape[1])]
    df.columns = [str(c) for c in df.columns]
    return [df]


def _code_table_reader(p, ins, outs):
    func, _ = _table_format(p.get("path") or "x.parquet")
    args = [py(p.get("path"))]
    if func == "read_excel":
        sheet = p.get("sheet")
        if sheet not in (None, ""):
            args.append(f"sheet_name={py(int(sheet) if str(sheet).strip().isdigit() else sheet)}")
        if not p.get("header", True):
            args.append("header=None")
    return f"{outs[0]} = pd.{func}({', '.join(args)})"


REGISTRY["io.table_reader"].code = _code_table_reader


# --------------------------------------------------------------------------
# Bases de données SQL
# --------------------------------------------------------------------------
SQLITE_EXT = (".db", ".sqlite", ".sqlite3", ".db3")


def _sql_source(ctx, source: str):
    """(« sqlite », chemin) ou (« url », URL SQLAlchemy). ``$NOM`` lit une variable d'environnement."""
    import os
    src = (source or "").strip()
    if src.startswith("$"):
        var = src[1:].strip("{}")
        src = os.environ.get(var, "").strip()
        if not src:
            raise NodeError(f"La variable d'environnement {var} n'est pas définie.")
    if not src:
        raise NodeError("Indiquez la base : un fichier SQLite de workspace/data ou une URL de connexion.")
    if "://" in src:
        if src.startswith("sqlite:///"):
            return "sqlite", _data_path(ctx, src[len("sqlite:///"):])
        return "url", src
    path = _data_path(ctx, src)
    if not path.exists():
        raise NodeError(f"Base SQLite introuvable : {source}")
    return "sqlite", path


def _sql_tables(kind, target) -> list[str]:
    if kind == "sqlite":
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(Path(target).resolve().as_uri() + "?mode=ro", uri=True)) as con:
            return [r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    import sqlalchemy
    eng = sqlalchemy.create_engine(target)
    try:
        insp = sqlalchemy.inspect(eng)
        return sorted(insp.get_table_names() + insp.get_view_names())
    finally:
        eng.dispose()


def _sql_engine_error(e: Exception) -> NodeError:
    msg = str(e)
    for driver, pkg in (("psycopg", "psycopg[binary]"), ("psycopg2", "psycopg2-binary"),
                        ("pymysql", "pymysql"), ("MySQLdb", "pymysql"), ("pyodbc", "pyodbc")):
        if f"No module named '{driver}'" in msg:
            return NodeError(f"Pilote de base de données manquant : installez-le avec « uv pip install {pkg} » "
                             "dans le dossier de KataML, puis relancez.")
    return NodeError(f"Connexion ou requête impossible : {msg.splitlines()[0][:400]}")


@register(
    "io.sql_reader", "Lecteur SQL (base de données)", CAT_IO,
    """
    Exécute une requête SQL et renvoie le résultat sous forme de table.

    La base est soit un fichier SQLite (.db, .sqlite) de workspace/data, soit
    une URL de connexion SQLAlchemy, par exemple
    postgresql+psycopg://utilisateur:motdepasse@localhost:5432/base ou
    mysql+pymysql://utilisateur@hote/base. Pour ne pas enregistrer de mot de
    passe dans le workflow, écrivez $DATABASE_URL : l'URL est lue dans cette
    variable d'environnement. La requête peut se réduire à un nom de table ;
    laissée vide, l'unique table de la base est lue (sinon la liste des tables
    est affichée). La base est ouverte en lecture seule pour SQLite.
    """,
    outputs=[("Table", DATA)],
    params=[
        P("source", "Base de données", "file", "", "Fichier SQLite de workspace/data, URL de connexion, ou $VARIABLE.",
          required=True),
        P("query", "Requête SQL ou nom de table", "code", "", "Ex. : SELECT * FROM vols WHERE annee = 2025", rows=6),
        P("limit", "Nombre maximal de lignes (0 = toutes)", "int", 0, min=0),
    ],
    keywords="sql base de données database sqlite postgresql postgres mysql requête query read_sql",
)
def sql_reader(ctx: Ctx, p):
    import re
    kind, target = _sql_source(ctx, p.get("source"))
    query = (p.get("query") or "").strip().rstrip(";").strip()
    try:
        if not query or re.fullmatch(r"[\w.]+", query):
            tables = _sql_tables(kind, target)
            if not query:
                if len(tables) != 1:
                    raise NodeError("Indiquez une requête ou une table. Tables disponibles : "
                                    + (", ".join(tables[:60]) or "aucune") + ".")
                query = tables[0]
            if query not in tables:
                raise NodeError(f"Table « {query} » introuvable. Tables disponibles : {', '.join(tables[:60]) or 'aucune'}.")
            query = f'SELECT * FROM "{query}"' if "." not in query else f"SELECT * FROM {query}"
        limit = int(p.get("limit") or 0)
        if kind == "sqlite":
            import sqlite3
            from contextlib import closing
            with closing(sqlite3.connect(Path(target).resolve().as_uri() + "?mode=ro", uri=True)) as con:
                df = (next(pd.read_sql_query(query, con, chunksize=limit), pd.DataFrame()) if limit
                      else pd.read_sql_query(query, con))
        else:
            try:
                import sqlalchemy
            except ImportError as e:
                raise NodeError("Les bases PostgreSQL / MySQL demandent SQLAlchemy et un pilote : "
                                "« uv pip install sqlalchemy psycopg[binary] » (PostgreSQL) ou "
                                "« uv pip install sqlalchemy pymysql » (MySQL), puis relancez KataML.") from e
            eng = sqlalchemy.create_engine(target)
            try:
                with eng.connect() as con:
                    q = sqlalchemy.text(query)
                    df = (next(pd.read_sql_query(q, con, chunksize=limit), pd.DataFrame()) if limit
                          else pd.read_sql_query(q, con))
            finally:
                eng.dispose()
    except NodeError:
        raise
    except Exception as e:
        raise _sql_engine_error(e) from e
    df.columns = [str(c) for c in df.columns]
    ctx.add_view({"type": "metrics", "items": [{"label": "Lignes", "value": len(df)},
                                               {"label": "Colonnes", "value": df.shape[1]}]})
    return [df]


def _code_sql_reader(p, ins, outs):
    src = (p.get("source") or "").strip()
    query = (p.get("query") or "").strip().rstrip(";") or "SELECT * FROM ma_table"
    if " " not in query:
        query = f"SELECT * FROM {query}"
    if src.startswith("$"):
        con = f"sqlalchemy.create_engine(os.environ[{py(src[1:].strip('{}'))}])"
        head = "import os\nimport sqlalchemy\n"
    elif "://" in src and not src.startswith("sqlite:///"):
        con, head = f"sqlalchemy.create_engine({py(src)})", "import sqlalchemy\n"
    else:
        con, head = f"sqlite3.connect({py(src.replace('sqlite:///', ''))})", "import sqlite3\n"
    return f"{head}{outs[0]} = pd.read_sql_query({py(query)}, {con})"


REGISTRY["io.sql_reader"].code = _code_sql_reader
REGISTRY["io.sql_reader"].has_view = True


DATASETS = {
    "iris": ("load_iris", "Iris (classification, 150×4, 3 classes)"),
    "wine": ("load_wine", "Vins (classification, 178×13, 3 classes)"),
    "breast_cancer": ("load_breast_cancer", "Cancer du sein (classification binaire, 569×30)"),
    "digits": ("load_digits", "Chiffres manuscrits (classification, 1797×64)"),
    "diabetes": ("load_diabetes", "Diabète (régression, 442×10)"),
    "linnerud": ("load_linnerud", "Linnerud (régression multi-sorties, 20×3)"),
}
GENERATORS = {
    "make_classification": "Générateur : classification",
    "make_regression": "Générateur : régression",
    "make_blobs": "Générateur : nuages gaussiens (blobs)",
    "make_moons": "Générateur : deux lunes",
    "make_circles": "Générateur : cercles concentriques",
}


@register(
    "io.dataset", "Jeu de données scikit-learn", CAT_IO,
    """
    Charge un jeu de données fourni avec scikit-learn (sans téléchargement)
    ou en génère un synthétique (make_classification, make_moons…).

    La cible est placée dans la colonne « target » (« species » pour iris
    avec les noms de classes en clair).
    """,
    outputs=[("Table", DATA)],
    params=[
        P("dataset", "Jeu de données", "choice", "iris",
          choices=list(DATASETS) + list(GENERATORS),
          choice_labels={**{k: v[1] for k, v in DATASETS.items()}, **GENERATORS}),
        P("n_samples", "Nombre d'échantillons (générateurs)", "int", 300),
        P("n_features", "Nombre de variables (classification/régression)", "int", 5),
        P("noise", "Bruit (générateurs)", "float", 0.1),
        P("centers", "Nombre de classes / centres", "int", 3),
        P("random_state", "Graine aléatoire", "int", 0),
    ],
    keywords="iris wine digits diabetes moons blobs exemple démo",
)
def dataset(ctx: Ctx, p):
    name = p.get("dataset") or "iris"
    rs = p.get("random_state")
    n = int(p.get("n_samples") or 300)
    if name in DATASETS:
        bunch = getattr(skdatasets, DATASETS[name][0])(as_frame=True)
        df = bunch.frame.copy()
        if name == "iris":
            df["species"] = pd.Categorical.from_codes(df.pop("target"), bunch.target_names).astype(str)
        elif name == "wine":
            df["target"] = df["target"].map(lambda i: f"classe_{i}")
        elif name == "breast_cancer":
            df["target"] = df["target"].map({0: "malignant", 1: "benign"})
        return [df]
    nf = int(p.get("n_features") or 5)
    k = int(p.get("centers") or 3)
    noise = float(p.get("noise") or 0.0)
    if name == "make_classification":
        X, y = skdatasets.make_classification(
            n_samples=n, n_features=max(nf, 2), n_informative=max(2, min(nf, nf // 2 + 1)),
            n_redundant=0, n_classes=k, n_clusters_per_class=1, flip_y=noise / 2, random_state=rs)
    elif name == "make_regression":
        X, y = skdatasets.make_regression(n_samples=n, n_features=nf, noise=noise * 100, random_state=rs)
    elif name == "make_blobs":
        X, y = skdatasets.make_blobs(n_samples=n, n_features=max(nf, 2) if nf else 2, centers=k, random_state=rs)
    elif name == "make_moons":
        X, y = skdatasets.make_moons(n_samples=n, noise=noise, random_state=rs)
    elif name == "make_circles":
        X, y = skdatasets.make_circles(n_samples=n, noise=noise, factor=0.5, random_state=rs)
    else:
        raise NodeError(f"Jeu de données inconnu : {name}")
    df = pd.DataFrame(X, columns=[f"x{i}" for i in range(X.shape[1])])
    df["target"] = y
    return [df]


def _code_dataset(p, ins, outs):
    name = p.get("dataset") or "iris"
    o = outs[0]
    if name in DATASETS:
        lines = [f"{o} = datasets.{DATASETS[name][0]}(as_frame=True).frame"]
        if name == "iris":
            lines.append(f"{o}['species'] = {o}.pop('target').map(dict(enumerate(datasets.load_iris().target_names)))")
        return "\n".join(lines)
    rs, n, nf = p.get("random_state"), int(p.get("n_samples") or 300), int(p.get("n_features") or 5)
    k, noise = int(p.get("centers") or 3), float(p.get("noise") or 0.0)
    call = {
        "make_classification": f"datasets.make_classification(n_samples={n}, n_features={max(nf, 2)}, n_informative={max(2, min(nf, nf // 2 + 1))}, n_redundant=0, n_classes={k}, n_clusters_per_class=1, flip_y={noise / 2}, random_state={rs})",
        "make_regression": f"datasets.make_regression(n_samples={n}, n_features={nf}, noise={noise * 100}, random_state={rs})",
        "make_blobs": f"datasets.make_blobs(n_samples={n}, n_features={max(nf, 2)}, centers={k}, random_state={rs})",
        "make_moons": f"datasets.make_moons(n_samples={n}, noise={noise}, random_state={rs})",
        "make_circles": f"datasets.make_circles(n_samples={n}, noise={noise}, factor=0.5, random_state={rs})",
    }[name]
    return (f"X, y = {call}\n{o} = pd.DataFrame(X, columns=[f'x{{i}}' for i in range(X.shape[1])])\n"
            f"{o}['target'] = y")


REGISTRY["io.dataset"].code = _code_dataset


@register(
    "io.csv_writer", "Écriture CSV", CAT_IO,
    """
    Écrit la table d'entrée dans un fichier CSV (par défaut dans
    workspace/exports). La table est aussi téléchargeable depuis la vue des
    ports de n'importe quel nœud.
    """,
    inputs=[("Table", DATA)],
    params=[
        P("path", "Fichier de sortie", "str", "exports/resultat.csv", required=True),
        P("sep", "Séparateur", "choice", ",", choices=[",", ";", "\\t"]),
        P("index", "Écrire l'index", "bool", False),
    ],
    keywords="export sauvegarder enregistrer",
)
def csv_writer(ctx: Ctx, p):
    path = Path(p.get("path") or "exports/resultat.csv").expanduser()
    if not path.is_absolute():
        path = ctx.workspace / path
    path.parent.mkdir(parents=True, exist_ok=True)
    sep = "\t" if p.get("sep") == "\\t" else (p.get("sep") or ",")
    ctx.data().to_csv(path, sep=sep, index=bool(p.get("index")))
    ctx.messages.append(f"Écrit : {path}")
    ctx.add_view({"type": "text", "text": f"{len(ctx.data())} lignes écrites dans {path}"})
    return []


REGISTRY["io.csv_writer"].code = lambda p, ins, outs: (
    f"{ins[0]}.to_csv({py(p.get('path'))}, sep={py(p.get('sep', ',').replace(chr(92) + 't', chr(9)))}, index={bool(p.get('index'))})")
REGISTRY["io.csv_writer"].has_view = True


@register(
    "io.model_writer", "Écriture de modèle", CAT_IO,
    """
    Sérialise le modèle avec joblib (format standard scikit-learn). Le fichier
    peut être rechargé dans n'importe quel script Python avec joblib.load().
    """,
    inputs=[("Modèle", MODEL)],
    params=[P("path", "Fichier de sortie", "str", "exports/modele.joblib", required=True)],
    keywords="joblib pickle sauvegarder export",
)
def model_writer(ctx: Ctx, p):
    import joblib
    path = Path(p.get("path") or "exports/modele.joblib").expanduser()
    if not path.is_absolute():
        path = ctx.workspace / path
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(ctx.model().estimator, path)
    ctx.add_view({"type": "text", "text": f"Modèle écrit dans {path}"})
    return []


REGISTRY["io.model_writer"].code = lambda p, ins, outs: f"joblib.dump({ins[0]}, {py(p.get('path'))})"
REGISTRY["io.model_writer"].has_view = True


# --------------------------------------------------------------------------
# Manipulation
# --------------------------------------------------------------------------

@register(
    "manip.column_filter", "Filtre de colonnes", CAT_MANIP,
    "Conserve ou retire une sélection de colonnes.",
    inputs=[("Table", DATA)], outputs=[("Table", DATA)],
    params=[
        P("columns", "Colonnes", "columns", [], port=0),
        P("mode", "Mode", "choice", "include", choices=["include", "exclude"],
          choice_labels={"include": "Garder la sélection", "exclude": "Retirer la sélection"}),
    ],
    keywords="sélection colonnes drop",
)
def column_filter(ctx, p):
    df = ctx.data()
    cols = p.get("columns") or []
    check_columns(df, cols)
    if p.get("mode") == "exclude":
        return [df.drop(columns=cols)]
    return [df[cols]] if cols else [df]


REGISTRY["manip.column_filter"].code = lambda p, ins, outs: (
    f"{outs[0]} = {ins[0]}.drop(columns={py(p.get('columns') or [])})" if p.get("mode") == "exclude"
    else f"{outs[0]} = {ins[0]}[{py(p.get('columns') or [])}]")


@register(
    "manip.row_filter", "Filtre de lignes", CAT_MANIP,
    """
    Filtre les lignes avec une expression pandas DataFrame.query, par exemple :
    `age > 30 and sexe == "F"` ou `` `petal length (cm)` < 2 `` (backticks
    pour les noms contenant des espaces).
    """,
    inputs=[("Table", DATA)], outputs=[("Table retenue", DATA), ("Table rejetée", DATA)],
    params=[P("query", "Expression", "code", "", "Syntaxe DataFrame.query.", required=True, rows=2)],
    keywords="query where condition sélection lignes",
)
def row_filter(ctx, p):
    df = ctx.data()
    q = (p.get("query") or "").strip()
    if not q:
        raise NodeError("Expression vide.")
    try:
        mask = df.eval(q)
    except Exception as e:
        raise NodeError(f"Expression invalide : {e}") from e
    mask = pd.Series(mask, index=df.index).astype(bool)
    return [df[mask], df[~mask]]


REGISTRY["manip.row_filter"].code = lambda p, ins, outs: (
    f"_mask = {ins[0]}.eval({py(p.get('query'))}).astype(bool)\n"
    f"{outs[0]}, {outs[1]} = {ins[0]}[_mask], {ins[0]}[~_mask]")


@register(
    "manip.expression", "Nouvelle colonne (expression)", CAT_MANIP,
    """
    Calcule une colonne à partir d'une expression DataFrame.eval, par exemple
    `poids / taille ** 2`. Si la colonne existe, elle est remplacée.
    """,
    inputs=[("Table", DATA)], outputs=[("Table", DATA)],
    params=[
        P("name", "Nom de la colonne", "str", "nouvelle_colonne", required=True),
        P("expr", "Expression", "code", "", required=True, rows=2),
    ],
    keywords="calcul formule math eval colonne",
)
def expression(ctx, p):
    df = ctx.data().copy()
    try:
        df[p.get("name") or "nouvelle_colonne"] = df.eval(p.get("expr") or "")
    except Exception as e:
        raise NodeError(f"Expression invalide : {e}") from e
    return [df]


REGISTRY["manip.expression"].code = lambda p, ins, outs: (
    f"{outs[0]} = {ins[0]}.copy()\n{outs[0]}[{py(p.get('name'))}] = {outs[0]}.eval({py(p.get('expr'))})")


@register(
    "manip.missing", "Lignes incomplètes", CAT_MANIP,
    """
    Supprime les lignes contenant des valeurs manquantes (dans toutes les
    colonnes ou une sélection). Pour imputer plutôt que supprimer, utilisez
    SimpleImputer, KNNImputer ou IterativeImputer (catégorie Prétraitement).
    """,
    inputs=[("Table", DATA)], outputs=[("Table", DATA)],
    params=[P("columns", "Colonnes à vérifier (vide = toutes)", "columns", [], port=0)],
    keywords="nan na manquant dropna",
)
def missing(ctx, p):
    df = ctx.data()
    cols = p.get("columns") or None
    if cols:
        check_columns(df, cols)
    out = df.dropna(subset=cols)
    ctx.messages.append(f"{len(df) - len(out)} lignes supprimées")
    return [out]


REGISTRY["manip.missing"].code = lambda p, ins, outs: f"{outs[0]} = {ins[0]}.dropna(subset={py(p.get('columns') or None)})"


@register(
    "manip.partition", "Partitionnement", CAT_MANIP,
    """
    Sépare la table en apprentissage / test avec
    sklearn.model_selection.train_test_split. La stratification sur la cible
    conserve les proportions de classes dans les deux parties.
    """,
    inputs=[("Table", DATA)], outputs=[("Apprentissage", DATA), ("Test", DATA)],
    params=[
        P("test_size", "Proportion de test", "float", 0.25, "Entre 0 et 1, ou un nombre de lignes entier.", min=0),
        P("stratify", "Stratifier selon", "column", "", port=0, allow_empty=True),
        P("shuffle", "Mélanger", "bool", True),
        P("random_state", "Graine aléatoire", "int", 42),
    ],
    doc_url="https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.train_test_split.html",
    keywords="split train test découpage holdout",
)
def partition(ctx, p):
    df = ctx.data()
    strat = p.get("stratify") or None
    if strat:
        check_columns(df, [strat])
    ts = p.get("test_size", 0.25)
    ts = int(ts) if isinstance(ts, (int, float)) and ts >= 1 else float(ts)
    try:
        tr, te = train_test_split(df, test_size=ts, shuffle=bool(p.get("shuffle", True)),
                                  stratify=df[strat] if strat else None,
                                  random_state=p.get("random_state"))
    except ValueError as e:
        raise NodeError(str(e)) from e
    return [tr, te]


def _code_partition(p, ins, outs):
    strat = f", stratify={ins[0]}[{py(p['stratify'])}]" if p.get("stratify") else ""
    return (f"{outs[0]}, {outs[1]} = train_test_split({ins[0]}, test_size={p.get('test_size', 0.25)}, "
            f"shuffle={bool(p.get('shuffle', True))}{strat}, random_state={p.get('random_state')})")


REGISTRY["manip.partition"].code = _code_partition


@register(
    "manip.sampling", "Échantillonnage", CAT_MANIP,
    "Tire un échantillon aléatoire de lignes (nombre ou fraction).",
    inputs=[("Table", DATA)], outputs=[("Table", DATA)],
    params=[
        P("frac", "Fraction (0–1)", "float", 0.1, "Ignorée si un nombre de lignes est donné."),
        P("n", "Nombre de lignes", "int", None, allow_empty=True),
        P("replace", "Avec remise", "bool", False),
        P("random_state", "Graine aléatoire", "int", 0),
    ],
    keywords="sample échantillon aléatoire bootstrap",
)
def sampling(ctx, p):
    df = ctx.data()
    n = p.get("n")
    kw = {"n": int(n)} if n not in (None, "") else {"frac": float(p.get("frac") or 0.1)}
    try:
        return [df.sample(replace=bool(p.get("replace")), random_state=p.get("random_state"), **kw)]
    except ValueError as e:
        raise NodeError(str(e)) from e


REGISTRY["manip.sampling"].code = lambda p, ins, outs: (
    f"{outs[0]} = {ins[0]}.sample("
    + (f"n={int(p['n'])}" if p.get("n") not in (None, "") else f"frac={p.get('frac', 0.1)}")
    + f", replace={bool(p.get('replace'))}, random_state={p.get('random_state')})")


@register(
    "manip.sorter", "Tri", CAT_MANIP, "Trie les lignes selon une ou plusieurs colonnes.",
    inputs=[("Table", DATA)], outputs=[("Table", DATA)],
    params=[
        P("columns", "Colonnes", "columns", [], port=0, required=True),
        P("ascending", "Croissant", "bool", True),
    ],
    keywords="sort trier ordre",
)
def sorter(ctx, p):
    df = ctx.data()
    cols = p.get("columns") or []
    check_columns(df, cols)
    return [df.sort_values(cols, ascending=bool(p.get("ascending", True)))]


REGISTRY["manip.sorter"].code = lambda p, ins, outs: (
    f"{outs[0]} = {ins[0]}.sort_values({py(p.get('columns') or [])}, ascending={bool(p.get('ascending', True))})")


@register(
    "manip.types", "Conversion de types", CAT_MANIP,
    """
    Convertit le type de colonnes : numérique (les valeurs invalides
    deviennent NaN), texte, catégorie, booléen ou date.
    """,
    inputs=[("Table", DATA)], outputs=[("Table", DATA)],
    params=[
        P("columns", "Colonnes", "columns", [], port=0, required=True),
        P("to", "Type cible", "choice", "numeric",
          choices=["numeric", "string", "category", "bool", "datetime"],
          choice_labels={"numeric": "Numérique", "string": "Texte", "category": "Catégorie",
                         "bool": "Booléen", "datetime": "Date / heure"}),
    ],
    keywords="cast dtype type conversion",
)
def types(ctx, p):
    df = ctx.data().copy()
    cols = p.get("columns") or []
    check_columns(df, cols)
    to = p.get("to", "numeric")
    for c in cols:
        if to == "numeric":
            df[c] = pd.to_numeric(df[c], errors="coerce")
        elif to == "datetime":
            df[c] = pd.to_datetime(df[c], errors="coerce")
        elif to == "string":
            df[c] = df[c].astype(str)
        else:
            df[c] = df[c].astype(to)
    return [df]


def _code_types(p, ins, outs):
    to, cols = p.get("to", "numeric"), p.get("columns") or []
    expr = {"numeric": "pd.to_numeric({c}, errors='coerce')", "datetime": "pd.to_datetime({c}, errors='coerce')",
            "string": "{c}.astype(str)"}.get(to, "{c}.astype(%r)" % to)
    return (f"{outs[0]} = {ins[0]}.copy()\nfor _c in {py(cols)}:\n"
            f"    {outs[0]}[_c] = " + expr.format(c=f"{outs[0]}[_c]"))


REGISTRY["manip.types"].code = _code_types


@register(
    "manip.groupby", "Agrégation (GroupBy)", CAT_MANIP,
    "Regroupe les lignes et agrège les colonnes (moyenne, somme, comptage…).",
    inputs=[("Table", DATA)], outputs=[("Table", DATA)],
    params=[
        P("by", "Grouper par", "columns", [], port=0, required=True),
        P("columns", "Colonnes à agréger (vide = toutes)", "columns", [], port=0),
        P("agg", "Fonction", "choice", "mean",
          choices=["mean", "median", "sum", "min", "max", "std", "count", "nunique", "first"]),
    ],
    keywords="group aggregate pivot moyenne somme",
)
def groupby(ctx, p):
    df = ctx.data()
    by = p.get("by") or []
    check_columns(df, by)
    cols = p.get("columns") or [c for c in df.columns if c not in by]
    check_columns(df, cols)
    agg = p.get("agg", "mean")
    g = df.groupby(by)[cols]
    numeric_only = agg in ("mean", "median", "sum", "std")
    out = g.agg(agg, numeric_only=True) if numeric_only else g.agg(agg)
    return [out.reset_index()]


REGISTRY["manip.groupby"].code = lambda p, ins, outs: (
    f"{outs[0]} = {ins[0]}.groupby({py(p.get('by'))})"
    + (f"[{py(p.get('columns'))}]" if p.get("columns") else "")
    + f".agg({py(p.get('agg', 'mean'))}"
    + (", numeric_only=True" if p.get("agg", "mean") in ("mean", "median", "sum", "std") else "")
    + ").reset_index()")


@register(
    "manip.join", "Jointure", CAT_MANIP,
    "Joint deux tables sur des colonnes clés (pandas.merge).",
    inputs=[("Gauche", DATA), ("Droite", DATA)], outputs=[("Table", DATA)],
    params=[
        P("left_on", "Clé(s) gauche", "columns", [], port=0, required=True),
        P("right_on", "Clé(s) droite", "columns", [], port=1, required=True),
        P("how", "Type", "choice", "inner", choices=["inner", "left", "right", "outer"],
          choice_labels={"inner": "Interne", "left": "Gauche", "right": "Droite", "outer": "Complète"}),
    ],
    keywords="merge join fusion",
)
def join(ctx, p):
    a, b = ctx.data(0), ctx.data(1)
    lo, ro = p.get("left_on") or [], p.get("right_on") or []
    check_columns(a, lo)
    check_columns(b, ro)
    if len(lo) != len(ro):
        raise NodeError("Les deux listes de clés doivent avoir la même longueur.")
    return [a.merge(b, left_on=lo, right_on=ro, how=p.get("how", "inner"), suffixes=("", " (droite)"))]


REGISTRY["manip.join"].code = lambda p, ins, outs: (
    f"{outs[0]} = {ins[0]}.merge({ins[1]}, left_on={py(p.get('left_on'))}, right_on={py(p.get('right_on'))}, "
    f"how={py(p.get('how', 'inner'))}, suffixes=('', ' (droite)'))")


@register(
    "manip.concat", "Concaténation", CAT_MANIP,
    "Empile les lignes de deux tables (pandas.concat).",
    inputs=[("Table 1", DATA), ("Table 2", DATA)], outputs=[("Table", DATA)],
    params=[P("ignore_index", "Réindexer", "bool", True)],
    keywords="concat union append empiler",
)
def concat(ctx, p):
    return [pd.concat([ctx.data(0), ctx.data(1)], ignore_index=bool(p.get("ignore_index", True)))]


REGISTRY["manip.concat"].code = lambda p, ins, outs: (
    f"{outs[0]} = pd.concat([{ins[0]}, {ins[1]}], ignore_index={bool(p.get('ignore_index', True))})")


# --- Remise en forme (grammaire des données : dépivoter, pivoter, scinder, éclater…) ---

@register(
    "manip.melt", "Dépivoter (format long)", CAT_MANIP,
    """
    Passe du format large au format long (pandas.melt) : les colonnes choisies
    deviennent deux colonnes, l'une pour le nom de la variable, l'autre pour sa
    valeur ; les colonnes d'identifiants sont répétées. Utile quand des en-têtes
    de colonnes sont en réalité des valeurs (une colonne par année, par exemple).
    """,
    inputs=[("Table", DATA)], outputs=[("Table", DATA)],
    params=[
        P("id_vars", "Colonnes d'identifiants (conservées)", "columns", [], port=0),
        P("value_vars", "Colonnes à dépivoter (vide = toutes les autres)", "columns", [], port=0),
        P("var_name", "Nom de la colonne de variable", "str", "variable"),
        P("value_name", "Nom de la colonne de valeur", "str", "valeur"),
    ],
    keywords="melt pivot_longer long remodelage dépivoter unpivot gather",
)
def melt(ctx, p):
    df = ctx.data()
    idv, valv = p.get("id_vars") or [], p.get("value_vars") or []
    check_columns(df, [*idv, *valv])
    return [df.melt(id_vars=idv or None, value_vars=valv or None,
                    var_name=p.get("var_name") or "variable", value_name=p.get("value_name") or "valeur")]


REGISTRY["manip.melt"].code = lambda p, ins, outs: (
    f"{outs[0]} = {ins[0]}.melt(id_vars={py(p.get('id_vars') or None)}, value_vars={py(p.get('value_vars') or None)}, "
    f"var_name={py(p.get('var_name') or 'variable')}, value_name={py(p.get('value_name') or 'valeur')})")


_NUMERIC_AGG = ("mean", "median", "sum")


def _is_num(s: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(s) or pd.api.types.is_bool_dtype(s)


@register(
    "manip.pivot", "Pivoter (format large)", CAT_MANIP,
    """
    Passe du format long au format large (pandas.pivot_table) : les valeurs
    d'une colonne deviennent des colonnes. Une fonction d'agrégation combine les
    éventuels doublons. C'est l'inverse du « Dépivoter ».
    """,
    inputs=[("Table", DATA)], outputs=[("Table", DATA)],
    params=[
        P("index", "Colonnes d'index (lignes)", "columns", [], port=0, required=True),
        P("columns", "Colonne(s) étalée(s) en colonnes", "columns", [], port=0, required=True),
        P("values", "Colonne(s) de valeurs (vide = toutes les autres)", "columns", [], port=0),
        P("aggfunc", "Fonction d'agrégation (doublons)", "choice", "mean",
          choices=["mean", "median", "sum", "min", "max", "count", "first"]),
    ],
    keywords="pivot pivot_wider large remodelage étaler spread",
)
def pivot(ctx, p):
    df = ctx.data()
    idx, cols = p.get("index") or [], p.get("columns") or []
    if not idx or not cols:
        raise NodeError("Choisissez au moins une colonne d'index et une colonne à étaler.")
    agg = p.get("aggfunc", "mean")
    numeric = agg in _NUMERIC_AGG
    check_columns(df, [*idx, *cols])
    # Par défaut : les autres colonnes, numériques seulement si la fonction l'exige.
    vals = p.get("values") or [c for c in df.columns if c not in idx and c not in cols
                               and (not numeric or _is_num(df[c]))]
    check_columns(df, vals)
    if not vals:
        raise NodeError("Aucune colonne de valeurs numérique : choisissez les colonnes de valeurs, "
                        "ou la fonction « first » ou « count ».")
    bad = [c for c in vals if numeric and not _is_num(df[c])]
    if bad:
        raise NodeError(f"La fonction « {agg} » demande des colonnes numériques, ce que ne sont pas : "
                        f"{', '.join(map(str, bad))}. Choisissez la fonction « first » ou « count », "
                        "ou d'autres colonnes de valeurs.")
    res = df.pivot_table(index=idx, columns=cols, values=vals, aggfunc=agg)
    res.columns = [" / ".join(str(x) for x in c) if isinstance(c, tuple) else str(c) for c in res.columns]
    return [res.reset_index()]


def _code_pivot(p, ins, outs):
    idx, cols, agg = p.get("index") or [], p.get("columns") or [], p.get("aggfunc", "mean")
    if p.get("values"):
        vals = py(p["values"])
    else:
        keep = " and pd.api.types.is_numeric_dtype(" + ins[0] + "[c])" if agg in _NUMERIC_AGG else ""
        vals = f"[c for c in {ins[0]}.columns if c not in {py([*idx, *cols])}{keep}]"
    return (f"{outs[0]} = {ins[0]}.pivot_table(index={py(idx)}, columns={py(cols)}, "
            f"values={vals}, aggfunc={py(agg)}).reset_index()")


REGISTRY["manip.pivot"].code = _code_pivot


def _names_list(s):
    return [x.strip() for x in (s or "").split(",") if x.strip()]


def _as_text(s: pd.Series) -> pd.Series:
    """Texte, en gardant les manquants manquants (avec pandas 2, astype(str) donne « nan »)."""
    return s.where(s.isna(), s.astype(str))


def _code_as_text(expr: str) -> str:
    return f"{expr}.where({expr}.isna(), {expr}.astype(str))"


@register(
    "manip.separate", "Scinder une colonne", CAT_MANIP,
    """
    Découpe une colonne de texte en plusieurs colonnes selon un séparateur
    (str.split). Utile quand une colonne encode plusieurs variables, par
    exemple « 2024-F » → année et sexe.
    """,
    inputs=[("Table", DATA)], outputs=[("Table", DATA)],
    params=[
        P("column", "Colonne à scinder", "column", "", port=0, required=True),
        P("sep", "Séparateur", "str", "_", "Vide = espaces."),
        P("into", "Noms des colonnes (séparés par des virgules ; vide = automatique)", "str", ""),
        P("drop", "Supprimer la colonne d'origine", "bool", True),
    ],
    keywords="separate split scinder découper texte colonne",
)
def separate(ctx, p):
    df = ctx.data().copy()
    col, sep = p.get("column"), p.get("sep")
    check_columns(df, [col])
    names = _names_list(p.get("into"))
    n = len(names) - 1 if names else -1
    s = _as_text(df[col])
    parts = s.str.split(sep, expand=True, regex=False, n=n) if sep else s.str.split(expand=True, n=n)
    if names:
        parts = parts.reindex(columns=range(len(names)))
        parts.columns = names
    else:
        parts.columns = [f"{col}_{i + 1}" for i in range(parts.shape[1])]
    base = df.drop(columns=[col]) if p.get("drop", True) else df
    return [pd.concat([base, parts], axis=1)]


def _code_separate(p, ins, outs):
    col, sep = py(p.get("column")), p.get("sep")
    names = _names_list(p.get("into"))
    n = len(names) - 1 if names else -1
    text = _code_as_text(f"{ins[0]}[{col}]")
    split = (f"{text}.str.split({py(sep)}, expand=True, regex=False, n={n})" if sep
             else f"{text}.str.split(expand=True, n={n})")
    lines = [f"_parts = {split}"]
    if names:
        lines.append(f"_parts = _parts.reindex(columns=range({len(names)}))")
        lines.append(f"_parts.columns = {py(names)}")
    else:
        lines.append(f"_parts.columns = [{py(str(p.get('column')) + '_')} + str(i + 1) for i in range(_parts.shape[1])]")
    base = f"{ins[0]}.drop(columns=[{col}])" if p.get("drop", True) else ins[0]
    lines.append(f"{outs[0]} = pd.concat([{base}, _parts], axis=1)")
    return "\n".join(lines)


REGISTRY["manip.separate"].code = _code_separate


@register(
    "manip.unite", "Réunir des colonnes", CAT_MANIP,
    """
    Réunit plusieurs colonnes en une seule colonne de texte, jointes par un
    séparateur. C'est l'inverse du « Scinder une colonne ». Une valeur
    manquante compte pour un texte vide ; si toutes le sont, le résultat est
    manquant.
    """,
    inputs=[("Table", DATA)], outputs=[("Table", DATA)],
    params=[
        P("columns", "Colonnes à réunir", "columns", [], port=0, required=True),
        P("name", "Nom de la colonne", "str", "réunion", required=True),
        P("sep", "Séparateur", "str", "_"),
        P("drop", "Supprimer les colonnes d'origine", "bool", True),
    ],
    keywords="unite réunir fusionner colonnes texte",
)
def unite(ctx, p):
    df = ctx.data().copy()
    cols = p.get("columns") or []
    if not cols:
        raise NodeError("Choisissez au moins une colonne à réunir.")
    check_columns(df, cols)
    sep, name = p.get("sep", "_"), p.get("name") or "réunion"
    united = (df[cols].apply(_as_text).fillna("").agg(sep.join, axis=1)
              .mask(df[cols].isna().all(axis=1)))
    if p.get("drop", True):
        df = df.drop(columns=cols)
    df[name] = united
    return [df]


REGISTRY["manip.unite"].code = lambda p, ins, outs: (
    f"{outs[0]} = {ins[0]}.copy()\n_cols = {py(p.get('columns') or [])}\n"
    f"_united = ({ins[0]}[_cols].apply(lambda s: {_code_as_text('s')}).fillna('')\n"
    f"    .agg({py(p.get('sep', '_'))}.join, axis=1).mask({ins[0]}[_cols].isna().all(axis=1)))\n"
    + (f"{outs[0]} = {outs[0]}.drop(columns=_cols)\n" if p.get("drop", True) else "")
    + f"{outs[0]}[{py(p.get('name') or 'réunion')}] = _united")


@register(
    "manip.explode", "Éclater une liste", CAT_MANIP,
    """
    Transforme une colonne de listes (ou de texte à séparateur) en une ligne
    par élément (pandas.explode), les autres colonnes étant répétées.
    """,
    inputs=[("Table", DATA)], outputs=[("Table", DATA)],
    params=[
        P("column", "Colonne à éclater", "column", "", port=0, required=True),
        P("sep", "Séparateur (si la colonne est du texte)", "str", "", "Vide = la colonne contient déjà des listes."),
    ],
    keywords="explode separate_rows éclater liste lignes",
)
def explode(ctx, p):
    df = ctx.data().copy()
    col, sep = p.get("column"), p.get("sep")
    check_columns(df, [col])
    if sep:
        df[col] = _as_text(df[col]).str.split(sep, regex=False)
    return [df.explode(col).reset_index(drop=True)]


REGISTRY["manip.explode"].code = lambda p, ins, outs: (
    f"{outs[0]} = {ins[0]}.copy()\n"
    + (f"{outs[0]}[{py(p.get('column'))}] = {_code_as_text(outs[0] + '[' + py(p.get('column')) + ']')}"
       f".str.split({py(p.get('sep'))}, regex=False)\n" if p.get("sep") else "")
    + f"{outs[0]} = {outs[0]}.explode({py(p.get('column'))}).reset_index(drop=True)")


@register(
    "manip.distinct", "Dédoublonner", CAT_MANIP,
    """
    Supprime les lignes en double (pandas.drop_duplicates), en considérant
    toutes les colonnes ou une sélection.
    """,
    inputs=[("Table", DATA)], outputs=[("Table", DATA)],
    params=[
        P("columns", "Colonnes à considérer (vide = toutes)", "columns", [], port=0),
        P("keep", "Garder", "choice", "first", choices=["first", "last"],
          choice_labels={"first": "Première occurrence", "last": "Dernière occurrence"}),
    ],
    keywords="distinct unique drop_duplicates dédoublonner doublons",
)
def distinct(ctx, p):
    df = ctx.data()
    cols = p.get("columns") or None
    if cols:
        check_columns(df, cols)
    out = df.drop_duplicates(subset=cols, keep=p.get("keep", "first"))
    ctx.messages.append(f"{len(df) - len(out)} lignes supprimées")
    return [out.reset_index(drop=True)]


REGISTRY["manip.distinct"].code = lambda p, ins, outs: (
    f"{outs[0]} = {ins[0]}.drop_duplicates(subset={py(p.get('columns') or None)}, "
    f"keep={py(p.get('keep', 'first'))}).reset_index(drop=True)")


@register(
    "manip.fill", "Propager les valeurs", CAT_MANIP,
    """
    Remplit les valeurs manquantes en propageant la dernière valeur connue vers
    l'avant (ffill) ou la suivante vers l'arrière (bfill). Pour une imputation
    statistique, utilisez SimpleImputer (catégorie Prétraitement).
    """,
    inputs=[("Table", DATA)], outputs=[("Table", DATA)],
    params=[
        P("columns", "Colonnes (vide = toutes)", "columns", [], port=0),
        P("direction", "Sens", "choice", "forward", choices=["forward", "backward"],
          choice_labels={"forward": "Vers l'avant (ffill)", "backward": "Vers l'arrière (bfill)"}),
    ],
    keywords="fill ffill bfill propager remplir manquant",
)
def fill(ctx, p):
    df = ctx.data().copy()
    cols = p.get("columns") or list(df.columns)
    check_columns(df, cols)
    method = "ffill" if p.get("direction", "forward") == "forward" else "bfill"
    df[cols] = getattr(df[cols], method)()
    return [df]


REGISTRY["manip.fill"].code = lambda p, ins, outs: (
    f"{outs[0]} = {ins[0]}.copy()\n_cols = {py(p.get('columns') or None)} or list({outs[0]}.columns)\n"
    f"{outs[0]}[_cols] = {outs[0]}[_cols].{'ffill' if p.get('direction', 'forward') == 'forward' else 'bfill'}()")


@register(
    "manip.rename", "Renommer des colonnes", CAT_MANIP,
    "Renomme des colonnes, une correspondance par ligne : `ancien -> nouveau`.",
    inputs=[("Table", DATA)], outputs=[("Table", DATA)],
    params=[P("mapping", "Correspondances", "code", "", "Une ligne par colonne : ancien -> nouveau", rows=4)],
    keywords="rename renommer nom",
)
def rename(ctx, p):
    return [ctx.data().rename(columns=_parse_mapping(p.get("mapping")))]


def _parse_mapping(text):
    mapping = {}
    for line in (text or "").splitlines():
        if "->" in line:
            a, b = line.split("->", 1)
            mapping[a.strip()] = b.strip()
    return mapping


REGISTRY["manip.rename"].code = lambda p, ins, outs: f"{outs[0]} = {ins[0]}.rename(columns={py(_parse_mapping(p.get('mapping')))})"


@register(
    "manip.python", "Script Python", CAT_MANIP,
    """
    Exécute du code Python libre. La table d'entrée est disponible dans
    `df` (et `df2` si le second port est connecté) ; affectez le résultat à
    `out`. pandas (pd), numpy (np) et sklearn sont importés.
    """,
    inputs=[("Table", DATA), ("Table 2 (optionnelle)", DATA)], outputs=[("Table", DATA)],
    params=[P("code", "Code", "code", "out = df.copy()\n", rows=12, required=True)],
    keywords="script code pandas libre custom",
)
def python_script(ctx, p):
    import sklearn
    env = {"pd": pd, "np": np, "sklearn": sklearn, "df": ctx.inputs[0].copy(),
           "df2": ctx.inputs[1].copy() if len(ctx.inputs) > 1 and isinstance(ctx.inputs[1], pd.DataFrame) else None}
    buf = io.StringIO()
    from contextlib import redirect_stdout
    try:
        with redirect_stdout(buf):
            exec(compile(p.get("code") or "", "<script>", "exec"), env)
    except Exception as e:
        raise NodeError(f"{type(e).__name__} : {e}") from e
    out = env.get("out")
    if isinstance(out, pd.Series):
        out = out.to_frame()
    if not isinstance(out, pd.DataFrame):
        raise NodeError("Le script doit affecter un DataFrame à la variable `out`.")
    if buf.getvalue():
        ctx.add_view({"type": "text", "title": "Sortie standard", "text": buf.getvalue()[-20000:], "mono": True})
    return [out]


REGISTRY["manip.python"].optional_inputs = [1]
REGISTRY["manip.python"].has_view = True
REGISTRY["manip.python"].code = lambda p, ins, outs: (
    f"df = {ins[0]}.copy()\n" + (f"df2 = {ins[1]}.copy()\n" if len(ins) > 1 and ins[1] else "")
    + (p.get("code") or "").rstrip() + f"\n{outs[0]} = out")


# --------------------------------------------------------------------------
# Visualisation
# --------------------------------------------------------------------------

@register(
    "view.statistics", "Statistiques", CAT_VIEW,
    """
    Statistiques descriptives par colonne (DataFrame.describe) : effectif,
    moyenne, écart-type, quantiles, valeurs manquantes, modalités.
    """,
    inputs=[("Table", DATA)], outputs=[("Statistiques", DATA)],
    has_view=True, color="view", keywords="describe résumé moyenne écart-type",
)
def statistics(ctx, p):
    df = ctx.data()
    rows = []
    for c in df.columns:
        s = df[c]
        num = pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s)
        rows.append({
            "colonne": str(c), "type": str(s.dtype), "non_nuls": int(s.notna().sum()),
            "manquants": int(s.isna().sum()), "uniques": int(s.nunique()),
            "moyenne": float(s.mean()) if num else None,
            "écart_type": float(s.std()) if num else None,
            "min": float(s.min()) if num else None,
            "q25": float(s.quantile(.25)) if num else None,
            "médiane": float(s.median()) if num else None,
            "q75": float(s.quantile(.75)) if num else None,
            "max": float(s.max()) if num else None,
            "mode": _jsonable(s.mode().iloc[0]) if s.notna().any() else None,
        })
    stats = pd.DataFrame(rows)
    ctx.add_view({"type": "metrics", "items": [
        {"label": "Lignes", "value": len(df)}, {"label": "Colonnes", "value": df.shape[1]},
        {"label": "Valeurs manquantes", "value": int(df.isna().sum().sum())},
        {"label": "Doublons", "value": int(df.duplicated().sum())},
    ]})
    ctx.add_view(table_block(stats.round(4), "Résumé par colonne"))
    hist = []
    for c in df.columns[:24]:
        s = df[c].dropna()
        if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s) and len(s):
            counts, edges = np.histogram(s, bins=min(20, max(5, int(np.sqrt(len(s))))))
            hist.append({"title": str(c), "counts": counts.tolist(), "edges": edges.tolist()})
        elif len(s):
            vc = s.astype(str).value_counts().head(12)
            hist.append({"title": str(c), "labels": vc.index.tolist(), "values": vc.values.tolist()})
    ctx.add_view({"type": "chart", "chart": "minihist", "title": "Distributions", "items": hist})
    return [stats]


REGISTRY["view.statistics"].code = lambda p, ins, outs: f"{outs[0]} = {ins[0]}.describe(include='all').T\nprint({outs[0]})"


@register(
    "view.scatter", "Nuage de points", CAT_VIEW,
    "Nuage de points de deux colonnes numériques, coloré par une troisième.",
    inputs=[("Table", DATA)],
    params=[
        P("x", "Axe X", "column", "", port=0, required=True),
        P("y", "Axe Y", "column", "", port=0, required=True),
        P("color", "Couleur", "column", "", port=0, allow_empty=True),
        P("max_points", "Points max.", "int", 5000),
    ],
    has_view=True, color="view", keywords="scatter plot graphique xy",
)
def scatter(ctx, p):
    df = ctx.data()
    x, y, c = p.get("x"), p.get("y"), p.get("color") or None
    check_columns(df, [x, y] + ([c] if c else []))
    d = df.sample(int(p.get("max_points") or 5000), random_state=0) if len(df) > int(p.get("max_points") or 5000) else df
    ensure_numeric(d, [x, y])
    block = {"type": "chart", "chart": "scatter", "x": d[x].tolist(), "y": d[y].tolist(),
             "xlabel": str(x), "ylabel": str(y)}
    if c:
        col = d[c]
        if pd.api.types.is_numeric_dtype(col) and col.nunique() > 12:
            block["cvalues"] = [_jsonable(v) for v in col]
        else:
            block["groups"] = [str(v) for v in col]
        block["clabel"] = str(c)
    block["x"] = [_jsonable(v) for v in block["x"]]
    block["y"] = [_jsonable(v) for v in block["y"]]
    ctx.add_view(block)
    return []


REGISTRY["view.scatter"].code = lambda p, ins, outs: (
    "# Graphique (nécessite matplotlib) :\n"
    f"# {ins[0]}.plot.scatter(x={py(p.get('x'))}, y={py(p.get('y'))}"
    + (f", c={py(p.get('color'))}, colormap='viridis'" if p.get("color") else "") + ")")


@register(
    "view.histogram", "Histogramme", CAT_VIEW,
    """
    Distribution d'une colonne : histogramme pour une variable numérique,
    diagramme en barres des effectifs pour une variable catégorielle.
    Option de regroupement par une colonne catégorielle.
    """,
    inputs=[("Table", DATA)],
    params=[
        P("column", "Colonne", "column", "", port=0, required=True),
        P("group", "Grouper par", "column", "", port=0, allow_empty=True),
        P("bins", "Nombre de classes", "int", 30),
    ],
    has_view=True, color="view", keywords="distribution barres histogram",
)
def histogram(ctx, p):
    df = ctx.data()
    col, grp = p.get("column"), p.get("group") or None
    check_columns(df, [col] + ([grp] if grp else []))
    s = df[col]
    if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
        edges = np.histogram_bin_edges(s.dropna(), bins=int(p.get("bins") or 30))
        series = []
        groups = [(None, s)] if not grp else [(str(k), g[col]) for k, g in df.groupby(grp)]
        for name, part in groups[:12]:
            counts, _ = np.histogram(part.dropna(), bins=edges)
            series.append({"name": name or str(col), "counts": counts.tolist()})
        ctx.add_view({"type": "chart", "chart": "histogram", "edges": edges.tolist(),
                      "series": series, "xlabel": str(col), "ylabel": "Effectif"})
    else:
        vc = s.astype(str).value_counts().head(40)
        ctx.add_view({"type": "chart", "chart": "bar", "labels": vc.index.tolist(),
                      "values": vc.values.tolist(), "xlabel": str(col), "ylabel": "Effectif"})
    return []


REGISTRY["view.histogram"].code = lambda p, ins, outs: f"# Graphique (nécessite matplotlib) :\n# {ins[0]}[{py(p.get('column'))}].hist(bins={p.get('bins', 30)})"


@register(
    "view.correlation", "Matrice de corrélation", CAT_VIEW,
    "Corrélations deux à deux entre colonnes numériques (Pearson, Spearman ou Kendall).",
    inputs=[("Table", DATA)], outputs=[("Corrélations", DATA)],
    params=[P("method", "Méthode", "choice", "pearson", choices=["pearson", "spearman", "kendall"])],
    has_view=True, color="view", keywords="corrélation heatmap pearson",
)
def correlation(ctx, p):
    df = ctx.data().select_dtypes("number")
    if df.shape[1] < 2:
        raise NodeError("Il faut au moins deux colonnes numériques.")
    corr = df.corr(method=p.get("method", "pearson"))
    ctx.add_view({"type": "chart", "chart": "heatmap", "labels": [str(c) for c in corr.columns],
                  "ylabels": [str(c) for c in corr.index], "matrix": np.round(corr.values, 3).tolist(),
                  "diverging": True, "vmin": -1, "vmax": 1, "title": f"Corrélation ({p.get('method', 'pearson')})"})
    return [corr.reset_index(names="colonne")]


REGISTRY["view.correlation"].code = lambda p, ins, outs: (
    f"{outs[0]} = {ins[0]}.select_dtypes('number').corr(method={py(p.get('method', 'pearson'))})\nprint({outs[0]})")


@register(
    "view.boxplot", "Boîtes à moustaches", CAT_VIEW,
    "Boîtes à moustaches des colonnes numériques, éventuellement par groupe.",
    inputs=[("Table", DATA)],
    params=[
        P("columns", "Colonnes (vide = numériques)", "columns", [], port=0),
        P("group", "Grouper par", "column", "", port=0, allow_empty=True),
        P("standardize", "Standardiser (z-score)", "bool", False),
    ],
    has_view=True, color="view", keywords="boxplot quartiles outliers",
)
def boxplot(ctx, p):
    df = ctx.data()
    cols = p.get("columns") or list(df.select_dtypes("number").columns)[:20]
    check_columns(df, cols)
    ensure_numeric(df, cols)
    grp = p.get("group") or None
    boxes = []

    def stats(s, label):
        s = s.dropna()
        if not len(s):
            return None
        q1, med, q3 = np.percentile(s, [25, 50, 75])
        iqr = q3 - q1
        lo, hi = s[s >= q1 - 1.5 * iqr].min(), s[s <= q3 + 1.5 * iqr].max()
        out = s[(s < lo) | (s > hi)]
        return {"label": label, "q1": float(q1), "median": float(med), "q3": float(q3),
                "lo": float(lo), "hi": float(hi), "outliers": out.head(200).astype(float).tolist()}

    for c in cols:
        s = df[c]
        if p.get("standardize"):
            s = (s - s.mean()) / (s.std() or 1)
        if grp:
            for k, part in s.groupby(df[grp]):
                b = stats(part, f"{c} · {k}")
                if b:
                    boxes.append(b)
        else:
            b = stats(s, str(c))
            if b:
                boxes.append(b)
    ctx.add_view({"type": "chart", "chart": "box", "boxes": boxes[:60]})
    return []


REGISTRY["view.boxplot"].code = lambda p, ins, outs: f"# Graphique (nécessite matplotlib) :\n# {ins[0]}.plot.box()"


@register(
    "view.table", "Vue de table", CAT_VIEW,
    "Affiche la table complète, paginée et triable, dans le panneau des sorties.",
    inputs=[("Table", DATA)], outputs=[("Table", DATA)],
    color="view", keywords="afficher table données voir",
)
def table_view(ctx, p):
    return [ctx.data()]


REGISTRY["view.table"].code = lambda p, ins, outs: f"{outs[0]} = {ins[0]}\nprint({outs[0]}.head(20))"


# --------------------------------------------------------------------------
# Nœuds scikit-learn générés : apprenants, clustering, transformeurs
# --------------------------------------------------------------------------

def build_estimator(cls, hp_specs, p, **fixed):
    """Instancie ``cls`` avec les hyperparamètres modifiés (``fixed`` : paramètres imposés)."""
    kwargs = {}
    for spec in hp_specs:
        name = spec["name"]
        if name not in p:
            continue
        raw = p[name]
        if raw is None or raw == "":
            continue
        val = parse_literal(raw) if spec["type"] == "literal" or (spec["type"] == "bool" and isinstance(raw, str)) else raw
        if spec["type"] == "literal" and isinstance(raw, str) and raw.strip() == spec["default_repr"]:
            continue
        kwargs[name] = val
    try:
        return cls(**kwargs, **fixed), kwargs
    except TypeError as e:
        raise NodeError(f"Paramètre invalide : {e}") from e


def hp_code(kwargs) -> str:
    return ", ".join(f"{k}={v!r}" for k, v in kwargs.items())


def _fit_message(e: Exception) -> NodeError:
    msg = str(e)
    if "could not convert string to float" in msg:
        msg += " — encodez les variables catégorielles (OneHotEncoder…) ou excluez-les."
    if "Input X contains NaN" in msg or "Input contains NaN" in msg:
        msg = ("Les données contiennent des valeurs manquantes. Ajoutez un nœud SimpleImputer "
               "ou « Lignes incomplètes » en amont, ou choisissez un estimateur qui les gère "
               "(HistGradientBoosting…).")
    return NodeError(msg)


def _transformer_message(e: Exception, name: str, df, cols, chosen: bool) -> NodeError:
    """Erreur d'un transformeur qui a reçu des colonnes texte : dire lesquelles et quoi faire."""
    msg = str(e)
    if "could not convert string to float" in msg or "non-numeric data" in msg:
        bad = [c for c in cols if c in df.columns and not pd.api.types.is_numeric_dtype(df[c])]
        if bad:
            names = ", ".join(f"« {c} »" for c in bad[:6]) + ("…" if len(bad) > 6 else "")
            scope = "Les colonnes choisies incluent" if chosen else \
                "Aucune colonne n'étant choisie, toutes sont transformées, y compris"
            what = "la colonne texte" if len(bad) == 1 else "les colonnes texte"
            return NodeError(
                f"{name} n'accepte que des colonnes numériques. {scope} {what} {names}. "
                "Si c'est la colonne à prédire, indiquez-la dans le champ « Cible » ; sinon, choisissez "
                "les « Colonnes à transformer » ou encodez d'abord ces colonnes (OneHotEncoder, OrdinalEncoder).")
    return _fit_message(e)


def _make_learner(name, info, kind):
    cls = info["cls"]
    base_param = sk_catalog.OPTIONAL_BASE.get(name)
    hps = [h for h in sk_catalog.hyperparams(cls) if h["name"] != base_param]
    supervised = kind in ("classifier", "regressor")
    accepts_weight = supervised and "sample_weight" in inspect.signature(cls.fit).parameters
    params = []
    if supervised:
        params.append(P("target", "Colonne cible", "column", "", port=0, required=True, group="Données"))
    params.append(P("features", "Variables explicatives (vide = toutes les autres)" if supervised
                    else "Variables (vide = toutes les numériques)", "columns", [], port=0, group="Données"))
    if accepts_weight:
        params.append(P("sample_weight", "Poids des observations (sample_weight)", "column", "", port=0,
                        allow_empty=True, group="Données", help="Colonne numérique de poids, facultative."))
    if kind == "cluster":
        params.append(P("label_column", "Nom de la colonne de cluster", "str", "Cluster", group="Données"))
    params += hps
    kind_fr = {"classifier": "classification", "regressor": "régression", "cluster": "clustering"}[kind]
    desc = (f"{info['summary']}\n\nNœud d'apprentissage ({kind_fr}) généré à partir de "
            f"{info['module']}.{name}.")
    if base_param:
        desc += (f" L'entrée « Estimateur de base » (facultative) fournit le paramètre {base_param} : "
                 "branchez la sortie d'un autre nœud d'apprentissage.")
    if supervised:
        desc += " Connectez la sortie modèle à un nœud « Prédicteur » pour l'appliquer à de nouvelles données."
        outputs = [("Modèle", MODEL)]
    else:
        desc += " La sortie table contient l'étiquette de cluster de chaque ligne."
        outputs = [("Table + clusters", DATA), ("Modèle", MODEL)]
    type_id = f"sk.{kind}.{name}"

    def run(ctx: Ctx, p):
        df = ctx.data()
        est, kwargs = build_estimator(cls, hps, p)
        if base_param and len(ctx.inputs) > 1 and ctx.inputs[1] is not None:
            est.set_params(**{base_param: clone(ctx.model(1).estimator)})
        target = p.get("target") if supervised else None
        if supervised:
            if not target:
                raise NodeError("Choisissez la colonne cible.")
            check_columns(df, [target], "Colonne cible")
        weight = p.get("sample_weight") or None
        if not supervised and not p.get("features"):
            feats = list(df.select_dtypes("number").columns)
        else:
            feats = resolve_features(df, p.get("features"), exclude=[c for c in (target, weight) if c])
        ensure_numeric(df, feats)
        if name == "IsotonicRegression" and len(feats) != 1:
            raise NodeError("La régression isotonique n'utilise qu'une seule variable : choisissez-la.")
        X = df[feats]
        with warnings.catch_warnings(record=True) as wlist:
            warnings.simplefilter("always")
            try:
                if supervised:
                    y = df[target]
                    if y.isna().any():
                        raise NodeError("La colonne cible contient des valeurs manquantes.")
                    if weight:
                        check_columns(df, [weight], "Colonne de poids")
                        est.fit(X, y, sample_weight=df[weight])
                    else:
                        est.fit(X, y)
                    labels = None
                else:
                    labels = est.fit_predict(X) if hasattr(est, "fit_predict") else est.fit(X).predict(X)
            except NodeError:
                raise
            except Exception as e:
                raise _fit_message(e) from e
        for w in wlist[:3]:
            ctx.messages.append(f"{w.category.__name__} : {str(w.message)[:200]}")
        model = ModelPort(est, kind, name, feats, target,
                          classes=list(est.classes_) if hasattr(est, "classes_") else None)
        _learner_view(ctx, model, X, df[target] if supervised else labels)
        if supervised:
            return [model]
        out = df.copy()
        out[p.get("label_column") or "Cluster"] = labels
        return [out, model]

    def code(p, ins, outs):
        _, kwargs = build_estimator(cls, hps, p)
        target = p.get("target")
        feats = p.get("features") or None
        mvar = outs[-1]
        lines = []
        if feats:
            lines.append(f"features = {py(feats)}")
        elif supervised:
            lines.append(f"features = [c for c in {ins[0]}.columns if c != {py(target)}]")
        else:
            lines.append(f"features = list({ins[0]}.select_dtypes('number').columns)")
        if base_param and len(ins) > 1 and ins[1]:
            kwargs = {**kwargs, base_param: f"clone({ins[1]})"}
            lines.append(f"{mvar} = {name}({', '.join(f'{k}={v}' if k == base_param else f'{k}={v!r}' for k, v in kwargs.items())})")
        else:
            lines.append(f"{mvar} = {name}({hp_code(kwargs)})")
        weight = p.get("sample_weight")
        if weight:
            lines[0] = lines[0].replace(f"c != {py(target)}]", f"c not in ({py(target)}, {py(weight)})]")
        if supervised:
            w = f", sample_weight={ins[0]}[{py(weight)}]" if weight else ""
            lines.append(f"{mvar}.fit({ins[0]}[features], {ins[0]}[{py(target)}]{w})")
            lines.append(f"{mvar}.features_, {mvar}.target_ = features, {py(target)}")
        else:
            lines.append(f"{outs[0]} = {ins[0]}.copy()")
            lines.append(f"{outs[0]}[{py(p.get('label_column') or 'Cluster')}] = {mvar}.fit_predict({ins[0]}[features])")
            lines.append(f"{mvar}.features_ = features")
        return "\n".join(lines)

    kind_en = {"classifier": "classification", "regressor": "regression", "cluster": "clustering"}[kind]
    desc_en = f"{info['summary']}\n\nLearner ({kind_en}) generated from {info['module']}.{name}."
    if base_param:
        desc_en += (f" The optional “Base estimator” input provides the {base_param} parameter: "
                    "connect the output of another learner.")
    desc_en += (" Connect the model output to a “Predictor” node to apply it to new data." if supervised
                else " The output table contains the cluster label of each row.")
    inputs = [("Table", DATA)] + ([("Estimateur de base (optionnel)", MODEL)] if base_param else [])
    REGISTRY[type_id] = NodeType(
        type_id, name, sk_catalog.KIND_CATEGORY[kind], desc, inputs, outputs, params,
        run, code, family=info["family"], doc_url=info["doc_url"], has_view=True,
        color={"classifier": "learner", "regressor": "learner", "cluster": "cluster"}[kind],
        keywords=f"{info['module']} {kind_fr} {info['keywords']}",
        optional_inputs=[1] if base_param else [], module=info["module"], kind=kind, description_en=desc_en,
    )
    REGISTRY[type_id].sk_import = (info["module"], name)


def _learner_view(ctx: Ctx, model: ModelPort, X, y):
    est = model.estimator
    items = [{"label": "Lignes", "value": len(X)}, {"label": "Variables", "value": X.shape[1]}]
    try:
        if model.kind == "classifier":
            items.append({"label": "Exactitude (apprentissage)", "value": round(float(est.score(X, y)), 4)})
            items.append({"label": "Classes", "value": len(model.classes or [])})
        elif model.kind == "regressor":
            items.append({"label": "R² (apprentissage)", "value": round(float(est.score(X, y)), 4)})
        elif model.kind == "cluster" and y is not None:
            labels = np.asarray(y)
            k = len(set(labels) - {-1})
            items.append({"label": "Clusters", "value": k})
            if 1 < k < len(X):
                items.append({"label": "Silhouette", "value": round(float(skm.silhouette_score(X, labels, sample_size=min(len(X), 3000), random_state=0)), 4)})
            if -1 in set(labels):
                items.append({"label": "Bruit (-1)", "value": int((labels == -1).sum())})
    except Exception:
        pass
    ctx.add_view({"type": "metrics", "items": items})
    imp = feature_importance_values(est, model.features)
    if imp is not None:
        ctx.add_view(imp)
    if model.kind == "cluster" and y is not None:
        vc = pd.Series(np.asarray(y)).value_counts().sort_index()
        ctx.add_view({"type": "chart", "chart": "bar", "title": "Taille des clusters",
                      "labels": [str(i) for i in vc.index], "values": vc.values.tolist()})
    ctx.add_view({"type": "model", "summary": model.summary()})


def feature_importance_values(est, features):
    vals, title = None, None
    if hasattr(est, "feature_importances_"):
        vals, title = np.asarray(est.feature_importances_), "Importance des variables (feature_importances_)"
    elif hasattr(est, "coef_"):
        coef = np.asarray(est.coef_)
        vals = np.abs(coef).mean(axis=0) if coef.ndim > 1 else coef
        title = "Coefficients (coef_)" if coef.ndim == 1 else "|Coefficients| moyens (coef_)"
    if vals is None or len(vals) != len(features):
        return None
    order = np.argsort(-np.abs(vals))[:30]
    return {"type": "chart", "chart": "hbar", "title": title,
            "labels": [str(features[i]) for i in order], "values": [float(vals[i]) for i in order]}


# Transformeurs qui n'ont de sens que sur des colonnes texte / catégorielles, ou que sur des nombres :
# sans sélection de colonnes, ils ne prennent que celles-là (au lieu de toutes, ce qui échouait).
TEXT_ENCODERS = {"OneHotEncoder", "OrdinalEncoder", "TargetEncoder"}
NUMERIC_ONLY = {"StandardScaler", "MinMaxScaler", "MaxAbsScaler", "RobustScaler", "Normalizer",
                "QuantileTransformer", "PowerTransformer", "PCA", "IncrementalPCA", "KernelPCA", "TruncatedSVD",
                "FastICA", "FactorAnalysis", "KBinsDiscretizer", "PolynomialFeatures", "SplineTransformer",
                "Binarizer"}
# Transformeurs supervisés que les étiquettes de scikit-learn ne signalent pas toujours.
NEEDS_TARGET = {"SelectKBest", "SelectPercentile", "SelectFpr", "SelectFdr", "SelectFwe",
                "GenericUnivariateSelect", "RFE", "RFECV", "SequentialFeatureSelector"}


def _is_text(s: pd.Series) -> bool:
    return not pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_datetime64_any_dtype(s)


def default_columns(name: str, df: pd.DataFrame, target) -> list[str]:
    """Colonnes transformées quand aucune n'est choisie (la cible est toujours exclue)."""
    rest = [c for c in df.columns if c != target]
    if name in TEXT_ENCODERS:
        return [c for c in rest if _is_text(df[c])]
    if name in NUMERIC_ONLY:
        return [c for c in rest if pd.api.types.is_numeric_dtype(df[c])]
    return rest


def _needs_target(est) -> bool:
    if type(est).__name__ in NEEDS_TARGET:
        return True
    try:
        return bool(est.__sklearn_tags__().target_tags.required)
    except Exception:
        return False


def _make_transformer(name, info):
    cls = info["cls"]
    hps = sk_catalog.hyperparams(cls)
    cols_label = ("Colonnes à transformer (vide = toutes les colonnes texte)" if name in TEXT_ENCODERS
                  else "Colonnes à transformer (vide = toutes les colonnes numériques)" if name in NUMERIC_ONLY
                  else "Colonnes à transformer (vide = toutes sauf la cible)")
    params = [
        P("columns", cols_label, "columns", [], port=0, group="Données"),
        P("target", "Cible (transformeurs supervisés uniquement)", "column", "", port=0,
          allow_empty=True, group="Données",
          help="Requise par ex. pour SelectKBest ou LinearDiscriminantAnalysis. Reste dans la table."),
    ] + hps
    desc = (f"{info['summary']}\n\nTransformeur généré à partir de {info['module']}.{name}. "
            "Il est ajusté (fit) sur la table d'entrée et appliqué aux colonnes choisies ; les autres "
            "colonnes sont conservées (ColumnTransformer, remainder='passthrough'). La sortie modèle "
            "permet d'appliquer exactement la même transformation à d'autres données via le nœud "
            "« Appliquer un transformeur ».")
    type_id = f"sk.transformer.{name}"

    def make(p):
        est, kwargs = build_estimator(cls, hps, p)
        if "sparse_output" in est.get_params() and "sparse_output" not in kwargs:
            est.set_params(sparse_output=False)
            kwargs["sparse_output"] = False
        return est, kwargs

    def run(ctx: Ctx, p):
        df = ctx.data()
        target = p.get("target") or None
        if target:
            check_columns(df, [target], "Colonne cible")
        est, _ = make(p)
        if _needs_target(est) and not target:
            raise NodeError(f"{name} a besoin de la colonne à prédire : choisissez-la dans le champ "
                            "« Cible (transformeurs supervisés uniquement) ». Elle n'est pas transformée "
                            "et reste dans la table.")
        if p.get("columns"):
            cols = resolve_features(df, p.get("columns"), exclude=[target] if target else [])
        else:
            cols = default_columns(name, df, target)
            if not cols:
                kind = "texte" if name in TEXT_ENCODERS else "numérique"
                raise NodeError(f"Aucune colonne {kind} à transformer dans la table"
                                + (f" (hors cible « {target} »)." if target else "."))
            if name in TEXT_ENCODERS or name in NUMERIC_ONLY:
                shown = ", ".join(cols[:12]) + ("…" if len(cols) > 12 else "")
                ctx.messages.append(f"Colonnes choisies automatiquement : {shown}")
        y = df[target] if target else None
        if not hasattr(est, "transform"):
            return _embedding_only(ctx, est, name, df, cols, y)
        ct = ColumnTransformer([(name, est, cols)], remainder="passthrough",
                               verbose_feature_names_out=False)
        try:
            try:
                ct.set_output(transform="pandas")
                out = ct.fit_transform(df, y)
            except Exception as e:
                if "set_output" not in str(e) and "get_feature_names_out" not in str(e) and "pandas" not in str(e):
                    raise
                ct = ColumnTransformer([(name, est, cols)], remainder="passthrough",
                                       verbose_feature_names_out=False)
                arr = ct.fit_transform(df, y)
                out = _to_frame(arr, ct, name, df.index)
        except NodeError:
            raise
        except Exception as e:
            raise _transformer_message(e, name, df, cols, bool(p.get("columns"))) from e
        out.index = df.index
        model = ModelPort(ct, "transformer", name, cols, target, output_columns=[str(c) for c in out.columns])
        ctx.add_view({"type": "metrics", "items": [
            {"label": "Colonnes en entrée", "value": len(cols)},
            {"label": "Colonnes en sortie", "value": out.shape[1]},
            {"label": "Lignes", "value": len(out)}]})
        inner = ct.named_transformers_[name]
        if hasattr(inner, "explained_variance_ratio_"):
            evr = np.asarray(inner.explained_variance_ratio_)
            ctx.add_view({"type": "chart", "chart": "bar", "title": "Variance expliquée par composante",
                          "labels": [f"C{i + 1}" for i in range(len(evr))], "values": evr.round(4).tolist(),
                          "cumulative": np.cumsum(evr).round(4).tolist(), "ylabel": "Ratio"})
        if hasattr(inner, "scores_") and len(np.atleast_1d(inner.scores_)) == len(cols):
            ctx.add_view(feature_importance_values(type("S", (), {"feature_importances_": np.nan_to_num(inner.scores_)})(), cols)
                         | {"title": "Scores des variables (scores_)"})
        ctx.add_view({"type": "model", "summary": model.summary()})
        return [out, model]

    def code(p, ins, outs):
        est, kwargs = make(p)
        target = p.get("target")
        cols = p.get("columns")
        lines = []
        if cols:
            lines.append(f"cols = {py(cols)}")
        elif name in TEXT_ENCODERS:
            lines.append(f"cols = [c for c in {ins[0]}.select_dtypes(exclude=['number', 'datetime']).columns "
                         f"if c != {py(target or None)}]")
        elif name in NUMERIC_ONLY:
            lines.append(f"cols = [c for c in {ins[0]}.select_dtypes('number').columns if c != {py(target or None)}]")
        else:
            lines.append(f"cols = [c for c in {ins[0]}.columns if c != {py(target)}]" if target
                         else f"cols = list({ins[0]}.columns)")
        if not hasattr(est, "transform"):   # fit_transform uniquement (MDS, SpectralEmbedding…)
            y = f", {ins[0]}[{py(target)}]" if target else ""
            lines.append(f"{outs[1]} = {name}({hp_code(kwargs)})")
            lines.append(f"_emb = {outs[1]}.fit_transform({ins[0]}[cols]{y})")
            lines.append(f"{outs[0]} = pd.concat([pd.DataFrame(_emb, columns=[f'{name.lower()}{{i}}' for i in range(_emb.shape[1])], "
                         f"index={ins[0]}.index), {ins[0]}.drop(columns=cols)], axis=1)")
            return "\n".join(lines)
        y = f", {ins[0]}[{py(target)}]" if target else ""
        if not hasattr(est, "set_output"):   # sortie numpy/creuse : on reconstruit la table
            lines.append(f"{outs[1]} = ColumnTransformer([({py(name)}, {name}({hp_code(kwargs)}), cols)], "
                         f"remainder='passthrough', sparse_threshold=0, verbose_feature_names_out=False)")
            lines.append(f"{outs[0]} = pd.DataFrame({outs[1]}.fit_transform({ins[0]}{y}), "
                         f"columns={outs[1]}.get_feature_names_out(), index={ins[0]}.index)")
            return "\n".join(lines)
        lines.append(f"{outs[1]} = ColumnTransformer([({py(name)}, {name}({hp_code(kwargs)}), cols)], "
                     f"remainder='passthrough', verbose_feature_names_out=False).set_output(transform='pandas')")
        lines.append(f"{outs[0]} = {outs[1]}.fit_transform({ins[0]}{y})")
        return "\n".join(lines)

    REGISTRY[type_id] = NodeType(
        type_id, name, sk_catalog.KIND_CATEGORY["transformer"], desc, [("Table", DATA)],
        [("Table transformée", DATA), ("Transformeur", MODEL)], params, run, code,
        family=info["family"], doc_url=info["doc_url"], has_view=True, color="transformer",
        keywords=f"{info['module']} prétraitement transformation {info['keywords']}",
        module=info["module"], kind="transformer",
        description_en=(f"{info['summary']}\n\nTransformer generated from {info['module']}.{name}. It is fitted on "
                        "the input table and applied to the chosen columns; other columns are kept (ColumnTransformer, "
                        "remainder='passthrough'). The model output applies exactly the same transformation to other "
                        "data with the “Transformer apply” node."),
    )
    REGISTRY[type_id].sk_import = (info["module"], name)


def _embedding_only(ctx: Ctx, est, name, df, cols, y):
    """Estimateurs sans ``transform`` (MDS, SpectralEmbedding…) : fit_transform uniquement."""
    ensure_numeric(df, cols)
    try:
        arr = est.fit_transform(df[cols], y) if y is not None else est.fit_transform(df[cols])
    except Exception as e:
        raise _fit_message(e) from e
    arr = np.asarray(arr.toarray() if hasattr(arr, "toarray") else arr)
    emb = pd.DataFrame(arr, columns=[f"{name.lower()}{i}" for i in range(arr.shape[1])], index=df.index)
    out = pd.concat([emb, df.drop(columns=cols)], axis=1)
    model = ModelPort(est, "embedding", name, list(cols), None, output_columns=[str(c) for c in out.columns])
    ctx.messages.append(f"{name} ne sait pas transformer de nouvelles données : la sortie modèle ne s'applique "
                        "pas à un jeu de test (fit_transform uniquement).")
    ctx.add_view({"type": "metrics", "items": [{"label": "Colonnes en entrée", "value": len(cols)},
                                               {"label": "Dimensions en sortie", "value": arr.shape[1]}]})
    if arr.shape[1] >= 2:
        ctx.add_view({"type": "chart", "chart": "scatter", "title": "Plongement (2 premières dimensions)",
                      "x": arr[:, 0].round(5).tolist()[:5000], "y": arr[:, 1].round(5).tolist()[:5000],
                      "xlabel": emb.columns[0], "ylabel": emb.columns[1]})
    ctx.add_view({"type": "model", "summary": model.summary()})
    return [out, model]


def _to_frame(arr, ct, name, index):
    if hasattr(arr, "toarray"):
        arr = arr.toarray()
    arr = np.asarray(arr)
    try:
        cols = [str(c) for c in ct.get_feature_names_out()]
        if len(cols) != arr.shape[1]:
            raise ValueError
    except Exception:
        cols = [f"{name.lower()}{i}" for i in range(arr.shape[1])]
    return pd.DataFrame(arr, columns=cols, index=index)


# --------------------------------------------------------------------------
# Estimateurs non supervisés « à score » : anomalies, covariance, densité, voisins
# --------------------------------------------------------------------------

UNSUP_KINDS = {
    "outlier": ("Détection d'anomalies", "outlier", "Table + anomalies"),
    "covariance": ("Estimation de covariance", "covariance", "Table + distance de Mahalanobis"),
    "density": ("Estimation de densité", "density", "Table + log-densité"),
    "neighbors": ("Plus proches voisins", "neighbors", "Table + voisins"),
}


def _make_unsupervised(name, info, kind):
    cls = info["cls"]
    hps = sk_catalog.hyperparams(cls)
    title, color, out_name = UNSUP_KINDS[kind]
    params = [P("features", "Variables (vide = toutes les numériques)", "columns", [], port=0, group="Données")]
    if kind == "outlier":
        params.append(P("label_column", "Nom de la colonne d'anomalie", "str", "Anomalie", group="Données"))
    params += hps
    explain = {
        "outlier": ("La table de sortie indique pour chaque ligne si elle est jugée anormale (1) ou normale (0), "
                    "avec un score (plus il est bas, plus la ligne est atypique). Le Prédicteur applique le "
                    "modèle à de nouvelles données (nouveautés)."),
        "covariance": ("La table de sortie contient la distance de Mahalanobis de chaque ligne au centre "
                       "estimé ; la vue montre la matrice de covariance."),
        "density": "La table de sortie contient le logarithme de la densité estimée en chaque ligne (score_samples).",
        "neighbors": ("La table de sortie contient, pour chaque ligne, l'index et la distance de ses plus "
                      "proches voisins (le premier voisin est la ligne elle-même)."),
    }[kind]
    desc = f"{info['summary']}\n\n{title} : nœud généré à partir de {info['module']}.{name}. {explain}"
    explain_en = {
        "outlier": ("The output table flags each row as an outlier (1) or inlier (0), with a score (the lower, "
                    "the more atypical). The Predictor applies the model to new data (novelty detection)."),
        "covariance": "The output table contains each row's Mahalanobis distance to the estimated centre; the view shows the covariance matrix.",
        "density": "The output table contains the log of the estimated density at each row (score_samples).",
        "neighbors": "The output table contains, for each row, the index and distance of its nearest neighbours (the first neighbour is the row itself).",
    }[kind]
    desc_en = f"{info['summary']}\n\nNode generated from {info['module']}.{name}. {explain_en}"
    type_id = f"sk.{kind}.{name}"

    def run(ctx: Ctx, p):
        df = ctx.data()
        feats = p.get("features") or list(df.select_dtypes("number").columns)
        check_columns(df, feats)
        ensure_numeric(df, feats)
        X = df[feats]
        est, _ = build_estimator(cls, hps, p)
        out = df.copy()
        items = [{"label": "Lignes", "value": len(df)}, {"label": "Variables", "value": len(feats)}]
        try:
            if kind == "outlier":
                # LocalOutlierFactor(novelty=True) n'a pas fit_predict : on ajuste puis on prédit.
                labels = est.fit_predict(X) if hasattr(est, "fit_predict") else est.fit(X).predict(X)
                col = p.get("label_column") or "Anomalie"
                out[col] = (labels == -1).astype(int)
                score = None
                try:
                    score = est.score_samples(X)
                except Exception:
                    score = getattr(est, "negative_outlier_factor_", None)
                if score is not None:
                    out[f"{col} (score)"] = np.asarray(score, dtype=float)
                n_out = int((labels == -1).sum())
                items += [{"label": "Anomalies", "value": n_out},
                          {"label": "Proportion", "value": f"{100 * n_out / max(1, len(df)):.1f} %"}]
                if len(feats) >= 2:
                    ctx.add_view({"type": "chart", "chart": "scatter", "title": "Anomalies (2 premières variables)",
                                  "x": X[feats[0]].astype(float).round(5).tolist()[:5000],
                                  "y": X[feats[1]].astype(float).round(5).tolist()[:5000],
                                  "groups": np.where(labels == -1, "anomalie", "normal").tolist()[:5000],
                                  "xlabel": str(feats[0]), "ylabel": str(feats[1]), "clabel": col})
                if score is not None:
                    counts, edges = np.histogram(np.asarray(score, dtype=float), bins=30)
                    ctx.add_view({"type": "chart", "chart": "histogram", "title": "Distribution des scores",
                                  "edges": edges.tolist(), "series": [{"name": "score", "counts": counts.tolist()}],
                                  "xlabel": "Score (bas = atypique)", "ylabel": "Effectif"})
            elif kind == "covariance":
                est.fit(X)
                out["Distance de Mahalanobis"] = np.sqrt(est.mahalanobis(X))
                cov = np.asarray(est.covariance_)
                ctx.add_view({"type": "chart", "chart": "heatmap", "title": "Matrice de covariance estimée",
                              "labels": [str(f) for f in feats], "ylabels": [str(f) for f in feats],
                              "matrix": np.round(cov, 4).tolist(), "diverging": True})
            elif kind == "density":
                est.fit(X)
                out["Log-densité"] = est.score_samples(X)
                counts, edges = np.histogram(out["Log-densité"], bins=30)
                ctx.add_view({"type": "chart", "chart": "histogram", "title": "Distribution de la log-densité",
                              "edges": edges.tolist(), "series": [{"name": "log-densité", "counts": counts.tolist()}],
                              "xlabel": "Log-densité", "ylabel": "Effectif"})
            else:
                est.fit(X)
                dist, idx = est.kneighbors(X)
                for j in range(idx.shape[1]):
                    out[f"voisin_{j + 1}"] = df.index.to_numpy()[idx[:, j]]
                    out[f"distance_{j + 1}"] = dist[:, j]
        except NodeError:
            raise
        except Exception as e:
            raise _fit_message(e) from e
        model = ModelPort(est, kind, name, feats, None)
        ctx.add_view({"type": "metrics", "items": items}, {"type": "model", "summary": model.summary()})
        ctx.view = [ctx.view[-2]] + ctx.view[:-2] + [ctx.view[-1]]
        return [out, model]

    def code(p, ins, outs):
        _, kwargs = build_estimator(cls, hps, p)
        feats = p.get("features")
        m, o = outs[1], outs[0]
        lines = [f"features = {py(feats)}" if feats else f"features = list({ins[0]}.select_dtypes('number').columns)",
                 f"{m} = {name}({hp_code(kwargs)})", f"{o} = {ins[0]}.copy()"]
        if kind == "outlier":
            col = p.get("label_column") or "Anomalie"
            lines.append(f"{o}[{py(col)}] = ({m}.fit({ins[0]}[features]).predict({ins[0]}[features]) == -1).astype(int)")
        elif kind == "covariance":
            lines += [f"{m}.fit({ins[0]}[features])", f"{o}['Distance de Mahalanobis'] = np.sqrt({m}.mahalanobis({ins[0]}[features]))"]
        elif kind == "density":
            lines += [f"{m}.fit({ins[0]}[features])", f"{o}['Log-densité'] = {m}.score_samples({ins[0]}[features])"]
        else:
            lines += [f"{m}.fit({ins[0]}[features])", f"_dist, _idx = {m}.kneighbors({ins[0]}[features])"]
        lines.append(f"{m}.features_, {m}.kind_ = features, {kind!r}")
        return "\n".join(lines)

    REGISTRY[type_id] = NodeType(
        type_id, name, title, desc, [("Table", DATA)], [(out_name, DATA), ("Modèle", MODEL)], params, run, code,
        family=info["family"], doc_url=info["doc_url"], has_view=True, color="cluster",
        keywords=f"{info['module']} {title.lower()} {info['keywords']}", module=info["module"], kind=kind,
        description_en=desc_en,
    )
    REGISTRY[type_id].sk_import = (info["module"], name)


def _register_sklearn():
    for name, info in sk_catalog.estimators().items():
        for kind in info["kinds"]:
            if kind == "transformer":
                _make_transformer(name, info)
            elif kind in UNSUP_KINDS:
                _make_unsupervised(name, info, kind)
            else:
                _make_learner(name, info, kind)


_register_sklearn()


# --------------------------------------------------------------------------
# Application de modèles
# --------------------------------------------------------------------------

@register(
    "apply.predictor", "Prédicteur", CAT_APPLY,
    """
    Applique un modèle entraîné (classification, régression ou clustering
    disposant de predict) à une table. Ajoute la colonne « Prediction
    (cible) » et, en option, les probabilités de chaque classe
    (predict_proba), nécessaires à la courbe ROC.
    """,
    inputs=[("Modèle", MODEL), ("Table", DATA)], outputs=[("Table + prédictions", DATA)],
    params=[
        P("proba", "Ajouter les probabilités", "bool", True),
        P("column", "Nom de la colonne (vide = automatique)", "str", ""),
    ],
    color="apply", keywords="predict prédiction appliquer scorer",
)
def predictor(ctx, p):
    m, df = ctx.model(0), ctx.data(1)
    if m.kind in ("transformer", "embedding"):
        raise NodeError("Ce modèle est un transformeur : utilisez « Appliquer un transformeur ».")
    if m.kind in ("covariance", "density", "neighbors"):
        raise NodeError(f"{m.name} ne fait pas de prédiction : son résultat est dans sa table de sortie.")
    if not hasattr(m.estimator, "predict"):
        raise NodeError(f"{m.name} ne sait pas prédire de nouvelles données (pas de méthode predict).")
    check_columns(df, m.features, "Variable du modèle")
    X = df[m.features]
    out = df.copy()
    if isinstance(m.target, (list, tuple)):
        try:
            pred = np.asarray(m.estimator.predict(X))
        except Exception as e:
            raise _fit_message(e) from e
        for j, t in enumerate(m.target):
            out[f"Prediction ({t})"] = pred[:, j]
        return [out]
    if m.kind == "outlier":
        try:
            out[p.get("column") or "Anomalie (prédite)"] = (np.asarray(m.estimator.predict(X)) == -1).astype(int)
        except AttributeError as e:
            raise NodeError(f"{m.name} ne s'applique pas à de nouvelles données dans ce réglage "
                            "(pour LocalOutlierFactor, activez novelty=True).") from e
        return [out]
    col = p.get("column") or (f"Prediction ({m.target})" if m.target else "Prediction (Cluster)")
    try:
        out[col] = m.estimator.predict(X)
        if p.get("proba", True) and m.kind == "classifier" and hasattr(m.estimator, "predict_proba"):
            proba = m.estimator.predict_proba(X)
            for i, c in enumerate(m.classes or range(proba.shape[1])):
                out[f"P ({m.target}={c})"] = proba[:, i]
    except Exception as e:
        raise _fit_message(e) from e
    return [out]


def _code_predictor(p, ins, outs):
    m, d, o = ins[0], ins[1], outs[0]
    col = py(p["column"]) if p.get("column") else None
    default_col = "f\"Prediction ({_target or 'Cluster'})\""
    lines = [f"{o} = {d}.copy()",
             f"_target = getattr({m}, 'target_', None)",
             f"_pred = {m}.predict({d}[{m}.features_])",
             "if isinstance(_target, list):  # plusieurs cibles",
             "    for _j, _t in enumerate(_target):",
             f"        {o}[f'Prediction ({{_t}})'] = np.asarray(_pred)[:, _j]",
             f"elif getattr({m}, 'kind_', None) == 'outlier':  # détection d'anomalies : -1 = anomalie",
             f"    {o}[{col or repr('Anomalie (prédite)')}] = (_pred == -1).astype(int)",
             "else:",
             f"    {o}[{col or default_col}] = _pred"]
    if p.get("proba", True):
        lines += [f"    if hasattr({m}, 'predict_proba') and hasattr({m}, 'classes_') and _target is not None:",
                  f"        _proba = {m}.predict_proba({d}[{m}.features_])",
                  f"        for _i, _c in enumerate({m}.classes_):",
                  f"            {o}[f'P ({{_target}}={{_c}})'] = _proba[:, _i]"]
    return "\n".join(lines)


REGISTRY["apply.predictor"].code = _code_predictor


@register(
    "apply.transformer", "Appliquer un transformeur", CAT_APPLY,
    """
    Applique un transformeur déjà ajusté (sortie modèle d'un nœud de
    prétraitement) à une nouvelle table, typiquement le jeu de test : la
    normalisation apprise sur l'apprentissage est réutilisée sans fuite
    d'information.
    """,
    inputs=[("Transformeur", MODEL), ("Table", DATA)], outputs=[("Table transformée", DATA)],
    color="apply", keywords="transform apply appliquer normalisation test",
)
def apply_transformer(ctx, p):
    m, df = ctx.model(0), ctx.data(1)
    if m.kind != "transformer":
        raise NodeError("Ce modèle n'est pas un transformeur : utilisez le « Prédicteur ».")
    check_columns(df, m.features, "Colonne du transformeur")
    try:
        out = m.estimator.transform(df)
    except Exception as e:
        raise _fit_message(e) from e
    if not isinstance(out, pd.DataFrame):
        out = pd.DataFrame(out.toarray() if hasattr(out, "toarray") else out,
                           columns=m.output_columns, index=df.index)
    out.index = df.index
    return [out]


REGISTRY["apply.transformer"].code = lambda p, ins, outs: f"{outs[0]} = {ins[0]}.transform({ins[1]})"


# --------------------------------------------------------------------------
# Évaluation
# --------------------------------------------------------------------------

def _true_pred(df, p):
    pred = p.get("pred") or detect_prediction_column(df)
    true = p.get("true") or detect_target_from_prediction(df, pred)
    if not pred or not true:
        raise NodeError("Choisissez la colonne réelle et la colonne prédite.")
    check_columns(df, [true, pred])
    return true, pred


def _code_true_pred(p, ins):
    pred = py(p["pred"]) if p.get("pred") else f"next(c for c in {ins[0]}.columns if str(c).startswith('Prediction'))"
    true = py(p["true"]) if p.get("true") else "_pred[len('Prediction ('):-1]"
    return f"_pred = {pred}\n_true = {true}\n"


@register(
    "score.classification", "Évaluation classification", CAT_SCORE,
    """
    Compare la colonne réelle et la colonne prédite : matrice de confusion,
    exactitude, précision, rappel, F1, kappa de Cohen, MCC, Jaccard, pertes de
    Hamming et 0-1 (sklearn.metrics). Avec les probabilités du Prédicteur,
    ajoute le log-loss et l'exactitude top-2. Les colonnes sont détectées
    automatiquement après un Prédicteur.
    """,
    inputs=[("Table + prédictions", DATA)], outputs=[("Métriques", DATA), ("Matrice de confusion", DATA)],
    params=[
        P("true", "Colonne réelle (auto si vide)", "column", "", port=0, allow_empty=True),
        P("pred", "Colonne prédite (auto si vide)", "column", "", port=0, allow_empty=True),
    ],
    has_view=True, color="score", doc_url="https://scikit-learn.org/stable/modules/model_evaluation.html#classification-metrics",
    keywords="scorer accuracy précision rappel f1 confusion",
)
def score_classification(ctx, p):
    df = ctx.data()
    true, pred = _true_pred(df, p)
    yt, yp = df[true], df[pred]
    if yt.isna().any():
        raise NodeError("La colonne réelle contient des valeurs manquantes.")
    labels = sorted(set(yt.unique()) | set(yp.unique()), key=str)
    cm = skm.confusion_matrix(yt, yp, labels=labels)
    rep = skm.classification_report(yt, yp, labels=labels, output_dict=True, zero_division=0)
    metrics = {
        "Exactitude": skm.accuracy_score(yt, yp),
        "Exactitude équilibrée": skm.balanced_accuracy_score(yt, yp),
        "Précision (macro)": rep["macro avg"]["precision"],
        "Rappel (macro)": rep["macro avg"]["recall"],
        "F1 (macro)": rep["macro avg"]["f1-score"],
        "F1 (pondéré)": rep["weighted avg"]["f1-score"],
        "Kappa de Cohen": skm.cohen_kappa_score(yt, yp),
        "MCC": skm.matthews_corrcoef(yt, yp),
        "Jaccard (macro)": skm.jaccard_score(yt, yp, average="macro", zero_division=0),
        "Perte de Hamming": skm.hamming_loss(yt, yp),
        "Perte 0-1": skm.zero_one_loss(yt, yp),
    }
    if len(labels) == 2:  # Rapports de vraisemblance (classification binaire).
        try:
            lrp, lrn = skm.class_likelihood_ratios(yt, yp)
            for k, v in (("LR+", lrp), ("LR−", lrn)):
                if np.isfinite(v):          # infini sans faux positif / faux négatif
                    metrics[k] = float(v)
        except Exception:
            pass
    prob_cols = [c for c in df.columns if re.match(r"P \((.+)=(.+)\)$", str(c))]
    if prob_cols:  # Métriques probabilistes si le Prédicteur a ajouté les probabilités.
        try:
            classes = [re.match(r"P \(.+?=(.+)\)$", str(c)).group(1) for c in prob_cols]
            yt_str, proba = yt.astype(str), df[prob_cols].to_numpy(float)
            if set(yt_str.unique()) <= set(classes):
                metrics["Log-loss"] = float(skm.log_loss(yt_str, proba, labels=classes))
                if len(classes) >= 3:
                    metrics["Exactitude top-2"] = float(skm.top_k_accuracy_score(yt_str, proba, k=2, labels=classes))
        except Exception:
            pass
    mdf = pd.DataFrame({"métrique": list(metrics), "valeur": [float(v) for v in metrics.values()]})
    cmdf = pd.DataFrame(cm, index=[str(l) for l in labels], columns=[str(l) for l in labels])
    cmdf.index.name = "réel \\ prédit"
    per_class = pd.DataFrame([
        {"classe": str(l), "précision": rep[str(l)]["precision"], "rappel": rep[str(l)]["recall"],
         "f1": rep[str(l)]["f1-score"], "effectif": int(rep[str(l)]["support"])}
        for l in labels if str(l) in rep
    ])
    ctx.add_view({"type": "metrics", "items": [{"label": k, "value": round(float(v), 4)} for k, v in list(metrics.items())[:6]]})
    ctx.add_view({"type": "chart", "chart": "heatmap", "title": "Matrice de confusion",
                  "labels": [str(l) for l in labels], "ylabels": [str(l) for l in labels],
                  "matrix": cm.tolist(), "xlabel": "Prédit", "ylabel": "Réel", "annot": True})
    ctx.add_view(table_block(per_class.round(4), "Rapport par classe"))
    return [mdf, cmdf.reset_index()]


REGISTRY["score.classification"].code = lambda p, ins, outs: (
    _code_true_pred(p, ins) +
    f"print(metrics.classification_report({ins[0]}[_true], {ins[0]}[_pred]))\n"
    f"print(metrics.confusion_matrix({ins[0]}[_true], {ins[0]}[_pred]))\n"
    f"{outs[0]} = pd.DataFrame({{'métrique': ['Exactitude'], 'valeur': [metrics.accuracy_score({ins[0]}[_true], {ins[0]}[_pred])]}})")


@register(
    "score.regression", "Évaluation régression", CAT_SCORE,
    """
    Métriques de régression : R², MAE, RMSE, MAPE, erreur médiane, variance
    expliquée, D² (erreur absolue). Sur cibles positives, ajoute MSLE/RMSLE et
    les déviances de Poisson et Gamma. La vue montre les valeurs prédites
    contre les valeurs réelles et la distribution des résidus.
    """,
    inputs=[("Table + prédictions", DATA)], outputs=[("Métriques", DATA)],
    params=[
        P("true", "Colonne réelle (auto si vide)", "column", "", port=0, allow_empty=True),
        P("pred", "Colonne prédite (auto si vide)", "column", "", port=0, allow_empty=True),
    ],
    has_view=True, color="score", doc_url="https://scikit-learn.org/stable/modules/model_evaluation.html#regression-metrics",
    keywords="numeric scorer r2 rmse mae erreur résidus",
)
def score_regression(ctx, p):
    df = ctx.data()
    true, pred = _true_pred(df, p)
    ensure_numeric(df, [true, pred])
    d = df[[true, pred]].dropna()
    yt, yp = d[true].to_numpy(float), d[pred].to_numpy(float)
    metrics = {
        "R²": skm.r2_score(yt, yp),
        "MAE": skm.mean_absolute_error(yt, yp),
        "RMSE": skm.root_mean_squared_error(yt, yp),
        "MSE": skm.mean_squared_error(yt, yp),
        "Erreur absolue médiane": skm.median_absolute_error(yt, yp),
        "MAPE": skm.mean_absolute_percentage_error(yt, yp),
        "Variance expliquée": skm.explained_variance_score(yt, yp),
        "Erreur max": skm.max_error(yt, yp),
        "D² (erreur absolue)": skm.d2_absolute_error_score(yt, yp),
    }
    # Métriques à domaine restreint : cibles (et prédictions) positives.
    if (yt >= 0).all() and (yp >= 0).all():
        try:
            metrics["MSLE"] = skm.mean_squared_log_error(yt, yp)
            metrics["RMSLE"] = skm.root_mean_squared_log_error(yt, yp)
        except Exception:
            pass
    if (yt >= 0).all() and (yp > 0).all():
        try:
            metrics["Déviance de Poisson"] = skm.mean_poisson_deviance(yt, yp)
        except Exception:
            pass
    if (yt > 0).all() and (yp > 0).all():
        try:
            metrics["Déviance Gamma"] = skm.mean_gamma_deviance(yt, yp)
        except Exception:
            pass
    ctx.add_view({"type": "metrics", "items": [{"label": k, "value": float(v)} for k, v in list(metrics.items())[:6]]})
    idx = np.random.default_rng(0).permutation(len(yt))[:4000]
    ctx.add_view({"type": "chart", "chart": "scatter", "title": "Prédit vs réel",
                  "x": yt[idx].tolist(), "y": yp[idx].tolist(), "xlabel": f"Réel ({true})",
                  "ylabel": "Prédit", "diagonal": True})
    res = yp - yt
    counts, edges = np.histogram(res, bins=30)
    ctx.add_view({"type": "chart", "chart": "histogram", "title": "Distribution des résidus (prédit − réel)",
                  "edges": edges.tolist(), "series": [{"name": "Résidus", "counts": counts.tolist()}],
                  "xlabel": "Résidu", "ylabel": "Effectif"})
    return [pd.DataFrame({"métrique": list(metrics), "valeur": [float(v) for v in metrics.values()]})]


REGISTRY["score.regression"].code = lambda p, ins, outs: (
    _code_true_pred(p, ins) +
    f"{outs[0]} = pd.DataFrame({{'métrique': ['R²', 'MAE', 'RMSE'], 'valeur': [\n"
    f"    metrics.r2_score({ins[0]}[_true], {ins[0]}[_pred]),\n"
    f"    metrics.mean_absolute_error({ins[0]}[_true], {ins[0]}[_pred]),\n"
    f"    metrics.root_mean_squared_error({ins[0]}[_true], {ins[0]}[_pred])]}})\nprint({outs[0]})")


def _cramers_v(ct):
    """V de Cramér à partir d'une table de contingence (numpy, sans scipy)."""
    ct = np.asarray(ct, dtype=float)
    n = ct.sum()
    if n == 0:
        return float("nan")
    expected = ct.sum(1, keepdims=True) @ ct.sum(0, keepdims=True) / n
    with np.errstate(divide="ignore", invalid="ignore"):
        chi2 = np.nansum(np.where(expected > 0, (ct - expected) ** 2 / expected, 0.0))
    denom = n * (min(ct.shape) - 1)
    return float(np.sqrt(chi2 / denom)) if denom > 0 else float("nan")


@register(
    "score.concordance", "Concordance entre deux colonnes", CAT_SCORE,
    """
    Mesure l'association entre deux colonnes catégorielles : table de
    contingence, V de Cramér, indice de Rand ajusté, information mutuelle
    (ajustée, normalisée), V-mesure (homogénéité, complétude) et
    Fowlkes–Mallows (sklearn.metrics). Sert aussi à comparer un clustering à
    une vérité terrain (deux étiquetages). Quand les deux colonnes emploient
    les mêmes catégories, l'accord brut et le kappa de Cohen sont ajoutés.
    """,
    inputs=[("Table", DATA)], outputs=[("Métriques", DATA), ("Table de contingence", DATA)],
    params=[
        P("col1", "Première colonne", "column", "", port=0, required=True),
        P("col2", "Deuxième colonne", "column", "", port=0, required=True),
    ],
    has_view=True, color="score",
    doc_url="https://scikit-learn.org/stable/modules/clustering.html#clustering-performance-evaluation",
    keywords="scorer concordance accord association contingence cramér rand mutual information kappa catégorielle",
)
def score_concordance(ctx, p):
    df = ctx.data()
    c1, c2 = p.get("col1"), p.get("col2")
    if not c1 or not c2:
        raise NodeError("Choisissez les deux colonnes à comparer.")
    check_columns(df, [c1, c2])
    d = df[[c1, c2]].dropna()
    if len(d) == 0:
        raise NodeError("Aucune ligne sans valeur manquante dans les deux colonnes.")
    a, b = d[c1], d[c2]
    ct = pd.crosstab(a, b)
    metrics = {
        "V de Cramér": _cramers_v(ct.to_numpy()),
        "Indice de Rand ajusté": skm.adjusted_rand_score(a, b),
        "Information mutuelle ajustée": skm.adjusted_mutual_info_score(a, b),
        "Information mutuelle normalisée": skm.normalized_mutual_info_score(a, b),
        "V-mesure": skm.v_measure_score(a, b),
        "Homogénéité": skm.homogeneity_score(a, b),
        "Complétude": skm.completeness_score(a, b),
        "Fowlkes–Mallows": skm.fowlkes_mallows_score(a, b),
        "Indice de Rand": skm.rand_score(a, b),
        "Information mutuelle": skm.mutual_info_score(a, b),
    }
    ua, ub = set(a.unique()), set(b.unique())
    if ua & ub and len(ua & ub) / len(ua | ub) >= 0.5:  # Mêmes catégories : accord pertinent.
        metrics["Accord brut"] = skm.accuracy_score(a, b)
        metrics["Kappa de Cohen"] = skm.cohen_kappa_score(a, b)
    head = ["V de Cramér", "Indice de Rand ajusté", "Information mutuelle ajustée", "V-mesure", "Fowlkes–Mallows"]
    head += ["Kappa de Cohen"] if "Kappa de Cohen" in metrics else ["Homogénéité"]
    ctx.add_view({"type": "metrics", "items": [  # « — » : non défini (une colonne constante, par exemple)
        {"label": k, "value": round(float(metrics[k]), 4) if np.isfinite(metrics[k]) else "—"} for k in head]})
    ctx.add_view({"type": "chart", "chart": "heatmap", "title": "Table de contingence",
                  "labels": [str(c) for c in ct.columns], "ylabels": [str(i) for i in ct.index],
                  "matrix": ct.to_numpy().tolist(), "xlabel": str(c2), "ylabel": str(c1), "annot": True})
    mdf = pd.DataFrame({"métrique": list(metrics), "valeur": [float(v) for v in metrics.values()]})
    return [mdf, ct.reset_index()]


REGISTRY["score.concordance"].code = lambda p, ins, outs: (
    f"_d = {ins[0]}[[{py(p.get('col1'))}, {py(p.get('col2'))}]].dropna()\n"
    f"_a, _b = _d[{py(p.get('col1'))}], _d[{py(p.get('col2'))}]\n"
    f"{outs[1]} = pd.crosstab(_a, _b)\nprint({outs[1]})\n"
    f"# V de Cramér : à calculer depuis la table de contingence (pas de fonction scikit-learn).\n"
    f"{outs[0]} = pd.DataFrame({{'métrique': ['ARI', 'AMI', 'V-mesure', 'Fowlkes-Mallows'], 'valeur': [\n"
    f"    metrics.adjusted_rand_score(_a, _b), metrics.adjusted_mutual_info_score(_a, _b),\n"
    f"    metrics.v_measure_score(_a, _b), metrics.fowlkes_mallows_score(_a, _b)]}})\n"
    f"{outs[1]} = {outs[1]}.reset_index()")


def _detect_label_column(df):
    if "Cluster" in df.columns:
        return "Cluster"
    return detect_prediction_column(df)


@register(
    "score.clustering", "Qualité du clustering", CAT_SCORE,
    """
    Qualité d'un clustering sans vérité terrain, à partir des variables et de
    la colonne de clusters : coefficient de silhouette (global et par cluster),
    indice de Calinski–Harabasz (plus haut = mieux) et indice de
    Davies–Bouldin (plus bas = mieux) (sklearn.metrics). Pour comparer le
    clustering à une étiquette connue, utilisez « Concordance entre deux
    colonnes ».
    """,
    inputs=[("Table + clusters", DATA)], outputs=[("Métriques", DATA), ("Silhouette par cluster", DATA)],
    params=[
        P("labels", "Colonne de clusters (auto si vide)", "column", "", port=0, allow_empty=True),
        P("features", "Variables (vide = toutes les numériques)", "columns", [], port=0),
    ],
    has_view=True, color="score",
    doc_url="https://scikit-learn.org/stable/modules/clustering.html#clustering-performance-evaluation",
    keywords="scorer silhouette calinski harabasz davies bouldin clustering qualité",
)
def score_clustering(ctx, p):
    df = ctx.data()
    lab = p.get("labels") or _detect_label_column(df)
    if not lab:
        raise NodeError("Choisissez la colonne de clusters.")
    check_columns(df, [lab])
    feats = p.get("features") or [
        c for c in df.columns
        if c != lab and (pd.api.types.is_numeric_dtype(df[c]) or pd.api.types.is_bool_dtype(df[c]))
    ]
    if not feats:
        raise NodeError("Aucune variable numérique pour évaluer le clustering.")
    check_columns(df, feats)
    ensure_numeric(df, feats)
    d = df[[*feats, lab]].dropna()
    X, labels = d[feats].to_numpy(float), np.asarray(d[lab])
    k = len(set(labels))
    if not (2 <= k < len(X)):
        raise NodeError("La silhouette demande entre 2 clusters et n−1 lignes : vérifiez la colonne de clusters.")
    sil = skm.silhouette_samples(X, labels)
    metrics = {
        "Silhouette": float(np.mean(sil)),
        "Calinski–Harabasz": float(skm.calinski_harabasz_score(X, labels)),
        "Davies–Bouldin": float(skm.davies_bouldin_score(X, labels)),
    }
    per = (pd.DataFrame({"cluster": labels, "silhouette": sil})
           .groupby("cluster", as_index=False)
           .agg(silhouette=("silhouette", "mean"), taille=("silhouette", "size"))
           .sort_values("cluster"))
    ctx.add_view({"type": "metrics", "items": [{"label": k2, "value": round(v, 4)} for k2, v in metrics.items()]})
    ctx.add_view({"type": "chart", "chart": "hbar", "title": "Silhouette moyenne par cluster",
                  "labels": [str(c) for c in per["cluster"]], "values": per["silhouette"].round(4).tolist()})
    ctx.add_view(table_block(per.round(4), "Silhouette par cluster"))
    mdf = pd.DataFrame({"métrique": list(metrics), "valeur": [float(v) for v in metrics.values()]})
    return [mdf, per.reset_index(drop=True)]


def _code_clustering(p, ins, outs):
    lab = py(p["labels"]) if p.get("labels") else repr("Cluster")
    feats = (py(p["features"]) if p.get("features")
             else f"[c for c in {ins[0]}.columns if c != _lab and pd.api.types.is_numeric_dtype({ins[0]}[c])]")
    return (f"_lab = {lab}\n_feats = {feats}\n"
            f"_d = {ins[0]}[_feats + [_lab]].dropna()\n_X, _y = _d[_feats], _d[_lab]\n"
            f"{outs[0]} = pd.DataFrame({{'métrique': ['Silhouette', 'Calinski-Harabasz', 'Davies-Bouldin'], 'valeur': [\n"
            f"    metrics.silhouette_score(_X, _y), metrics.calinski_harabasz_score(_X, _y),\n"
            f"    metrics.davies_bouldin_score(_X, _y)]}})\nprint({outs[0]})\n"
            f"{outs[1]} = (pd.DataFrame({{'cluster': _y, 'silhouette': metrics.silhouette_samples(_X, _y)}})\n"
            f"    .groupby('cluster', as_index=False)['silhouette'].mean())")


REGISTRY["score.clustering"].code = _code_clustering


@register(
    "score.roc", "Courbe ROC", CAT_SCORE,
    """
    Courbes ROC (un contre tous) et aire sous la courbe pour chaque classe, à
    partir des colonnes de probabilités « P (cible=classe) » produites par
    le Prédicteur. Affiche aussi la courbe précision-rappel.
    """,
    inputs=[("Table + probabilités", DATA)], outputs=[("AUC", DATA)],
    params=[P("true", "Colonne réelle (auto si vide)", "column", "", port=0, allow_empty=True)],
    has_view=True, color="score", doc_url="https://scikit-learn.org/stable/modules/generated/sklearn.metrics.roc_curve.html",
    keywords="roc auc courbe précision rappel",
)
def score_roc(ctx, p):
    df = ctx.data()
    prob_cols = [c for c in df.columns if re.match(r"P \((.+)=(.+)\)$", str(c))]
    if not prob_cols:
        raise NodeError("Aucune colonne de probabilité « P (cible=classe) ». Activez « Ajouter les probabilités » dans le Prédicteur.")
    target = p.get("true") or re.match(r"P \((.+?)=", prob_cols[0]).group(1)
    check_columns(df, [target])
    yt = df[target].astype(str)
    curves, pr, rows = [], [], []
    for c in prob_cols:
        cls = re.match(r"P \(.+?=(.+)\)$", str(c)).group(1)
        pos = (yt == cls).astype(int)
        if pos.nunique() < 2:
            continue
        fpr, tpr, _ = skm.roc_curve(pos, df[c])
        auc = skm.auc(fpr, tpr)
        prec, rec, _ = skm.precision_recall_curve(pos, df[c])
        ap = skm.average_precision_score(pos, df[c])
        step = max(1, len(fpr) // 400)
        curves.append({"name": f"{cls} (AUC={auc:.3f})", "x": fpr[::step].tolist() + [1.0], "y": tpr[::step].tolist() + [1.0]})
        step = max(1, len(rec) // 400)
        pr.append({"name": f"{cls} (AP={ap:.3f})", "x": rec[::step].tolist(), "y": prec[::step].tolist()})
        rows.append({"classe": cls, "AUC": float(auc), "précision moyenne": float(ap)})
        if len(prob_cols) == 2:
            break
    if not rows:
        raise NodeError("Impossible de calculer la courbe : une seule classe présente.")
    ctx.add_view({"type": "metrics", "items": [{"label": f"AUC {r['classe']}", "value": round(r["AUC"], 4)} for r in rows]})
    ctx.add_view({"type": "chart", "chart": "line", "title": "Courbe ROC", "series": curves,
                  "xlabel": "Taux de faux positifs", "ylabel": "Taux de vrais positifs", "diagonal": True,
                  "domain": [0, 1]})
    ctx.add_view({"type": "chart", "chart": "line", "title": "Précision-rappel", "series": pr,
                  "xlabel": "Rappel", "ylabel": "Précision", "domain": [0, 1]})
    return [pd.DataFrame(rows)]


REGISTRY["score.roc"].code = lambda p, ins, outs: (
    f"# Courbe ROC : metrics.RocCurveDisplay.from_predictions(y_true == classe, {ins[0]}['P (cible=classe)'])")


@register(
    "score.importance", "Importance des variables", CAT_EXPLAIN,
    """
    Importance par permutation (sklearn.inspection.permutation_importance) :
    baisse du score quand on mélange chaque variable. Fonctionne avec tout
    modèle supervisé ; à calculer de préférence sur le jeu de test.
    """,
    inputs=[("Modèle", MODEL), ("Table", DATA)], outputs=[("Importances", DATA)],
    params=[
        P("n_repeats", "Répétitions", "int", 5),
        P("scoring", "Score", "literal", "", "Vide = score par défaut du modèle. Ex. 'f1_macro', 'r2'."),
        P("random_state", "Graine aléatoire", "int", 0),
    ],
    has_view=True, color="explain",
    doc_url="https://scikit-learn.org/stable/modules/permutation_importance.html",
    keywords="permutation importance variables explicabilité",
)
def score_importance(ctx, p):
    from sklearn.inspection import permutation_importance
    m, df = ctx.model(0), ctx.data(1)
    if m.kind not in ("classifier", "regressor"):
        raise NodeError("Un modèle supervisé est requis.")
    check_columns(df, m.features + [m.target])
    r = permutation_importance(m.estimator, df[m.features], df[m.target],
                               n_repeats=int(p.get("n_repeats") or 5),
                               scoring=parse_literal(p.get("scoring")) or None,
                               random_state=p.get("random_state"), n_jobs=n_jobs(len(df)))
    out = pd.DataFrame({"variable": m.features, "importance": r.importances_mean,
                        "écart_type": r.importances_std}).sort_values("importance", ascending=False)
    ctx.add_view({"type": "chart", "chart": "hbar", "title": "Importance par permutation",
                  "labels": out["variable"].astype(str).tolist()[:30], "values": out["importance"].round(5).tolist()[:30],
                  "errors": out["écart_type"].round(5).tolist()[:30]})
    return [out]


REGISTRY["score.importance"].code = lambda p, ins, outs: (
    f"_r = permutation_importance({ins[0]}, {ins[1]}[{ins[0]}.features_], {ins[1]}[{ins[0]}.target_], "
    f"n_repeats={int(p.get('n_repeats') or 5)}, random_state={p.get('random_state')})\n"
    f"{outs[0]} = pd.DataFrame({{'variable': {ins[0]}.features_, 'importance': _r.importances_mean}})"
    ".sort_values('importance', ascending=False)")


# --------------------------------------------------------------------------
# Validation croisée et recherche d'hyperparamètres
# --------------------------------------------------------------------------

# Stratégies de validation croisée (sklearn.model_selection).
CV_STRATEGIES = {
    "auto": "Automatique (StratifiedKFold en classification, sinon KFold)",
    "kfold": "KFold", "stratified": "StratifiedKFold",
    "repeated": "RepeatedKFold", "repeated_stratified": "RepeatedStratifiedKFold",
    "shuffle": "ShuffleSplit", "stratified_shuffle": "StratifiedShuffleSplit",
    "group": "GroupKFold (par groupes)", "stratified_group": "StratifiedGroupKFold (par groupes)",
    "group_shuffle": "GroupShuffleSplit (par groupes)", "leave_one_group_out": "LeaveOneGroupOut (par groupes)",
    "time_series": "TimeSeriesSplit (séries temporelles)", "leave_one_out": "LeaveOneOut",
}
GROUP_STRATEGIES = {"group", "stratified_group", "group_shuffle", "leave_one_group_out"}


def cv_params(data_port: int, default_k: int = 5) -> list[dict]:
    g = "Validation croisée"
    return [
        P("cv_strategy", "Stratégie", "choice", "auto", choices=list(CV_STRATEGIES), choice_labels=CV_STRATEGIES, group=g),
        P("cv", "Nombre de plis (k)", "int", default_k, min=2, group=g),
        P("n_repeats", "Répétitions (stratégies répétées)", "int", 3, min=1, group=g),
        P("test_size", "Part de test (stratégies ShuffleSplit)", "float", 0.2, group=g),
        P("groups", "Colonne de groupes (stratégies par groupes)", "column", "", port=data_port, allow_empty=True, group=g,
          help="Les lignes d'un même groupe (patient, client, site…) restent du même côté de la séparation."),
        P("shuffle", "Mélanger", "bool", True, group=g),
        P("random_state", "Graine aléatoire", "int", 0, group=g),
    ]


def make_cv(p: dict, kind: str | None, df: pd.DataFrame | None, multi_target: bool = False):
    """Renvoie (splitter, groups, code Python du splitter)."""
    from sklearn import model_selection as ms
    strat = p.get("cv_strategy") or "auto"
    k = int(p.get("cv") or 5)
    shuffle = bool(p.get("shuffle", True))
    rs = p.get("random_state")
    if strat == "auto":
        strat = "stratified" if kind == "classifier" and not multi_target else "kfold"
    rsk = rs if shuffle else None
    spec = {
        "kfold": ("KFold", dict(n_splits=k, shuffle=shuffle, random_state=rsk)),
        "stratified": ("StratifiedKFold", dict(n_splits=k, shuffle=shuffle, random_state=rsk)),
        "repeated": ("RepeatedKFold", dict(n_splits=k, n_repeats=int(p.get("n_repeats") or 3), random_state=rs)),
        "repeated_stratified": ("RepeatedStratifiedKFold", dict(n_splits=k, n_repeats=int(p.get("n_repeats") or 3), random_state=rs)),
        "shuffle": ("ShuffleSplit", dict(n_splits=k, test_size=float(p.get("test_size") or 0.2), random_state=rs)),
        "stratified_shuffle": ("StratifiedShuffleSplit", dict(n_splits=k, test_size=float(p.get("test_size") or 0.2), random_state=rs)),
        "group": ("GroupKFold", dict(n_splits=k)),
        "stratified_group": ("StratifiedGroupKFold", dict(n_splits=k, shuffle=shuffle, random_state=rsk)),
        "group_shuffle": ("GroupShuffleSplit", dict(n_splits=k, test_size=float(p.get("test_size") or 0.2), random_state=rs)),
        "leave_one_group_out": ("LeaveOneGroupOut", {}),
        "time_series": ("TimeSeriesSplit", dict(n_splits=k)),
        "leave_one_out": ("LeaveOneOut", {}),
    }.get(strat)
    if spec is None:
        raise NodeError(f"Stratégie de validation inconnue : {strat}")
    cls_name, kwargs = spec
    groups = None
    if strat in GROUP_STRATEGIES and df is not None:
        col = p.get("groups")
        if not col:
            raise NodeError("Cette stratégie demande une colonne de groupes.")
        check_columns(df, [col], "Colonne de groupes")
        groups = df[col]
    code = f"{cls_name}({', '.join(f'{a}={b!r}' for a, b in kwargs.items())})"
    return getattr(ms, cls_name)(**kwargs), groups, code


def _scorer_names():
    try:
        return sorted(skm.get_scorer_names())
    except Exception:
        return ["accuracy", "f1_macro", "r2", "neg_mean_squared_error"]


def supervised_target(m: "ModelPort", df: pd.DataFrame):
    """Vérifie un modèle supervisé et renvoie (X, y, multisortie)."""
    if m.kind not in ("classifier", "regressor"):
        raise NodeError("Un modèle supervisé (classification ou régression) est requis.")
    targets = list(m.target) if isinstance(m.target, (list, tuple)) else [m.target]
    check_columns(df, list(m.features) + targets)
    y = df[targets] if len(targets) > 1 else df[targets[0]]
    return df[m.features], y, len(targets) > 1


def cv_code(p: dict, model: str, data: str) -> tuple[str, str]:
    """Code Python (splitter, groupes) correspondant aux paramètres de validation."""
    strat = p.get("cv_strategy") or "auto"
    if strat == "auto":
        k, sh, rs = int(p.get("cv") or 5), bool(p.get("shuffle", True)), p.get("random_state")
        return (f"(StratifiedKFold if is_classifier({model}) else KFold)(n_splits={k}, shuffle={sh}, "
                f"random_state={rs if sh else None})", "None")
    code = make_cv(p, None, None)[2]
    groups = f"{data}[{py(p.get('groups'))}]" if strat in GROUP_STRATEGIES and p.get("groups") else "None"
    return code, groups


@register(
    "tune.cross_validation", "Validation croisée", CAT_TUNE,
    """
    Évalue la configuration d'un modèle par validation croisée
    (sklearn.model_selection.cross_validate). Connectez la sortie d'un nœud
    d'apprentissage ou d'un Pipeline : ses hyperparamètres, variables et cible
    sont repris, et le modèle est réentraîné sur chaque pli. Toutes les
    stratégies de scikit-learn sont disponibles : k plis, répétées, par
    groupes, séries temporelles, leave-one-out…
    """,
    inputs=[("Modèle (configuration)", MODEL), ("Table", DATA)], outputs=[("Scores par pli", DATA)],
    params=[
        P("scoring", "Métriques", "multichoice", [], "Vide = score par défaut (exactitude ou R²).",
          choices=_scorer_names()),
        *cv_params(1),
    ],
    has_view=True, color="tune",
    doc_url="https://scikit-learn.org/stable/modules/cross_validation.html",
    keywords="cross validation k-fold cv évaluation groupkfold timeseriessplit leave one out",
)
def cross_validation(ctx, p):
    m, df = ctx.model(0), ctx.data(1)
    X, y, multi = supervised_target(m, df)
    cv, groups, _ = make_cv(p, m.kind, df, multi)
    scoring = p.get("scoring") or None
    nested = _is_search(m.estimator)
    if nested and _needs_groups(m.estimator.cv):
        raise NodeError("Validation croisée imbriquée : la recherche interne utilise une stratégie par groupes, "
                        "non prise en charge ici. Choisissez une autre stratégie dans la recherche "
                        "(la validation externe peut, elle, être par groupes).")
    try:
        r = cross_validate(clone(m.estimator), X, y, cv=cv, groups=groups, scoring=scoring,
                           return_train_score=True, return_estimator=nested, n_jobs=n_jobs(len(X)))
    except Exception as e:
        raise _fit_message(e) from e
    chosen = [est.best_params_ for est in r.pop("estimator")] if nested else []
    out = pd.DataFrame({k.replace("test_", "test · ").replace("train_", "train · "): v for k, v in r.items()})
    out.insert(0, "pli", range(1, len(out) + 1))
    for name in (chosen[0] if chosen else {}):
        out[f"choisi · {name}"] = [str(c.get(name)) for c in chosen]
    tests = [c for c in out.columns if c.startswith("test · ")]
    ctx.add_view({"type": "metrics", "items": [
        {"label": f"{c[7:]} (moyenne ± écart-type)", "value": f"{out[c].mean():.4f} ± {out[c].std():.4f}"} for c in tests]
        + [{"label": "Plis", "value": len(out)}]})
    if len(out) <= 30:
        ctx.add_view({"type": "chart", "chart": "groupedbar", "title": "Score par pli",
                      "labels": [f"Pli {i}" for i in out["pli"]],
                      "series": [{"name": c, "values": out[c].round(4).tolist()} for c in out.columns
                                 if c.startswith(("test · ", "train · "))][:6]})
    summary = out.drop(columns=["pli"] + [c for c in out.columns if c.startswith("choisi · ")])
    summary = summary.agg(["mean", "std"]).T.reset_index(names="mesure")
    ctx.add_view(table_block(summary.round(5), "Synthèse"))
    if nested:
        ctx.messages.append("Validation croisée imbriquée : la recherche d'hyperparamètres est refaite dans "
                            "chaque pli externe ; le score évalue la procédure de réglage complète.")
        choice = out[["pli"] + [c for c in out.columns if c.startswith("choisi · ")]]
        # Juste après les indicateurs : c'est l'information propre à la validation imbriquée.
        ctx.view.insert(1, table_block(choice.rename(columns=lambda c: c.replace("choisi · ", "")),
                                       "Hyperparamètres choisis dans chaque pli (validation imbriquée)"))
    return [out]


def _is_search(est) -> bool:
    from sklearn.model_selection._search import BaseSearchCV
    return isinstance(est, BaseSearchCV)


def _needs_groups(cv) -> bool:
    from sklearn import model_selection as ms
    return isinstance(cv, (ms.GroupKFold, ms.StratifiedGroupKFold, ms.GroupShuffleSplit, ms.LeaveOneGroupOut))


def _code_cv(p, ins, outs):
    splitter, groups = cv_code(p, ins[0], ins[1])
    return (f"_cv = {splitter}\n"
            f"_r = cross_validate(clone({ins[0]}), {ins[1]}[{ins[0]}.features_], {ins[1]}[{ins[0]}.target_], cv=_cv, "
            f"groups={groups}, scoring={py(p.get('scoring') or None)}, return_train_score=True)\n"
            f"{outs[0]} = pd.DataFrame(_r)\nprint({outs[0]}.mean())")


REGISTRY["tune.cross_validation"].code = _code_cv


@register(
    "tune.cross_val_predict", "Prédictions hors pli", CAT_TUNE,
    """
    Prédit chaque ligne avec un modèle qui ne l'a pas vue à l'entraînement
    (sklearn.model_selection.cross_val_predict). La table obtenue se branche
    sur les nœuds d'évaluation (matrice de confusion, ROC, résidus…) pour
    évaluer sur toute la table, sans jeu de test séparé.
    """,
    inputs=[("Modèle (configuration)", MODEL), ("Table", DATA)], outputs=[("Table + prédictions", DATA)],
    params=[P("proba", "Ajouter les probabilités (classification)", "bool", True), *cv_params(1)],
    color="tune",
    doc_url="https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.cross_val_predict.html",
    keywords="cross_val_predict hors pli out of fold prédictions validation croisée",
)
def cross_val_predict_node(ctx, p):
    from sklearn.model_selection import cross_val_predict
    m, df = ctx.model(0), ctx.data(1)
    X, y, multi = supervised_target(m, df)
    cv, groups, _ = make_cv(p, m.kind, df, multi)
    if p.get("cv_strategy") in ("repeated", "repeated_stratified", "shuffle", "stratified_shuffle", "group_shuffle", "time_series"):
        raise NodeError("cross_val_predict exige une partition (chaque ligne testée une fois) : "
                        "choisissez KFold, StratifiedKFold, GroupKFold ou LeaveOneOut.")
    out = df.copy()
    try:
        want_proba = (not multi and p.get("proba", True) and m.kind == "classifier"
                      and hasattr(m.estimator, "predict_proba"))
        proba = None
        if want_proba:
            proba = cross_val_predict(clone(m.estimator), X, y, cv=cv, groups=groups,
                                      method="predict_proba", n_jobs=n_jobs(len(X)))
        if proba is not None and _argmax_predicts(m.estimator):
            # Même résultat que predict pour ces modèles : on évite un second entraînement complet.
            pred = np.unique(y)[np.argmax(proba, axis=1)]
        else:
            pred = cross_val_predict(clone(m.estimator), X, y, cv=cv, groups=groups, n_jobs=n_jobs(len(X)))
        if multi:
            for j, t in enumerate(m.target):
                out[f"Prediction ({t})"] = np.asarray(pred)[:, j]
        else:
            out[f"Prediction ({m.target})"] = pred
            if proba is not None:
                for i, c in enumerate(sorted(pd.unique(y), key=str) if m.classes is None else m.classes):
                    out[f"P ({m.target}={c})"] = proba[:, i]
    except NodeError:
        raise
    except Exception as e:
        raise _fit_message(e) from e
    return [out]


# Classifieurs dont predict renvoie exactement la classe de plus forte probabilité.
ARGMAX_CLASSIFIERS = {
    "LogisticRegression", "LogisticRegressionCV", "DecisionTreeClassifier", "ExtraTreeClassifier",
    "RandomForestClassifier", "ExtraTreesClassifier", "GradientBoostingClassifier",
    "HistGradientBoostingClassifier", "KNeighborsClassifier", "RadiusNeighborsClassifier", "GaussianNB",
    "BernoulliNB", "MultinomialNB", "ComplementNB", "CategoricalNB", "MLPClassifier",
    "LinearDiscriminantAnalysis", "QuadraticDiscriminantAnalysis", "GaussianProcessClassifier",
}


def _argmax_predicts(est) -> bool:
    final = est.steps[-1][1] if hasattr(est, "steps") else est
    return type(final).__name__ in ARGMAX_CLASSIFIERS


def _code_cvp(p, ins, outs):
    splitter, groups = cv_code(p, ins[0], ins[1])
    return (f"from sklearn.model_selection import cross_val_predict\n_cv = {splitter}\n"
            f"{outs[0]} = {ins[1]}.copy()\n"
            f"{outs[0]}[f'Prediction ({{{ins[0]}.target_}})'] = cross_val_predict(clone({ins[0]}), "
            f"{ins[1]}[{ins[0]}.features_], {ins[1]}[{ins[0]}.target_], cv=_cv, groups={groups})")


REGISTRY["tune.cross_val_predict"].code = _code_cvp


@register(
    "tune.permutation_test", "Test de permutation", CAT_TUNE,
    """
    Le score du modèle est-il meilleur que le hasard ? Le modèle est évalué
    par validation croisée, puis réévalué de nombreuses fois après avoir
    mélangé la cible (sklearn.model_selection.permutation_test_score). La
    p-valeur est la proportion de scores « au hasard » au moins aussi bons.
    """,
    inputs=[("Modèle (configuration)", MODEL), ("Table", DATA)], outputs=[("Scores permutés", DATA)],
    params=[
        P("n_permutations", "Nombre de permutations", "int", 100, min=10),
        P("scoring", "Métrique", "choice", "", choices=[""] + _scorer_names(), choice_labels={"": "(par défaut)"}),
        *cv_params(1),
    ],
    has_view=True, color="tune",
    doc_url="https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.permutation_test_score.html",
    keywords="permutation test p-valeur significativité hasard",
)
def permutation_test_node(ctx, p):
    from sklearn.model_selection import permutation_test_score
    m, df = ctx.model(0), ctx.data(1)
    X, y, multi = supervised_target(m, df)
    cv, groups, _ = make_cv(p, m.kind, df, multi)
    try:
        score, perm, pvalue = permutation_test_score(
            clone(m.estimator), X, y, cv=cv, groups=groups, scoring=p.get("scoring") or None,
            n_permutations=int(p.get("n_permutations") or 100), random_state=p.get("random_state"), n_jobs=n_jobs(len(X)))
    except Exception as e:
        raise _fit_message(e) from e
    ctx.add_view({"type": "metrics", "items": [
        {"label": "Score du modèle", "value": round(float(score), 4)},
        {"label": "Score moyen au hasard", "value": round(float(np.mean(perm)), 4)},
        {"label": "p-valeur", "value": float(pvalue)}]})
    counts, edges = np.histogram(perm, bins=25)
    ctx.add_view({"type": "chart", "chart": "histogram", "title": "Scores obtenus en mélangeant la cible",
                  "edges": edges.tolist(), "series": [{"name": "permutations", "counts": counts.tolist()}],
                  "xlabel": f"Score (modèle : {score:.4f})", "ylabel": "Effectif"})
    return [pd.DataFrame({"permutation": range(1, len(perm) + 1), "score": perm})]


REGISTRY["tune.permutation_test"].code = lambda p, ins, outs: (
    "from sklearn.model_selection import permutation_test_score\n"
    f"_cv = {cv_code(p, ins[0], ins[1])[0]}\n"
    f"_score, _perm, _pvalue = permutation_test_score(clone({ins[0]}), {ins[1]}[{ins[0]}.features_], "
    f"{ins[1]}[{ins[0]}.target_], cv=_cv, groups={cv_code(p, ins[0], ins[1])[1]}, "
    f"n_permutations={int(p.get('n_permutations') or 100)}, random_state={p.get('random_state')})\n"
    f"{outs[0]} = pd.DataFrame({{'score': _perm}})\nprint('score', _score, 'p-valeur', _pvalue)")


@register(
    "tune.grid_search", "Recherche d'hyperparamètres", CAT_TUNE,
    """
    Recherche exhaustive sur une grille (GridSearchCV) ou aléatoire
    (RandomizedSearchCV) avec validation croisée. La grille est un
    dictionnaire Python, par exemple :
    {"n_estimators": [50, 100, 200], "max_depth": [None, 5, 10]}.
    La sortie « Meilleur modèle » est le meilleur estimateur réentraîné sur toute
    la table. La sortie « Recherche (configuration) » transmet la recherche
    elle-même : branchée sur une validation croisée, elle donne une validation
    croisée imbriquée (la recherche est refaite dans chaque pli externe).
    """,
    inputs=[("Modèle (configuration)", MODEL), ("Table", DATA)],
    outputs=[("Meilleur modèle", MODEL), ("Résultats", DATA), ("Recherche (configuration)", MODEL)],
    params=[
        P("grid", "Grille de paramètres", "code", '{\n  "max_depth": [None, 3, 5, 10]\n}', rows=5, required=True),
        P("search", "Stratégie de recherche", "choice", "grid", choices=["grid", "random"],
          choice_labels={"grid": "Grille exhaustive (GridSearchCV)", "random": "Aléatoire (RandomizedSearchCV)"}),
        P("n_iter", "Itérations (aléatoire)", "int", 20),
        P("scoring", "Métrique", "choice", "", choices=[""] + _scorer_names(), choice_labels={"": "(par défaut)"}),
        *cv_params(1),
    ],
    has_view=True, color="tune",
    doc_url="https://scikit-learn.org/stable/modules/grid_search.html",
    keywords="grid search gridsearchcv randomizedsearchcv hyperparamètres tuning optimisation",
)
def grid_search(ctx, p):
    from sklearn.model_selection import RandomizedSearchCV
    m, df = ctx.model(0), ctx.data(1)
    X, y, multi = supervised_target(m, df)
    try:
        grid = ast.literal_eval(p.get("grid") or "{}")
    except Exception as e:
        raise NodeError(f"Grille invalide (dictionnaire Python attendu) : {e}") from e
    if not isinstance(grid, (dict, list)) or not grid:
        raise NodeError("La grille doit être un dictionnaire non vide.")
    valid = set(m.estimator.get_params())
    bad = [k for k in (grid if isinstance(grid, dict) else {}) if k not in valid]
    if bad:
        raise NodeError(f"Paramètres inconnus pour {m.name} : {', '.join(bad)}. "
                        f"Paramètres réglables : {', '.join(tunable_params(m.estimator)[:25])}")
    scoring = p.get("scoring") or None
    cv, groups, _ = make_cv(p, m.kind, df, multi)
    if p.get("search") == "random":
        search = RandomizedSearchCV(clone(m.estimator), grid, n_iter=int(p.get("n_iter") or 20), cv=cv,
                                    scoring=scoring, random_state=p.get("random_state"), n_jobs=n_jobs(len(X)))
    else:
        search = GridSearchCV(clone(m.estimator), grid, cv=cv, scoring=scoring, n_jobs=n_jobs(len(X)))
    try:
        search.fit(X, y, groups=groups)
    except Exception as e:
        raise _fit_message(e) from e
    res = pd.DataFrame(search.cv_results_)
    keep = ["rank_test_score", "mean_test_score", "std_test_score", "mean_fit_time"] + [c for c in res.columns if c.startswith("param_")]
    res = res[keep].sort_values("rank_test_score")
    for c in res.columns:
        if c.startswith("param_"):
            res[c] = res[c].astype(str)
    best = ModelPort(search.best_estimator_, m.kind, m.name, m.features, m.target,
                     classes=list(search.best_estimator_.classes_) if hasattr(search.best_estimator_, "classes_") and not multi else None)
    ctx.add_view({"type": "metrics", "items": [
        {"label": "Meilleur score (CV)", "value": round(float(search.best_score_), 4)},
        {"label": "Combinaisons testées", "value": len(res)}]})
    ctx.add_view({"type": "text", "title": "Meilleurs paramètres", "text": json.dumps(
        {k: _jsonable(v) if not isinstance(v, (list, tuple)) else str(v) for k, v in search.best_params_.items()},
        ensure_ascii=False, indent=2), "mono": True})
    ctx.add_view(table_block(res.head(50).round(5), "Classement"))
    nested = ModelPort(search, m.kind, f"{type(search).__name__} ({m.name})", m.features, m.target,
                       classes=best.classes)
    return [best, res, nested]


def _code_grid(p, ins, outs):
    cls = "RandomizedSearchCV" if p.get("search") == "random" else "GridSearchCV"
    extra = f", n_iter={int(p.get('n_iter') or 20)}, random_state={p.get('random_state')}" if cls == "RandomizedSearchCV" else ""
    splitter, groups = cv_code(p, ins[0], ins[1])
    return (f"_search = {cls}(clone({ins[0]}), {(p.get('grid') or '{}').strip()}, cv={splitter}, "
            f"scoring={py(p.get('scoring') or None)}{extra})\n"
            f"_search.fit({ins[1]}[{ins[0]}.features_], {ins[1]}[{ins[0]}.target_], groups={groups})\n"
            f"{outs[0]} = _search.best_estimator_\n"
            f"{outs[0]}.features_, {outs[0]}.target_ = {ins[0]}.features_, {ins[0]}.target_\n"
            f"{outs[1]} = pd.DataFrame(_search.cv_results_).sort_values('rank_test_score')\n"
            f"{outs[2]} = _search      # recherche complète : validation croisée imbriquée si on la réévalue\n"
            f"{outs[2]}.features_, {outs[2]}.target_ = {ins[0]}.features_, {ins[0]}.target_\n"
            f"print('Meilleurs paramètres :', _search.best_params_)")


REGISTRY["tune.grid_search"].code = _code_grid


@register(
    "tune.learning_curve", "Courbe d'apprentissage", CAT_TUNE,
    """
    Score d'apprentissage et de validation en fonction de la taille du jeu
    d'entraînement (sklearn.model_selection.learning_curve) : diagnostique le
    sur- ou sous-apprentissage.
    """,
    inputs=[("Modèle (configuration)", MODEL), ("Table", DATA)], outputs=[("Courbe", DATA)],
    params=[
        P("steps", "Nombre de tailles", "int", 6),
        P("scoring", "Métrique", "choice", "", choices=[""] + _scorer_names(), choice_labels={"": "(par défaut)"}),
        *cv_params(1),
    ],
    has_view=True, color="tune",
    doc_url="https://scikit-learn.org/stable/modules/learning_curve.html",
    keywords="learning curve surapprentissage overfitting biais variance",
)
def learning_curve_node(ctx, p):
    from sklearn.model_selection import learning_curve
    m, df = ctx.model(0), ctx.data(1)
    X, y, multi = supervised_target(m, df)
    cv, groups, _ = make_cv(p, m.kind, df, multi)
    try:
        sizes, tr, va = learning_curve(clone(m.estimator), X, y, cv=cv, groups=groups,
                                       scoring=p.get("scoring") or None,
                                       train_sizes=np.linspace(0.1, 1.0, int(p.get("steps") or 6)),
                                       shuffle=True, random_state=0, n_jobs=n_jobs(len(X)))
    except Exception as e:
        raise _fit_message(e) from e
    out = pd.DataFrame({"taille": sizes, "train_moyen": tr.mean(1), "train_std": tr.std(1),
                        "validation_moyen": va.mean(1), "validation_std": va.std(1)})
    ctx.add_view({"type": "chart", "chart": "line", "title": "Courbe d'apprentissage",
                  "xlabel": "Taille du jeu d'apprentissage", "ylabel": "Score", "markers": True,
                  "series": [{"name": "Apprentissage", "x": sizes.tolist(), "y": tr.mean(1).tolist(), "band": tr.std(1).tolist()},
                             {"name": "Validation", "x": sizes.tolist(), "y": va.mean(1).tolist(), "band": va.std(1).tolist()}]})
    return [out]


REGISTRY["tune.learning_curve"].code = lambda p, ins, outs: (
    f"_sizes, _tr, _va = learning_curve(clone({ins[0]}), {ins[1]}[{ins[0]}.features_], {ins[1]}[{ins[0]}.target_], "
    f"cv={cv_code(p, ins[0], ins[1])[0]}, groups={cv_code(p, ins[0], ins[1])[1]}, "
    f"train_sizes=np.linspace(0.1, 1.0, {int(p.get('steps') or 6)}), shuffle=True, random_state=0)\n"
    f"{outs[0]} = pd.DataFrame({{'taille': _sizes, 'train': _tr.mean(1), 'validation': _va.mean(1)}})")


def tunable_params(est) -> list[str]:
    """Noms de paramètres utilisables dans une grille (valeurs simples uniquement)."""
    out = []
    for k, v in est.get_params(deep=True).items():
        if isinstance(v, (int, float, str, bool, type(None))) and not k.endswith(("verbose", "n_jobs", "memory")):
            out.append(k)
    return out


# Nœuds de composition, d'explicabilité et de données complémentaires.
from . import nodes_compose, nodes_explain, nodes_data, nodes_report  # noqa: E402,F401


# Module scikit-learn de référence des nœuds propres à KataML (vue « API » du dépôt).
FUNCTION_MODULES = {
    "io.dataset": "sklearn.datasets", "io.openml": "sklearn.datasets", "manip.partition": "sklearn.model_selection",
    "compose.pipeline": "sklearn.pipeline", "tune.": "sklearn.model_selection", "score.calibration": "sklearn.calibration",
    "score.importance": "sklearn.inspection", "score.": "sklearn.metrics", "explain.tree": "sklearn.tree",
    "explain.": "sklearn.inspection",
}


def _module_of(node_type: str) -> str:
    for key in sorted(FUNCTION_MODULES, key=len, reverse=True):
        if node_type.startswith(key):
            return FUNCTION_MODULES[key]
    return "kataml"


def catalog(lang: str = "fr") -> list[dict]:
    """Spécifications des nœuds, classées selon le guide scikit-learn (voir taxonomy.py)."""
    from . import i18n, taxonomy
    by_label = {lbl: key for key, labels in taxonomy.SECTIONS.items() for lbl in (*labels, key)}
    by_label.update(taxonomy.ALIASES)
    out = []
    for nt in REGISTRY.values():
        spec = nt.spec()
        if nt.extension and nt.category not in by_label:
            section, family = None, ""
            spec["category"] = nt.category
        else:
            section, family = (by_label[nt.category], "") if nt.extension else taxonomy.classify(nt.type, nt.module, nt.kind)
            spec["category"] = taxonomy.label(taxonomy.SECTIONS, section, lang)
        spec["family"] = taxonomy.label(taxonomy.FAMILIES, family, lang) if family else None
        spec["section"] = section
        spec["module"] = nt.module or ("extension" if nt.extension else _module_of(nt.type))
        out.append(i18n.translate_spec(spec, lang) if lang != "fr" else spec)
    return out
