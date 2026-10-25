# Inspecteur

L'inspecteur, à droite, montre le nœud sélectionné : son état, sa configuration et sa
documentation.

<div class="grid" markdown>

![Configuration](../../assets/screenshots/fr/inspector-config.png){ .shot }

![Description](../../assets/screenshots/fr/inspector-description.png){ .shot }

</div>

## En-tête

- Le nom et la catégorie du nœud (chapitre et famille du guide scikit-learn).
- Le champ d'annotation, pour un nom libre (« modèle final », « Forêt 200 arbres »…) affiché sous le
  nom du nœud sur le canevas, utilisé aussi dans les rapports et par le comparateur de
  modèles.
- L'état (pastille), la durée de la dernière exécution et les boutons **Réinit.** (++f8++) et
  **Exécuter** (++f7++).
- En cas d'erreur, le message complet ; en cas de configuration incomplète, la liste de ce
  qui manque ; les éventuels avertissements de scikit-learn (convergence…).

## Onglet « Configuration »

Les paramètres sont groupés :

- **Données** : colonne cible, variables explicatives, poids des observations, colonnes à
  transformer…
- **Paramètres** : options propres au nœud.
- **Validation croisée** (nœuds d'évaluation) : stratégie, nombre de plis, groupes…
- **Hyperparamètres** (nœuds scikit-learn) : tous les paramètres du constructeur de la
  classe, lus directement dans scikit-learn.

Chaque modification est **appliquée immédiatement** (pas de bouton « Valider ») et remet
le nœud et ses descendants en attente. ++ctrl+z++ annule.

### Types de champs

| Champ | Utilisation |
|---|---|
| liste de colonnes (une) | choisir une colonne de la table en entrée ; le type pandas est affiché |
| cases à cocher (plusieurs colonnes) | filtrer, **Tout**, **Aucun**, **Num.** (colonnes numériques) ; vide = valeur par défaut indiquée (souvent « toutes les autres colonnes ») |
| liste de choix | valeurs autorisées par scikit-learn ; la valeur par défaut est marquée |
| interrupteur | paramètres booléens |
| champ « littéral » | une valeur Python : `100`, `0.5`, `None`, `'auto'`, `[1, 2]`, `(1, 2)` ; le texte non reconnu est pris comme chaîne ; des suggestions sont proposées |
| zone de code | expressions pandas, grilles de paramètres, Markdown, scripts |
| fichier | fichier importé dans `workspace/data`, bouton **Importer**, ou chemin absolu |

!!! info "Colonnes inconnues"
    Pour proposer les colonnes, l'inspecteur doit connaître la table en entrée. Si le nœud
    amont n'est pas encore exécuté, un bouton **Charger** l'exécute ; on peut aussi taper
    les noms à la main.

### Hyperparamètres

- Seuls les hyperparamètres **modifiés** sont transmis à scikit-learn ; un liseré bleu les
  signale et **défaut** les réinitialise un par un (**Tout réinitialiser** pour tous).
- Le type attendu (extrait de la docstring scikit-learn) est indiqué à côté du nom ;
  l'aide se déplie d'un clic.
- Au-delà de huit hyperparamètres, un champ **filtre** permet de les retrouver ; les
  paramètres techniques (`verbose`, `n_jobs`, `copy`…) sont masqués tant que
  l'interrupteur **Avancés** n'est pas activé.
- Le lien **Documentation scikit-learn** ouvre la page officielle de la classe.

## Onglet « Description »

Résumé de la classe (issu de scikit-learn), rôle du nœud dans KataML, ports d'entrée et
de sortie (avec leur type et leur caractère optionnel), et documentation de chaque
paramètre. Cliquer sur un nœud **du dépôt** affiche aussi cette description, sans
l'ajouter au workflow.

## Composant sélectionné

Quand un composant réduit est sélectionné, l'inspecteur affiche son nom (modifiable), son
état global, la liste de ses nœuds (un clic déplie le composant et sélectionne le nœud), et
les boutons **Déplier / Réduire**, **Exécuter**, **Enregistrer comme composant**,
**Dissocier**.
