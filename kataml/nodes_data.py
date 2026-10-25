"""Données complémentaires : vectorisation de texte, caractéristiques de dates, OpenML."""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from sklearn.feature_extraction import text as sktext

from . import sk_catalog
from .sklearn_ext import TextColumnVectorizer
from .nodes import (
    CAT_IO, CAT_MANIP, DATA, MODEL, REGISTRY, Ctx, ModelPort, NodeError, NodeType, P,
    _fit_message, build_estimator, check_columns, hp_code, py, register, table_block,
)


# --------------------------------------------------------------------------
# Texte : CountVectorizer, TfidfVectorizer, HashingVectorizer
# --------------------------------------------------------------------------

# Valeurs par défaut raisonnables : la sortie est une table dense.
TEXT_DEFAULTS = {"max_features": 500, "n_features": 256}


def _make_vectorizer(cls):
    name = cls.__name__
    hps = [h for h in sk_catalog.hyperparams(cls) if h["name"] not in ("input", "dtype")]
    for h in hps:
        if h["name"] in TEXT_DEFAULTS:
            h["help"] = (f"KataML utilise {TEXT_DEFAULTS[h['name']]} par défaut pour garder une table de "
                         f"taille raisonnable. " + h["help"])
    summary, _ = sk_catalog.parse_docstring(cls.__doc__ or "")
    params = [P("column", "Colonne de texte", "column", "", port=0, required=True, group="Données")] + hps
    desc = (f"{summary}\n\nVectorise une colonne de texte ({sk_catalog.public_module(cls)}.{name}) : elle est "
            "remplacée par une colonne par terme, les autres colonnes sont conservées (valeurs manquantes = "
            "texte vide). La sortie "
            "« Transformeur » s'applique au jeu de test ou s'insère dans un Pipeline. Par défaut, le "
            "vocabulaire est limité pour garder une table dense de taille raisonnable.")
    type_id = f"text.{name}"

    def make(p):
        est, kwargs = build_estimator(cls, hps, p)
        for k, v in TEXT_DEFAULTS.items():
            if k in est.get_params() and k not in kwargs:
                est.set_params(**{k: v})
                kwargs[k] = v
        return est, kwargs

    def run(ctx: Ctx, p):
        df = ctx.data()
        col = p.get("column")
        if not col:
            raise NodeError("Choisissez la colonne de texte.")
        check_columns(df, [col])
        est, _ = make(p)
        step = TextColumnVectorizer(col, est)
        try:
            out = step.fit_transform(df)
        except Exception as e:
            raise _fit_message(e) from e
        names = [str(c) for c in out.columns]
        model = ModelPort(step, "transformer", name, [col], None, output_columns=names)
        terms = step.terms_
        ctx.add_view({"type": "metrics", "items": [
            {"label": "Documents", "value": len(df)}, {"label": "Termes", "value": len(terms)},
            {"label": "Colonnes en sortie", "value": out.shape[1]}]})
        if hasattr(step.vectorizer_, "vocabulary_"):
            df_count = np.asarray((out[terms] > 0).sum(axis=0))
            order = np.argsort(-df_count)[:25]
            ctx.add_view({"type": "chart", "chart": "hbar", "title": "Termes les plus fréquents (nombre de documents)",
                          "labels": [terms[i] for i in order], "values": [int(df_count[i]) for i in order]})
        ctx.add_view({"type": "model", "summary": model.summary()})
        return [out, model]

    def code(p, ins, outs):
        _, kwargs = make(p)
        col = p.get("column")
        return (f"{outs[1]} = TextColumnVectorizer({py(col)}, {name}({hp_code(kwargs)}))\n"
                f"{outs[0]} = {outs[1]}.fit_transform({ins[0]})")

    REGISTRY[type_id] = NodeType(
        type_id, name, "Prétraitement", desc, [("Table", DATA)],
        [("Table vectorisée", DATA), ("Transformeur", MODEL)], params, run, code,
        family="Texte", doc_url=sk_catalog.doc_url(cls), has_view=True, color="transformer",
        keywords=f"sklearn.feature_extraction.text texte mots tf-idf sac de mots nlp {name}",
        module="sklearn.feature_extraction.text", kind="transformer",
        description_en=(f"{summary}\n\nVectorizes a text column ({sk_catalog.public_module(cls)}.{name}): it is replaced "
                        "by one column per term, other columns are kept (missing values = empty text). The “Transformer” "
                        "output applies to the test set or goes into a Pipeline. By default the vocabulary is limited to "
                        "keep a dense table of reasonable size."),
    )
    REGISTRY[type_id].sk_import = ("sklearn.feature_extraction.text", name)
    REGISTRY[type_id].extra_imports = ["from kataml.sklearn_ext import TextColumnVectorizer"]


for _cls in (sktext.CountVectorizer, sktext.TfidfVectorizer, sktext.HashingVectorizer):
    _make_vectorizer(_cls)


# --------------------------------------------------------------------------
# Dates
# --------------------------------------------------------------------------

DATE_PARTS = {
    "year": "Année", "quarter": "Trimestre", "month": "Mois", "day": "Jour du mois",
    "dayofweek": "Jour de la semaine (0 = lundi)", "dayofyear": "Jour de l'année",
    "week": "Semaine ISO", "hour": "Heure", "minute": "Minute", "is_weekend": "Week-end (0/1)",
}
CYCLES = {"month": 12, "dayofweek": 7, "hour": 24, "dayofyear": 366}


@register(
    "manip.dates", "Caractéristiques de dates", CAT_MANIP,
    """
    Extrait des variables numériques d'une ou plusieurs colonnes de dates :
    année, mois, jour de la semaine, heure, week-end… L'encodage cyclique
    (sinus / cosinus) indique au modèle que décembre est proche de janvier.
    Les valeurs non reconnues deviennent manquantes.
    """,
    inputs=[("Table", DATA)], outputs=[("Table", DATA)],
    params=[
        P("columns", "Colonnes de dates", "columns", [], port=0, required=True),
        P("parts", "Éléments à extraire", "multichoice", ["year", "month", "dayofweek"],
          choices=list(DATE_PARTS), choice_labels=DATE_PARTS),
        P("cyclic", "Encodage cyclique (sin/cos)", "bool", False),
        P("drop", "Supprimer la colonne d'origine", "bool", True),
    ],
    keywords="date heure datetime temps saison mois jour semaine",
)
def dates_node(ctx: Ctx, p):
    df = ctx.data().copy()
    cols = p.get("columns") or []
    check_columns(df, cols)
    parts = p.get("parts") or ["year", "month", "dayofweek"]
    for c in cols:
        d = pd.to_datetime(df[c], errors="coerce")
        if d.notna().sum() == 0:
            raise NodeError(f"Aucune date reconnue dans « {c} ».")
        for part in parts:
            if part == "week":
                v = d.dt.isocalendar().week.astype("Float64")
            elif part == "is_weekend":
                v = (d.dt.dayofweek >= 5).astype("Int64").where(d.notna())
            else:
                v = getattr(d.dt, part)
            df[f"{c}_{part}"] = v.astype(float)
            if p.get("cyclic") and part in CYCLES:
                angle = 2 * np.pi * df[f"{c}_{part}"] / CYCLES[part]
                df[f"{c}_{part}_sin"], df[f"{c}_{part}_cos"] = np.sin(angle), np.cos(angle)
        if p.get("drop", True):
            df = df.drop(columns=c)
    return [df]


def _code_dates(p, ins, outs):
    parts = p.get("parts") or ["year", "month", "dayofweek"]
    lines = [f"{outs[0]} = {ins[0]}.copy()", f"for _c in {py(p.get('columns') or [])}:",
             f"    _d = pd.to_datetime({outs[0]}[_c], errors='coerce')"]
    for part in parts:
        expr = {"week": "_d.dt.isocalendar().week.astype(float)",
                "is_weekend": "(_d.dt.dayofweek >= 5).astype(float).where(_d.notna())"}.get(part, f"_d.dt.{part}.astype(float)")
        lines.append(f"    {outs[0]}[f'{{_c}}_{part}'] = {expr}")
        if p.get("cyclic") and part in CYCLES:
            lines.append(f"    {outs[0]}[f'{{_c}}_{part}_sin'] = np.sin(2 * np.pi * {outs[0]}[f'{{_c}}_{part}'] / {CYCLES[part]})")
            lines.append(f"    {outs[0]}[f'{{_c}}_{part}_cos'] = np.cos(2 * np.pi * {outs[0]}[f'{{_c}}_{part}'] / {CYCLES[part]})")
    if p.get("drop", True):
        lines.append(f"    {outs[0]} = {outs[0]}.drop(columns=_c)")
    return "\n".join(lines)


REGISTRY["manip.dates"].code = _code_dates


# --------------------------------------------------------------------------
# OpenML
# --------------------------------------------------------------------------

@register(
    "io.openml", "Jeu de données OpenML", CAT_IO,
    """
    Télécharge un jeu de données depuis openml.org (sklearn.datasets.fetch_openml),
    par nom ou par identifiant numérique. Exemples : titanic, adult, credit-g,
    diabetes, blood-transfusion-service-center, wine-quality-red. Les fichiers
    sont mis en cache dans workspace/openml : une connexion n'est nécessaire
    qu'au premier chargement.
    """,
    outputs=[("Table", DATA)],
    params=[
        P("name", "Nom ou identifiant", "str", "titanic", required=True),
        P("version", "Version", "str", "1", "Numéro de version, ou « active » pour la dernière."),
    ],
    doc_url="https://scikit-learn.org/stable/modules/generated/sklearn.datasets.fetch_openml.html",
    keywords="openml télécharger internet jeu de données dataset titanic adult",
)
def openml_node(ctx: Ctx, p):
    from sklearn.datasets import fetch_openml
    ref = str(p.get("name") or "").strip()
    if not ref:
        raise NodeError("Indiquez un nom ou un identifiant OpenML.")
    version = str(p.get("version") or "active").strip()
    kw = {"data_id": int(ref)} if ref.isdigit() else {"name": ref, "version": int(version) if version.isdigit() else version}
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            bunch = fetch_openml(as_frame=True, parser="auto", data_home=str(ctx.workspace / "openml"), **kw)
    except Exception as e:
        raise NodeError(f"Chargement OpenML impossible ({type(e).__name__} : {e}). "
                        "Vérifiez le nom et la connexion internet.") from e
    df = bunch.frame if bunch.frame is not None else pd.concat([bunch.data, bunch.target], axis=1)
    for c in df.columns:          # catégories pandas → texte, plus simple à manipuler
        if isinstance(df[c].dtype, pd.CategoricalDtype):
            df[c] = df[c].astype(object).where(df[c].notna(), None)
    ctx.add_view({"type": "text", "title": "Description",
                  "text": f"{bunch.details.get('name', ref)} (version {bunch.details.get('version', '?')}) — "
                          f"cible : {', '.join(bunch.target_names) if getattr(bunch, 'target_names', None) else '?'}\n\n"
                          + (bunch.DESCR or "")[:4000]})
    return [df]


REGISTRY["io.openml"].has_view = True
REGISTRY["io.openml"].code = lambda p, ins, outs: (
    f"{outs[0]} = datasets.fetch_openml("
    + (f"data_id={int(p['name'])}" if str(p.get("name", "")).strip().isdigit()
       else f"name={py(str(p.get('name')).strip())}, version={py(int(p['version']) if str(p.get('version', '')).isdigit() else (p.get('version') or 'active'))}")
    + ", as_frame=True, parser='auto').frame")
