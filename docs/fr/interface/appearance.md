# Apparence et thèmes

KataML se personnalise à deux niveaux : chaque utilisateur choisit ses préférences dans
l'interface, et un fichier `theme.css` peut imposer une charte à tous (salle de TP,
établissement, entreprise).

## La boîte « Apparence »

Le bouton palette, en haut à droite, ouvre la boîte **Apparence**. Les changements
s'appliquent immédiatement et sont mémorisés par le navigateur.

![Boîte Apparence](../../assets/screenshots/fr/dialog-theme.png){ .shot }

| Réglage | Choix |
|---|---|
| **Mode** | **Automatique** (suit le réglage clair / sombre du système), **Clair**, **Sombre** |
| **Couleur principale** | **Par défaut** (marquée « A »), sept teintes (sarcelle, bleu, vert, indigo, orange, framboise, ardoise) ou une couleur **personnalisée** |
| **Fond du canevas** | **Points**, **Grille** ou **Uni** |

La couleur principale colore les boutons principaux, la sélection, les liens et les
onglets actifs. Les teintes proposées existent en deux versions, une pour chaque mode ; une couleur personnalisée trop sombre est éclaircie automatiquement en mode
sombre. La couleur du texte des boutons (blanc ou noir) est choisie pour garder un bon
contraste. Les couleurs des **familles de nœuds** et des séries de graphiques ne changent
pas : elles portent du sens.

Le bouton lune / soleil, à côté, bascule directement entre clair et sombre.
**Réinitialiser** revient aux réglages d'origine.

![Exemple : bleu, mode sombre, grille](../../assets/screenshots/fr/theme-custom.png){ .shot }

Les **rapports** reprennent la couleur principale choisie (ils restent en mode clair, pour
l'impression).

## Le fichier `theme.css`

Pour aller plus loin, placez un fichier `theme.css` à la racine de l'[espace de
travail](../concepts/workspace.md). Il est chargé après la feuille de style de KataML et
peut redéfinir toutes ses **variables CSS**. Il s'applique à l'interface et aux rapports
générés, y compris en [ligne de commande](../cli.md). Rechargez la page après l'avoir
modifié.

```css
/* workspace/theme.css : charte d'un établissement */
:root {
  --accent: #b91c1c;                 /* couleur principale (mode clair) */
  --font: "Atkinson Hyperlegible", system-ui, sans-serif;
  --r: 4px; --r-sm: 3px; --r-lg: 6px; /* angles moins arrondis */
}
:root[data-theme="dark"] {
  --accent: #f87171;                 /* couleur principale (mode sombre) */
}
```

Dans la boîte Apparence, la couleur **Par défaut** devient alors celle de `theme.css` ;
un utilisateur peut toujours choisir une autre teinte pour lui-même.

### Variables disponibles

| Variables | Rôle |
|---|---|
| `--accent` | couleur principale ; les teintes dérivées (`--accent-2`, `--accent-soft`, `--accent-ring`) en sont calculées |
| `--on-accent` | texte posé sur la couleur principale |
| `--bg`, `--panel`, `--panel-2`, `--canvas`, `--canvas-dot` | fonds : page, panneaux, canevas, points ou lignes de la grille |
| `--text`, `--text-2`, `--muted`, `--line`, `--line-strong` | textes et bordures |
| `--ok`, `--warn`, `--err`, `--run` | états : exécuté, avertissement, erreur, en cours |
| `--c-io`, `--c-manip`, `--c-view`, `--c-learner`, `--c-transformer`, `--c-score`, `--c-tune`… | couleurs des familles de nœuds |
| `--s1` … `--s8` | séries des graphiques |
| `--font`, `--mono` | polices de l'interface et du code |
| `--r-sm`, `--r`, `--r-lg` | rayons des angles |

La liste complète est en tête de `kataml/static/css/app.css`. Les variables du mode sombre
se redéfinissent sous `:root[data-theme="dark"]`.

!!! tip "Polices"
    KataML fonctionne hors ligne et n'inclut pas de polices web : indiquez dans `--font`
    une police installée sur les postes, suivie d'une police de repli (`system-ui`).
