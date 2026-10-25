"""Import d'un script Python : reconstruit le schéma (workflow) équivalent.

Le script n'est jamais exécuté : il est analysé (module ``ast``) et ses appels
pandas / scikit-learn reconnus deviennent des nœuds reliés. Les fonctions du
script sont suivies (« inlining ») et les opérations pandas non reconnues
deviennent des nœuds « Script Python ». Tout ce qui n'a pas pu être converti
est signalé dans une note posée sur le canevas.

Reconnus :
- lecture : pd.read_csv, read_parquet, read_excel, read_feather, sklearn.datasets.load_* ;
- préparation : dropna, drop(columns=…), df[[…]], train_test_split ;
- modèles : estimateurs scikit-learn, Pipeline, make_pipeline, ColumnTransformer ;
- application : fit, predict, predict_proba, fit_transform, score ;
- évaluation : métriques sklearn.metrics, cross_val_score, cross_validate, cross_val_predict.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field

READERS = {"read_csv": "io.csv_reader", "read_table": "io.csv_reader", "read_parquet": "io.table_reader",
           "read_excel": "io.table_reader", "read_feather": "io.table_reader"}
DATASETS = {"iris", "wine", "breast_cancer", "digits", "diabetes", "linnerud"}
REGRESSION_METRICS = {"mean_squared_error", "mean_absolute_error", "r2_score", "root_mean_squared_error",
                      "mean_absolute_percentage_error", "median_absolute_error", "explained_variance_score",
                      "max_error", "mean_squared_log_error"}
ROC_METRICS = {"roc_auc_score", "roc_curve", "average_precision_score", "precision_recall_curve"}
MAX_PREPS = 3          # entrées « Prétraitement » du nœud Pipeline
MAX_DEPTH = 12         # profondeur d'appel des fonctions suivies


class Unknown:
    """Valeur que l'analyse ne sait pas suivre (``name`` : origine, pour les messages)."""

    def __init__(self, name: str = ""):
        self.name = name


@dataclass(eq=False)
class Tab:
    """Table qui circule dans le schéma : sortie ``port`` du nœud ``node``."""
    node: str
    port: int = 0
    role: str = "table"            # table | X | y | pred
    target: object = None          # colonne cible connue (str) ou Unknown
    dropped: list = field(default_factory=list)
    model: object = None           # pour role == "pred" : le modèle appliqué


@dataclass(eq=False)
class Est:
    """Estimateur scikit-learn non ajusté."""
    name: str
    kind: str                      # classifier | regressor | cluster | transformer
    params: dict
    line: int = 0
    fitted: object = None          # Fitted après .fit()


@dataclass(eq=False)
class ColT:
    parts: list                    # [(Est, colonnes | Unknown)]
    remainder: str = "drop"
    line: int = 0
    fitted: object = None


@dataclass(eq=False)
class Pipe:
    steps: list                    # Est | ColT
    line: int = 0
    fitted: object = None
    names: list = field(default_factory=list)


@dataclass(eq=False)
class Steps:
    """``pipe.named_steps`` / ``pipe.steps`` : accès aux étapes par nom ou par indice."""
    pipe: Pipe


@dataclass(eq=False)
class Fitted:
    node: str
    port: int
    kind: str
    target: object
    train: Tab
    preps: list = field(default_factory=list)   # sorties « modèle » des transformeurs


@dataclass(eq=False)
class Deferred:
    """Expression pandas non reconnue gardée de côté (``masque = df["a"] > 0``) : elle est
    recopiée telle quelle dans le nœud « Script Python » qui l'utilise."""
    node: ast.expr
    tabs: list                     # [(nom de variable, Tab)]


@dataclass
class CV:
    params: dict


class _Return(Exception):
    def __init__(self, value):
        self.value = value


def _guess_kind(name: str) -> str | None:
    if name in ("LogisticRegression", "LogisticRegressionCV", "Perceptron", "RidgeClassifier", "SVC",
                "LinearSVC", "NuSVC", "GaussianNB", "MultinomialNB", "BernoulliNB", "CategoricalNB",
                "LinearDiscriminantAnalysis", "QuadraticDiscriminantAnalysis", "SGDClassifier"):
        return "classifier"
    if name.endswith("Classifier") or name.endswith("NB"):
        return "classifier"
    if name.endswith("Regressor") or name.endswith("Regression") or name in (
            "Ridge", "Lasso", "ElasticNet", "LinearSVR", "SVR", "NuSVR", "Lars", "LassoLars", "BayesianRidge",
            "ARDRegression", "HuberRegressor", "KernelRidge"):
        return "regressor"
    if name in ("KMeans", "MiniBatchKMeans", "DBSCAN", "HDBSCAN", "AgglomerativeClustering", "Birch",
                "MeanShift", "SpectralClustering", "OPTICS", "AffinityPropagation", "GaussianMixture"):
        return "cluster"
    if name.endswith(("Scaler", "Encoder", "Imputer", "Transformer", "Discretizer")) or name in (
            "PCA", "TruncatedSVD", "Normalizer", "Binarizer", "PolynomialFeatures", "SelectKBest",
            "VarianceThreshold", "SplineTransformer", "KBinsDiscretizer", "FactorAnalysis", "FastICA", "NMF"):
        return "transformer"
    return None


class Converter:
    def __init__(self, known_types=None):
        self.known = set(known_types) if known_types is not None else None
        self.nodes: list[dict] = []
        self.edges: list[dict] = []
        self.notes: list[str] = []
        self.imports: dict[str, str] = {}
        self.funcs: dict[str, ast.FunctionDef] = {}
        self.depth = 0
        self.scores: dict[str, set] = {}         # nœud prédicteur -> évaluations déjà ajoutées
        self.cache: dict = {}
        self.genv: dict = {}
        self.written: dict[str, Tab] = {}        # fichier écrit par le script -> table écrite

    # -- outils ----------------------------------------------------------------
    def note(self, line, msg):
        txt = f"ligne {line} : {msg}" if line else msg
        if txt not in self.notes:
            self.notes.append(txt)

    def add(self, type_, label, params=None, line=0) -> str:
        nid = f"n{len(self.nodes) + 1}"
        self.nodes.append({"id": nid, "type": type_, "x": 0, "y": 0, "label": label,
                           "params": params or {}, "_line": line})
        return nid

    def link(self, src: Tab | Fitted | tuple, dst: str, port: int):
        node, p = (src.node, src.port) if not isinstance(src, tuple) else src
        self.edges.append({"from": node, "fromPort": p, "to": dst, "toPort": port})

    def kind_of(self, name: str) -> str | None:
        if self.known is not None:
            for k in ("classifier", "regressor", "transformer", "cluster"):
                if f"sk.{k}.{name}" in self.known:
                    return k
            return None
        return _guess_kind(name)

    def qualname(self, f: ast.expr) -> str:
        """Nom complet d'une fonction appelée (``pd.read_csv`` -> ``pandas.read_csv``)."""
        parts = []
        while isinstance(f, ast.Attribute):
            parts.append(f.attr)
            f = f.value
        if not isinstance(f, ast.Name):
            return ""
        parts.append(self.imports.get(f.id, f.id))
        return ".".join(reversed(parts))

    @staticmethod
    def lit(v):
        return v if not isinstance(v, (Unknown, Tab, Est, ColT, Pipe, Fitted, CV, Deferred)) else None

    def is_lit(self, v):
        return not isinstance(v, (Unknown, Tab, Est, ColT, Pipe, Fitted, CV, Deferred, Steps, tuple, list)) or (
            isinstance(v, (tuple, list)) and all(self.is_lit(x) for x in v))

    def param_value(self, v):
        """Valeur d'hyperparamètre telle que l'attend l'inspecteur de KataML."""
        if isinstance(v, bool) or isinstance(v, str):
            return v
        if isinstance(v, float) and v == float("inf"):
            return "1e999"
        return repr(list(v) if isinstance(v, tuple) else v)

    def columns(self, v, line, what="colonnes"):
        if isinstance(v, str):
            return [v]
        if isinstance(v, (list, tuple)) and all(isinstance(c, str) for c in v):
            return list(v)
        name = getattr(v, "name", "") if isinstance(v, Unknown) else ""
        self.note(line, f"{what} {('« ' + name + ' » ') if name else ''}inconnues à l'analyse : à choisir dans l'inspecteur.")
        return []

    def col(self, v, line, what="colonne cible"):
        if isinstance(v, str):
            return v
        name = getattr(v, "name", "") if isinstance(v, Unknown) else ""
        self.note(line, f"{what} {('« ' + name + ' » ') if name else ''}inconnue à l'analyse : à choisir dans l'inspecteur.")
        return ""

    # -- exécution symbolique --------------------------------------------------
    def run(self, tree: ast.Module):
        self.block(tree.body, {})

    def block(self, stmts, env):
        for s in stmts:
            self.stmt(s, env)

    def stmt(self, s, env):
        line = getattr(s, "lineno", 0)
        if isinstance(s, (ast.Import, ast.ImportFrom)):
            for a in s.names:
                full = f"{s.module}.{a.name}" if isinstance(s, ast.ImportFrom) and s.module else a.name
                self.imports[a.asname or a.name.split(".")[0]] = full if (a.asname or isinstance(s, ast.ImportFrom)) else a.name.split(".")[0]
        elif isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self.funcs[s.name] = s
        elif isinstance(s, ast.ClassDef):
            self.note(line, f"classe « {s.name} » ignorée.")
        elif isinstance(s, (ast.Assign, ast.AnnAssign)):
            if s.value is None:
                return
            targets = s.targets if isinstance(s, ast.Assign) else [s.target]
            if any(isinstance(t, ast.Subscript) for t in targets):
                return self.mutate(s, env, targets)
            val = self.expr(s.value, env, assigned=True)
            if isinstance(val, Unknown):
                tabs = self.tabs_in(s.value, env)
                if tabs and self.frame_like(s.value, env):
                    val = self.materialize(s.value, env, line) or val
                elif tabs:
                    val = Deferred(self.substitute(s.value, env), tabs)
            for t in targets:
                self.bind(t, val, env, line)
        elif isinstance(s, ast.AugAssign):
            if isinstance(s.target, ast.Name) and isinstance(env.get(s.target.id), Tab):
                self.mutate(s, env, [s.target])
        elif isinstance(s, ast.Expr):
            self.expr(s.value, env)
        elif isinstance(s, ast.Return):
            val = self.expr(s.value, env) if s.value else None
            if isinstance(val, (Unknown, Deferred)) and self.frame_like(s.value, env):
                val = self.materialize(s.value, env, line) or val
            elif isinstance(val, Tab) and val.role == "X" and val.target is None and val.dropped:
                nid = self.add("manip.column_filter", "Colonnes retirées", {"columns": list(val.dropped), "mode": "exclude"}, line)
                self.link(val, nid, 0)
                val = Tab(nid, 0)
            raise _Return(val)
        elif isinstance(s, ast.If):
            t = s.test
            if (isinstance(t, ast.Compare) and isinstance(t.left, ast.Name) and t.left.id == "__name__"):
                self.block(s.body, env)
            else:
                self.note(line, "condition « if » : seule la première branche est reprise.")
                self.block(s.body, env)
        elif isinstance(s, (ast.For, ast.While)):
            self.note(line, "boucle : son contenu est repris une seule fois.")
            self.block(s.body, env)
        elif isinstance(s, (ast.With, ast.Try)):
            self.block(s.body, env)
            for h in getattr(s, "finalbody", []) or []:
                self.stmt(h, env)

    def bind(self, t, val, env, line):
        if isinstance(t, ast.Name):
            env[t.id] = val
        elif isinstance(t, (ast.Tuple, ast.List)):
            vals = list(val) if isinstance(val, (tuple, list)) and len(val) == len(t.elts) else [Unknown()] * len(t.elts)
            for e, v in zip(t.elts, vals):
                self.bind(e, v, env, line)

    def call_user(self, fdef, args, kwargs, env):
        if self.depth >= MAX_DEPTH:
            return Unknown(fdef.name)
        local = dict(self.genv)
        a = fdef.args
        params = [p.arg for p in a.posonlyargs + a.args]
        defaults = a.defaults or []
        for p, d in zip(params[len(params) - len(defaults):], defaults):
            local[p] = self.expr(d, env)
        for p, v in zip(params, args):
            local[p] = v
        for k, v in kwargs.items():
            local[k] = v
        self.depth += 1
        try:
            self.block(fdef.body, local)
            return None
        except _Return as r:
            return r.value
        finally:
            self.depth -= 1

    # -- expressions ---------------------------------------------------------------
    def expr(self, e, env, assigned=False):
        if e is None:
            return None
        if isinstance(e, ast.Constant):
            return e.value
        if isinstance(e, (ast.List, ast.Tuple, ast.Set)):
            vals = []
            for x in e.elts:
                v = self.expr(x, env)
                if isinstance(x, ast.Starred) and isinstance(v, (list, tuple)):
                    vals.extend(v)
                else:
                    vals.append(v)
            return vals if isinstance(e, ast.List) else tuple(vals)
        if isinstance(e, ast.Dict):
            return Unknown("dict")
        if isinstance(e, ast.JoinedStr):
            parts = []
            for v in e.values:
                x = v.value if isinstance(v, ast.Constant) else self.expr(v.value, env)
                if not isinstance(x, (str, int, float)) or isinstance(x, bool):
                    return Unknown("f-string")
                parts.append(str(x))
            return "".join(parts)
        if isinstance(e, (ast.GeneratorExp, ast.ListComp)) and len(e.generators) == 1 and not e.generators[0].ifs \
                and isinstance(e.generators[0].target, ast.Name):
            it = self.expr(e.generators[0].iter, env)
            if isinstance(it, (list, tuple)) and all(self.is_lit(x) for x in it):
                vals = [self.expr(e.elt, {**env, e.generators[0].target.id: x}) for x in it]
                if all(self.is_lit(v) for v in vals):
                    return vals
            return Unknown("compréhension")
        if isinstance(e, ast.Name):
            if e.id in env:
                return env[e.id]
            return Unknown(e.id)
        if isinstance(e, ast.UnaryOp) and isinstance(e.op, ast.USub):
            v = self.expr(e.operand, env)
            return -v if isinstance(v, (int, float)) and not isinstance(v, bool) else Unknown()
        if isinstance(e, ast.BinOp):
            l, r = self.expr(e.left, env), self.expr(e.right, env)
            if isinstance(l, Tab) or isinstance(r, Tab):
                return Unknown()
            if isinstance(e.op, ast.Div) and isinstance(r, str) and not isinstance(l, (int, float)):
                return r                    # Path(...) / "fichier.csv" : seul le nom compte
            
            try:
                if self.is_lit(l) and self.is_lit(r) and not isinstance(l, (list, tuple)):
                    return {ast.Add: lambda: l + r, ast.Sub: lambda: l - r, ast.Mult: lambda: l * r,
                            ast.Div: lambda: l / r}.get(type(e.op), lambda: Unknown())()
                if isinstance(l, list) and isinstance(r, list):
                    return l + r
            except Exception:
                pass
            return Unknown()
        if isinstance(e, ast.Starred):
            return self.expr(e.value, env)
        if isinstance(e, ast.Compare):
            for v in [self.expr(e.left, env)] + [self.expr(x, env) for x in e.comparators]:
                if isinstance(v, Tab) and v.role == "pred":
                    return v
            return Unknown()
        if isinstance(e, ast.Attribute):
            q = self.qualname(e)
            if q in ("numpy.inf", "math.inf"):
                return float("inf")
            if q in ("numpy.nan", "math.nan"):
                return Unknown("nan")
            base = self.expr(e.value, env)
            if isinstance(base, Tab) and e.attr in ("values", "to_numpy"):
                return base
            if isinstance(base, Pipe) and e.attr in ("named_steps", "steps"):
                return Steps(base)
            return Unknown(q or e.attr)
        if isinstance(e, ast.Subscript):
            return self.subscript(e, env)
        if isinstance(e, ast.Call):
            return self.call(e, env, assigned)
        return Unknown()

    def subscript(self, e, env):
        base = self.expr(e.value, env)
        key = self.expr(e.slice, env)
        if isinstance(base, Tab) and base.role in ("table", "X"):
            if isinstance(key, list):
                cols = self.columns(key, e.lineno)
                nid = self.add("manip.column_filter", "Sélection de colonnes", {"columns": cols, "mode": "include"}, e.lineno)
                self.link(base, nid, 0)
                return Tab(nid, 0, "X" if base.role == "X" else "table", base.target)
            if isinstance(key, str) or (isinstance(key, Unknown) and isinstance(e.slice, (ast.Name, ast.Attribute))):
                return Tab(base.node, base.port, "y", key)
        if isinstance(e.value, ast.Attribute) and self.qualname(e.value) == "os.environ" and isinstance(key, str):
            return "$" + key
        if isinstance(base, Steps):
            p = base.pipe
            if isinstance(key, str) and key in p.names:
                return p.steps[p.names.index(key)]
            if isinstance(key, int) and -len(p.steps) <= key < len(p.steps):
                return p.steps[key]
            return Unknown("étape")
        if isinstance(base, (tuple, list)) and isinstance(key, int) and -len(base) <= key < len(base):
            return base[key]
        if isinstance(base, Tab) and base.role == "pred":
            return base
        return Unknown()

    def kw(self, call, env):
        return {k.arg: self.expr(k.value, env) for k in call.keywords if k.arg}

    def call(self, c, env, assigned=False):
        q = self.qualname(c.func)
        short = q.rsplit(".", 1)[-1]
        line = c.lineno
        # Méthode appelée sur une valeur suivie (df.dropna(), model.fit()…)
        if isinstance(c.func, ast.Attribute):
            obj = self.expr(c.func.value, env)
            if isinstance(obj, (Tab, Est, ColT, Pipe, Fitted)):
                return self.method(obj, c.func.attr, c, env, assigned)
        args = [self.expr(a, env) for a in c.args]
        kwargs = self.kw(c, env)
        if isinstance(c.func, ast.Attribute) and c.func.attr == "join" and isinstance(c.func.value, ast.Constant) \
                and isinstance(c.func.value.value, str) and args and isinstance(args[0], (list, tuple)) \
                and all(isinstance(x, str) for x in args[0]):
            return c.func.value.value.join(args[0])
        if q in ("os.getenv", "os.environ.get") and args and isinstance(args[0], str):
            return "$" + args[0]             # lu à l'exécution dans la variable d'environnement
        if short in ("create_engine", "connect") and args and isinstance(args[0], str):
            return args[0]                   # sqlalchemy.create_engine(url), sqlite3.connect(fichier)
        if isinstance(c.func, ast.Name) and c.func.id in self.funcs:
            return self.call_user(self.funcs[c.func.id], args, kwargs, env)
        if short in READERS and (q.startswith("pandas.") or q.startswith("pd.")):
            return self.reader(short, args, kwargs, line)
        if short in ("read_sql", "read_sql_query", "read_sql_table"):
            return self.sql_reader(short, args, kwargs, line)
        if q.startswith("sklearn.datasets.load_") and short[5:] in DATASETS:
            nid = self.add("io.dataset", short[5:].replace("_", " ").title(), {"dataset": short[5:]}, line)
            t = Tab(nid)
            if kwargs.get("return_X_y"):
                return (Tab(nid, 0, "X", "target"), Tab(nid, 0, "y", "target"))
            return t
        if short == "train_test_split":
            return self.split(args, kwargs, line)
        if short in ("Pipeline", "make_pipeline"):
            steps = args[0] if short == "Pipeline" and args else (kwargs.get("steps") if short == "Pipeline" else args)
            out, names = [], []
            for i, st in enumerate(steps or []):
                nm = f"step{i}"
                if isinstance(st, tuple) and len(st) >= 2:
                    nm, st = st[0], st[1]
                if isinstance(st, (Est, ColT, Pipe)):
                    sub = st.steps if isinstance(st, Pipe) else [st]
                    out.extend(sub)
                    names.extend(st.names if isinstance(st, Pipe) else [nm])
                elif st not in ("passthrough", None):
                    self.note(line, "étape de Pipeline non reconnue, ignorée.")
            return Pipe(out, line, names=names)
        if short in ("ColumnTransformer", "make_column_transformer"):
            items = (args[0] if args else kwargs.get("transformers")) if short == "ColumnTransformer" else args
            parts = []
            for it in items or []:
                if isinstance(it, tuple):
                    est, cols = (it[1], it[2]) if len(it) == 3 else (it[0], it[1])
                    if isinstance(est, Pipe):
                        parts += [(s, cols) for s in est.steps if isinstance(s, Est)]
                    elif isinstance(est, Est):
                        parts.append((est, cols))
            rem = kwargs.get("remainder", "drop")
            return ColT(parts, rem if isinstance(rem, str) else "drop", line)
        if short in ("KFold", "StratifiedKFold", "RepeatedKFold", "RepeatedStratifiedKFold", "ShuffleSplit",
                     "StratifiedShuffleSplit", "GroupKFold", "TimeSeriesSplit", "LeaveOneOut"):
            return self.cv_spec(short, args, kwargs)
        if short in ("cross_val_score", "cross_validate", "cross_val_predict"):
            return self.crossval(short, args, kwargs, line)
        if q.startswith("sklearn.metrics.") or short in REGRESSION_METRICS or short in ROC_METRICS or short.endswith("_score"):
            return self.metric(short, args, kwargs, line)
        if q.startswith("sklearn.") and short[:1].isupper():
            kind = self.kind_of(short)
            if kind:
                params = {}
                for k, v in kwargs.items():
                    if self.is_lit(v):
                        params[k] = self.param_value(v)
                    else:
                        self.note(line, f"{short} : paramètre {k} non repris (valeur calculée).")
                return Est(short, kind, params, line)
            self.note(line, f"{short} n'a pas d'équivalent sous forme de nœud.")
            return Unknown(short)
        if q.startswith("numpy.") and any(isinstance(a, Tab) and a.role == "pred" for a in args):
            return next(a for a in args if isinstance(a, Tab) and a.role == "pred")
        if short in ("len", "print", "int", "float", "str", "round", "list", "sorted"):
            return Unknown(short)
        if any(isinstance(a, Tab) for a in args):
            return Unknown(q)
        return Unknown(q or short)

    def reader(self, short, args, kwargs, line):
        path = args[0] if args else kwargs.get("filepath_or_buffer", kwargs.get("path", kwargs.get("io")))
        if isinstance(path, str) and path.replace("\\", "/").rsplit("/", 1)[-1] in self.written:
            # Fichier écrit plus haut par le script (préparation -> modèle) : on relie directement.
            name = path.replace("\\", "/").rsplit("/", 1)[-1]
            self.note(0, f"« {name} » est écrit puis relu par les scripts : les deux parties sont reliées.")
            return self.written[name]
        params = {}
        if isinstance(path, str):
            params["path"] = path.replace("\\", "/").rsplit("/", 1)[-1]
            label = params["path"]
        else:
            params["path"] = ""
            label = "Données"
            self.note(line, f"fichier lu par {short} inconnu à l'analyse"
                      + (f" (« {path.name} »)" if isinstance(path, Unknown) and path.name else "")
                      + " : déposez-le sur le canevas ou choisissez-le dans l'inspecteur.")
        if READERS[short] == "io.csv_reader":
            sep = kwargs.get("sep", kwargs.get("delimiter"))
            if isinstance(sep, str):
                params["sep"] = "\\t" if sep == "\t" else sep
            if kwargs.get("decimal") == ",":
                params["decimal"] = ","
        elif short == "read_excel":
            sheet = kwargs.get("sheet_name")
            if isinstance(sheet, (str, int)) and not isinstance(sheet, bool):
                params["sheet"] = str(sheet)
        return Tab(self.add(READERS[short], label, params, line))

    def sql_reader(self, short, args, kwargs, line):
        query = args[0] if args else kwargs.get("sql", kwargs.get("table_name"))
        con = args[1] if len(args) > 1 else kwargs.get("con")
        params = {"source": "", "query": ""}
        if isinstance(query, str):
            params["query"] = query.strip()
        else:
            self.note(line, "requête SQL calculée : écrivez-la dans le nœud « Lecteur SQL ».")
        if isinstance(con, str):
            if con.startswith("$"):
                params["source"] = con
                self.note(line, f"connexion lue dans la variable d'environnement {con[1:]} : définissez-la "
                          "avant de lancer KataML (ex. export " + con[1:] + "=postgresql+psycopg://…).")
            elif "://" in con and "@" in con and ":" in con.split("://", 1)[1].split("@", 1)[0]:
                params["source"] = ""
                self.note(line, "l'URL de connexion contient un mot de passe : elle n'a pas été recopiée. "
                          "Indiquez-la dans le nœud, ou mieux, dans une variable d'environnement ($NOM).")
            else:
                params["source"] = con.replace("sqlite:///", "").replace("\\", "/").rsplit("/", 1)[-1] \
                    if not "://" in con or con.startswith("sqlite:///") else con
        else:
            self.note(line, "connexion à la base inconnue à l'analyse : indiquez le fichier SQLite ou l'URL dans le nœud.")
        label = "Base de données"
        return Tab(self.add("io.sql_reader", label, params, line))

    def split(self, args, kwargs, line):
        tabs = [a for a in args if isinstance(a, Tab)]
        if not tabs:
            self.note(line, "train_test_split sur des données non suivies : ignoré.")
            return Unknown("train_test_split")
        src = tabs[0]
        target = next((t.target for t in tabs if t.role == "y"), src.target)
        params = {}
        ts = kwargs.get("test_size")
        if ts is None and isinstance(kwargs.get("train_size"), float):
            ts = round(1 - kwargs["train_size"], 6)
        params["test_size"] = ts if isinstance(ts, (int, float)) and not isinstance(ts, bool) else 0.25
        rs = kwargs.get("random_state")
        if isinstance(rs, int) and not isinstance(rs, bool):
            params["random_state"] = rs
        elif rs is not None:
            self.note(line, "graine aléatoire calculée : valeur par défaut (42) utilisée.")
        if kwargs.get("shuffle") is False:
            params["shuffle"] = False
        strat = kwargs.get("stratify")
        if isinstance(strat, Tab):
            params["stratify"] = self.col(strat.target, line, "colonne de stratification")
        nid = self.add("manip.partition", "Apprentissage / test", params, line)
        self.link(src, nid, 0)
        out = []
        for t in tabs:
            out.append(Tab(nid, 0, t.role, target if t.role != "table" else t.target, list(t.dropped)))
            out.append(Tab(nid, 1, t.role, target if t.role != "table" else t.target, list(t.dropped)))
        return tuple(out)

    def cv_spec(self, short, args, kwargs):
        k = kwargs.get("n_splits", args[0] if args else 5)
        strategy = {"KFold": "kfold", "StratifiedKFold": "stratified", "RepeatedKFold": "repeated_kfold",
                    "RepeatedStratifiedKFold": "repeated_stratified", "ShuffleSplit": "shuffle_split",
                    "StratifiedShuffleSplit": "stratified_shuffle_split", "GroupKFold": "group_kfold",
                    "TimeSeriesSplit": "time_series", "LeaveOneOut": "leave_one_out"}[short]
        p = {"cv_strategy": strategy}
        if isinstance(k, int) and not isinstance(k, bool):
            p["cv"] = k
        if kwargs.get("shuffle") is False:
            p["shuffle"] = False
        rs = kwargs.get("random_state")
        if isinstance(rs, int) and not isinstance(rs, bool):
            p["random_state"] = rs
        return CV(p)

    # -- construction des modèles -----------------------------------------------
    def flatten(self, est):
        """(prétraitements [(Est, colonnes)], estimateur final Est | None)."""
        steps = est.steps if isinstance(est, Pipe) else [est]
        preps, final = [], None
        for i, s in enumerate(steps):
            if isinstance(s, ColT):
                preps += [(e, cols, s.remainder) for e, cols in s.parts]
            elif isinstance(s, Est):
                if i == len(steps) - 1:
                    final = s
                else:
                    preps.append((s, None, "passthrough"))
        return preps, final

    def prepare_x(self, X: Tab, y, line):
        target = y.target if isinstance(y, Tab) else X.target
        extra = [c for c in X.dropped if isinstance(c, str) and c != target]
        src = X
        if extra and ("drop", X.node, X.port, tuple(extra)) in self.cache:
            src = self.cache[("drop", X.node, X.port, tuple(extra))]
        elif extra:
            nid = self.add("manip.column_filter", "Colonnes retirées", {"columns": extra, "mode": "exclude"}, line)
            self.link(X, nid, 0)
            src = Tab(nid, 0, "X", target)
            self.cache[("drop", X.node, X.port, tuple(extra))] = src
        return src, target

    @staticmethod
    def signature(est):
        """Empreinte d'un modèle : deux modèles identiques réutilisent les mêmes nœuds."""
        def one(e):
            return (e.name, tuple(sorted(e.params.items())))
        def cols(c):
            return tuple(c) if isinstance(c, (list, tuple)) else repr(c) if not isinstance(c, Unknown) else id(c)
        steps = est.steps if isinstance(est, Pipe) else [est]
        out = []
        for st in steps:
            if isinstance(st, ColT):
                out.append(("colt", st.remainder, tuple((one(e), cols(c)) for e, c in st.parts)))
            elif isinstance(st, Est):
                out.append(one(st))
        return tuple(out)

    def build(self, est, X: Tab, y, line) -> Fitted | None:
        key = (self.signature(est), X.node, X.port, tuple(X.dropped))
        if key in self.cache:
            return self.cache[key]
        src, target = self.prepare_x(X, y, line)
        tcol = self.col(target, line) if (isinstance(y, Tab) or target is not None) else ""
        preps, final = self.flatten(est)
        cur, prep_models = src, []
        rem_drop = False
        for e, cols, rem in preps:
            params = {"columns": self.columns(cols, e.line or line) if cols is not None else []}
            if tcol:
                params["target"] = tcol
            params.update(e.params)
            nid = self.add(f"sk.transformer.{e.name}", e.name, params, e.line or line)
            self.link(cur, nid, 0)
            cur = Tab(nid, 0, "X", target)
            prep_models.append(Tab(nid, 1))
            rem_drop = rem_drop or (cols is not None and rem == "drop")
        if rem_drop:
            self.note(0, "ColumnTransformer(remainder='drop') : KataML conserve les autres colonnes ; "
                      "restreignez au besoin les variables explicatives du modèle.")
        if final is None:
            if not prep_models:
                return None
            f = Fitted(prep_models[-1].node, 1, "transformer", target, src, prep_models)
            self.cache[key] = f
            return f
        params = {}
        if final.kind in ("classifier", "regressor"):
            params["target"] = tcol
        params.update(final.params)
        lid = self.add(f"sk.{final.kind}.{final.name}", final.name, params, final.line or line)
        self.link(cur, lid, 0)
        result = Fitted(lid, 0, final.kind, target, src)
        if prep_models:
            result = self.pipeline(result, prep_models, src, line)
        self.cache[key] = result
        return result

    def pipeline(self, learner: Fitted, prep_models, src, line) -> Fitted:
        """Nœud Pipeline : prétraitements + apprenant, ajusté sur la table brute ``src``."""
        if len(prep_models) > MAX_PREPS:
            self.note(line, f"{len(prep_models)} prétraitements : le nœud Pipeline n'en accepte que {MAX_PREPS}, "
                      "il n'est donc pas créé. Appliquez les transformeurs aux données de test avec "
                      "« Appliquer un transformeur », ou regroupez des étapes.")
            return learner
        pid = self.add("compose.pipeline", "Pipeline", {}, line)
        self.link(src, pid, 0)
        self.link(learner, pid, 1)
        for i, pm in enumerate(prep_models):
            self.link(pm, pid, 2 + i)
        return Fitted(pid, 0, learner.kind, learner.target, src, prep_models)

    def assemble(self, pipe: Pipe, line):
        """Pipeline dont les étapes ont été ajustées une par une (named_steps[...].fit…)."""
        final = pipe.steps[-1] if pipe.steps else None
        if not isinstance(final, Est) or not isinstance(final.fitted, Fitted):
            return None
        preps, src = [], None
        for st in pipe.steps[:-1]:
            if not isinstance(st.fitted, Fitted):
                return None
            preps += st.fitted.preps or [Tab(st.fitted.node, st.fitted.port)]
            src = src or st.fitted.train
        pipe.fitted = self.pipeline(final.fitted, preps, src, line) if preps else final.fitted
        self.cache[(self.signature(pipe), src.node, src.port, tuple(src.dropped))] = pipe.fitted
        return pipe.fitted

    def predict(self, model: Fitted, X, line, proba=False):
        if not isinstance(X, Tab):
            self.note(line, "prédiction sur des données non suivies : ignorée.")
            return Unknown("predict")
        src, _ = self.prepare_x(X, None, line) if X.dropped else (X, None)
        key = ("pred", model.node, model.port, src.node, src.port)
        if key not in self.cache:
            nid = self.add("apply.predictor", "Prédicteur", {"proba": True}, line)
            self.link(model, nid, 0)
            self.link(src, nid, 1)
            self.cache[key] = Tab(nid, 0, "pred", model.target, model=model)
        return self.cache[key]

    def method(self, obj, name, c, env, assigned):
        line = c.lineno
        args = [self.expr(a, env) for a in c.args]
        kwargs = self.kw(c, env)
        if isinstance(obj, Tab):
            return self.tab_method(obj, name, c, args, kwargs, env, assigned)
        model = obj if isinstance(obj, Fitted) else obj.fitted
        if model is None and isinstance(obj, Pipe) and name not in ("fit", "fit_transform", "fit_predict"):
            model = self.assemble(obj, line)
        if name in ("fit", "fit_transform", "fit_predict"):
            X = args[0] if args else kwargs.get("X")
            y = args[1] if len(args) > 1 else kwargs.get("y")
            if not isinstance(X, Tab):
                self.note(line, f".{name}() sur des données non suivies : ignoré.")
                return obj
            if isinstance(obj, Fitted):
                return obj
            f = self.build(obj, X, y, line)
            obj.fitted = f
            if name == "fit_transform" and f is not None:
                return Tab(f.node if f.kind != "transformer" else f.node, 0, "X", f.target)
            if name == "fit_predict" and f is not None:
                return self.predict(f, X, line)
            return obj
        if name in ("predict", "predict_proba", "decision_function", "transform", "score"):
            if model is None:
                self.note(line, f".{name}() avant .fit() : ignoré.")
                return Unknown(name)
            X = args[0] if args else kwargs.get("X")
            if name == "transform" and model.kind == "transformer":
                if isinstance(X, Tab):
                    nid = self.add("apply.transformer", "Appliquer le transformeur", {}, line)
                    self.link(model, nid, 0)
                    self.link(X, nid, 1)
                    return Tab(nid, 0, "X", model.target)
                return Unknown(name)
            pred = self.predict(model, X, line, proba=name == "predict_proba")
            if name == "score" and isinstance(pred, Tab):
                self.add_score(pred, "accuracy_score" if model.kind == "classifier" else "r2_score", line)
                return Unknown("score")
            return pred
        if name == "set_params":
            return obj
        return Unknown(name)

    def tab_method(self, t, name, c, args, kwargs, env, assigned):
        line = c.lineno
        if t.role == "pred":
            return t
        if name in ("to_csv", "to_parquet", "to_excel", "to_feather"):
            path = args[0] if args else kwargs.get("path", kwargs.get("path_or_buf", kwargs.get("excel_writer")))
            if isinstance(path, str):
                self.written[path.replace("\\", "/").rsplit("/", 1)[-1]] = t
            return Unknown(name)
        if name == "dropna" and not kwargs.get("axis") and not kwargs.get("inplace"):
            subset = kwargs.get("subset")
            params = {"columns": self.columns(subset, line) if subset is not None else []}
            nid = self.add("manip.missing", "Lignes incomplètes", params, line)
            self.link(t, nid, 0)
            return Tab(nid, 0, t.role, t.target, list(t.dropped))
        if name == "drop" and (kwargs.get("columns") is not None or kwargs.get("axis") in (1, "columns")):
            cols = kwargs.get("columns", args[0] if args else None)
            cols = [cols] if isinstance(cols, (str, Unknown)) else (cols or [])
            known = [x for x in cols if isinstance(x, str)]
            unknown = [x for x in cols if not isinstance(x, str)]
            if unknown and len(cols) == 1:
                # X = df.drop(columns=CIBLE) : la colonne retirée est la cible (inconnue).
                return Tab(t.node, t.port, "X", unknown[0], list(t.dropped))
            out = Tab(t.node, t.port, "X", t.target, list(t.dropped) + known)
            if len(known) == 1 and t.target is None:
                out.target = known[0]
                out.dropped = list(t.dropped) + known
            return out
        if name in ("copy", "reset_index", "astype") and name != "astype":
            return t
        if name in ("head", "info", "describe", "plot", "to_csv", "to_parquet", "to_excel", "mean", "sum"):
            return Unknown(name)
        return self.fallback(c, env, t, line)

    def fallback(self, e, env, t, line):
        """Opération pandas non reconnue sur une table : nœud « Script Python »."""
        if t.role not in ("table", "X") or not self.frame_like(e, env):
            return Unknown("pandas")
        return self.materialize(e, env, line) or Unknown("pandas")

    def tabs_in(self, node, env) -> list:
        """Tables (et valeurs différées) utilisées par ``node`` : [(nom, Tab)], sans doublon."""
        out, seen = [], set()
        for n in ast.walk(node):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                v = env.get(n.id)
                pairs = [(n.id, v)] if isinstance(v, Tab) and v.role in ("table", "X") else (v.tabs if isinstance(v, Deferred) else [])
                for name, t in pairs:
                    if name not in seen:
                        seen.add(name)
                        out.append((name, t))
        return out

    PANDAS_FUNCS = {"merge", "concat", "get_dummies", "pivot_table", "melt", "crosstab"}
    # Attributs / méthodes qui ne renvoient pas une table : le résultat reste une valeur différée.
    NOT_FRAME = {"columns", "shape", "index", "dtypes", "values", "size", "ndim", "str", "dt", "cat", "empty",
                 "mean", "sum", "count", "nunique", "value_counts", "unique", "tolist", "to_list", "to_numpy",
                 "max", "min", "std", "var", "median", "idxmax", "idxmin", "any", "all", "item", "isin",
                 "to_csv", "to_parquet", "to_excel", "to_sql", "to_json", "plot", "hist", "info", "memory_usage"}

    def frame_like(self, node, env) -> bool:
        """Chaîne pandas partant d'une table et dont le résultat est (vraisemblablement) une table."""
        if not self.rooted(node, env):
            return False
        n = node.func if isinstance(node, ast.Call) else node
        if isinstance(n, ast.Attribute) and n.attr in self.NOT_FRAME:
            return False
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
            return False                     # df["colonne"] : une série
        for sub in ast.walk(node):
            if isinstance(sub, ast.Attribute) and sub.attr in ("str", "dt", "cat", "columns", "shape", "index"):
                return False
        return True

    def rooted(self, node, env) -> bool:
        """Vrai si ``node`` est une chaîne pandas partant d'une table (``df.loc[m].dropna()``,
        ``df[cols]``, ``pd.merge(a, b)``) : seules celles-ci deviennent des nœuds « Script Python »."""
        n = node
        while True:
            if isinstance(n, ast.Call):
                q = self.qualname(n.func)
                if q.startswith("pandas.") and q.rsplit(".", 1)[-1] in self.PANDAS_FUNCS:
                    return bool(self.tabs_in(n, env))
                n = n.func
            elif isinstance(n, (ast.Attribute, ast.Subscript)):
                n = n.value
            elif isinstance(n, ast.Name):
                v = env.get(n.id)
                return (isinstance(v, Tab) and v.role in ("table", "X")) or (isinstance(v, Deferred) and self.rooted(v.node, env))
            else:
                return False

    def substitute(self, node, env):
        """Copie de ``node`` : constantes connues et valeurs différées remplacées par leur valeur."""
        conv = self

        class R(ast.NodeTransformer):
            def visit_Name(self, n):
                if not isinstance(n.ctx, ast.Load):
                    return n
                v = env.get(n.id)
                if isinstance(v, Deferred):
                    return ast.copy_location(copy.deepcopy(v.node), n)
                if v is not None and conv.is_lit(v) and not isinstance(v, bool):
                    try:
                        return ast.copy_location(ast.parse(repr(v), mode="eval").body, n)
                    except SyntaxError:
                        return n
                return n

        import copy
        return R().visit(copy.deepcopy(node))

    def materialize(self, node, env, line, first: str | None = None, statement=False):
        """Nœud « Script Python » qui reproduit ``node`` (expression, ou instruction si ``statement``).

        La première table devient ``df`` (entrée 1), la seconde ``df2`` (entrée 2).
        """
        tabs = self.tabs_in(node, env)
        if first:
            tabs.sort(key=lambda p: p[0] != first)
        if not tabs:
            return None
        if len(tabs) > 2:
            self.note(line, "opération sur plus de deux tables : non convertie.")
            return None
        names = {tabs[0][0]: "df"}
        if len(tabs) == 2:
            names[tabs[1][0]] = "df2"
        body = self.substitute(node, env)

        class R(ast.NodeTransformer):
            def visit_Name(self, n):
                return ast.copy_location(ast.Name(names[n.id], n.ctx), n) if n.id in names else n

        code = ast.unparse(R().visit(body))
        code = f"{code}\nout = df\n" if statement else f"out = {code}\n"
        nid = self.add("manip.python", "Script Python", {"code": code}, line)
        for i, (_, t) in enumerate(tabs):
            self.link(t, nid, i)
        base = tabs[0][1]
        return Tab(nid, 0, base.role if base.role in ("table", "X") else "table", base.target, list(base.dropped))

    def mutate(self, s, env, targets):
        """``df[col] = …`` ou ``df += …`` : nœud « Script Python » qui modifie la table."""
        names = [n.id for n in ast.walk(targets[0]) if isinstance(n, ast.Name)]
        var = names[0] if names else None
        if not isinstance(env.get(var), Tab):
            return
        out = self.materialize(s, env, s.lineno, first=var, statement=True)
        if out is not None:
            env[var] = out

    # -- évaluation ---------------------------------------------------------------
    def find_pred(self, args, kwargs):
        for v in list(args) + list(kwargs.values()):
            if isinstance(v, Tab) and v.role == "pred":
                return v
        return None

    def add_score(self, pred: Tab, metric, line):
        kind = pred.model.kind if pred.model else "classifier"
        if metric in ROC_METRICS:
            type_, label = "score.roc", "Courbe ROC"
        elif kind == "regressor" or metric in REGRESSION_METRICS:
            type_, label = "score.regression", "Évaluation régression"
        elif kind == "cluster":
            type_, label = "score.clustering", "Qualité du clustering"
        else:
            type_, label = "score.classification", "Évaluation classification"
        done = self.scores.setdefault(pred.node, set())
        if type_ not in done:
            done.add(type_)
            nid = self.add(type_, label, {}, line)
            self.link(pred, nid, 0)

    def metric(self, short, args, kwargs, line):
        pred = self.find_pred(args, kwargs)
        if pred is None:
            if any(isinstance(a, Tab) for a in args):
                self.note(line, f"{short} : prédictions non reconnues, métrique ignorée.")
            return Unknown(short)
        self.add_score(pred, short, line)
        return Unknown(short)

    def crossval(self, short, args, kwargs, line):
        est = args[0] if args else kwargs.get("estimator")
        X = args[1] if len(args) > 1 else kwargs.get("X")
        y = args[2] if len(args) > 2 else kwargs.get("y")
        if isinstance(est, Fitted):
            model = est
        elif isinstance(est, (Est, Pipe, ColT)) and isinstance(X, Tab):
            model = self.build(est, X, y, line)
        else:
            self.note(line, f"{short} : modèle ou données non suivis, ignoré.")
            return Unknown(short)
        if model is None:
            return Unknown(short)
        src, _ = self.prepare_x(X, y, line) if isinstance(X, Tab) else (model.train, None)
        cv = kwargs.get("cv")
        params = dict(cv.params) if isinstance(cv, CV) else ({"cv": cv} if isinstance(cv, int) and not isinstance(cv, bool) else {})
        if short == "cross_val_predict":
            params["proba"] = True
            nid = self.add("tune.cross_val_predict", "Prédictions hors pli", params, line)
            self.link(model, nid, 0)
            self.link(src, nid, 1)
            return Tab(nid, 0, "pred", model.target, model=model)
        scoring = kwargs.get("scoring")
        if isinstance(scoring, str):
            params["scoring"] = [scoring]
        elif isinstance(scoring, (list, tuple)) and all(isinstance(s, str) for s in scoring):
            params["scoring"] = list(scoring)
        nid = self.add("tune.cross_validation", "Validation croisée", params, line)
        self.link(model, nid, 0)
        self.link(src, nid, 1)
        return Unknown(short)

    # -- résultat -------------------------------------------------------------------
    def layout(self):
        ids = [n["id"] for n in self.nodes]
        parents = {i: [e["from"] for e in self.edges if e["to"] == i] for i in ids}
        depth: dict[str, int] = {}

        def d(i, seen=()):
            if i not in depth:
                depth[i] = 0 if not parents[i] or i in seen else 1 + max(d(p, seen + (i,)) for p in parents[i])
            return depth[i]

        rows: dict[int, int] = {}
        for n in self.nodes:
            col = d(n["id"])
            r = rows.get(col, 0)
            rows[col] = r + 1
            n["x"], n["y"] = 40 + col * 260, 140 + r * 130

    def workflow(self, name: str) -> dict:
        # Retire les nœuds de types inconnus de cette installation (et leurs liens).
        if self.known is not None:
            bad = {n["id"] for n in self.nodes if n["type"] not in self.known}
            for n in self.nodes:
                if n["id"] in bad:
                    self.note(n.get("_line"), f"« {n['label']} » n'existe pas dans cette version : nœud retiré.")
            self.nodes = [n for n in self.nodes if n["id"] not in bad]
            self.edges = [e for e in self.edges if e["from"] not in bad and e["to"] not in bad]
        self.layout()
        for n in self.nodes:
            n.pop("_line", None)
        n_ok = len(self.nodes)
        text = [f"Import de {name}", f"{n_ok} nœud(s) reconstruit(s) à partir du script."]
        if self.notes:
            text.append("À vérifier :")
            text += [f"• {x}" for x in self.notes[:14]]
            if len(self.notes) > 14:
                text.append(f"• … et {len(self.notes) - 14} autre(s) remarque(s).")
        else:
            text.append("Tout a été reconnu. Lancez l'exécution pour vérifier.")
        h = 40 + 18 * len(text)
        ann = {"id": "a1", "x": 40, "y": 120 - h - 20, "w": 620, "h": h, "text": "\n".join(text), "color": "jaune"}
        return {"name": name.rsplit(".", 1)[0], "description": f"Schéma reconstruit à partir du script {name}.",
                "version": 1, "nodes": self.nodes, "edges": self.edges, "annotations": [ann], "groups": []}


def _module_names(tree) -> set[str]:
    """Derniers composants des modules importés (``app.models.evaluation`` -> ``evaluation``)."""
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.module:
            out.add(n.module.rsplit(".", 1)[-1])
            out.update(a.name for a in n.names)
        elif isinstance(n, ast.Import):
            out.update(a.name.rsplit(".", 1)[-1] for a in n.names)
    return out


def _has_main(tree) -> bool:
    return any(isinstance(s, ast.If) and isinstance(s.test, ast.Compare) and isinstance(s.test.left, ast.Name)
               and s.test.left.id == "__name__" for s in tree.body)


def _declare(conv: Converter, tree, env):
    """Imports, fonctions et constantes littérales d'un module (sans rien exécuter)."""
    for s in tree.body:
        if isinstance(s, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef)):
            conv.stmt(s, env)
        elif isinstance(s, (ast.Assign, ast.AnnAssign)) and s.value is not None and (isinstance(
                s.value, (ast.Constant, ast.List, ast.Tuple, ast.UnaryOp, ast.BinOp, ast.Attribute, ast.Name, ast.JoinedStr))
                or isinstance(s.value, ast.Call) and conv.qualname(s.value.func) in ("os.getenv", "os.environ.get")):
            v = conv.expr(s.value, env)
            if v is not None and conv.is_lit(v):
                for t in (s.targets if isinstance(s, ast.Assign) else [s.target]):
                    if isinstance(t, ast.Name):
                        env[t.id] = v


def scripts_to_workflow(files, known_types=None, library=()) -> tuple[dict, list[str]]:
    """Analyse un ou plusieurs scripts et renvoie ``(workflow, remarques)``.

    ``files`` : liste de ``(nom, source)``. Les fichiers importés par les autres
    (``from app.models.evaluation import …``) servent de bibliothèques : leurs
    fonctions et constantes sont reprises. Le script principal est celui que les
    autres n'importent pas (de préférence avec un bloc ``if __name__ == "__main__"``).
    ``library`` : autres scripts disponibles (bibliothèque de scripts) ; seuls ceux
    que les scripts importent, directement ou non, sont repris.
    Lève ValueError si un fichier est invalide ou si rien n'est reconnu.
    """
    def parse(name, source):
        try:
            return ast.parse(source, filename=name)
        except SyntaxError as e:
            raise ValueError(f"{name} : erreur de syntaxe ligne {e.lineno} ({e.msg}).") from e

    stem = lambda n: n.replace("\\", "/").rsplit("/", 1)[-1].rsplit(".", 1)[0]
    trees = [(name, parse(name, source)) for name, source in files]
    if not trees:
        raise ValueError("Aucun script fourni.")
    given = {stem(n) for n, _ in trees}
    pending = {stem(n): (n, src) for n, src in library if stem(n) not in given}
    wanted = set().union(*(_module_names(t) for _, t in trees))
    while True:
        add = [k for k in pending if k in wanted]
        if not add:
            break
        for k in add:
            n, src = pending.pop(k)
            try:
                t = ast.parse(src, filename=n)
            except SyntaxError:
                continue
            trees.append((n, t))
            wanted |= _module_names(t)
    nlib = len(trees) - len(files)
    imported = set()
    for _, t in trees:
        imported |= _module_names(t)
    # Scripts principaux, chacun déroulé : les scripts choisis qu'aucun autre n'importe, plus
    # ceux qu'un autre importe mais qui ont leur propre bloc « if __name__ == "__main__" »
    # (ex. préparation des données, déroulée avant le modèle qui l'importe).
    chosen = trees[:len(trees) - nlib]
    upstream = [(n, t) for n, t in chosen if stem(n) in imported and _has_main(t)]
    mains = upstream + sorted([(n, t) for n, t in chosen if stem(n) not in imported],
                              key=lambda m: not _has_main(m[1]))
    mains = mains or chosen[:1]
    conv = Converter(known_types)
    env: dict = {}
    for n, t in trees:                       # constantes et fonctions de tous les fichiers
        _declare(conv, t, env)
    for _, t in mains:
        local = dict(env)
        _declare(conv, t, local)
        conv.genv = local
        conv.block(t.body, local)
    if not conv.nodes:
        raise ValueError("Aucune opération pandas ou scikit-learn reconnue dans ce script.")
    main = mains[0]
    nmod = len(trees) - len(mains)
    title = " + ".join(n for n, _ in mains) + (f" (+{nmod} module(s))" if nmod else "")
    wf = conv.workflow(title)
    wf["name"] = stem(main[0])
    return wf, conv.notes


def script_to_workflow(source: str, name: str = "script.py", known_types=None) -> tuple[dict, list[str]]:
    """Raccourci pour un seul script."""
    return scripts_to_workflow([(name, source)], known_types)
