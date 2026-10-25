# Exécution, cache et annulation

## Lancer une exécution

| Portée | Commande | Effet |
|---|---|---|
| un nœud | ++f7++, bouton ▶ au survol, ou **Exécuter** dans l'inspecteur | exécute le nœud, après ceux dont il dépend s'ils ne l'ont pas encore été |
| tout le workflow | **Tout exécuter** (++shift+f7++) | exécute tous les nœuds configurés ; les nœuds incomplets (feu rouge) et leurs descendants sont ignorés, avec un message |
| un nœud et sa suite | clic droit › *Exécuter jusqu'en aval* | exécute le nœud et tout ce qui en dépend |

Pendant l'exécution, les nœuds en attente et en cours clignotent, et un trait animé
parcourt les connexions qui mènent au nœud en cours. Une erreur arrête les nœuds qui
dépendent du nœud fautif ; les autres branches continuent.

## Le cache

Chaque nœud a une signature, calculée à partir de son type, de ses paramètres, des
signatures de ses entrées et, pour un *Lecteur CSV*, de la date de modification du fichier.
Tant que la signature ne change pas, le résultat est réutilisé. Modifier un paramètre ne
remet donc en attente que le nœud concerné et ses descendants, et annuler la modification
(++ctrl+z++) retrouve instantanément l'ancien résultat.

Les résultats sont aussi enregistrés sur disque, dans `workspace/.cache` : après un
redémarrage de KataML, les nœuds déjà calculés restent verts. Ce cache est limité à 1 Go
(variable `KATAML_CACHE_MB`) et les résultats les plus anciens sont supprimés au-delà.
**Réinitialiser**, dans la barre d'outils, le vide entièrement ; **Réinit.** dans
l'inspecteur, ou ++f8++, efface les résultats d'un nœud et de ses descendants.

!!! note "Reproductibilité"
    Le cache suppose qu'un nœud donne le même résultat pour les mêmes entrées. Fixer les
    paramètres `random_state` (graine aléatoire) rend les résultats reproductibles, et les
    comparaisons de modèles équitables.

## Interrompre un calcul

Les calculs tournent dans un processus distinct du serveur. L'interface reste donc
réactive pendant un entraînement, et l'on peut consulter des tables ou des vues. Le bouton
**Arrêter** interrompt le calcul même au milieu d'un `fit` de plusieurs minutes : le
processus est arrêté puis relancé, et les résultats déjà obtenus sont relus depuis le cache
disque.

## Avertissements et erreurs

Les avertissements de scikit-learn (convergence non atteinte, paramètre déprécié…)
s'affichent dans l'inspecteur sans bloquer l'exécution. Les messages d'erreur nomment la
cause et la correction possible : colonne introuvable (avec la liste des colonnes
disponibles), variables non numériques, valeurs manquantes (avec les nœuds qui permettent
de les traiter), paramètre invalide…
