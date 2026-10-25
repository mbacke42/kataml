"""Blocs de rapport : texte libre (Markdown) inséré dans les rapports générés."""

from __future__ import annotations

from .nodes import REGISTRY, Ctx, P, register

CAT_REPORT = "Rapport"


@register(
    "report.text", "Texte du rapport", CAT_REPORT,
    """
    Bloc de texte (Markdown) pour le rapport : introduction, interprétation
    d'un résultat, conclusion… Placez-le sur le canevas près des nœuds qu'il
    commente : le rapport suit l'ordre du workflow (modifiable dans la boîte
    « Rapport »). Syntaxe : # titre, **gras**, *italique*, `code`, - liste,
    > citation, [lien](https://…).
    """,
    params=[
        P("title", "Titre de la section", "str", "", "Facultatif."),
        P("text", "Texte (Markdown)", "code", "## Objectif\n\nDécrivez ici la question étudiée.\n", rows=12),
    ],
    has_view=True, color="report", keywords="rapport texte markdown commentaire conclusion introduction",
)
def report_text(ctx: Ctx, p):
    ctx.add_view({"type": "markdown", "title": p.get("title") or None, "text": p.get("text") or ""})
    return []


REGISTRY["report.text"].code = lambda p, ins, outs: "\n".join(
    "# " + line for line in ((p.get("title") or "") + "\n" + (p.get("text") or "")).strip().splitlines())
