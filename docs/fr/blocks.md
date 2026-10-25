# Écrire ses propres blocs

Un bloc (nœud) KataML est une fonction Python décorée par `register`. Elle reçoit
les entrées du nœud et ses paramètres, et renvoie la liste de ses sorties. Tout le
reste vient automatiquement : place dans le dépôt, formulaire de configuration,
feu d'état, cache, affichage des tables, rapports.

## D'où viennent les extensions

Au démarrage, KataML réunit les blocs de trois sources dans le même dépôt :

| Source | Pour qui | Activation |
|---|---|---|
| **Fichiers** `workspace/extensions/*.py` | prototypage, usage personnel | chargés automatiquement ; créés et édités dans **Mes blocs** |
| **Extensions fournies** (livrées avec l'application) | blocs « maison » prêts à l'emploi | **case à cocher** dans **Mes blocs** (désactivées par défaut) |
| **Paquets Python** (point d'entrée `kataml.extensions`) | diffusion à d'autres utilisateurs | installés avec `pip`/`uv`, chargés automatiquement |

Les trois cohabitent. `KATAML_NO_EXTENSIONS=1` les désactive toutes (diagnostic). Un bloc
s'exécute avec les droits de l'utilisateur : n'activez que des extensions de confiance.

Pour écrire une extension **avec un assistant IA**, une *skill* dédiée est fournie dans le
dépôt (`.claude/skills/kataml-extension/`) : elle donne à l'agent toute l'API et les
conventions nécessaires.

## Créer un bloc

1. **Depuis l'interface** : bouton **Mes blocs** (en haut du dépôt), puis
   **Nouveau bloc**. Un fichier commenté est créé dans `workspace/extensions/`
   et s'ouvre dans l'éditeur intégré ; **Enregistrer et recharger** (Ctrl+S) le
   met à jour immédiatement. Les erreurs (syntaxe, import…) s'affichent sous l'éditeur.
2. **À partir d'un Script Python** : clic droit sur un nœud « Script Python »,
   puis **Convertir en bloc réutilisable**. Son code devient un bloc du dépôt.
3. **Sous forme de paquet Python**, pour diffuser des blocs à d'autres
   utilisateurs : voir plus bas.

Les fichiers de `workspace/extensions/` sont aussi chargés par les versions
portables (AppImage, zip Windows) et par `kataml run`. Le
[tutoriel 10](tutorials/10-report-blocks.md) déroule un exemple complet.

## Anatomie d'un bloc

```python
from kataml.extension import DATA, MODEL, NodeError, P, check_columns, register

KATAML_EXTENSION = {"name": "mes_blocs", "version": "1.0", "description": "…"}

@register(
    "ext.mes_blocs.log",            # identifiant unique (préfixe ext. conseillé)
    "Logarithme",                   # nom affiché
    "Manipulation",                 # catégorie du dépôt (existante ou nouvelle)
    "Ajoute log(1 + x) pour les colonnes choisies.",
    inputs=[("Table", DATA)],       # ports d'entrée : DATA (table) ou MODEL (modèle)
    outputs=[("Table", DATA)],
    params=[
        P("columns", "Colonnes", "columns", [], port=0, required=True),
        P("suffix", "Suffixe", "str", "_log"),
    ],
)
def log1p(ctx, p):
    import numpy as np
    df = ctx.data(0).copy()          # entrée n° 0 sous forme de DataFrame
    check_columns(df, p["columns"])
    for c in p["columns"]:
        df[c + p["suffix"]] = np.log1p(df[c])
    return [df]                      # une valeur par port de sortie
```

### Paramètres (`P(nom, libellé, type, défaut, aide, …)`)

| Type | Contrôle | Options utiles |
|---|---|---|
| `str`, `int`, `float` | champ de saisie | `allow_empty=True` |
| `bool` | interrupteur | |
| `choice` | liste déroulante | `choices=[…]`, `choice_labels={…}` |
| `multichoice` | cases à cocher | `choices=[…]` |
| `column` / `columns` | colonne(s) de la table en entrée | `port=0` (indice de l'entrée) |
| `code` | zone de texte multiligne | `rows=8` |
| `literal` | valeur Python (`[1, 2]`, `None`, `'texte'`) | |

`required=True` met le nœud au rouge tant que le paramètre est vide.

### Contexte (`ctx`)

- `ctx.data(i)` : table de l'entrée `i` ; `ctx.model(i)` : modèle de l'entrée `i`
  (`m.estimator`, `m.features`, `m.target`, `m.kind`) ;
- `ctx.add_view(bloc, …)` : ajoute une vue (avec `has_view=True` dans `register`).
  Blocs disponibles : `{"type": "metrics", "items": [{"label", "value"}]}`,
  `{"type": "chart", "chart": "bar" | "hbar" | "line" | "scatter" | "histogram" | …}`,
  `table_block(df, "titre")`, `{"type": "text", "text": "…"}`,
  `{"type": "markdown", "text": "…"}` ;
- `ctx.messages.append("…")` : avertissement affiché dans l'inspecteur ;
- `raise NodeError("…")` : erreur claire affichée sur le nœud.

### Export Python

`register(..., code=lambda p, ins, outs: "…")` fournit le code équivalent pour
l'export en script ou en notebook (`ins` / `outs` : noms des variables).

## Extensions fournies

Deux extensions « maison » sont **livrées avec KataML**, donc présentes aussi dans les
versions portables, sans rien installer : **Analyse exploratoire** (six blocs : vue
d'ensemble, valeurs manquantes, fréquences, relation avec la cible, distributions, valeurs
extrêmes) et **Exemple (préparation)** (écrêtage, encodage par fréquence). Elles sont
**désactivées par défaut** : on les active d'une case à cocher dans **Mes blocs**, section
« Extensions fournies ». Le choix est mémorisé dans `workspace/extensions.json`.

## Distribuer des blocs dans un paquet

Le dossier `extensions/kataml-exemple/` du dépôt est un modèle minimal (deux blocs) pour
publier vos propres blocs en paquet. Il suffit de déclarer un point d'entrée dans le
`pyproject.toml` :

```toml
[project.entry-points."kataml.extensions"]
mes_blocs = "mon_paquet"          # module importé au démarrage de KataML
```

Installation à côté de KataML :

```bash
uv tool install git+https://gitlab.com/fredbl/kataml.git --with ./mon-paquet
```

ou, dans l'environnement de KataML, `pip install ./mon-paquet`. Les extensions
installées sont listées dans **Mes blocs**. `KATAML_NO_EXTENSIONS=1` les désactive
toutes (diagnostic).

## Bonnes pratiques

- Préfixez les identifiants (`ext.mon_paquet.…`) : un identifiant ne peut pas
  remplacer un nœud intégré, et il est enregistré dans les workflows.
- Ne modifiez pas les tables reçues : travaillez sur une copie (`.copy()`).
- Restez déterministes (graines aléatoires en paramètre) : le cache suppose qu'un
  même nœud, avec les mêmes entrées et paramètres, produit le même résultat.
  Modifier le code d'un bloc invalide automatiquement ses résultats en cache.
- Un bloc s'exécute avec les droits de l'utilisateur : n'installez que des
  extensions de confiance.
