# Composants (groupes de nœuds)

Un **composant** regroupe plusieurs nœuds en une unité : le canevas reste lisible, et une
chaîne de traitements utile se réutilise d'un workflow à l'autre.

## Grouper

Sélectionnez au moins deux nœuds, puis ++ctrl+g++ (ou clic droit › **Grouper en
composant**) et donnez un nom. Le composant apparaît **réduit** : un seul nœud, avec une
pile visible pour rappeler qu'il en contient plusieurs.

![Composant réduit](../../assets/screenshots/fr/component-collapsed.png){ .shot }

## Les ports d'un composant

Ses ports sont calculés automatiquement :

- entrées : les entrées de ses nœuds qui ne sont pas alimentées depuis l'intérieur du
  groupe (reliées à l'extérieur, ou libres) ;
- sorties : les sorties de ses nœuds qui sont utilisées à l'extérieur, ou pas utilisées
  du tout.

Les connexions se font comme avec un nœud ordinaire ; en interne, elles relient les nœuds
du groupe. Cliquer sur une sortie du composant affiche la sortie du nœud correspondant.

## Déplier, réduire, dissocier

- Un double-clic sur le composant le déplie : ses nœuds réapparaissent dans un
  cadre pointillé portant son nom. Le cadre se déplace par son titre ; **Réduire** le
  replie.
- **Dissocier** (clic droit ou inspecteur) supprime le groupe et garde les nœuds.
- **Exécuter** exécute tous ses nœuds ; son feu résume leur état (vert si tous sont
  exécutés, rouge si l'un est en erreur ou incomplet).

![Composant déplié](../../assets/screenshots/fr/component-expanded.png){ .shot }

L'inspecteur d'un composant liste ses nœuds : un clic déplie le composant et sélectionne
le nœud pour le configurer.

![Inspecteur d'un composant](../../assets/screenshots/fr/component-inspector.png){ .shot }

## Pipelines contractés

Un Pipeline contracté est un composant particulier : il regroupe le nœud Pipeline et ses
étapes, n'affiche que la table brute en entrée et le Pipeline en sortie, et porte ses
étapes en sous-titre. Voir [Le Pipeline](pipeline.md#pipeline-contracte).

## Composants réutilisables

Clic droit › **Enregistrer comme composant réutilisable** : le groupe (ses nœuds, leurs
réglages et leurs connexions internes) est enregistré dans `workspace/components`. Il
apparaît dans le dépôt, catégorie **Mes composants** : glissez-le ou double-cliquez pour
l'insérer, déjà réduit, dans n'importe quel workflow. Clic droit sur un composant du dépôt
pour le supprimer.

!!! tip "Idées de composants"
    Une préparation de données standard (imputation + encodage + normalisation), un trio de
    modèles à comparer, une batterie d'évaluation (prédicteur + métriques + ROC +
    calibration)…
