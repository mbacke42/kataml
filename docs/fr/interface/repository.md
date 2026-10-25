# Dépôt de nœuds

Le dépôt, à gauche, contient tous les nœuds disponibles. Il se parcourt de deux façons et
se filtre par une recherche.

<div class="grid" markdown>

![Vue « Guide »](../../assets/screenshots/fr/repository-guide.png){ .shot }

![Vue « API »](../../assets/screenshots/fr/repository-api.png){ .shot }

</div>

## Vue « Guide » : les chapitres de scikit-learn

Par défaut, les nœuds sont classés comme le
[guide utilisateur de scikit-learn](https://scikit-learn.org/stable/user_guide.html) :
une **catégorie** par chapitre, puis des **familles** qui reprennent ses sections.

| Catégorie | Contenu | Exemples de familles |
|---|---|---|
| **Essentiels** | sélection des nœuds les plus utiles pour débuter | |
| **Données** | lecture et écriture (CSV, jeux scikit-learn, OpenML, modèles) | |
| **Manipulation (pandas)** | filtres, colonnes calculées, partition, tri, jointures, dates, script Python | |
| **Visualisation** | statistiques, nuages de points, histogrammes, corrélations, boîtes à moustaches | |
| **Transformations de données** | chapitre 6 du guide | Prétraitement, Imputation, Extraction de caractéristiques, Approximation de noyaux, Projections aléatoires, Pipelines |
| **Apprentissage supervisé** | chapitre 1 | Modèles linéaires, SVM, Plus proches voisins, Arbres, Ensembles, Multiclasse et multisortie, Sélection de variables, Calibration, Réseaux de neurones… |
| **Apprentissage non supervisé** | chapitre 2 | Clustering, Mélanges gaussiens, Décomposition (ACP…), Variétés, Covariance, Détection d'anomalies, Densité |
| **Prédiction** | appliquer un modèle (`predict`) ou un transformeur (`transform`) | |
| **Sélection et évaluation de modèles** | chapitre 3 | Validation croisée, Réglage des hyperparamètres, Seuil de décision, Métriques, Courbes de validation |
| **Inspection** | chapitre 4 | Dépendance partielle, Importance par permutation, Visualisation des modèles |
| **Rapport** | blocs de texte pour les rapports | |
| **Mes composants** | vos groupes de nœuds enregistrés ([Composants](../concepts/components.md)) | |
| **Mes blocs** | vos nœuds Python ([Blocs personnalisés](../blocks.md)) | |

!!! info "Emplacement de chaque estimateur"
    Comme dans scikit-learn, un même estimateur ne figure qu'à un endroit : par exemple
    `SelectKBest` est dans *Apprentissage supervisé › Sélection de variables* (section 1.13
    du guide), `PCA` dans *Apprentissage non supervisé › Décomposition* (section 2.5).
    La recherche reste le moyen le plus rapide de trouver un nœud.

## Vue « API » : les modules Python

Le bouton **API** regroupe les nœuds par module : `sklearn.linear_model`,
`sklearn.ensemble`, `sklearn.model_selection`… Les nœuds propres à KataML (lecture,
manipulation, visualisation) sont rangés sous `kataml`. Pratique quand on connaît déjà
scikit-learn, ou pour retrouver un nœud vu dans un script.

## Recherche

![Recherche « forêt »](../../assets/screenshots/fr/repository-search.png){ .shot }

Le champ de recherche filtre en direct, dans les deux langues : noms de classes
(`RandomForest`, `pca`), mots français (« forêt », « acp », « normalisation »,
« anomalies »), modules (`ensemble`). Les résultats s'affichent avec leur famille.
++enter++ ajoute le premier résultat ; ++escape++ efface la recherche.

## Ajouter un nœud

- **Glisser-déposer** un nœud du dépôt sur le canevas. Déposé sur un nœud existant, il est
  relié automatiquement à sa première sortie compatible.
- **Double-cliquer** dans le dépôt : le nœud est ajouté à droite du nœud sélectionné et
  relié à lui.
- **Cliquer** une fois sur un nœud du dépôt affiche sa description dans l'inspecteur, sans
  l'ajouter.

On peut aussi ajouter un nœud directement depuis le canevas, voir
[Ajout rapide](canvas.md#ajout-rapide).

## Le bouton « Mes blocs »

En haut du dépôt, **Mes blocs** ouvre le gestionnaire de blocs personnalisés : créer un
nœud en Python, le modifier, le recharger. Voir [Blocs personnalisés](../blocks.md).
