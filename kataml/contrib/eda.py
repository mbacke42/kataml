"""Extension fournie : analyse exploratoire des données.

Six blocs pour la phase de découverte, avant la modélisation : vue d'ensemble,
valeurs manquantes, fréquences catégorielles, relation avec la cible,
distributions et valeurs extrêmes. Tout repose sur pandas (et numpy) ; aucune
dépendance supplémentaire.

Fournie avec KataML : à activer dans « Mes blocs » (case à cocher). C'est aussi
un exemple d'extension ; voir docs/blocks.md pour en écrire une.
"""

import numpy as np
import pandas as pd

from kataml.extension import DATA, NodeError, P, check_columns, ensure_numeric, py, register, table_block

KATAML_EXTENSION = {
    "name": "eda", "version": "1.0.0",
    "description": "Analyse exploratoire : vue d'ensemble, manquants, fréquences, cible, distributions, extrêmes.",
}

CAT = "Analyse exploratoire"


# --------------------------------------------------------------------------
# Utilitaires (autonomes : rien de privé à KataML)
# --------------------------------------------------------------------------

def _kind(s: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(s):
        return "booléen"
    if pd.api.types.is_numeric_dtype(s):
        return "numérique"
    if pd.api.types.is_datetime64_any_dtype(s):
        return "date"
    if isinstance(s.dtype, pd.CategoricalDtype):
        return "catégoriel"
    return "texte"


def _cramers_v(ct) -> float:
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


def _corr_ratio(cats, values) -> float:
    """Rapport de corrélation η ∈ [0,1] entre une variable catégorielle et une numérique."""
    cats, values = np.asarray(cats), np.asarray(values, dtype=float)
    grand = values.mean()
    ss_tot = ((values - grand) ** 2).sum()
    if ss_tot == 0 or len(values) < 2:
        return 0.0 if ss_tot == 0 else float("nan")
    ss_between = sum(len(g) * (g.mean() - grand) ** 2
                     for g in (values[cats == c] for c in pd.unique(cats)) if len(g))
    return float(np.sqrt(ss_between / ss_tot))


# --------------------------------------------------------------------------
# Blocs
# --------------------------------------------------------------------------

@register(
    "ext.eda.overview", "Vue d'ensemble", CAT,
    """
    Profil de la table : par colonne, type, valeurs manquantes, cardinalité,
    colonnes constantes et exemples de valeurs. Donne aussi le nombre de lignes,
    de colonnes, de doublons et la part de cellules manquantes.
    """,
    inputs=[("Table", DATA)], outputs=[("Profil", DATA)],
    has_view=True, keywords="profil overview résumé découverte exploration describe",
    code=lambda p, ins, outs: (
        f"{outs[0]} = pd.DataFrame({{'colonne': [str(c) for c in {ins[0]}.columns],\n"
        f"    'type': [str({ins[0]}[c].dtype) for c in {ins[0]}.columns],\n"
        f"    'manquants': {ins[0]}.isna().sum().values,\n"
        f"    'uniques': [{ins[0]}[c].nunique(dropna=True) for c in {ins[0]}.columns]}})\nprint({outs[0]})"),
)
def overview(ctx, p):
    df = ctx.data()
    n = len(df)
    rows = []
    for c in df.columns:
        s = df[c]
        miss, uniq = int(s.isna().sum()), int(s.nunique(dropna=True))
        rows.append({
            "colonne": str(c), "type": _kind(s), "non_nuls": int(s.notna().sum()), "manquants": miss,
            "% manquants": round(100 * miss / n, 1) if n else 0.0, "uniques": uniq,
            "constante": "oui" if uniq <= 1 else "non",
            "exemples": ", ".join(str(x) for x in s.dropna().unique()[:3])[:60],
        })
    prof = pd.DataFrame(rows)
    miss_pct = round(100 * int(df.isna().sum().sum()) / df.size, 1) if df.size else 0.0
    ctx.add_view({"type": "metrics", "items": [
        {"label": "Lignes", "value": n}, {"label": "Colonnes", "value": df.shape[1]},
        {"label": "Cellules manquantes", "value": f"{miss_pct} %"},
        {"label": "Doublons", "value": int(df.duplicated().sum())},
    ]})
    ctx.add_view(table_block(prof, "Profil par colonne"))
    return [prof]


@register(
    "ext.eda.missing", "Valeurs manquantes", CAT,
    """
    Nombre et proportion de valeurs manquantes par colonne, et motifs de
    co-occurrence des manquants (corrélation des indicateurs d'absence : deux
    colonnes souvent manquantes ensemble ont une valeur proche de 1).
    """,
    inputs=[("Table", DATA)], outputs=[("Manquants par colonne", DATA)],
    has_view=True, keywords="manquants na nan missing nullité exploration",
    code=lambda p, ins, outs: (
        f"{outs[0]} = ({ins[0]}.isna().sum().rename('manquants').rename_axis('colonne').reset_index()\n"
        f"    .assign(**{{'% manquants': lambda d: (100 * d['manquants'] / len({ins[0]})).round(1)}})\n"
        f"    .sort_values('manquants', ascending=False).reset_index(drop=True))\nprint({outs[0]})"),
)
def missing(ctx, p):
    df = ctx.data()
    n = len(df)
    miss = df.isna().sum()
    out = (pd.DataFrame({"colonne": [str(c) for c in miss.index], "manquants": miss.values.astype(int)})
           .assign(**{"% manquants": lambda d: (100 * d["manquants"] / n).round(1) if n else 0.0})
           .sort_values("manquants", ascending=False).reset_index(drop=True))
    ctx.add_view({"type": "metrics", "items": [
        {"label": "Colonnes avec manquants", "value": int((miss > 0).sum())},
        {"label": "Lignes complètes", "value": int(df.notna().all(axis=1).sum())},
        {"label": "Cellules manquantes", "value": f"{round(100 * int(miss.sum()) / df.size, 1) if df.size else 0.0} %"},
    ]})
    shown = out[out["manquants"] > 0]
    if len(shown):
        ctx.add_view({"type": "chart", "chart": "hbar", "title": "Valeurs manquantes par colonne (%)",
                      "labels": shown["colonne"].tolist(), "values": shown["% manquants"].tolist()})
    cols = [c for c in df.columns if df[c].isna().any()]
    if len(cols) >= 2:
        corr = df[cols].isna().astype(int).corr().fillna(0.0).round(2)
        ctx.add_view({"type": "chart", "chart": "heatmap", "title": "Co-occurrence des manquants",
                      "labels": [str(c) for c in corr.columns], "ylabels": [str(c) for c in corr.index],
                      "matrix": corr.to_numpy().tolist(), "annot": True})
    return [out]


@register(
    "ext.eda.frequencies", "Fréquences catégorielles", CAT,
    """
    Table et graphique des effectifs des modalités d'une colonne catégorielle
    (value_counts). Si aucune colonne n'est choisie, la première colonne non
    numérique est utilisée.
    """,
    inputs=[("Table", DATA)], outputs=[("Effectifs", DATA)],
    params=[
        P("column", "Colonne", "column", "", port=0, allow_empty=True),
        P("top", "Modalités affichées", "int", 20),
    ],
    has_view=True, keywords="fréquences value_counts modalités catégoriel effectifs barres",
    code=lambda p, ins, outs: (
        f"_col = {py(p.get('column'))} or next((c for c in {ins[0]}.columns "
        f"if not pd.api.types.is_numeric_dtype({ins[0]}[c])), {ins[0]}.columns[0])\n"
        f"{outs[0]} = ({ins[0]}[_col].value_counts(dropna=False).rename('effectif')\n"
        f"    .rename_axis('modalité').reset_index())\nprint({outs[0]}.head({int(p.get('top', 20) or 20)}))"),
)
def frequencies(ctx, p):
    df = ctx.data()
    if not len(df.columns):
        raise NodeError("La table ne contient aucune colonne.")
    col = p.get("column") or next((c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])), df.columns[0])
    check_columns(df, [col])
    top = max(1, int(p.get("top", 20) or 20))
    vc = df[col].value_counts(dropna=False)
    total = int(vc.sum()) or 1
    full = pd.DataFrame({"modalité": [str(i) for i in vc.index], "effectif": vc.values.astype(int),
                         "fréquence (%)": (100 * vc.values / total).round(1)})
    ctx.add_view({"type": "metrics", "items": [
        {"label": "Modalités", "value": int(df[col].nunique(dropna=True))},
        {"label": "Manquants", "value": int(df[col].isna().sum())},
    ]})
    head = full.head(top)
    ctx.add_view({"type": "chart", "chart": "hbar", "title": f"Effectifs — {col} (jusqu'à {top})",
                  "labels": head["modalité"].tolist(), "values": head["effectif"].tolist()})
    return [full]


@register(
    "ext.eda.target", "Relation avec la cible", CAT,
    """
    Classe les variables par force d'association à une colonne cible, dans
    [0,1] : V de Cramér (catégorielle–catégorielle), rapport de corrélation η
    (catégorielle–numérique) ou |corrélation de Pearson| (numérique–numérique).
    Repère les variables les plus liées à la cible avant de modéliser.
    """,
    inputs=[("Table", DATA)], outputs=[("Associations", DATA)],
    params=[
        P("target", "Colonne cible", "column", "", port=0, required=True),
        P("features", "Variables (vide = toutes les autres)", "columns", [], port=0),
    ],
    has_view=True, keywords="cible target association cramér corrélation sélection découverte",
)
def target(ctx, p):
    df = ctx.data()
    tgt = p.get("target")
    if not tgt:
        raise NodeError("Choisissez la colonne cible.")
    check_columns(df, [tgt])
    feats = [c for c in (p.get("features") or df.columns) if c != tgt]
    check_columns(df, feats)
    t_num = pd.api.types.is_numeric_dtype(df[tgt]) and df[tgt].nunique(dropna=True) > 10
    rows = []
    for c in feats:
        d = df[[c, tgt]].dropna()
        if len(d) < 2:
            continue
        f_num = pd.api.types.is_numeric_dtype(d[c])
        if t_num and f_num:
            score = abs(float(np.corrcoef(d[c].to_numpy(float), d[tgt].to_numpy(float))[0, 1]))
            mesure = "|corrélation|"
        elif t_num and not f_num:
            score, mesure = _corr_ratio(d[c].to_numpy(), d[tgt].to_numpy(float)), "rapport η"
        elif (not t_num) and f_num:
            score, mesure = _corr_ratio(d[tgt].to_numpy(), d[c].to_numpy(float)), "rapport η"
        else:
            score, mesure = _cramers_v(pd.crosstab(d[c], d[tgt]).to_numpy()), "V de Cramér"
        if score == score:  # écarte les NaN
            rows.append({"variable": str(c), "mesure": mesure, "association": round(float(score), 4)})
    if not rows:
        raise NodeError("Aucune association calculable (données insuffisantes).")
    out = pd.DataFrame(rows).sort_values("association", ascending=False).reset_index(drop=True)
    ctx.add_view({"type": "metrics", "items": [   # le type est dans le libellé : seuls les libellés sont traduits
        {"label": "Cible numérique" if t_num else "Cible catégorielle", "value": str(tgt)},
        {"label": "Variables", "value": len(out)},
    ]})
    ctx.add_view({"type": "chart", "chart": "hbar", "title": "Association à la cible (0–1)",
                  "labels": out["variable"].tolist(), "values": out["association"].tolist()})
    ctx.add_view(table_block(out, "Variables classées"))
    return [out]


@register(
    "ext.eda.distributions", "Distributions", CAT,
    """
    Histogramme de chaque variable numérique (jusqu'à douze) et tableau des
    statistiques de forme (moyenne, écart-type, asymétrie, aplatissement) pour
    repérer dissymétries et queues de distribution.
    """,
    inputs=[("Table", DATA)], outputs=[("Statistiques de forme", DATA)],
    params=[P("columns", "Variables (vide = toutes les numériques)", "columns", [], port=0)],
    has_view=True, keywords="distribution histogramme asymétrie skew kurtosis forme",
    code=lambda p, ins, outs: (
        f"_cols = {py(p.get('columns') or [])} or list({ins[0]}.select_dtypes('number').columns)\n"
        f"{outs[0]} = pd.DataFrame({{'variable': _cols,\n"
        f"    'moyenne': [{ins[0]}[c].mean() for c in _cols], 'écart-type': [{ins[0]}[c].std() for c in _cols],\n"
        f"    'asymétrie': [{ins[0]}[c].skew() for c in _cols],\n"
        f"    'aplatissement': [{ins[0]}[c].kurt() for c in _cols]}})\nprint({outs[0]})"),
)
def distributions(ctx, p):
    df = ctx.data()
    cols = p.get("columns") or list(df.select_dtypes("number").columns)
    if not cols:
        raise NodeError("Aucune variable numérique à représenter.")
    check_columns(df, cols)
    ensure_numeric(df, cols)
    rows = []
    for c in cols:
        s = df[c].dropna()
        rows.append({"variable": str(c), "moyenne": float(s.mean()) if len(s) else float("nan"),
                     "écart-type": float(s.std()) if len(s) > 1 else float("nan"),
                     "asymétrie": float(s.skew()) if len(s) > 2 else float("nan"),
                     "aplatissement": float(s.kurt()) if len(s) > 3 else float("nan")})
    stats = pd.DataFrame(rows)
    for c in cols[:12]:
        s = df[c].dropna().to_numpy(float)
        if len(s) == 0:
            continue
        counts, edges = np.histogram(s, bins=30)
        ctx.add_view({"type": "chart", "chart": "histogram", "title": f"Distribution — {c}",
                      "edges": edges.tolist(), "series": [{"name": str(c), "counts": counts.tolist()}],
                      "xlabel": str(c), "ylabel": "Effectif"})
    ctx.add_view(table_block(stats.round(4), "Statistiques de forme"))
    return [stats]


@register(
    "ext.eda.outliers", "Valeurs extrêmes (IQR)", CAT,
    """
    Compte, par variable numérique, les valeurs hors de l'intervalle
    [Q1 − k·IQR, Q3 + k·IQR] (règle de Tukey, k = 1,5 par défaut) : un premier
    repérage des valeurs atypiques.
    """,
    inputs=[("Table", DATA)], outputs=[("Valeurs extrêmes", DATA)],
    params=[
        P("columns", "Variables (vide = toutes les numériques)", "columns", [], port=0),
        P("factor", "Facteur IQR (k)", "float", 1.5),
    ],
    has_view=True, keywords="outliers extrêmes aberrantes iqr tukey quartiles",
    code=lambda p, ins, outs: (
        f"_cols = {py(p.get('columns') or [])} or list({ins[0]}.select_dtypes('number').columns)\n"
        f"_k = {float(p.get('factor', 1.5) or 1.5)}\n"
        f"_q1, _q3 = {ins[0]}[_cols].quantile(0.25), {ins[0]}[_cols].quantile(0.75)\n_iqr = _q3 - _q1\n"
        f"{outs[0]} = ((({ins[0]}[_cols] < _q1 - _k * _iqr) | ({ins[0]}[_cols] > _q3 + _k * _iqr)).sum()\n"
        f"    .rename('nb_extrêmes').rename_axis('variable').reset_index())\nprint({outs[0]})"),
)
def outliers(ctx, p):
    df = ctx.data()
    cols = p.get("columns") or list(df.select_dtypes("number").columns)
    if not cols:
        raise NodeError("Aucune variable numérique à analyser.")
    check_columns(df, cols)
    ensure_numeric(df, cols)
    k = float(p.get("factor", 1.5) or 1.5)
    q1, q3 = df[cols].quantile(0.25), df[cols].quantile(0.75)
    iqr = q3 - q1
    low, high = q1 - k * iqr, q3 + k * iqr
    counts = ((df[cols] < low) | (df[cols] > high)).sum()
    n = len(df)
    out = (pd.DataFrame({
        "variable": [str(c) for c in cols], "bas": [round(float(low[c]), 4) for c in cols],
        "haut": [round(float(high[c]), 4) for c in cols], "nb_extrêmes": [int(counts[c]) for c in cols],
        "% extrêmes": [round(100 * int(counts[c]) / n, 1) if n else 0.0 for c in cols],
    }).sort_values("nb_extrêmes", ascending=False).reset_index(drop=True))
    ctx.add_view({"type": "metrics", "items": [
        {"label": "Variables", "value": len(cols)}, {"label": "Total extrêmes", "value": int(counts.sum())},
    ]})
    ctx.add_view({"type": "chart", "chart": "hbar", "title": "Valeurs extrêmes par variable",
                  "labels": out["variable"].tolist(), "values": out["nb_extrêmes"].tolist()})
    ctx.add_view(table_block(out, "Bornes et comptage"))
    return [out]
