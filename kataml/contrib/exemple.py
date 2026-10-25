"""Extension fournie (exemple) : deux blocs de préparation de données.

Fournie avec KataML : à activer dans « Mes blocs » (case à cocher). Le dossier
extensions/kataml-exemple/ du dépôt reprend ce code comme modèle de paquet
externe (point d'entrée kataml.extensions).
"""

from kataml.extension import DATA, NodeError, P, check_columns, py, register

KATAML_EXTENSION = {"name": "exemple", "version": "1.0.0",
                      "description": "Écrêtage des valeurs extrêmes, encodage par fréquence."}


@register(
    "ext.exemple.winsorize", "Écrêtage (winsorisation)", "Manipulation",
    """
    Ramène les valeurs extrêmes des colonnes choisies aux quantiles indiqués
    (par exemple 1 % et 99 %) : les valeurs aberrantes pèsent moins sur les
    modèles sensibles aux extrêmes (régression linéaire, k-moyennes…).
    """,
    inputs=[("Table", DATA)], outputs=[("Table", DATA)],
    params=[
        P("columns", "Colonnes (vide = toutes les numériques)", "columns", [], port=0),
        P("low", "Quantile bas", "float", 0.01),
        P("high", "Quantile haut", "float", 0.99),
    ],
    has_view=True, keywords="winsorisation écrêtage outliers extrêmes quantiles",
    code=lambda p, ins, outs: (
        f"{outs[0]} = {ins[0]}.copy()\n"
        f"_cols = {py(p.get('columns') or [])} or list({outs[0]}.select_dtypes('number').columns)\n"
        f"{outs[0]}[_cols] = {outs[0]}[_cols].clip({outs[0]}[_cols].quantile({p.get('low', 0.01)}), "
        f"{outs[0]}[_cols].quantile({p.get('high', 0.99)}), axis=1)"),
)
def winsorize(ctx, p):
    df = ctx.data().copy()
    cols = p.get("columns") or list(df.select_dtypes("number").columns)
    check_columns(df, cols)
    lo, hi = float(p.get("low", 0.01)), float(p.get("high", 0.99))
    if not 0 <= lo < hi <= 1:
        raise NodeError("Les quantiles doivent vérifier 0 ≤ bas < haut ≤ 1.")
    q_lo, q_hi = df[cols].quantile(lo), df[cols].quantile(hi)
    changed = ((df[cols] < q_lo) | (df[cols] > q_hi)).sum()
    df[cols] = df[cols].clip(q_lo, q_hi, axis=1)
    ctx.add_view({"type": "chart", "chart": "hbar", "title": "Valeurs écrêtées par colonne",
                  "labels": [str(c) for c in changed.index], "values": [int(v) for v in changed.values]})
    return [df]


@register(
    "ext.exemple.frequency", "Encodage par fréquence", "Prétraitement",
    """
    Remplace chaque modalité d'une variable catégorielle par sa fréquence
    relative dans la table : une alternative compacte au one-hot pour les
    variables à nombreuses modalités.
    """,
    inputs=[("Table", DATA)], outputs=[("Table", DATA)],
    params=[P("columns", "Colonnes catégorielles", "columns", [], port=0, required=True)],
    keywords="fréquence encodage catégoriel count encoding",
)
def frequency(ctx, p):
    df = ctx.data().copy()
    cols = p.get("columns") or []
    check_columns(df, cols)
    for c in cols:
        df[f"{c}_freq"] = df[c].map(df[c].value_counts(normalize=True)).astype(float)
    return [df.drop(columns=cols)]
