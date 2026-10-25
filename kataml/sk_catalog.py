"""Introspection de scikit-learn : génère automatiquement les nœuds d'estimateurs.

Chaque estimateur public (``sklearn.utils.discovery.all_estimators``) dont le
constructeur n'a pas de paramètre obligatoire devient un nœud. Les
hyperparamètres sont lus via ``inspect.signature`` et décrits à partir de la
docstring numpydoc de la classe.
"""

from __future__ import annotations

import inspect
import math
import re
import warnings
from functools import lru_cache

import sklearn
from sklearn.utils.discovery import all_estimators

# Modules exclus : entrées spécifiques (texte, dictionnaires, cibles seules…).
EXCLUDED_MODULES = ("sklearn.feature_extraction",)
# Exceptions aux modules exclus (estimateurs utilisables sur une table numérique).
ALLOWED_NAMES = {"TfidfTransformer"}
# Estimateurs volontairement absents des nœuds, avec la raison (affichée dans la documentation).
NOT_AS_NODES = {
    "Pipeline": "nœud dédié « Pipeline »",
    "GridSearchCV": "nœud dédié « Recherche d'hyperparamètres »",
    "RandomizedSearchCV": "nœud dédié « Recherche d'hyperparamètres »",
    "ColumnTransformer": "utilisé par chaque transformeur (colonnes choisies) et par le Pipeline",
    "FeatureUnion": "remplacé par l'enchaînement de transformeurs dans un Pipeline",
    "LabelEncoder": "n'agit que sur la cible ; les classifieurs acceptent des étiquettes texte",
    "LabelBinarizer": "n'agit que sur la cible",
    "MultiLabelBinarizer": "n'agit que sur la cible (multi-étiquette)",
    "FunctionTransformer": "attend une fonction Python : utiliser le nœud Script Python ou un bloc personnalisé",
    "KernelCenterer": "agit sur une matrice de noyau, pas sur une table",
    "PatchExtractor": "extraction d'imagettes (images)",
    "DictVectorizer": "entrée sous forme de dictionnaires",
    "FeatureHasher": "entrée sous forme de dictionnaires ou de listes de chaînes",
    "SparseCoder": "exige un dictionnaire d'atomes fourni en paramètre",
    "FrozenEstimator": "utilitaire interne (estimateur figé)",
    "SpectralBiclustering": "biclustering d'une matrice (lignes et colonnes)",
    "SpectralCoclustering": "biclustering d'une matrice (lignes et colonnes)",
    "TfidfVectorizer": "nœud dédié « TfidfVectorizer » (catégorie Extraction de caractéristiques)",
    "CountVectorizer": "nœud dédié « CountVectorizer »",
    "HashingVectorizer": "nœud dédié « HashingVectorizer »",
}

EXCLUDED_NAMES = {
    "LabelBinarizer", "LabelEncoder", "MultiLabelBinarizer", "FunctionTransformer",
    "KernelCenterer", "PatchExtractor", "FrozenEstimator",
}

FAMILY_LABELS = {
    "linear_model": "Modèles linéaires",
    "ensemble": "Ensembles",
    "tree": "Arbres de décision",
    "svm": "SVM",
    "neighbors": "Plus proches voisins",
    "naive_bayes": "Bayésien naïf",
    "neural_network": "Réseaux de neurones",
    "gaussian_process": "Processus gaussiens",
    "discriminant_analysis": "Analyse discriminante",
    "semi_supervised": "Semi-supervisé",
    "calibration": "Calibration",
    "dummy": "Référence (dummy)",
    "kernel_ridge": "Ridge à noyau",
    "cross_decomposition": "Décomposition croisée",
    "cluster": "Clustering",
    "mixture": "Mélanges gaussiens",
    "preprocessing": "Mise à l'échelle & encodage",
    "impute": "Valeurs manquantes",
    "feature_selection": "Sélection de variables",
    "decomposition": "Décomposition (PCA…)",
    "manifold": "Apprentissage de variétés",
    "random_projection": "Projections aléatoires",
    "kernel_approximation": "Approximation de noyaux",
    "covariance": "Covariance",
    "compose": "Composition",
}

KIND_CATEGORY = {
    "classifier": "Classification",
    "regressor": "Régression",
    "cluster": "Clustering",
    "transformer": "Prétraitement",
    "outlier": "Détection d'anomalies",
    "covariance": "Estimation de covariance",
    "density": "Estimation de densité",
    "neighbors": "Plus proches voisins",
}

# Mots-clés français pour la recherche dans le dépôt (sous-chaîne du nom -> mots).
FR_KEYWORDS = {
    "RandomForest": "forêt aléatoire arbres", "ExtraTrees": "forêt arbres extrêmement aléatoires",
    "DecisionTree": "arbre de décision", "GradientBoosting": "boosting gradient", "AdaBoost": "boosting",
    "LogisticRegression": "régression logistique", "LinearRegression": "régression linéaire moindres carrés",
    "Ridge": "pénalisation l2", "Lasso": "pénalisation l1", "ElasticNet": "pénalisation",
    "KNeighbors": "k plus proches voisins knn", "SVC": "svm machine à vecteurs de support",
    "SVR": "svm machine à vecteurs de support", "MLP": "réseau de neurones perceptron",
    "NB": "bayésien naïf", "KMeans": "k-moyennes kmeans", "DBSCAN": "densité",
    "Agglomerative": "classification hiérarchique ascendante cah", "GaussianMixture": "mélange gaussien",
    "PCA": "acp analyse en composantes principales réduction dimension",
    "TSNE": "réduction dimension visualisation", "StandardScaler": "normalisation standardisation centrer réduire",
    "MinMaxScaler": "normalisation mise à l'échelle", "RobustScaler": "normalisation robuste",
    "OneHotEncoder": "encodage catégoriel indicatrices dummies", "OrdinalEncoder": "encodage catégoriel",
    "Imputer": "imputation valeurs manquantes nan", "SelectKBest": "sélection variables",
    "Polynomial": "polynomiales interactions", "KBinsDiscretizer": "discrétisation classes",
    "Dummy": "référence baseline",
    "Voting": "vote ensemble combinaison", "Stacking": "empilement ensemble combinaison",
    "OneVsRest": "un contre tous multiclasse", "OneVsOne": "un contre un multiclasse",
    "RFE": "élimination récursive sélection variables", "SelectFromModel": "sélection variables importance",
    "SequentialFeatureSelector": "sélection séquentielle variables", "Threshold": "seuil décision",
    "Vectorizer": "texte mots tf-idf sac de mots nlp",
    "IsolationForest": "anomalies outliers forêt d'isolement", "LocalOutlierFactor": "anomalies outliers lof",
    "OneClassSVM": "anomalies outliers nouveauté", "EllipticEnvelope": "anomalies outliers gaussien",
    "SGDOneClassSVM": "anomalies outliers", "GaussianMixture": "mélange gaussien gmm clustering",
    "KernelDensity": "densité noyau kde", "Covariance": "covariance mahalanobis", "LedoitWolf": "covariance rétrécissement",
    "OAS": "covariance rétrécissement", "GraphicalLasso": "covariance précision parcimonieuse",
    "MinCovDet": "covariance robuste", "MDS": "positionnement multidimensionnel réduction dimension",
    "SpectralEmbedding": "plongement spectral réduction dimension", "NearestNeighbors": "voisins knn recherche",
    "Isotonic": "monotone croissante", "MultiOutput": "multisortie plusieurs cibles", "Chain": "chaîne multisortie plusieurs cibles",
    "Bagging": "bootstrap ensemble", "Calibrated": "calibration probabilités", "SelfTraining": "semi-supervisé auto-apprentissage",
    "RANSAC": "robuste outliers", "TransformedTarget": "transformation de la cible",
}

# Paramètres masqués par défaut dans le formulaire (rarement utiles en TP).
ADVANCED = {"verbose", "n_jobs", "copy", "copy_X", "warm_start", "memory", "pre_dispatch"}


def public_module(cls) -> str:
    """Module public le plus court exposant la classe (ex. sklearn.ensemble)."""
    import importlib
    parts = cls.__module__.split(".")
    for i in range(2, len(parts) + 1):
        if parts[i - 1].startswith("_"):
            break
        mod = ".".join(parts[:i])
        try:
            if getattr(importlib.import_module(mod), cls.__name__, None) is cls:
                return mod
        except ImportError:
            pass
    return ".".join(p for p in parts if not p.startswith("_"))


def doc_url(cls) -> str:
    return (
        "https://scikit-learn.org/stable/modules/generated/"
        f"{public_module(cls)}.{cls.__name__}.html"
    )


_RST_SUBS = [
    (re.compile(r":(?:class|func|meth|attr|mod|term|ref|obj|data):`~?([^`<]+?)(?:\s*<[^>]+>)?`"), r"\1"),
    (re.compile(r"``([^`]+)``"), r"\1"),
    (re.compile(r"`([^`]+)`_?"), r"\1"),
    (re.compile(r"\s+"), " "),
]


def clean_rst(text: str) -> str:
    for pat, rep in _RST_SUBS:
        text = pat.sub(rep, text)
    return text.strip()


def _sections(doc: str) -> dict[str, list[str]]:
    """Découpe une docstring numpydoc en sections {titre: lignes}."""
    doc = inspect.cleandoc(doc or "")
    lines = doc.splitlines()
    sections: dict[str, list[str]] = {"__summary__": []}
    current = "__summary__"
    i = 0
    while i < len(lines):
        line = lines[i]
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if line.strip() and re.fullmatch(r"-{3,}", nxt.strip()) and not line.startswith(" "):
            current = line.strip()
            sections[current] = []
            i += 2
            continue
        sections[current].append(line)
        i += 1
    return sections


def parse_docstring(doc: str) -> tuple[str, dict[str, dict]]:
    """Renvoie (résumé, {param: {"type": str, "help": str}})."""
    secs = _sections(doc)
    summary_lines: list[str] = []
    for line in secs.get("__summary__", []):
        if line.strip().startswith(".. ") or line.strip().startswith("Read more"):
            break
        summary_lines.append(line)
    paras, buf = [], []
    for line in summary_lines + [""]:
        if line.strip():
            buf.append(line)
        elif buf:
            text = clean_rst(" ".join(buf))
            if "sphx_glr" not in text and not text.startswith("For a usage example"):
                paras.append(text)
            buf = []
    summary = "\n\n".join(paras[:3])

    params: dict[str, dict] = {}
    cur = None
    for line in secs.get("Parameters", []):
        m = re.match(r"^(\w+)\s*:\s*(.*)$", line)
        if m and not line.startswith(" "):
            cur = m.group(1)
            params[cur] = {"type": m.group(2).strip(), "help_lines": []}
        elif m is None and not line.startswith(" ") and line.strip() and cur is None:
            continue
        elif cur:
            params[cur]["help_lines"].append(line)
    for name, info in params.items():
        paragraphs, buf, skipping = [], [], False
        for line in info.pop("help_lines"):
            s = line.strip()
            if s.startswith(".. "):
                # Ignore les directives (versionadded, note…) et leur contenu.
                if buf:
                    paragraphs.append(" ".join(buf))
                buf, skipping = [], True
                continue
            if not s:
                if buf:
                    paragraphs.append(" ".join(buf))
                buf, skipping = [], False
                continue
            if not skipping:
                buf.append(s)
        if buf:
            paragraphs.append(" ".join(buf))
        text = clean_rst(" ".join(paragraphs[:2]))
        info["help"] = text[:700] + ("…" if len(text) > 700 else "")
    return summary, params


_QUOTED = re.compile(r"""["']([^"']+)["']""")


def _choices(type_str: str) -> tuple[list[str], bool]:
    """Extrait les valeurs d'un ensemble {"a", "b"} ; exclusif si rien d'autre."""
    m = re.search(r"\{([^}]*)\}", type_str)
    if not m:
        return [], False
    items = [s.strip() for s in m.group(1).split(",") if s.strip()]
    quoted = [q.group(1) for s in items if (q := _QUOTED.fullmatch(s))]
    if not quoted:
        return [], False
    rest = (type_str[: m.start()] + type_str[m.end():]).strip()
    rest = re.sub(r",?\s*default\s*=.*$", "", rest).strip(" ,")
    exclusive = len(quoted) == len(items) and rest == ""
    return quoted, exclusive


def _fmt_default(value) -> str:
    if isinstance(value, str):
        return repr(value)
    if isinstance(value, (int, float, bool, type(None), tuple, list)):
        return repr(value)
    return str(value)


def hyperparams(cls) -> list[dict]:
    _, docs = parse_docstring(cls.__doc__ or "")
    out = []
    sig = inspect.signature(cls.__init__)
    for name, p in sig.parameters.items():
        if name == "self" or p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            continue
        info = docs.get(name, {})
        type_str = info.get("type", "")
        default = p.default
        spec = {
            "name": name,
            "label": name,
            "help": info.get("help", ""),
            "typeinfo": type_str,
            "default": default if isinstance(default, (bool, int, str, type(None)))
            or (isinstance(default, float) and math.isfinite(default)) else None,
            "default_repr": _fmt_default(default),
            "group": "Hyperparamètres",
            "advanced": name in ADVANCED,
        }
        choices, exclusive = _choices(type_str)
        is_bool_only = isinstance(default, bool) and re.match(r"^bool\b(,|$)", type_str or "bool") and " or " not in type_str.split(",")[0]
        if is_bool_only:
            spec["type"] = "bool"
        elif exclusive and isinstance(default, str) and default in choices:
            spec["type"] = "choice"
            spec["choices"] = choices
        else:
            spec["type"] = "literal"
            spec["suggestions"] = [repr(c) for c in choices]
        out.append(spec)
    return out


def _kinds(cls) -> list[str]:
    """Rôle(s) de l'estimateur dans KataML."""
    from sklearn.base import (
        ClassifierMixin, ClusterMixin, OutlierMixin, RegressorMixin, TransformerMixin,
    )
    module = public_module(cls)
    if issubclass(cls, OutlierMixin):
        return ["outlier"]
    kinds = []
    if issubclass(cls, ClassifierMixin):
        kinds.append("classifier")
    if issubclass(cls, RegressorMixin):
        kinds.append("regressor")
    if issubclass(cls, ClusterMixin) or (module == "sklearn.mixture" and hasattr(cls, "fit_predict")):
        kinds.append("cluster")
    if kinds:
        return kinds
    if issubclass(cls, TransformerMixin) or (module == "sklearn.manifold" and hasattr(cls, "fit_transform")):
        return ["transformer"]
    if module == "sklearn.covariance":
        return ["covariance"]
    if cls.__name__ == "KernelDensity":
        return ["density"]
    if cls.__name__ == "NearestNeighbors":
        return ["neighbors"]
    return []


@lru_cache(maxsize=1)
def estimators() -> dict[str, dict]:
    """{nom: {"cls", "kinds", "family", "summary", "doc_url"}}"""
    result: dict[str, dict] = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for name, cls in all_estimators():
            if name in EXCLUDED_NAMES or (cls.__module__.startswith(EXCLUDED_MODULES) and name not in ALLOWED_NAMES):
                continue
            sig = inspect.signature(cls.__init__)
            required = [
                p for n, p in sig.parameters.items()
                if n != "self" and p.default is inspect._empty
                and p.kind not in (p.VAR_KEYWORD, p.VAR_POSITIONAL)
            ]
            if required:
                continue
            kinds = _kinds(cls)
            if not kinds:
                continue
            family_key = public_module(cls).split(".")[1] if "." in public_module(cls) else ""
            summary, _ = parse_docstring(cls.__doc__ or "")
            result[name] = {
                "cls": cls,
                "kinds": kinds,
                "family": FAMILY_LABELS.get(family_key, family_key.replace("_", " ").capitalize()),
                "summary": summary,
                "doc_url": doc_url(cls),
                "module": public_module(cls),
                "keywords": " ".join(v for k, v in FR_KEYWORDS.items() if k in name),
            }
    return result


def sklearn_version() -> str:
    return sklearn.__version__


# Méta-estimateurs : ils prennent un ou plusieurs estimateurs en paramètre, fournis
# dans KataML par des ports « modèle ».
#   single : nom du paramètre recevant un estimateur de base
#   multi  : nom du paramètre recevant une liste [(nom, estimateur), …]
#   final  : estimateur final optionnel (stacking)
META_SPECS = {
    "VotingClassifier": {"kind": "classifier", "multi": "estimators"},
    "VotingRegressor": {"kind": "regressor", "multi": "estimators"},
    "StackingClassifier": {"kind": "classifier", "multi": "estimators", "final": "final_estimator"},
    "StackingRegressor": {"kind": "regressor", "multi": "estimators", "final": "final_estimator"},
    "OneVsRestClassifier": {"kind": "classifier", "single": "estimator"},
    "OneVsOneClassifier": {"kind": "classifier", "single": "estimator"},
    "OutputCodeClassifier": {"kind": "classifier", "single": "estimator"},
    "FixedThresholdClassifier": {"kind": "classifier", "single": "estimator"},
    "TunedThresholdClassifierCV": {"kind": "classifier", "single": "estimator"},
    "RFE": {"kind": "transformer", "single": "estimator"},
    "RFECV": {"kind": "transformer", "single": "estimator"},
    "SelectFromModel": {"kind": "transformer", "single": "estimator"},
    "SequentialFeatureSelector": {"kind": "transformer", "single": "estimator"},
    "MultiOutputClassifier": {"kind": "classifier", "single": "estimator", "targets": True},
    "MultiOutputRegressor": {"kind": "regressor", "single": "estimator", "targets": True},
    "ClassifierChain": {"kind": "classifier", "single": "estimator", "targets": True},
    "RegressorChain": {"kind": "regressor", "single": "estimator", "targets": True},
}

# Estimateurs dont l'estimateur de base (optionnel) peut être fourni par un port « modèle ».
OPTIONAL_BASE = {
    "BaggingClassifier": "estimator", "BaggingRegressor": "estimator",
    "AdaBoostClassifier": "estimator", "AdaBoostRegressor": "estimator",
    "CalibratedClassifierCV": "estimator", "SelfTrainingClassifier": "estimator",
    "RANSACRegressor": "estimator", "TransformedTargetRegressor": "regressor",
}


@lru_cache(maxsize=1)
def meta_estimators() -> dict[str, dict]:
    """{nom: {"cls", "spec", "family", "summary", "doc_url", "module", "keywords"}}"""
    found = dict(all_estimators())
    result = {}
    for name, spec in META_SPECS.items():
        cls = found.get(name)
        if cls is None:          # absent de cette version de scikit-learn
            continue
        module = public_module(cls)
        family_key = module.split(".")[1] if "." in module else ""
        summary, _ = parse_docstring(cls.__doc__ or "")
        result[name] = {
            "cls": cls, "spec": spec, "summary": summary, "doc_url": doc_url(cls), "module": module,
            "family": FAMILY_LABELS.get(family_key, family_key.replace("_", " ").capitalize()),
            "keywords": " ".join(v for k, v in FR_KEYWORDS.items() if k in name),
        }
    return result
