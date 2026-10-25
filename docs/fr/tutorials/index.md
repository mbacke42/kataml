# Tutoriels

Les dix tutoriels vont de la première prédiction au rapport et au bloc personnalisé ; chacun
demande de 20 à 45 minutes. Ils s'appuient les uns sur les autres, mais chaque page indique
ses prérequis.

| # | Tutoriel | Notions | Exemple corrigé |
|---|---|---|---|
| 1 | [Premier workflow](01-first-workflow.md) | nœuds, connexions, apprentissage / test, évaluation | Classification des iris |
| 2 | [Évaluer sans tricher](02-leakage.md) | validation croisée, fuite d'information, Pipeline | Fuite d'information |
| 3 | [Nettoyer un fichier CSV](03-csv-cleaning.md) | valeurs manquantes, variables catégorielles, classes déséquilibrées | CSV : nettoyage et encodage |
| 4 | [Régression](04-regression.md) | métriques de régression, comparaison de modèles, variance de l'évaluation | Régression : diabète |
| 5 | [Surapprentissage](05-overfitting.md) | complexité, frontières de décision, courbe de validation | Frontières de décision et surapprentissage |
| 6 | [Régler les hyperparamètres](06-tuning.md) | recherche sur grille, courbe d'apprentissage, validation imbriquée | Réglage d'hyperparamètres |
| 7 | [Apprentissage non supervisé](07-unsupervised.md) | clustering, mélanges gaussiens, ACP, anomalies | Non supervisé : clusters et anomalies ; Clustering : k-moyennes et ACP |
| 8 | [Texte et dates](08-text-dates.md) | TF-IDF, caractéristiques de dates, encodage cyclique, séries temporelles | Texte : classer des avis ; Dates : locations de vélos |
| 9 | [Comprendre un modèle](09-understanding.md) | importance par permutation, dépendance partielle, arbres | Comprendre un modèle |
| 10 | [Rapport et bloc personnalisé](10-report-blocks.md) | rapport HTML, export Python, écriture d'un nœud | Classification des iris |

## Organisation d'une page

Chaque tutoriel commence par ses objectifs et ses prérequis, puis construit le workflow
nœud par nœud, avec une capture d'écran aux étapes importantes. Les encadrés « Dans
scikit-learn » donnent le code Python équivalent. Les questions ont leur réponse repliée
sous le titre ; la section « À vous de jouer » propose des variantes à essayer seul. Le
workflow complet se trouve dans **Ouvrir › Exemples**.

Les chiffres cités ont été obtenus avec les graines aléatoires indiquées (`random_state`) ;
ils peuvent varier légèrement d'une version de scikit-learn à l'autre. **Ouvrir** ne
remplace le workflow en cours qu'après confirmation, et celui-ci est sauvegardé
automatiquement : on peut consulter l'exemple corrigé sans perdre son travail.

Pour une utilisation en cours, les annotations (++a++) permettent d'écrire les consignes
sur le canevas, et chaque exemple s'exporte en notebook Jupyter.
