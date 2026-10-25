# Panneau des sorties

Le panneau du bas montre les résultats du nœud sélectionné. Ses onglets correspondent aux
sorties du nœud (une par port de sortie), précédées de la **Vue** quand le nœud en
produit une. La flèche à droite réduit ou agrandit le panneau ; sa hauteur se règle avec
le séparateur.

## Vue

![Vue d'une évaluation](../../assets/screenshots/fr/outputs-view.png){ .shot }

La vue rassemble ce que le nœud a à montrer : indicateurs (métriques), graphiques,
tableaux de synthèse, texte. Les graphiques sont interactifs : le survol affiche les
valeurs exactes ; les courbes ont un réticule. Les principaux types :

| Graphique | Nœuds |
|---|---|
| matrice de confusion, carte de chaleur | Évaluation classification, Matrice de corrélation, covariance |
| barres, barres horizontales | importances, coefficients, comparaison de modèles, tailles des clusters |
| histogrammes, boîtes à moustaches | Statistiques, Histogramme, résidus, scores d'anomalie |
| nuages de points | Nuage de points, prédit vs réel, anomalies, plongements |
| courbes avec bandes d'écart-type | ROC, précision-rappel, calibration, courbes d'apprentissage et de validation, dépendance partielle |
| carte de décision | Frontière de décision |
| arbre | Visualiser l'arbre |

## Table

![Table](../../assets/screenshots/fr/outputs-table.png){ .shot }

- 100 lignes par page, navigation en bas ; le total de lignes et de colonnes est indiqué.
- Cliquer sur un **en-tête** trie (croissant, décroissant, puis ordre d'origine) ; le type
  pandas de chaque colonne est affiché sous son nom.
- Les valeurs manquantes apparaissent en *NaN* grisé ; l'index d'origine est conservé.
- **CSV** télécharge la table complète.

## Profil

![Profil des colonnes](../../assets/screenshots/fr/outputs-profile.png){ .shot }

Le bouton **Profil** remplace la table par une fiche par colonne : type, nombre de valeurs
distinctes et manquantes, histogramme et statistiques (numérique) ou modalités les plus
fréquentes (texte). Idéal pour un premier coup d'œil sur des données inconnues.

## Modèle

![Modèle](../../assets/screenshots/fr/outputs-model.png){ .shot }

Pour un port modèle : estimateur, type (classifieur, régresseur, clustering,
transformeur…), cible, variables utilisées, classes, colonnes produites (transformeurs),
hyperparamètres effectifs, **attributs appris** (`coef_`, `feature_importances_`,
`n_iter_`…) et représentation Python. **joblib** télécharge le modèle, rechargeable dans
n'importe quel script avec `joblib.load()`.
