# 1. Premier workflow : classer des iris

!!! abstract "Objectifs"
    - Construire un workflow complet : données, apprentissage, prédiction, évaluation.
    - Comprendre pourquoi on sépare les données en apprentissage et test.
    - Lire une matrice de confusion et une validation croisée.

    Prérequis : KataML installé ([Installation](../installation.md)). Durée : 30 min.

## Les données

Le jeu de données *iris* décrit 150 fleurs de trois espèces (*setosa*, *versicolor*,
*virginica*) par quatre mesures : longueur et largeur des sépales et des pétales. Il s'agit
de prédire l'espèce à partir des mesures. C'est une tâche de classification supervisée : le
modèle apprend à partir d'exemples dont la réponse est connue.

## Étape 1 : charger les données

1. Cliquez sur **Nouveau** dans la barre d'outils.
2. Dans le dépôt, catégorie **Données**, glissez **Jeu de données scikit-learn** sur le
   canevas (ou double-cliquez sur le fond du canevas et tapez « jeu »).
3. Le nœud est sélectionné. Dans l'inspecteur, choisissez **Jeu de données** : `iris`. Le
   feu passe à l'orange : le nœud est prêt.
4. Appuyez sur ++f7++. Le feu passe au vert et la ligne d'information indique `150 × 5`.

Le panneau du bas affiche la table. Le bouton **Profil** présente une fiche par colonne :
distribution des mesures, et trois espèces de 50 fleurs chacune.

??? question "Pourquoi la colonne `species` est-elle de type texte ?"
    C'est la cible, une catégorie et non une mesure. Les classifieurs de scikit-learn
    acceptent directement des étiquettes textuelles.

## Étape 2 : regarder les données

1. Tirez une connexion depuis la sortie du nœud (le triangle à droite) et relâchez-la dans
   le vide. La recherche rapide ne propose alors que des nœuds qui acceptent une table.
   Tapez « nuage » et choisissez **Nuage de points**, qui est relié automatiquement.
2. Configurez **Axe X** `petal length (cm)`, **Axe Y** `petal width (cm)`, **Couleur**
   `species`, puis exécutez (++f7++).

![Nuage de points des iris](../../assets/screenshots/fr/tuto-iris-scatter.png){ .shot }

*setosa* est nettement à part ; *versicolor* et *virginica* se chevauchent un peu, et le
modèle devrait parfois les confondre.

## Étape 3 : séparer apprentissage et test

Évalué sur les données qui ont servi à l'entraîner, un modèle paraît toujours bon, puisqu'il
a pu les apprendre par cœur. Pour estimer ses performances sur des fleurs qu'il n'a jamais
vues, on garde une partie des données de côté.

1. Ajoutez **Partitionnement** (catégorie **Manipulation**) et reliez-le au jeu de données.
2. Réglez **Proportion de test** `0.25`, **Stratifier selon** `species` (mêmes proportions
   d'espèces des deux côtés) et **Graine aléatoire** `42`.
3. Exécutez. Le nœud a deux sorties, **Apprentissage** (112 lignes) et **Test** (38
   lignes) ; un clic sur chaque port de sortie affiche la table correspondante.

## Étape 4 : entraîner un modèle

1. Dans le dépôt, **Apprentissage supervisé › Ensembles**, glissez
   **RandomForestClassifier**. Une forêt aléatoire fait voter de nombreux arbres de
   décision.
2. Reliez la sortie **Apprentissage** du partitionnement à son entrée.
3. Dans l'inspecteur, réglez **Colonne cible** sur `species` et laissez **Variables
   explicatives** vide (toutes les autres colonnes). Dans **Hyperparamètres**, mettez
   `n_estimators` à `200` et `random_state` à `0`.
4. Exécutez. La sortie est un modèle (port carré) ; un clic dessus montre ses paramètres et
   ses attributs appris (`feature_importances_`…).

!!! info "Hyperparamètres"
    Les hyperparamètres sont les réglages du modèle, fixés avant l'apprentissage. L'onglet
    **Description** de l'inspecteur reprend l'aide de scikit-learn pour chacun, avec un lien
    vers la documentation officielle. Un champ laissé vide garde la valeur par défaut de
    scikit-learn.

## Étape 5 : prédire et évaluer

1. Ajoutez **Prédicteur** (catégorie **Prédiction**). Reliez la sortie **Modèle** à son
   entrée **Modèle**, et la sortie **Test** du partitionnement à son entrée **Table**.
2. Exécutez : la table de test reçoit une colonne `Prediction (species)`.
3. Reliez-lui **Évaluation classification** (catégorie **Sélection et évaluation de
   modèles**) et exécutez.

![Évaluation](../../assets/screenshots/fr/tuto-iris-eval.png){ .shot }

L'exactitude est d'environ 89 % : 34 fleurs bien classées sur 38. La matrice de confusion
(lignes : espèce réelle, colonnes : espèce prédite) situe les erreurs, toutes entre
*versicolor* et *virginica*, comme le laissait prévoir le nuage de points.

??? question "Pourquoi n'y a-t-il aucune erreur sur *setosa* ?"
    Ses pétales sont beaucoup plus petits que ceux des deux autres espèces : une seule règle
    (« longueur du pétale < 2,5 cm ») suffit à la reconnaître.

## Étape 6 : estimer plus finement par validation croisée

Avec 38 fleurs de test, une ou deux erreurs de plus font varier l'exactitude de 3 à 5
points. La validation croisée répète l'apprentissage et l'évaluation sur cinq découpages
différents.

1. Ajoutez **Validation croisée** (catégorie **Sélection et évaluation de modèles**).
2. Reliez la sortie **Modèle** à **Modèle (configuration)** et la sortie **Apprentissage**
   à **Table**. Le modèle est réentraîné sur chaque pli, avec les mêmes réglages.
3. Dans **Métriques**, cochez `accuracy` et `f1_macro`, puis exécutez.

![Validation croisée](../../assets/screenshots/fr/tuto-iris-cv.png){ .shot }

La validation croisée donne 0,94 ± 0,04. Le score de test (0,89) se situe dans cette
fourchette ; il était seulement plus incertain. Le score d'apprentissage vaut 1,0 sur
chaque pli, car la forêt reconnaît parfaitement les fleurs qu'elle a vues : seul le score de
test renseigne sur la qualité du modèle.

!!! example "Dans scikit-learn"
    ```python
    from sklearn.datasets import load_iris
    from sklearn.model_selection import train_test_split, cross_validate
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, confusion_matrix

    df = load_iris(as_frame=True).frame            # KataML renomme target en species
    X, y = df.drop(columns="target"), df["target"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, stratify=y, random_state=42)
    model = RandomForestClassifier(n_estimators=200, random_state=0).fit(X_train, y_train)
    y_pred = model.predict(X_test)
    print(accuracy_score(y_test, y_pred), confusion_matrix(y_test, y_pred))
    print(cross_validate(model, X_train, y_train, cv=5, scoring=["accuracy", "f1_macro"]))
    ```
    **Exporter** produit ce code pour n'importe quel workflow.

## À vous de jouer

- [ ] Remplacez la forêt par **KNeighborsClassifier** (Apprentissage supervisé › Plus
  proches voisins), en le reliant à la place de la forêt : une entrée n'accepte qu'une
  connexion, et la nouvelle remplace l'ancienne. Le score change-t-il ?
- [ ] N'utilisez que les sépales (**Variables explicatives** `sepal length (cm)` et
  `sepal width (cm)`). Que devient l'exactitude, et qu'en déduire sur ces variables ?
- [ ] Changez la graine du partitionnement (`1`, `2`, `3`…) en notant chaque fois
  l'exactitude de test, puis comparez sa dispersion à l'écart-type de la validation
  croisée.

## Exemple corrigé

**Ouvrir › Exemples › Classification des iris** contient ce workflow avec quelques
ajouts : la normalisation et la forêt y sont réunies dans un Pipeline (sujet du tutoriel
suivant), une courbe ROC et une frontière de décision complètent l'évaluation, et des blocs
**Texte du rapport** préparent un rapport (tutoriel 10).

![Exemple corrigé](../../assets/screenshots/fr/01_classification_iris-canvas.png){ .shot }
