"""Extensions « maison » fournies avec KataML.

Ces modules voyagent dans le paquet (donc aussi dans les versions portables) mais
ne sont pas chargés tant qu'ils ne sont pas activés dans « Mes blocs » (case à
cocher). Désactivés par défaut. L'activation est persistée dans
``<espace de travail>/extensions.json`` et gérée par ``kataml.extension``.

Chaque module est une extension ordinaire (il importe ``kataml.extension`` et
déclare ses nœuds avec ``register``) : la seule différence est qu'il est fourni
avec l'application au lieu d'être installé en paquet ou déposé en fichier.
"""

from __future__ import annotations

#: Extensions fournies, dans l'ordre d'affichage. Chargées à la demande par leur module.
BUNDLED = [
    {
        "key": "eda", "module": "kataml.contrib.eda", "name": "Analyse exploratoire",
        "description": "Vue d'ensemble, valeurs manquantes, fréquences, relation avec la cible, "
                       "distributions, valeurs extrêmes.",
    },
    {
        "key": "exemple", "module": "kataml.contrib.exemple", "name": "Exemple (préparation)",
        "description": "Écrêtage des valeurs extrêmes et encodage par fréquence.",
    },
]
