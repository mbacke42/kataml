# 2. Évaluer sans tricher : la fuite d'information

!!! abstract "Objectifs"
    - Constater qu'une évaluation peut être fausse alors que la démarche paraît correcte.
    - Comprendre la fuite d'information entre apprentissage et test.
    - Utiliser le nœud **Pipeline** pour l'éviter.

    Prérequis : [tutoriel 1](01-first-workflow.md). Durée : 30 min.

## Principe de l'expérience

Les données de ce tutoriel ne contiennent rien à apprendre : 100 lignes, 2 000 variables
tirées au hasard et une cible 0/1 tirée au hasard elle aussi. Sur de nouvelles données,
aucun modèle ne peut dépasser 50 % d'exactitude. On applique pourtant une démarche courante,
puis on mesure ce qu'elle annonce.

## Étape 1 : générer des données aléatoires

1. Cliquez sur **Nouveau**, puis ajoutez un nœud **Script Python** (catégorie
   **Manipulation**). Ce nœud exécute du code pandas et attend une table en entrée, même
   s'il ne s'en sert pas : reliez-lui un **Jeu de données scikit-learn** (iris, par
   exemple).
2. Dans **Code**, écrivez :

    ```python
    import numpy as np
    rng = np.random.default_rng(0)
    # 100 lignes, 2 000 variables de pur hasard, cible au hasard.
    out = pd.DataFrame(rng.normal(size=(100, 2000)), columns=[f'x{i}' for i in range(2000)])
    out['target'] = rng.integers(0, 2, size=100)
    ```

3. Exécutez : le nœud produit une table `100 × 2001`.

## Étape 2 : la démarche qui fuit

Avec 2 000 variables pour 100 lignes, on commence par retenir les variables qui semblent
utiles.

1. Ajoutez **SelectKBest** (Apprentissage supervisé › Sélection de variables), relié au
   script, avec **Cible** `target` et `k` = `20`. Exécuté, il garde les 20 variables les
   plus liées à la cible (test ANOVA).
2. Ajoutez **LogisticRegression** sur sa **Table transformée**, avec **Colonne cible**
   `target`.
3. Ajoutez **Validation croisée**, en reliant **Modèle (configuration)** à la régression
   logistique et **Table** à la table transformée de SelectKBest, puis exécutez.

![Validation croisée avec fuite](../../assets/screenshots/fr/tuto-leak-wrong.png){ .shot }

La validation croisée annonce 81 % d'exactitude sur des données de pur hasard, alors que le
modèle n'a rien appris de réel.

??? question "Où est l'erreur ?"
    SelectKBest a choisi ses 20 variables en regardant les 100 lignes, y compris celles qui
    servent ensuite de test dans chaque pli. Parmi 2 000 variables aléatoires, certaines
    sont corrélées à la cible par hasard sur ces 100 lignes précises, et la sélection les a
    trouvées grâce aux réponses du test. La validation croisée ne réentraîne que la
    régression logistique : la sélection a déjà vu le test.

## Étape 3 : la bonne démarche avec un Pipeline

La chaîne entière (sélection et modèle) doit être réapprise sur chaque pli d'apprentissage,
sans jamais voir le pli de test.

1. Ajoutez un nœud **Pipeline** (Transformations de données › Pipelines et estimateurs
   composites).
2. Reliez **Table brute** à la sortie du script (les données avant sélection), **Modèle** à
   la régression logistique et **Prétraitement 1** à la sortie **Transformeur** de
   SelectKBest.

    !!! tip "Raccourcis"
        Sélectionner SelectKBest et la régression logistique (++shift++ + clic), puis faire
        un clic droit › **Créer un Pipeline** établit les trois connexions ; le Pipeline
        apparaît contracté avec ses étapes, et un double-clic le déplie. On peut aussi
        sélectionner la première validation croisée : l'inspecteur signale la fuite et
        propose **Créer le Pipeline et l'utiliser**.

3. Ajoutez une seconde **Validation croisée**, avec **Modèle (configuration)** relié au
   Pipeline et **Table** à la sortie du script, puis exécutez.

![Validation croisée sans fuite](../../assets/screenshots/fr/tuto-leak-right.png){ .shot }

Le score tombe à 52 %, le niveau du hasard. Chaque pli refait désormais la sélection sur ses
seules données d'apprentissage, et les variables retenues ne valent rien sur le test.

!!! example "Dans scikit-learn"
    ```python
    from sklearn.pipeline import make_pipeline
    from sklearn.feature_selection import SelectKBest
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score

    # Faux : la sélection voit tout le jeu de données
    X_sel = SelectKBest(k=20).fit_transform(X, y)
    cross_val_score(LogisticRegression(), X_sel, y, cv=5).mean()      # ≈ 0.81

    # Juste : la sélection est refaite dans chaque pli
    pipe = make_pipeline(SelectKBest(k=20), LogisticRegression())
    cross_val_score(pipe, X, y, cv=5).mean()                          # ≈ 0.52
    ```

## Étapes à placer dans le Pipeline

Toute étape qui apprend quelque chose des données (normalisation, imputation, sélection de
variables, ACP, encodage…) fait partie du modèle et doit être ajustée sur les seules données
d'apprentissage. Le Pipeline le garantit, en validation croisée comme en recherche
d'hyperparamètres, et s'applique ensuite directement à des données brutes. La fuite est
d'autant plus forte que les variables sont nombreuses et les lignes rares ; sur des données
réelles, elle est moins visible qu'ici, mais elle fausse l'évaluation de la même façon.

Voir aussi : [Le Pipeline](../concepts/pipeline.md).

## À vous de jouer

- [ ] Faites varier `k` (5, 50, 200) dans SelectKBest. Comment évoluent les deux scores ?
- [ ] Remplacez la cible aléatoire par une cible liée à une variable :
  `out['target'] = (out['x0'] + rng.normal(scale=0.5, size=100) > 0).astype(int)`.
  Les deux démarches donnent-elles encore des résultats différents ?
- [ ] Ajoutez un **Test de permutation** sur le Pipeline. Que vaut la p-valeur ?

## Exemple corrigé

**Ouvrir › Exemples › Fuite d'information**.

![Exemple corrigé](../../assets/screenshots/fr/10_fuite_information-canvas.png){ .shot }
