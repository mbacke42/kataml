# 5. Surapprentissage et frontières de décision

!!! abstract "Objectifs"
    - Visualiser ce qu'un modèle a appris grâce à sa frontière de décision.
    - Reconnaître le surapprentissage et le sous-apprentissage.
    - Choisir la complexité d'un modèle avec une courbe de validation.

    Prérequis : [tutoriel 1](01-first-workflow.md). Durée : 30 min.

## Les données

Ajoutez un **Jeu de données scikit-learn** réglé sur `make_moons` (deux « lunes »
imbriquées), avec **Nombre d'échantillons** `400`, **Bruit** `0.3` et **Graine aléatoire**
`0`. La table a deux variables, `x0` et `x1`, et une cible 0/1. Le bruit mélange les deux
classes près de la frontière : un modèle ne peut tout classer correctement qu'en apprenant
ce bruit.

Ajoutez un **Partitionnement** : test `0.3`, stratifié selon `target`, graine `0`.

## Étape 1 : un arbre sans limite

1. Ajoutez **DecisionTreeClassifier** (Apprentissage supervisé › Arbres de décision) sur
   l'apprentissage, avec la cible `target` et `random_state` `0`, sans autre réglage.
2. Ajoutez **Frontière de décision** (Inspection), avec **Modèle** relié à l'arbre et
   **Table** à la sortie **Test**, puis exécutez.

![Arbre profond](../../assets/screenshots/fr/tuto-boundary-deep.png){ .shot }

La carte colore chaque point du plan selon la classe prédite ; les points affichés sont les
données de test. L'arbre a découpé le plan en une multitude de petits rectangles, y compris
des îlots isolés : il a appris chaque point d'apprentissage, bruit compris, et son
exactitude d'apprentissage est de 100 %.

## Étape 2 : un arbre élagué

Dupliquez l'arbre (++ctrl+d++), réglez `max_depth` à `3` et reliez-lui une seconde
frontière de décision.

![Arbre de profondeur 3](../../assets/screenshots/fr/tuto-boundary-pruned.png){ .shot }

La frontière se réduit à quelques grands rectangles : elle est plus grossière, mais ne suit
plus le bruit. Le nœud **Visualiser l'arbre** branché sur ce modèle montre 7 feuilles et des
règles lisibles (`x1 <= 0.09`…).

## Étape 3 : comparer quatre modèles

Ajoutez **KNeighborsClassifier** (`n_neighbors` = `15`) et **SVC** (noyau RBF par défaut),
chacun avec sa frontière de décision, puis **Comparer des modèles** avec les quatre modèles
et la sortie **Apprentissage**.

| Modèle | Exactitude (5 plis) |
|---|---|
| SVM RBF | 0,893 ± 0,054 |
| 15 voisins | 0,889 ± 0,071 |
| Arbre (profondeur 3) | 0,886 ± 0,040 |
| Arbre profond | 0,861 ± 0,063 |

L'arbre profond, parfait sur l'apprentissage, est le moins bon sur des données nouvelles :
c'est le surapprentissage. Les frontières lisses du SVM et des 15 voisins suivent la forme
des lunes.

??? question "Que se passe-t-il avec `n_neighbors` = 1 ?"
    Avec un seul voisin, chaque point d'apprentissage impose sa classe autour de lui et la
    frontière devient très irrégulière, comme celle de l'arbre profond. Avec 200 voisins,
    elle devient au contraire presque droite : le modèle est trop simple pour la forme des
    lunes, c'est le sous-apprentissage.

## Étape 4 : la courbe de validation

Pour choisir `max_depth`, ajoutez une **Courbe de validation**, avec **Modèle
(configuration)** relié à l'arbre profond et **Table** à la sortie **Apprentissage**.
Réglez **Hyperparamètre** sur `max_depth` et **Valeurs testées** sur
`[1, 2, 3, 4, 6, 8, 12, None]`.

![Courbe de validation](../../assets/screenshots/fr/tuto-validation-curve.png){ .shot }

Le graphique trace deux courbes, chacune avec sa bande d'écart-type. Le score
d'apprentissage monte jusqu'à 1,0 quand la profondeur augmente. Le score de validation
culmine vers 0,89 pour une profondeur de 2 ou 3, puis redescend (0,84 à la profondeur 6).
L'écart croissant entre les deux courbes est la signature du surapprentissage ; à gauche
(profondeur 1), les deux scores sont bas, ce qui signale un sous-apprentissage.

```text
           sous-apprentissage    bon compromis       surapprentissage
score       les deux bas        validation max      écart apprentissage / validation
complexité  faible ──────────────────────────────────────────────────── forte
```

!!! example "Dans scikit-learn"
    ```python
    from sklearn.model_selection import validation_curve
    from sklearn.inspection import DecisionBoundaryDisplay
    from sklearn.tree import DecisionTreeClassifier

    depths = [1, 2, 3, 4, 6, 8, 12, None]
    train, valid = validation_curve(DecisionTreeClassifier(random_state=0), X_train, y_train,
                                    param_name="max_depth", param_range=depths, cv=5)
    tree = DecisionTreeClassifier(max_depth=3, random_state=0).fit(X_train, y_train)
    DecisionBoundaryDisplay.from_estimator(tree, X_test)
    ```

## À vous de jouer

- [ ] Tracez la courbe de validation de `n_neighbors` pour les k plus proches voisins
  (`[1, 3, 5, 10, 15, 30, 60, 120]`). Où se situe le sous-apprentissage ?
- [ ] Tracez celle de `C` pour le SVC (`[0.01, 0.1, 1, 10, 100, 1000]`, échelle
  logarithmique).
- [ ] Réduisez le **Bruit** à `0.1`. Les écarts entre modèles se réduisent-ils ?
- [ ] Essayez `min_samples_leaf` = `10` sur l'arbre profond, à la place de `max_depth`.

## Exemple corrigé

**Ouvrir › Exemples › Frontières de décision et surapprentissage**.

![Exemple corrigé](../../assets/screenshots/fr/06_frontiere_decision-canvas.png){ .shot }
