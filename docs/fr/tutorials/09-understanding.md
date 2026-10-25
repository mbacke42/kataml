# 9. Comprendre un modèle

!!! abstract "Objectifs"
    - Mesurer l'importance des variables par permutation et en connaître les limites.
    - Lire une courbe de dépendance partielle.
    - Dessiner un arbre et une frontière de décision.

    Prérequis : tutoriels [1](01-first-workflow.md) et [5](05-overfitting.md). Durée : 40 min.

## Le modèle étudié

Construisez le workflow suivant : **Jeu de données scikit-learn** `breast_cancer` (569
tumeurs, 30 mesures, cible `benign` ou `malignant`), **Partitionnement** (test `0.25`,
stratifié selon `target`, graine `0`), **RandomForestClassifier** (`n_estimators` = `200`,
`random_state` = `0`), puis Prédicteur et Évaluation classification sur le test.
L'exactitude est de 0,958 : une seule tumeur maligne manquée sur 53, et cinq fausses
alertes.

Une forêt de 200 arbres ne se lit pas directement. Les outils d'inspection de scikit-learn
(`sklearn.inspection`) permettent d'examiner ses décisions sous plusieurs angles.

## Étape 1 : importance des variables

Ajoutez **Importance des variables** (Inspection), avec **Modèle** relié à la forêt,
**Table** à la sortie **Test** et **Répétitions** `10`.

![Importance par permutation](../../assets/screenshots/fr/tuto-importance.png){ .shot }

La méthode mélange au hasard une colonne du test, ce qui rompt son lien avec la cible, et
mesure la baisse du score qui en résulte. Une variable importante fait chuter le score, une
variable inutile le laisse inchangé. L'opération est répétée, d'où les barres d'erreur.

Les baisses observées sont très faibles (moins de 0,01) : aucune variable n'est
indispensable, alors que le modèle utilise bel et bien ces mesures. Les 30 variables sont en
effet très corrélées, puisque le rayon, le périmètre et l'aire d'une tumeur varient
ensemble. Quand `worst perimeter` est brouillée, la forêt retrouve la même information dans
`worst radius` ou `worst area`.

!!! warning "Limites de l'importance par permutation"
    - Avec des variables corrélées, l'importance se répartit entre elles ou disparaît : une
      importance faible ne signifie pas qu'une variable est inutile.
    - Elle se calcule sur le test ; sur l'apprentissage, elle mesure aussi ce que le modèle
      a appris par cœur.
    - L'importance par impureté (`feature_importances_`, visible dans l'onglet **Modèle** de
      la forêt) favorise les variables à nombreuses valeurs distinctes ; l'importance par
      permutation est plus fiable.

??? question "Comment mesurer l'importance d'un groupe de variables corrélées ?"
    En retirant tout le groupe (Filtre de colonnes) et en comparant les scores de validation
    croisée avec et sans lui. On peut aussi regrouper les variables corrélées et n'en garder
    qu'une par groupe avant d'interpréter.

## Étape 2 : sens de l'effet

L'importance mesure l'ampleur d'un effet, pas son sens. Ajoutez **Dépendance partielle**
(Inspection), avec **Modèle** relié à la forêt, **Table** à la sortie **Test** et
**Variables** `worst area`, `worst concave points`, `mean texture`.

![Dépendance partielle](../../assets/screenshots/fr/tuto-pdp.png){ .shot }

Chaque courbe montre la probabilité moyenne prédite de malignité quand une variable varie,
les autres gardant leurs valeurs observées. Pour `worst area`, elle passe de 0,35 à 0,53 :
plus la tumeur est grande, plus le modèle penche vers « maligne », avec un seuil marqué.
L'effet de `mean texture` est faible. Les corrélations atténuent ici aussi les effets, car
une aire qui grandit à rayon constant n'existe pas dans la réalité.

## Étape 3 : lire un arbre

Ajoutez **Visualiser l'arbre** (Inspection), avec **Modèle** relié à la forêt, **Indice de
l'arbre** `0` et **Profondeur affichée** `3`.

![Un arbre de la forêt](../../assets/screenshots/fr/tuto-tree.png){ .shot }

Le graphique donne les règles du premier des 200 arbres : chaque nœud teste une variable,
chaque feuille indique une classe et sa proportion. L'arbre complet a 8 niveaux et 19
feuilles, et la forêt fait voter 200 arbres de ce type, chacun entraîné sur un échantillon
différent. Un arbre isolé se lit facilement ; la forêt, plus précise, ne se lit plus
directement. C'est le compromis habituel entre interprétabilité et performance.

## Étape 4 : la frontière de décision en deux dimensions

Ajoutez **Frontière de décision**, avec **Modèle** relié à la forêt, **Table** à la sortie
**Test**, **Axe X** `worst area` et **Axe Y** `worst concave points`. Comme le modèle
utilise 30 variables, les 28 autres sont fixées à leur médiane pour dessiner en deux
dimensions ; la liste de ces valeurs figure sous la carte. La carte montre comment la
décision dépend des deux mesures choisies, toutes choses égales par ailleurs.

!!! example "Dans scikit-learn"
    ```python
    from sklearn.inspection import permutation_importance, PartialDependenceDisplay
    from sklearn.tree import plot_tree

    r = permutation_importance(forest, X_test, y_test, n_repeats=10, random_state=0)
    PartialDependenceDisplay.from_estimator(
        forest, X_test, ["worst area", "worst concave points", "mean texture"])
    plot_tree(forest.estimators_[0], max_depth=3, feature_names=X.columns)
    ```

## Valeurs de Shapley

Les valeurs de Shapley (bibliothèque `shap`) expliquent chaque prédiction individuelle.
Elles ne font pas partie de scikit-learn, mais peuvent être ajoutées sous forme de
[bloc personnalisé](../blocks.md) si `shap` est installé dans le même environnement.
L'importance par permutation et la dépendance partielle couvrent l'essentiel des besoins
d'explication globale.

## À vous de jouer

- [ ] Calculez l'importance sur l'apprentissage au lieu du test. Qu'est-ce qui change ?
- [ ] Remplacez la forêt par un **DecisionTreeClassifier** de profondeur 3 et comparez
  exactitude et lisibilité.
- [ ] Ne gardez que les 10 variables `mean …` (Filtre de colonnes). L'importance par
  permutation devient-elle plus nette ?
- [ ] Ajoutez **LogisticRegression** dans un Pipeline avec StandardScaler et examinez ses
  coefficients dans l'onglet **Modèle**. Que signifie leur signe ?

## Exemple corrigé

**Ouvrir › Exemples › Comprendre un modèle**.

![Exemple corrigé](../../assets/screenshots/fr/12_comprendre_modele-canvas.png){ .shot }
