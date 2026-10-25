# Tour de l'interface

L'interface de KataML s'ouvre dans le navigateur. Elle est organisée en cinq zones.

![Les cinq zones de l'interface](../../assets/screenshots/fr/interface-overview.png){ .shot }

| Zone | Rôle | Page détaillée |
|---|---|---|
| **Barre d'outils** (en haut) | nom du workflow, fichiers, annulation, export, rapport, exécution | [Barre d'outils](toolbar.md) |
| **Dépôt de nœuds** (à gauche) | tous les nœuds disponibles, classés selon le guide scikit-learn, avec recherche | [Dépôt de nœuds](repository.md) |
| **Canevas** (au centre) | le workflow : nœuds, connexions, annotations, composants | [Canevas](canvas.md) |
| **Inspecteur** (à droite) | configuration et documentation du nœud sélectionné | [Inspecteur](inspector.md) |
| **Panneau des sorties** (en bas) | tables, modèles et vues du nœud sélectionné | [Sorties](outputs.md) |

Les séparateurs entre les zones se déplacent à la souris : élargissez l'inspecteur pour
lire les aides des hyperparamètres, ou agrandissez le panneau des sorties pour les
graphiques. Les tailles choisies sont mémorisées.

## Le cycle de travail

1. **Ajouter** des nœuds depuis le dépôt (glisser-déposer ou double-clic).
2. **Relier** une sortie à une entrée : les ports triangulaires transportent des tables,
   les ports carrés des modèles.
3. **Configurer** chaque nœud dans l'inspecteur : son feu passe du rouge à l'orange.
4. **Exécuter** (++f7++ ou **Tout exécuter**) : le feu passe au vert.
5. **Inspecter** les résultats dans le panneau des sorties, en cliquant sur un nœud ou sur
   l'une de ses sorties.

Tout changement de configuration remet en attente le nœud concerné et ceux qui en
dépendent ; les autres gardent leurs résultats (voir [Exécution et cache](../concepts/execution.md)).

## Langue et apparence

En haut à droite : **?** ouvre l'aide (++f1++), **EN / FR** bascule la langue (l'interface
est rechargée), la palette ouvre la boîte [Apparence](appearance.md) (mode, couleur
principale, fond du canevas), l'icône lune / soleil bascule entre clair et sombre, et **⏻**
arrête KataML.
