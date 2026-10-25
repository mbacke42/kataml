# Canevas

Le canevas contient le workflow : des nœuds reliés par des connexions, des annotations et,
le cas échéant, des composants (groupes de nœuds).

## Anatomie d'un nœud

![États des nœuds](../../assets/screenshots/fr/node-states.png){ .shot }

Chaque nœud affiche :

- une icône colorée indiquant sa famille (données, manipulation, modèle, évaluation…) ;
- son nom (le type de nœud) et, dessous, son annotation (un nom libre donné dans
  l'inspecteur, ou son numéro) ;
- un feu tricolore et une ligne d'information : taille des tables produites (`150 × 5`),
  « modèle entraîné », durée, ou premier problème de configuration ;
- ses ports : entrées à gauche, sorties à droite.

| Feu | Signification |
|---|---|
| 🔴 rouge | à configurer : un paramètre obligatoire ou une entrée manque (le message dit lequel) ; ou erreur à l'exécution (pastille ✕, message dans l'inspecteur) |
| 🟠 orange | configuré, prêt à être exécuté |
| 🟢 vert | exécuté : les résultats sont disponibles |
| 🔵 clignotant | en cours d'exécution ou en attente |

Au survol, un bouton ▶ exécute le nœud (avec ce qui le précède si nécessaire).

## Ports et connexions

Un port triangulaire transporte une table (un DataFrame pandas), un port carré un modèle
(un estimateur scikit-learn ajusté, avec ses variables et sa cible). Les connexions de
modèles sont dessinées en pointillés bleus.

Pour relier, **tirez depuis un port de sortie vers un port d'entrée** du même type ; les
ports incompatibles s'estompent pendant le geste. Une entrée n'accepte qu'une connexion :
en relier une nouvelle remplace l'ancienne. Tirer depuis une entrée déjà reliée détache la
connexion pour la déplacer. Les cycles sont impossibles.

Un **clic simple sur un port de sortie** d'un nœud exécuté affiche cette sortie dans le
panneau du bas. Une connexion se sélectionne d'un clic et se supprime avec ++delete++.

Les ports semi-transparents sont **optionnels** (par exemple « Table 2 » du Script Python,
ou « Estimateur de base » de `BaggingClassifier`).

## Ajout rapide

![Ajout rapide](../../assets/screenshots/fr/quick-add.png){ .shot }

Un double-clic sur le fond du canevas ouvre une recherche flottante qui propose tous les
nœuds ; ++up++, ++down++ et ++enter++ servent à choisir. Une connexion relâchée dans le vide
ouvre la même recherche, limitée aux nœuds compatibles avec le port de départ, et le nouveau
nœud est relié automatiquement.

## Sélection, déplacement, édition

| Geste | Effet |
|---|---|
| clic sur un nœud | sélectionner (affiche configuration et sorties) |
| ++shift++ ou ++ctrl++ + clic | ajouter / retirer de la sélection |
| ++shift++ + glisser le fond | sélection rectangulaire |
| glisser un nœud | déplacer (la sélection entière ; magnétisme sur une grille de 10 px, ++alt++ pour s'en affranchir) |
| glisser le fond, clic molette, ou ++space++ + glisser | se déplacer dans le canevas |
| molette, pincement | zoomer (vers le pointeur) |
| double-clic sur un nœud | ouvrir sa configuration |
| ++delete++ | supprimer la sélection |
| ++ctrl+c++ / ++ctrl+v++ / ++ctrl+d++ | copier / coller / dupliquer (les connexions internes sont conservées) |
| ++ctrl+a++ | tout sélectionner |
| ++f++ | ajuster la vue à tout le workflow |

La barre de zoom, en bas à droite, propose aussi −, +, 100 % et « ajuster ».

## Menus contextuels

![Menu contextuel d'un nœud](../../assets/screenshots/fr/context-menu.png){ .shot }

Le clic droit ouvre un menu qui dépend de l'élément visé :

- sur un nœud : exécuter, exécuter jusqu'en aval, réinitialiser, configurer, afficher
  la vue ou une sortie, télécharger une sortie (CSV ou modèle joblib), copier, dupliquer,
  supprimer ; avec plusieurs nœuds sélectionnés : grouper en composant, créer un Pipeline,
  organiser la sélection ; sur un Script Python : convertir en bloc réutilisable ;
- sur une connexion : la supprimer ;
- sur une annotation : modifier le texte, changer la couleur, supprimer ;
- sur le fond : ajouter un nœud, une annotation, coller, tout sélectionner, ajuster.

## Annotations

Une annotation (bouton **Annotation** ou touche ++a++) est une note colorée posée sur le
canevas : consignes d'un TP, explication d'une étape… **Double-cliquez** pour modifier le
texte (la première ligne s'affiche en gras), tirez le coin inférieur droit pour la
redimensionner. Les annotations sont reprises dans les rapports et les notebooks exportés.

## Organiser automatiquement

**Organiser** (++l++) dispose le graphe en couches de gauche à droite, chaque nœud une
colonne après son prédécesseur le plus profond, en limitant les croisements. Appliqué à
une sélection, il ne range que celle-ci. Un composant réduit compte pour un seul nœud.
L'opération s'annule avec ++ctrl+z++.

## Composants

Plusieurs nœuds peuvent être regroupés en un **composant** (++ctrl+g++), réduit en un seul
nœud à ports, déplié à la demande, et enregistré pour être réutilisé. Voir
[Composants](../concepts/components.md).

## Créer un Pipeline depuis la sélection

Sélectionnez des transformeurs (jusqu'à trois) et **un** modèle supervisé, puis clic droit
› **Créer un Pipeline** : KataML ajoute un nœud Pipeline relié à la table brute, au
modèle et aux transformeurs dans le bon ordre, puis le **contracte** avec ses étapes en un
seul nœud (double-clic pour le déplier). Un Pipeline existant se contracte par clic droit ›
**Contracter le Pipeline**. Voir [Le Pipeline](../concepts/pipeline.md).

## Déposer un fichier

Glissez un fichier **CSV** depuis votre explorateur de fichiers sur le canevas : il est
copié dans `workspace/data` et un nœud *Lecteur CSV* est créé. Un fichier **Parquet** ou
**Excel** crée un nœud *Lecteur Parquet / Excel*. Un fichier **.json** de workflow est
ouvert directement, et un ou plusieurs scripts **.py** sont convertis en schéma (voir
[Importer un script Python](toolbar.md#importer-un-script-python)).
