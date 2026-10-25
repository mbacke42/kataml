# 3. Nettoyer un fichier CSV

!!! abstract "Objectifs"
    - Importer ses propres données et en établir le profil.
    - Traiter les valeurs manquantes et les variables catégorielles.
    - Choisir une métrique adaptée à des classes déséquilibrées.

    Prérequis : tutoriels [1](01-first-workflow.md) et [2](02-leakage.md). Durée : 45 min.

## Les données

`clients.csv`, fourni avec les exemples, décrit 800 clients d'un opérateur fictif : région,
offre souscrite, âge, revenu, ancienneté, nombre d'appels au support, et la cible `resilie`
(oui / non). Le but est de prédire les résiliations afin de contacter les clients à risque.

## Étape 1 : lire et profiler

1. Cliquez sur **Nouveau**, puis ajoutez un **Lecteur CSV** (catégorie **Données**). Dans
   **Fichier**, choisissez `clients.csv`. Vos propres données s'ajoutent avec le bouton
   **Importer**, ou en glissant le fichier sur le canevas.
2. Laissé vide, le séparateur de colonnes est détecté automatiquement. Pour un fichier qui
   utilise `;` et la virgule décimale, réglez **Séparateur décimal** sur `,`.
3. Reliez un nœud **Statistiques** et exécutez.

![Profil des données](../../assets/screenshots/fr/tuto-csv-profile.png){ .shot }

Le profil fait apparaître 158 valeurs manquantes (53 pour `age`, 79 pour `revenu`, 26 pour
`anciennete`), deux colonnes textuelles, `region` (5 modalités) et `offre` (3), et une cible
déséquilibrée : environ 28 % de résiliations.

??? question "Pourquoi ne pas supprimer les lignes incomplètes ?"
    Le nœud **Lignes incomplètes** (`dropna`) le ferait, mais on perdrait près d'un client
    sur cinq, et les clients aux données incomplètes ne ressemblent pas forcément aux
    autres. Surtout, le modèle devra prédire pour de nouveaux clients, qui auront eux aussi
    des valeurs manquantes : il doit apprendre à les compléter.

## Étape 2 : partitionner d'abord

Ajoutez un **Partitionnement** avec **Proportion de test** `0.25`, **Stratifier selon**
`resilie` et **Graine aléatoire** `1`. Toutes les étapes suivantes apprennent sur la sortie
**Apprentissage**.

## Étape 3 : préparer les colonnes

Enchaînez trois transformeurs de la catégorie **Transformations de données**, chacun
recevant la **Table transformée** du précédent :

| Nœud | Réglages | Rôle |
|---|---|---|
| **SimpleImputer** (Imputation des valeurs manquantes) | colonnes `age`, `revenu`, `anciennete` ; `strategy` = `median` | remplace chaque valeur manquante par la médiane de la colonne, calculée sur l'apprentissage |
| **OneHotEncoder** (Prétraitement) | colonnes `region`, `offre` ; `handle_unknown` = `ignore` | crée une colonne 0/1 par modalité |
| **StandardScaler** (Prétraitement) | cible `resilie` | centre et réduit les colonnes numériques, sauf la cible |

Les colonnes non choisies sont conservées telles quelles. Après l'encodage, la table
contient des colonnes `region_Est`, `region_Nord`, etc.

!!! warning "La cible dans les transformeurs"
    Réglé sur « toutes les colonnes », un transformeur traiterait aussi la cible.
    Indiquez-la dans son champ **Cible** pour l'exclure.

## Étape 4 : modèle et Pipeline

1. Ajoutez **LogisticRegression** sur la sortie du StandardScaler, avec la cible `resilie`,
   `max_iter` = `1000` et `class_weight` = `'balanced'`.
2. Sélectionnez les trois transformeurs et le modèle, puis faites un clic droit ›
   **Créer un Pipeline**. Sa table brute est la sortie **Apprentissage** du partitionnement.
   Le Pipeline apparaît contracté, ses quatre étapes réunies en un seul nœud ; un
   double-clic les affiche.
3. Ajoutez un **Prédicteur**, avec **Modèle** relié au Pipeline et **Table** à la sortie
   **Test** brute : le Pipeline impute, encode et normalise lui-même. Terminez par
   **Évaluation classification** et **Courbe ROC**.

![Évaluation](../../assets/screenshots/fr/tuto-csv-eval.png){ .shot }

## Étape 5 : lire l'évaluation

L'exactitude n'est que de 58 %, alors qu'un modèle répondant toujours « non » atteindrait
72 %. La matrice de confusion nuance ce constat : le modèle détecte 35 résiliations sur 56
(rappel de 62 %), au prix de fausses alertes, quand le modèle « toujours non » n'en détecte
aucune.

Le réglage `class_weight='balanced'` donne plus de poids à la classe rare ; le modèle
cherche donc les résiliations au lieu de privilégier la réponse majoritaire. L'exactitude
équilibrée (moyenne des rappels par classe) vaut 0,59, au-dessus du 0,5 du hasard. L'AUC
(0,65) mesure la capacité à classer les clients du plus au moins risqué, indépendamment du
seuil de décision.

Ces données sont peu prédictives, ce qui est fréquent en pratique.

??? question "Quelle métrique choisir ?"
    Celle qui reflète le coût des erreurs. Si contacter un client coûte peu et qu'en perdre
    un coûte cher, on privilégie le rappel de la classe « oui » ; pour comparer des modèles
    indépendamment du seuil, l'AUC ou la précision moyenne. L'exactitude seule est
    trompeuse dès que les classes sont déséquilibrées.

## Étape 6 : régler la régularisation

Ajoutez **Recherche d'hyperparamètres**, avec **Modèle (configuration)** relié au Pipeline
et **Table** à la sortie **Apprentissage**, et la grille suivante :

```json
{ "model__C": [0.01, 0.1, 1, 10] }
```

Choisissez la **Métrique** `roc_auc`. Le préfixe `model__` désigne l'étape modèle du
Pipeline ; la vue du Pipeline liste tous les paramètres réglables. Les quatre valeurs
donnent une AUC de validation croisée proche de 0,74 : la régularisation change peu de
chose, les données sont le facteur limitant.

!!! example "Dans scikit-learn"
    ```python
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from sklearn.pipeline import make_pipeline
    from sklearn.linear_model import LogisticRegression

    prep = ColumnTransformer([
        ("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()),
         ["age", "revenu", "anciennete", "appels_support"]),
        ("cat", OneHotEncoder(handle_unknown="ignore"), ["region", "offre"]),
    ])
    pipe = make_pipeline(prep, LogisticRegression(max_iter=1000, class_weight="balanced"))
    ```

## À vous de jouer

- [ ] Ajoutez un **DummyClassifier** (Apprentissage supervisé) et comparez-le au Pipeline
  avec **Comparer des modèles**, en métrique `balanced_accuracy` puis `accuracy`.
- [ ] Retirez `class_weight`. Que deviennent l'exactitude, le rappel des résiliations et
  l'AUC ? Pourquoi l'AUC varie-t-elle peu ?
- [ ] Essayez **HistGradientBoostingClassifier**, qui accepte les valeurs manquantes sans
  imputation.

## Exemple corrigé

**Ouvrir › Exemples › CSV : nettoyage et encodage**.

![Exemple corrigé](../../assets/screenshots/fr/04_csv_pretraitement-canvas.png){ .shot }
