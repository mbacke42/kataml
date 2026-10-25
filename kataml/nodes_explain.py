"""Explicabilité et diagnostic : frontière de décision, arbre, courbe de validation,
dépendance partielle, calibration."""

from __future__ import annotations

import ast

import numpy as np
import pandas as pd
from sklearn import metrics as skm
from sklearn.base import clone

from .nodes import (
    CAT_EXPLAIN, CAT_SCORE, CAT_TUNE, DATA, MODEL, REGISTRY, Ctx, ModelPort, NodeError, P,
    n_jobs, _fit_message, _jsonable, _scorer_names, check_columns, cv_code, cv_params, make_cv, py, register,
    supervised_target, table_block,
)


def _supervised(m: ModelPort, what="Ce nœud"):
    if m.kind not in ("classifier", "regressor"):
        raise NodeError(f"{what} requiert un modèle supervisé (classification ou régression).")


def _typical_row(X: pd.DataFrame) -> dict:
    """Valeur « typique » de chaque colonne : médiane si numérique, mode sinon."""
    row = {}
    for c in X.columns:
        s = X[c].dropna()
        if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
            row[c] = float(s.median()) if len(s) else 0.0
        else:
            row[c] = s.mode().iloc[0] if len(s) else None
    return row


# --------------------------------------------------------------------------
# Frontière de décision
# --------------------------------------------------------------------------

@register(
    "explain.decision_boundary", "Frontière de décision", CAT_EXPLAIN,
    """
    Carte des prédictions du modèle dans le plan de deux variables : chaque zone
    colorée correspond à une classe prédite (ou à une valeur prédite pour une
    régression), avec les points de la table par-dessus. L'intensité indique la
    confiance (probabilité maximale) quand le modèle sait la calculer.

    Idéal avec make_moons ou make_circles pour voir le sous- ou le
    surapprentissage (arbre profond, k voisins, C d'un SVM…). Si le modèle
    utilise d'autres variables, elles sont fixées à leur médiane (ou à leur mode).
    """,
    inputs=[("Modèle", MODEL), ("Table", DATA)],
    params=[
        P("x", "Axe X (vide = 1re variable)", "column", "", port=1, allow_empty=True),
        P("y", "Axe Y (vide = 2e variable)", "column", "", port=1, allow_empty=True),
        P("resolution", "Résolution de la grille", "int", 150, min=20),
        P("max_points", "Points affichés max.", "int", 2000),
    ],
    has_view=True, color="explain",
    doc_url="https://scikit-learn.org/stable/modules/generated/sklearn.inspection.DecisionBoundaryDisplay.html",
    keywords="frontière décision zones carte classes surapprentissage moons",
)
def decision_boundary(ctx: Ctx, p):
    m, df = ctx.model(0), ctx.data(1)
    if not hasattr(m.estimator, "predict"):
        raise NodeError(f"{m.name} ne sait pas prédire de nouveaux points.")
    feats = list(m.features)
    if len(feats) < 2 and not (p.get("x") and p.get("y")):
        raise NodeError("Il faut au moins deux variables.")
    x = p.get("x") or feats[0]
    y = p.get("y") or next(f for f in feats if f != x)
    for c in (x, y):
        if c not in feats:
            raise NodeError(f"« {c} » n'est pas une variable du modèle ({', '.join(feats[:10])}…).")
    check_columns(df, feats)
    X = df[feats]
    for c in (x, y):
        if not pd.api.types.is_numeric_dtype(X[c]):
            raise NodeError(f"« {c} » n'est pas numérique.")
    res = max(20, min(400, int(p.get("resolution") or 150)))
    pad = lambda s: (s.max() - s.min()) * 0.05 or 1.0
    x0, x1 = X[x].min() - pad(X[x]), X[x].max() + pad(X[x])
    y0, y1 = X[y].min() - pad(X[y]), X[y].max() + pad(X[y])
    gx, gy = np.meshgrid(np.linspace(x0, x1, res), np.linspace(y0, y1, res))
    base = _typical_row(X)
    grid = pd.DataFrame({c: [base[c]] * (res * res) for c in feats})
    grid[x], grid[y] = gx.ravel(), gy.ravel()
    try:
        pred = m.estimator.predict(grid)
        conf = None
        if m.kind == "classifier" and hasattr(m.estimator, "predict_proba"):
            conf = m.estimator.predict_proba(grid).max(axis=1)
    except Exception as e:
        raise _fit_message(e) from e
    n = len(X)
    idx = np.random.default_rng(0).permutation(n)[: int(p.get("max_points") or 2000)]
    block = {"type": "chart", "chart": "decision", "title": f"Frontière de décision ({m.name})",
             "x0": float(x0), "x1": float(x1), "y0": float(y0), "y1": float(y1), "nx": res, "ny": res,
             "xlabel": str(x), "ylabel": str(y),
             "px": X[x].to_numpy()[idx].astype(float).round(5).tolist(),
             "py": X[y].to_numpy()[idx].astype(float).round(5).tolist()}
    if m.kind == "regressor":
        block.update(continuous=True, z=np.round(pred.astype(float), 5).tolist())
        if m.target in df.columns:
            block["pv"] = df[m.target].to_numpy()[idx].astype(float).round(5).tolist()
    else:
        classes = list(m.classes) if m.classes is not None else sorted(set(pred), key=str)
        lookup = {c: i for i, c in enumerate(classes)}
        block.update(classes=[str(c) for c in classes], z=[lookup.get(v, -1) for v in pred])
        if conf is not None:
            block["conf"] = np.round(conf, 3).tolist()
        truth = m.target if m.target in df.columns else None
        labels = df[truth] if truth else pd.Series(m.estimator.predict(X))
        block["pc"] = [lookup.get(v, -1) for v in labels.to_numpy()[idx]]
    ctx.add_view(block)
    others = [f for f in feats if f not in (x, y)]
    if others:
        ctx.add_view({"type": "text", "title": "Autres variables fixées", "text": ", ".join(
            f"{c} = {_jsonable(base[c]) if not isinstance(base[c], float) else round(base[c], 4)}" for c in others[:20])
            + (" …" if len(others) > 20 else "")})
    return []


REGISTRY["explain.decision_boundary"].code = lambda p, ins, outs: (
    "# Frontière de décision (nécessite matplotlib) :\n"
    f"# from sklearn.inspection import DecisionBoundaryDisplay\n"
    f"# DecisionBoundaryDisplay.from_estimator({ins[0]}, {ins[1]}[{ins[0]}.features_[:2]])")


# --------------------------------------------------------------------------
# Arbre de décision
# --------------------------------------------------------------------------

def _find_tree(m: ModelPort, index: int):
    est = m.final_estimator()
    names = getattr(est, "feature_names_in_", None)
    if hasattr(est, "tree_"):
        return est, names
    if hasattr(est, "estimators_"):
        trees = np.asarray(est.estimators_, dtype=object).ravel()
        if not len(trees) or not hasattr(trees[0], "tree_"):
            raise NodeError(f"{m.name} n'est pas un ensemble d'arbres.")
        if not 0 <= index < len(trees):
            raise NodeError(f"Indice d'arbre hors limites (0 à {len(trees) - 1}).")
        t = trees[index]
        return t, getattr(t, "feature_names_in_", None) if getattr(t, "feature_names_in_", None) is not None else names
    raise NodeError(f"{m.name} n'est pas un modèle à base d'arbres (DecisionTree, RandomForest, GradientBoosting…).")


@register(
    "explain.tree", "Visualiser l'arbre", CAT_EXPLAIN,
    """
    Dessine un arbre de décision : condition de chaque nœud, nombre
    d'échantillons, impureté et classe majoritaire (ou valeur moyenne). Pour une
    forêt ou un boosting, choisissez l'indice de l'arbre à afficher. Les règles
    sont aussi données sous forme de texte (sklearn.tree.export_text).
    """,
    inputs=[("Modèle", MODEL)],
    params=[
        P("max_depth", "Profondeur affichée", "int", 4, min=1),
        P("tree_index", "Indice de l'arbre (forêts, boosting)", "int", 0, min=0),
    ],
    has_view=True, color="explain",
    doc_url="https://scikit-learn.org/stable/modules/tree.html",
    keywords="arbre décision règles visualiser dessiner tree",
)
def tree_view(ctx: Ctx, p):
    from sklearn.tree import export_text
    m = ctx.model(0)
    est, names = _find_tree(m, int(p.get("tree_index") or 0))
    t = est.tree_
    names = [str(n) for n in names] if names is not None else (
        list(m.features) if len(m.features) == t.n_features else [f"x{i}" for i in range(t.n_features)])
    classes = [str(c) for c in getattr(est, "classes_", [])] or None
    depth = max(1, int(p.get("max_depth") or 4))

    def node(i, d):
        leaf = t.children_left[i] == -1
        value = t.value[i][0]
        info = {"samples": int(t.n_node_samples[i]), "impurity": round(float(t.impurity[i]), 4)}
        if classes and len(value) == len(classes):
            dist = value / value.sum() if value.sum() else value
            info["class"] = classes[int(np.argmax(value))]
            info["dist"] = [round(float(v), 3) for v in dist]
        else:
            info["value"] = round(float(value[0]), 4)
        if not leaf:
            info["rule"] = f"{names[t.feature[i]]} ≤ {t.threshold[i]:.4g}"
            if d < depth:
                info["children"] = [node(t.children_left[i], d + 1), node(t.children_right[i], d + 1)]
            else:
                info["truncated"] = True
        return info

    ctx.add_view({"type": "metrics", "items": [
        {"label": "Profondeur", "value": int(est.get_depth())},
        {"label": "Feuilles", "value": int(est.get_n_leaves())},
        {"label": "Nœuds", "value": int(t.node_count)}]})
    ctx.add_view({"type": "chart", "chart": "tree", "title": "Arbre de décision", "root": node(0, 0),
                  "classes": classes, "criterion": getattr(est, "criterion", "")})
    ctx.add_view({"type": "text", "title": "Règles", "mono": True,
                  "text": export_text(est, feature_names=names, max_depth=depth)[:30000]})
    return []


REGISTRY["explain.tree"].code = lambda p, ins, outs: (
    "from sklearn.tree import export_text\n"
    f"_tree = {ins[0]}.estimators_[{int(p.get('tree_index') or 0)}] if hasattr({ins[0]}, 'estimators_') else {ins[0]}\n"
    f"print(export_text(_tree, feature_names=list({ins[0]}.features_), max_depth={int(p.get('max_depth') or 4)}))")


# --------------------------------------------------------------------------
# Courbe de validation
# --------------------------------------------------------------------------

@register(
    "tune.validation_curve", "Courbe de validation", CAT_TUNE,
    """
    Score d'apprentissage et de validation croisée en fonction d'un
    hyperparamètre (sklearn.model_selection.validation_curve). L'écart entre
    les deux courbes montre où commence le surapprentissage. Exemples :
    max_depth avec [1, 2, 4, 8, 16, None], C avec [0.01, 0.1, 1, 10, 100].
    Pour un Pipeline, préfixez le nom : model__C.
    """,
    inputs=[("Modèle (configuration)", MODEL), ("Table", DATA)], outputs=[("Courbe", DATA)],
    params=[
        P("param", "Hyperparamètre", "str", "", "Nom exact du paramètre (voir la vue du modèle).", required=True),
        P("values", "Valeurs testées", "literal", "", "Liste Python, ex. [1, 2, 4, 8, None].", required=True),
        P("scoring", "Métrique", "choice", "", choices=[""] + _scorer_names(), choice_labels={"": "(par défaut)"}),
        P("log", "Échelle logarithmique", "choice", "auto", choices=["auto", "oui", "non"]),
        *cv_params(1),
    ],
    has_view=True, color="tune",
    doc_url="https://scikit-learn.org/stable/modules/learning_curve.html#validation-curve",
    keywords="validation curve hyperparamètre surapprentissage complexité",
)
def validation_curve_node(ctx: Ctx, p):
    from sklearn.model_selection import validation_curve
    m, df = ctx.model(0), ctx.data(1)
    X, y, multi = supervised_target(m, df)
    cv, groups, _ = make_cv(p, m.kind, df, multi)
    param = (p.get("param") or "").strip()
    if param not in m.estimator.get_params():
        from .nodes import tunable_params
        raise NodeError(f"Paramètre inconnu « {param} ». Possibles : {', '.join(tunable_params(m.estimator)[:25])}")
    try:
        values = ast.literal_eval(p.get("values") or "")
    except Exception as e:
        raise NodeError(f"Valeurs invalides (liste Python attendue) : {e}") from e
    if not isinstance(values, (list, tuple)) or len(values) < 2:
        raise NodeError("Donnez au moins deux valeurs, sous forme de liste.")
    try:
        tr, va = validation_curve(clone(m.estimator), X, y, param_name=param, param_range=list(values),
                                  cv=cv, groups=groups, scoring=p.get("scoring") or None, n_jobs=n_jobs(len(X)))
    except Exception as e:
        raise _fit_message(e) from e
    labels = [repr(v) for v in values]
    out = pd.DataFrame({param: labels, "train_moyen": tr.mean(1), "train_std": tr.std(1),
                        "validation_moyen": va.mean(1), "validation_std": va.std(1)})
    numeric = all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values)
    best = int(np.argmax(va.mean(1)))
    ctx.add_view({"type": "metrics", "items": [
        {"label": "Meilleure valeur", "value": labels[best]},
        {"label": "Score de validation", "value": round(float(va.mean(1)[best]), 4)}]})
    if numeric:
        pos = [v for v in values if v > 0]
        log = p.get("log") == "oui" or (p.get("log", "auto") == "auto" and len(pos) == len(values)
                                         and max(values) / min(values) >= 50)
        ctx.add_view({"type": "chart", "chart": "line", "title": f"Courbe de validation ({param})",
                      "xlabel": param, "ylabel": "Score", "markers": True, "xlog": log,
                      "series": [{"name": "Apprentissage", "x": list(map(float, values)), "y": tr.mean(1).tolist(), "band": tr.std(1).tolist()},
                                 {"name": "Validation", "x": list(map(float, values)), "y": va.mean(1).tolist(), "band": va.std(1).tolist()}]})
    else:
        ctx.add_view({"type": "chart", "chart": "groupedbar", "title": f"Courbe de validation ({param})", "labels": labels,
                      "series": [{"name": "Apprentissage", "values": tr.mean(1).round(4).tolist()},
                                 {"name": "Validation", "values": va.mean(1).round(4).tolist()}]})
    return [out]


REGISTRY["tune.validation_curve"].code = lambda p, ins, outs: (
    f"_tr, _va = validation_curve(clone({ins[0]}), {ins[1]}[{ins[0]}.features_], {ins[1]}[{ins[0]}.target_], "
    f"param_name={py(p.get('param'))}, param_range={(p.get('values') or '[]').strip()}, "
    f"cv={cv_code(p, ins[0], ins[1])[0]}, groups={cv_code(p, ins[0], ins[1])[1]}, "
    f"scoring={py(p.get('scoring') or None)})\n"
    f"{outs[0]} = pd.DataFrame({{'valeur': {(p.get('values') or '[]').strip()}, 'train': _tr.mean(1), 'validation': _va.mean(1)}})\n"
    f"print({outs[0]})")


# --------------------------------------------------------------------------
# Dépendance partielle
# --------------------------------------------------------------------------

@register(
    "explain.partial_dependence", "Dépendance partielle", CAT_EXPLAIN,
    """
    Effet moyen d'une variable sur la prédiction, toutes les autres variables
    étant moyennées (sklearn.inspection.partial_dependence). Pour une
    classification, une courbe par classe (probabilité prédite).
    """,
    inputs=[("Modèle", MODEL), ("Table", DATA)], outputs=[("Dépendances", DATA)],
    params=[
        P("features", "Variables (vide = 3 premières)", "columns", [], port=1),
        P("grid_resolution", "Points par courbe", "int", 40, min=5),
    ],
    has_view=True, color="explain",
    doc_url="https://scikit-learn.org/stable/modules/partial_dependence.html",
    keywords="dépendance partielle pdp effet marginal explicabilité",
)
def partial_dependence_node(ctx: Ctx, p):
    from sklearn.inspection import partial_dependence
    m, df = ctx.model(0), ctx.data(1)
    _supervised(m)
    feats = list(p.get("features") or m.features[:3])
    for f in feats:
        if f not in m.features:
            raise NodeError(f"« {f} » n'est pas une variable du modèle.")
    check_columns(df, m.features)
    X = df[m.features]
    rows = []
    for f in feats[:8]:
        categorical = not pd.api.types.is_numeric_dtype(X[f])
        try:
            r = partial_dependence(m.estimator, X, [f], grid_resolution=int(p.get("grid_resolution") or 40),
                                   kind="average", categorical_features=[f] if categorical else None)
        except Exception as e:
            raise _fit_message(e) from e
        grid = r["grid_values"][0]
        avg = np.asarray(r["average"])
        names = ([str(c) for c in m.classes] if m.kind == "classifier" and avg.shape[0] > 1
                 else [str(m.classes[1]) if m.kind == "classifier" and m.classes is not None and len(m.classes) == 2 else "prédiction"])
        for k, name in enumerate(names):
            for g, v in zip(grid, avg[k]):
                rows.append({"variable": f, "valeur": _jsonable(g), "sortie": name, "dépendance": float(v)})
        if categorical:
            ctx.add_view({"type": "chart", "chart": "groupedbar", "title": f"Dépendance partielle : {f}",
                          "labels": [str(g) for g in grid],
                          "series": [{"name": n, "values": np.round(avg[k], 4).tolist()} for k, n in enumerate(names)][:6]})
        else:
            ctx.add_view({"type": "chart", "chart": "line", "title": f"Dépendance partielle : {f}", "xlabel": str(f),
                          "ylabel": "Probabilité" if m.kind == "classifier" else "Prédiction",
                          "series": [{"name": n, "x": [float(g) for g in grid], "y": np.round(avg[k], 5).tolist()}
                                     for k, n in enumerate(names)][:8]})
    return [pd.DataFrame(rows)]


REGISTRY["explain.partial_dependence"].code = lambda p, ins, outs: (
    "from sklearn.inspection import partial_dependence\n"
    f"_rows = []\nfor _f in {py(p.get('features') or [])} or list({ins[0]}.features_[:3]):\n"
    f"    _r = partial_dependence({ins[0]}, {ins[1]}[{ins[0]}.features_], [_f], kind='average')\n"
    f"    _rows += [{{'variable': _f, 'valeur': g, 'dépendance': v}} for g, v in zip(_r['grid_values'][0], _r['average'][0])]\n"
    f"{outs[0]} = pd.DataFrame(_rows)")


# --------------------------------------------------------------------------
# Calibration
# --------------------------------------------------------------------------

@register(
    "score.calibration", "Courbe de calibration", CAT_SCORE,
    """
    Compare les probabilités prédites aux fréquences observées
    (sklearn.calibration.calibration_curve) : un modèle bien calibré suit la
    diagonale. Utilise les colonnes « P (cible=classe) » du Prédicteur et
    affiche le score de Brier (plus bas = mieux).
    """,
    inputs=[("Table + probabilités", DATA)], outputs=[("Calibration", DATA)],
    params=[
        P("true", "Colonne réelle (auto si vide)", "column", "", port=0, allow_empty=True),
        P("n_bins", "Nombre de classes de probabilité", "int", 10, min=2),
        P("strategy", "Découpage", "choice", "uniform", choices=["uniform", "quantile"],
          choice_labels={"uniform": "Intervalles égaux", "quantile": "Effectifs égaux (quantiles)"}),
    ],
    has_view=True, color="score",
    doc_url="https://scikit-learn.org/stable/modules/calibration.html",
    keywords="calibration probabilités fiabilité brier",
)
def calibration_node(ctx: Ctx, p):
    import re
    from sklearn.calibration import calibration_curve
    df = ctx.data()
    prob_cols = [c for c in df.columns if re.match(r"P \((.+)=(.+)\)$", str(c))]
    if not prob_cols:
        raise NodeError("Aucune colonne « P (cible=classe) ». Activez « Ajouter les probabilités » dans le Prédicteur.")
    target = p.get("true") or re.match(r"P \((.+?)=", prob_cols[0]).group(1)
    check_columns(df, [target])
    yt = df[target].astype(str)
    cols = prob_cols[1:2] if len(prob_cols) == 2 else prob_cols
    series, hist, rows, items = [], [], [], []
    edges = np.linspace(0, 1, 11)
    for c in cols[:8]:
        cls = re.match(r"P \(.+?=(.+)\)$", str(c)).group(1)
        pos = (yt == cls).astype(int)
        if pos.nunique() < 2:
            continue
        frac, mean = calibration_curve(pos, df[c], n_bins=int(p.get("n_bins") or 10),
                                       strategy=p.get("strategy") or "uniform")
        brier = skm.brier_score_loss(pos, df[c])
        series.append({"name": f"{cls} (Brier={brier:.3f})", "x": mean.tolist(), "y": frac.tolist()})
        hist.append({"name": cls, "counts": np.histogram(df[c], bins=edges)[0].tolist()})
        items.append({"label": f"Brier {cls}", "value": round(float(brier), 4)})
        rows += [{"classe": cls, "probabilité moyenne": float(a), "fréquence observée": float(b)} for a, b in zip(mean, frac)]
    if not series:
        raise NodeError("Impossible de calculer la calibration : une seule classe présente.")
    ctx.add_view({"type": "metrics", "items": items})
    ctx.add_view({"type": "chart", "chart": "line", "title": "Courbe de calibration", "series": series,
                  "xlabel": "Probabilité prédite (moyenne)", "ylabel": "Fréquence observée",
                  "diagonal": True, "domain": [0, 1], "markers": True})
    ctx.add_view({"type": "chart", "chart": "histogram", "title": "Distribution des probabilités prédites",
                  "edges": edges.tolist(), "series": hist, "xlabel": "Probabilité", "ylabel": "Effectif"})
    return [pd.DataFrame(rows)]


REGISTRY["score.calibration"].code = lambda p, ins, outs: (
    "from sklearn.calibration import calibration_curve\n"
    f"# _frac, _mean = calibration_curve({ins[0]}['cible'] == 'classe', {ins[0]}['P (cible=classe)'], n_bins={int(p.get('n_bins') or 10)})")
