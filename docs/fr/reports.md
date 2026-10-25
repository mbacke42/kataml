# Rapports

Un rapport présente un workflow et ses résultats sous forme d'un document lisible :
pour rendre un TP, documenter une étude, partager une analyse avec quelqu'un qui n'a pas
KataML.

## Générer un rapport

Bouton **Rapport** de la barre d'outils, ou ++ctrl+p++.

![Boîte de dialogue Rapport](../assets/screenshots/fr/dialog-report.png){ .shot }

| Réglage | Effet |
|---|---|
| **Titre**, **Auteur** | en-tête du rapport (titre par défaut : le nom du workflow) |
| **Schéma du workflow** | dessin du graphe, nœuds colorés selon leur état |
| **Annotations** | les notes du canevas, en encadrés |
| **Aperçu des tables** | pour les nœuds sans vue (manipulations), les 10 premières lignes de la table produite |
| **Script Python en annexe** | le code exporté, en fin de rapport |
| **Contenu et ordre des sections** | les nœuds à inclure (cases à cocher) et leur ordre (↑ ↓) |

Par défaut, sont cochés les nœuds qui produisent une **vue** (évaluations, graphiques,
inspection…) et les blocs **Texte du rapport**, dans l'ordre d'exécution.

**Générer le rapport** exécute d'abord les nœuds cochés qui ne le sont pas encore, puis
enregistre le fichier dans `workspace/reports`. Une fenêtre propose de l'**ouvrir** dans un
nouvel onglet ou de le **télécharger**. Les cinq derniers rapports sont listés en bas de la
boîte de dialogue.

Les réglages sont enregistrés **avec le workflow** : la prochaine génération, depuis
l'interface ou la [ligne de commande](cli.md), reprend la même sélection.

## Contenu du rapport

![Rapport](../assets/screenshots/fr/report-page.png){ .shot }

1. **En-tête** : titre, auteur, date, versions de KataML, scikit-learn et pandas
   (utile pour la reproductibilité).
2. **Sommaire** cliquable.
3. **Schéma du workflow** et **annotations**.
4. Une **section par nœud** : nom (annotation) et type, puis sa vue complète :
   indicateurs, graphiques interactifs, tableaux. Un nœud en erreur affiche son message.
5. **Annexe** : le script Python équivalent (si demandé).

## Commenter : les blocs « Texte du rapport »

Le nœud **Texte du rapport** (catégorie **Rapport**) n'a ni entrée ni sortie. Il porte un
titre de section et un texte en Markdown :

```markdown
## Objectif

Prédire l'espèce d'un iris à partir de **quatre mesures**.

- 150 fleurs, 50 par espèce ;
- évaluation par validation croisée à 5 plis.

Source : [scikit-learn](https://scikit-learn.org/stable/datasets/toy_dataset.html#iris-dataset).
```

Sont reconnus : titres (`#` à `####`), paragraphes, listes à puces et numérotées, **gras**,
*italique*, `code`, liens et citations. Placez ces blocs dans l'ordre des sections pour
introduire, expliquer et conclure.

## Un fichier autonome

Le rapport est un fichier HTML unique qui contient tout ce dont il a besoin : données des
graphiques, styles et code d'affichage. Il s'ouvre hors ligne dans n'importe quel
navigateur, sans KataML ; ses graphiques affichent les valeurs au survol ; il s'imprime
proprement en PDF (++ctrl+p++ dans le navigateur, avec une mise en page adaptée) ; et il
s'envoie par courriel ou se dépose sur un ENT comme n'importe quel autre fichier.

!!! tip "Langue"
    Le rapport est rédigé dans la langue de l'interface. En ligne de commande :
    `--lang en`.
