"""Composition de modèles : Pipeline scikit-learn, méta-estimateurs, comparateur.

Les ports « modèle » transportent des estimateurs ajustés ; ces nœuds en réutilisent
la *configuration* (``sklearn.base.clone``) pour construire des objets composés,
réajustés de bout en bout. Une validation croisée sur un Pipeline réajuste donc
aussi le prétraitement à chaque pli : pas de fuite d'information.
"""

from __future__ import annotations

import re
import warnings

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import KFold, StratifiedKFold, cross_validate
from sklearn.pipeline import Pipeline

from . import sk_catalog
from .nodes import (
    CAT_COMPOSE, CAT_TUNE, DATA, MODEL, REGISTRY, Ctx, ModelPort, NodeError, NodeType, P,
    n_jobs, _fit_message, _learner_view, _scorer_names, build_estimator, check_columns, cv_code, cv_params,
    hp_code, make_cv, py, register, table_block, tunable_params,
)


# --------------------------------------------------------------------------
# Utilitaires
# --------------------------------------------------------------------------

def selector(cols) -> ColumnTransformer:
    """Étape de Pipeline qui ne garde que ``cols`` (en conservant un DataFrame)."""
    ct = ColumnTransformer([("select", "passthrough", list(cols))], remainder="drop",
                           verbose_feature_names_out=False)
    return ct.set_output(transform="pandas")


def as_step(m: ModelPort, available: list[str]):
    """Clone l'estimateur de ``m`` ; ajoute une sélection de colonnes si nécessaire."""
    est = clone(m.estimator)
    if list(m.features) == list(available):
        return est
    return Pipeline([("colonnes", selector(m.features)), ("estimateur", est)])


def step_name(label: str | None, m: ModelPort, used: set[str]) -> str:
    base = re.sub(r"[^0-9a-zA-Z_]+", "_", (label or m.name)).strip("_").lower() or "modele"
    base = base.replace("__", "_")
    name, i = base, 2
    while name in used:
        name, i = f"{base}_{i}", i + 1
    used.add(name)
    return name


def supervised_inputs(models: list[ModelPort]) -> tuple[str, str, list[str]]:
    """Vérifie que des modèles sont compatibles : même cible, même type. Renvoie (cible, type, variables)."""
    kinds = {m.kind for m in models}
    targets = {tuple(m.target) if isinstance(m.target, (list, tuple)) else m.target for m in models}
    if not kinds <= {"classifier", "regressor"}:
        raise NodeError("Des modèles supervisés (classification ou régression) sont attendus.")
    if len(kinds) > 1:
        raise NodeError("Les modèles mélangent classification et régression.")
    if len(targets) > 1:
        raise NodeError(f"Les modèles n'ont pas la même cible : {', '.join(map(str, targets))}.")
    feats: list[str] = []
    for m in models:
        feats += [f for f in m.features if f not in feats]
    target = targets.pop()
    return (list(target) if isinstance(target, tuple) else target), kinds.pop(), feats


def connected_models(ctx: Ctx, first: int) -> list[tuple[ModelPort, str | None]]:
    out = []
    for i in range(first, len(ctx.inputs)):
        v = ctx.inputs[i]
        if v is None:
            continue
        if not isinstance(v, ModelPort):
            raise NodeError(f"Le port d'entrée {i + 1} attend un modèle.")
        out.append((v, ctx.label(i)))
    return out


def fit_quietly(ctx: Ctx, est, X, y=None):
    with warnings.catch_warnings(record=True) as wlist:
        warnings.simplefilter("always")
        try:
            est.fit(X, y) if y is not None else est.fit(X)
        except NodeError:
            raise
        except Exception as e:
            raise _fit_message(e) from e
    for w in wlist[:3]:
        ctx.messages.append(f"{w.category.__name__} : {str(w.message)[:200]}")


def tunable_block(est) -> dict:
    keys = tunable_params(est)
    params = est.get_params(deep=True)
    rows = [[k, repr(params[k])] for k in keys[:80]]
    return {"type": "table", "title": "Paramètres réglables (pour la recherche d'hyperparamètres)",
            "columns": ["paramètre", "valeur"], "rows": rows}


# --------------------------------------------------------------------------
# Pipeline
# --------------------------------------------------------------------------

PIPE_DESC = """
Assemble un ou plusieurs prétraitements et un modèle en un seul objet
sklearn.pipeline.Pipeline, réajusté sur les données brutes.

Branchez la table *brute* (avant prétraitement), le modèle (sortie d'un nœud
d'apprentissage) et, dans l'ordre, les transformeurs (sorties « Transformeur »).
Leurs réglages sont repris, mais tout est réentraîné ensemble.

Le Pipeline obtenu s'applique directement aux données brutes de test avec le
Prédicteur, sans nœud « Appliquer un transformeur ». Surtout, la validation
croisée et la recherche d'hyperparamètres réajustent alors le prétraitement à
chaque pli : c'est la façon correcte d'évaluer un modèle sans fuite
d'information. Les paramètres se nomment prep1__…, model__… (voir la vue).
"""


@register(
    "compose.pipeline", "Pipeline", CAT_COMPOSE, PIPE_DESC,
    inputs=[("Table brute", DATA), ("Modèle", MODEL), ("Prétraitement 1", MODEL),
            ("Prétraitement 2", MODEL), ("Prétraitement 3", MODEL)],
    outputs=[("Pipeline", MODEL)],
    params=[],
    has_view=True, color="compose",
    doc_url="https://scikit-learn.org/stable/modules/compose.html#pipeline",
    keywords="pipeline enchaîner composer prétraitement fuite leakage make_pipeline",
)
def pipeline_node(ctx: Ctx, p):
    df, model = ctx.data(0), ctx.model(1)
    preps = connected_models(ctx, 2)
    steps = []
    for i, (m, _) in enumerate(preps, 1):
        if m.kind != "transformer":
            raise NodeError(f"Le prétraitement {i} doit être un transformeur (sortie « Transformeur »).")
        steps.append((f"prep{i}", clone(m.estimator)))
    supervised = model.kind in ("classifier", "regressor")
    target = model.target if supervised else None
    if supervised:
        check_columns(df, [target], "Colonne cible du modèle")
    for i, (m, _) in enumerate(preps, 1):
        if target and target in m.features:
            raise NodeError(f"Le prétraitement {i} ({m.name}) transforme la colonne cible « {target} » : "
                            "indiquez-la comme cible dans ce nœud pour l'exclure.")
    raw = [c for c in df.columns if c != target]
    if preps:
        check_columns(df, preps[0][0].features, "Colonne du prétraitement 1")
    upstream_out = preps[-1][0].output_columns if preps else raw
    if model.kind == "transformer":
        steps.append(("model", clone(model.estimator)))
    else:
        if upstream_out is None or list(model.features) != [c for c in upstream_out if c != target]:
            steps.append(("select", selector(model.features)))
        steps.append(("model", clone(model.estimator)))
    pipe = Pipeline(steps).set_output(transform="pandas")
    X = df[raw]
    y = df[target] if supervised else None
    if y is not None and y.isna().any():
        raise NodeError("La colonne cible contient des valeurs manquantes.")
    fit_quietly(ctx, pipe, X, y)
    name = " → ".join([m.name for m, _ in preps] + [model.name])
    out = ModelPort(pipe, model.kind, name, raw, target,
                    classes=list(pipe.classes_) if hasattr(pipe, "classes_") else None)
    ctx.add_view({"type": "text", "title": "Étapes", "text": "  →  ".join(
        f"{n} ({type(s).__name__ if not isinstance(s, ColumnTransformer) else _ct_name(s)})" for n, s in pipe.steps)})
    if supervised:
        _learner_view(ctx, out, X, y)
    ctx.add_view(tunable_block(pipe))
    return [out]


def _ct_name(ct: ColumnTransformer) -> str:
    return ", ".join(type(t).__name__ if not isinstance(t, str) else t for _, t, _ in ct.transformers)


def _code_pipeline(p, ins, outs):
    data, model, *preps = ins
    preps = [v for v in preps if v]
    o = outs[0]
    steps = ", ".join(f"(\"prep{i}\", clone({v}))" for i, v in enumerate(preps, 1))
    out_cols = (f"[c for c in {preps[-1]}.get_feature_names_out() if c != _target]" if preps
                else f"[c for c in {data}.columns if c != _target]")
    return (f"_target = getattr({model}, 'target_', None)\n"
            f"_features = [c for c in {data}.columns if c != _target]\n"
            f"# Sélection des variables du modèle si elles diffèrent de la sortie du prétraitement.\n"
            f"_select = [] if list({model}.features_) == {out_cols} else [(\"select\", colonnes({model}.features_))]\n"
            f"{o} = Pipeline([{steps}{', ' if steps else ''}*_select, (\"model\", clone({model}))]).set_output(transform='pandas')\n"
            f"{o}.fit({data}[_features], {data}[_target] if _target else None)\n"
            f"{o}.features_, {o}.target_ = _features, _target")


REGISTRY["compose.pipeline"].code = _code_pipeline
REGISTRY["compose.pipeline"].optional_inputs = [2, 3, 4]


# --------------------------------------------------------------------------
# Méta-estimateurs (générés depuis scikit-learn)
# --------------------------------------------------------------------------

def _make_meta(name: str, info: dict):
    cls, spec = info["cls"], info["spec"]
    kind = spec["kind"]
    model_params = {spec.get("single"), spec.get("multi"), spec.get("final")} - {None}
    hps = [h for h in sk_catalog.hyperparams(cls) if h["name"] not in model_params]
    inputs = [("Table", DATA)]
    optional = []
    if spec.get("targets"):
        hps = [P("targets", "Colonnes cibles", "columns", [], port=0, required=True, group="Données"),
               P("features", "Variables explicatives (vide = toutes sauf les cibles)", "columns", [], port=0,
                 group="Données")] + hps
    if spec.get("multi"):
        inputs += [("Modèle 1", MODEL), ("Modèle 2", MODEL), ("Modèle 3", MODEL), ("Modèle 4", MODEL)]
        optional += [3, 4]
        if spec.get("final"):
            inputs.append(("Modèle final (optionnel)", MODEL))
            optional.append(5)
        how = ("Branchez de 2 à 4 modèles (sorties de nœuds d'apprentissage) : leurs réglages sont "
               "repris et ils sont réentraînés ensemble.")
    else:
        inputs.append(("Estimateur de base", MODEL))
        how = "Branchez l'estimateur de base (sortie d'un nœud d'apprentissage) : ses réglages sont repris."
        if spec.get("targets"):
            how += (" Choisissez les colonnes cibles : un modèle est appris pour chacune (ou en chaîne). "
                    "Le Prédicteur produit une colonne de prédiction par cible.")
    desc = f"{info['summary']}\n\nMéta-estimateur généré à partir de {info['module']}.{name}. {how}"
    if kind == "transformer":
        outputs = [("Table transformée", DATA), ("Transformeur", MODEL)]
        desc += (" La cible et les variables sont celles de l'estimateur de base ; les colonnes non "
                 "sélectionnées sont retirées, les autres colonnes de la table sont conservées.")
    else:
        outputs = [("Modèle", MODEL)]
    type_id = f"meta.{name}"
    how_en = ("Connect 2 to 4 models (learner outputs): their settings are reused and they are refitted together."
              if spec.get("multi") else "Connect the base estimator (output of a learner): its settings are reused.")
    if spec.get("targets"):
        how_en += " Choose the target columns: one model is fitted per target (or in a chain). The Predictor outputs one prediction column per target."
    desc_en = f"{info['summary']}\n\nMeta-estimator generated from {info['module']}.{name}. {how_en}"

    def build(ctx: Ctx, p):
        if spec.get("multi"):
            ports = connected_models(ctx, 1)
            final = None
            if spec.get("final") and len(ctx.inputs) > 5 and ctx.inputs[5] is not None:
                final = ports.pop()
            if len(ports) < 2:
                raise NodeError("Branchez au moins deux modèles.")
            target, mkind, feats = supervised_inputs([m for m, _ in ports])
            used: set[str] = set()
            fixed = {spec["multi"]: [(step_name(lbl, m, used), as_step(m, feats)) for m, lbl in ports]}
            if final is not None:
                fixed[spec["final"]] = clone(final[0].estimator)
            est, _ = build_estimator(cls, hps, p, **fixed)
            return est, target, feats
        base = ctx.model(1)
        if base.kind not in ("classifier", "regressor"):
            raise NodeError("L'estimateur de base doit être un modèle supervisé.")
        model_hps = [h for h in hps if h.get("group") == "Hyperparamètres"]
        est, _ = build_estimator(cls, model_hps, p, **{spec["single"]: clone(base.estimator)})
        if spec.get("targets"):
            df = ctx.data(0)
            targets = list(p.get("targets") or [])
            if len(targets) < 2:
                raise NodeError("Choisissez au moins deux colonnes cibles.")
            check_columns(df, targets, "Colonne cible")
            feats = list(p.get("features") or [c for c in df.columns if c not in targets])
            return est, targets, feats
        return est, base.target, list(base.features)

    def run(ctx: Ctx, p):
        df = ctx.data(0)
        est, target, feats = build(ctx, p)
        targets = target if isinstance(target, list) else [target]
        check_columns(df, feats + targets)
        y = df[targets] if len(targets) > 1 else df[target]
        if y.isna().any().any() if len(targets) > 1 else y.isna().any():
            raise NodeError("La colonne cible contient des valeurs manquantes.")
        if kind == "transformer":
            ct = ColumnTransformer([(name, est, feats)], remainder="passthrough",
                                   verbose_feature_names_out=False).set_output(transform="pandas")
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    out = ct.fit_transform(df, y)
                except Exception as e:
                    raise _fit_message(e) from e
            out.index = df.index
            inner = ct.named_transformers_[name]
            kept = [f for f, keep in zip(feats, inner.get_support()) if keep] if hasattr(inner, "get_support") else []
            model = ModelPort(ct, "transformer", name, feats, target, output_columns=[str(c) for c in out.columns])
            ctx.add_view({"type": "metrics", "items": [
                {"label": "Variables candidates", "value": len(feats)},
                {"label": "Variables retenues", "value": len(kept)}]})
            if kept:
                ctx.add_view({"type": "text", "title": "Variables retenues", "text": ", ".join(map(str, kept))})
                ranking = getattr(inner, "ranking_", None)
                if ranking is not None:
                    order = np.argsort(ranking)
                    ctx.add_view({"type": "chart", "chart": "hbar", "title": "Rang d'élimination (1 = retenue)",
                                  "labels": [str(feats[i]) for i in order][:30],
                                  "values": [int(ranking[i]) for i in order][:30]})
            ctx.add_view({"type": "model", "summary": model.summary()})
            return [out, model]
        X = df[feats]
        fit_quietly(ctx, est, X, y)
        model = ModelPort(est, kind, name, feats, target,
                          classes=list(est.classes_) if hasattr(est, "classes_") and len(targets) == 1 else None)
        _learner_view(ctx, model, X, y)
        ctx.add_view(tunable_block(est))
        return [model]

    def code(p, ins, outs):
        placeholder = {spec[k]: None for k in ("single", "multi") if spec.get(k)}
        _, kwargs = build_estimator(cls, [h for h in hps if h.get("group") == "Hyperparamètres"], p, **placeholder)
        data, *models = ins
        m = outs[-1]
        lines = []
        if spec.get("multi"):
            final = models[4] if spec.get("final") and len(models) > 4 else None
            bases = [v for v in models[:4] if v]
            items = ", ".join(f"(\"m{i}\", make_pipeline(colonnes({v}.features_), clone({v})))"
                              for i, v in enumerate(bases, 1))
            extra = f", {spec['final']}=clone({final})" if final else ""
            lines.append(f"{m} = {name}({spec['multi']}=[{items}]{extra}{', ' if kwargs else ''}{hp_code(kwargs)})")
            lines.append(f"_features = list(dict.fromkeys(f for v in [{', '.join(bases)}] for f in v.features_))")
            lines.append(f"_target = {bases[0]}.target_")
        else:
            base = models[0]
            lines.append(f"{m} = {name}({spec['single']}=clone({base}){', ' if kwargs else ''}{hp_code(kwargs)})")
            if spec.get("targets"):
                tg = list(p.get("targets") or [])
                feats = p.get("features")
                lines.append(f"_target = {py(tg)}")
                lines.append(f"_features = {py(feats)}" if feats else f"_features = [c for c in {data}.columns if c not in _target]")
            else:
                lines.append(f"_features, _target = {base}.features_, {base}.target_")
        if kind == "transformer":
            lines.append(f"{outs[1]} = ColumnTransformer([({py(name)}, {m}, _features)], remainder='passthrough', "
                         "verbose_feature_names_out=False).set_output(transform='pandas')")
            lines.append(f"{outs[0]} = {outs[1]}.fit_transform({data}, {data}[_target])")
        else:
            lines.append(f"{m}.fit({data}[_features], {data}[_target])")
            lines.append(f"{m}.features_, {m}.target_ = _features, _target")
        return "\n".join(lines)

    category = sk_catalog.KIND_CATEGORY[kind] if kind == "transformer" else CAT_COMPOSE
    REGISTRY[type_id] = NodeType(
        type_id, name, category, desc, inputs, outputs, [*hps], run, code,
        family=info["family"] if kind == "transformer" else "Méta-estimateurs",
        doc_url=info["doc_url"], has_view=True,
        color="transformer" if kind == "transformer" else "compose",
        keywords=f"{info['module']} méta ensemble {info['keywords']}",
        optional_inputs=optional, uses_labels=bool(spec.get("multi")), module=info["module"],
        kind="transformer" if kind == "transformer" else kind, description_en=desc_en,
    )
    REGISTRY[type_id].sk_import = (info["module"], name)


for _name, _info in sk_catalog.meta_estimators().items():
    _make_meta(_name, _info)


# --------------------------------------------------------------------------
# Comparateur de modèles
# --------------------------------------------------------------------------

@register(
    "tune.compare", "Comparer des modèles", CAT_TUNE,
    """
    Évalue plusieurs modèles par validation croisée sur les mêmes plis et les
    classe. Branchez de 1 à 6 sorties de nœuds d'apprentissage ou de Pipelines
    (même cible) : chaque configuration est réentraînée sur chaque pli. Le nom
    affiché est l'annotation du nœud amont, à défaut le nom de l'estimateur.
    """,
    inputs=[("Table", DATA)] + [(f"Modèle {i}", MODEL) for i in range(1, 7)],
    outputs=[("Classement", DATA), ("Scores par pli", DATA)],
    params=[
        P("scoring", "Métrique", "choice", "", choices=[""] + _scorer_names(), choice_labels={"": "(par défaut)"}),
        *cv_params(0),
    ],
    has_view=True, color="tune",
    doc_url="https://scikit-learn.org/stable/modules/cross_validation.html",
    keywords="comparer comparaison benchmark classement leaderboard modèles",
)
def compare_models(ctx: Ctx, p):
    df = ctx.data(0)
    ports = connected_models(ctx, 1)
    if not ports:
        raise NodeError("Branchez au moins un modèle.")
    target, kind, feats = supervised_inputs([m for m, _ in ports])
    targets = target if isinstance(target, list) else [target]
    check_columns(df, feats + targets)
    y = df[targets] if len(targets) > 1 else df[target]
    cv, groups, _ = make_cv(p, kind, df, len(targets) > 1)
    scoring = p.get("scoring") or None
    used: set[str] = set()
    rows, folds = [], {}
    for m, lbl in ports:
        name = lbl or m.name
        if name in used:
            name = f"{name} ({len(used) + 1})"
        used.add(name)
        try:
            r = cross_validate(clone(m.estimator), df[m.features], y, cv=cv, groups=groups, scoring=scoring,
                               n_jobs=n_jobs(len(df)))
        except Exception as e:
            raise NodeError(f"{name} : {_fit_message(e)}") from e
        s = r["test_score"]
        folds[name] = s
        rows.append({"modèle": name, "score moyen": float(s.mean()), "écart-type": float(s.std()),
                     "min": float(s.min()), "max": float(s.max()),
                     "temps d'ajustement (s)": float(r["fit_time"].mean())})
    board = pd.DataFrame(rows).sort_values("score moyen", ascending=False).reset_index(drop=True)
    board.insert(0, "rang", range(1, len(board) + 1))
    fold_df = pd.DataFrame(folds)
    fold_df.insert(0, "pli", range(1, len(fold_df) + 1))
    metric = scoring or ("accuracy" if kind == "classifier" else "R²")
    best = board.iloc[0]
    ctx.add_view({"type": "metrics", "items": [
        {"label": "Meilleur modèle", "value": best["modèle"]},
        {"label": f"Score ({metric})", "value": f"{best['score moyen']:.4f} ± {best['écart-type']:.4f}"},
        {"label": "Modèles comparés", "value": len(board)}]})
    ctx.add_view({"type": "chart", "chart": "hbar", "title": f"Score moyen ({metric}) ± écart-type",
                  "labels": board["modèle"].tolist(), "values": board["score moyen"].round(5).tolist(),
                  "errors": board["écart-type"].round(5).tolist()})
    boxes = []
    for name in board["modèle"]:
        s = np.asarray(folds[name])
        q1, med, q3 = np.percentile(s, [25, 50, 75])
        boxes.append({"label": name, "q1": float(q1), "median": float(med), "q3": float(q3),
                      "lo": float(s.min()), "hi": float(s.max()), "outliers": []})
    ctx.add_view({"type": "chart", "chart": "box", "title": "Dispersion des scores par pli", "boxes": boxes})
    ctx.add_view(table_block(board.round(5), "Classement"))
    return [board, fold_df]


def _code_compare(p, ins, outs):
    data, *models = ins
    models = [v for v in models if v]
    splitter, groups = cv_code(p, models[0], data)
    lines = [f"_cv = {splitter}",
             "_rows = []",
             f"for _name, _m in [{', '.join(f'({v!r}, {v})' for v in models)}]:",
             f"    _s = cross_validate(clone(_m), {data}[_m.features_], {data}[_m.target_], cv=_cv, groups={groups}, "
             f"scoring={py(p.get('scoring') or None)})['test_score']",
             "    _rows.append({'modèle': _name, 'score moyen': _s.mean(), 'écart-type': _s.std()})",
             f"{outs[0]} = pd.DataFrame(_rows).sort_values('score moyen', ascending=False)",
             f"print({outs[0]})"]
    return "\n".join(lines)


REGISTRY["tune.compare"].code = _code_compare
REGISTRY["tune.compare"].optional_inputs = [2, 3, 4, 5, 6]
REGISTRY["tune.compare"].uses_labels = True
