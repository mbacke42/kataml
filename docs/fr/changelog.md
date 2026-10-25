# Historique des versions

## Version de développement

- **Import d'un script Python** : le bouton « Importer un script Python (.py) » de la boîte
  « Ouvrir » (ou le dépôt d'un `.py` sur le canevas) reconstruit le schéma à partir d'un script
  pandas / scikit-learn. Le script n'est **jamais exécuté** : il est analysé. Sont reconnus la
  lecture des données, `dropna`, `drop`, `train_test_split`, les estimateurs, `Pipeline`,
  `ColumnTransformer`, `fit` / `predict`, les métriques et la validation croisée ; les
  fonctions du script sont suivies, et les opérations pandas non reconnues deviennent des
  nœuds « Script Python ». Sélectionnez aussi les modules importés par le script : leurs
  constantes (nom de la cible, colonnes…) et fonctions sont reprises. Une note sur le
  canevas liste ce qui reste à vérifier.
- **Lecteur Parquet / Excel** : nouveau nœud qui lit les fichiers `.parquet`, `.xlsx`, `.xls`
  et `.feather` (feuille Excel au choix). Déposer un tel fichier sur le canevas crée ce nœud.
  `pyarrow` et `openpyxl` rejoignent les dépendances.
- **Lecteur SQL** : lit une base SQLite de `workspace/data` (en lecture seule) ou une base
  PostgreSQL / MySQL par son URL de connexion. Écrire `$DATABASE_URL` lit l'URL dans une
  variable d'environnement, pour ne pas enregistrer de mot de passe dans le workflow. Une
  requête, un nom de table, ou rien (s'il n'y a qu'une table). L'import de script convertit
  `pd.read_sql(…)`, y compris une requête construite par f-string et une URL lue par
  `os.getenv`.
- **Fenêtre « Données et scripts »** (bouton « Données ») : les fichiers de `workspace/data`
  (ajout au canevas avec le bon lecteur, retrait) et une **bibliothèque de scripts**
  (`workspace/scripts`) : ajouter, écrire à partir d'un modèle, modifier, puis cocher les
  scripts à convertir en schéma. Les autres scripts de la bibliothèque servent de modules
  quand ils sont importés.
- **Import d'un dossier de projet** : les scripts rejoignent la bibliothèque (les dossiers
  `.venv`, `.git`, caches… sont ignorés) et seuls les fichiers de données lus par le schéma
  sont importés. Après une conversion, KataML signale les fichiers de données manquants et
  propose de les importer.
- **Calculs plus rapides sur les gros jeux de données** : au-delà de 10 000 lignes, validation
  croisée, prédictions hors pli, recherche d'hyperparamètres, courbes et permutations
  utilisent tous les cœurs du processeur (option `--jobs`, variable `KATAML_N_JOBS`). Les
  prédictions hors pli n'entraînent plus le modèle deux fois quand les probabilités suffisent
  à donner la classe prédite. Option `--cache-mb` pour agrandir le cache des résultats.
- **Encodeurs et colonnes texte** : sans colonnes choisies, OneHotEncoder, OrdinalEncoder et
  TargetEncoder ne prennent que les colonnes texte, et les normalisations / PCA que les
  colonnes numériques (au lieu de toutes, ce qui échouait sur du texte). Les colonnes retenues
  sont indiquées dans les messages du nœud. Un transformeur qui a besoin de la cible
  (TargetEncoder, SelectKBest…) le dit clairement si le champ « Cible » est vide.
- L'import de script reprend mieux le code de préparation : variables intermédiaires
  (masques, dates), chaînes pandas et opérations sur deux tables (`df` et `df2`) deviennent
  des nœuds « Script Python » lisibles.

## 0.5.8 (16 octobre 2026)

- Les extensions « maison » (analyse exploratoire, exemple de préparation) sont désormais
  **livrées avec l'application**, donc présentes dans les versions portables sans rien
  installer. On les **active d'une case à cocher** dans « Mes blocs », section « Extensions
  fournies » (désactivées par défaut ; choix mémorisé dans `workspace/extensions.json`).
- Les blocs d'**analyse exploratoire** (vue d'ensemble, valeurs manquantes, fréquences,
  relation avec la cible, distributions, valeurs extrêmes) sont ainsi disponibles partout,
  et traduits en anglais comme le reste de l'interface.
- Une *skill* pour assistant IA (`.claude/skills/kataml-extension/`) décrit l'API et les
  conventions pour écrire ses propres extensions ; le guide des blocs présente les trois
  sources d'extensions.
- Corrections : **Réunir des colonnes** ne plante plus sur une valeur manquante (elle compte
  pour un texte vide) ; **Scinder une colonne** et **Éclater une liste** gardent les manquants
  au lieu de produire le texte « nan » ; **Pivoter** se limite par défaut aux colonnes
  numériques avec « mean », « median » ou « sum », et explique l'erreur sinon ;
  **Concordance** affiche « — » pour une mesure non définie (colonne constante) au lieu de
  bloquer la vue ; les valeurs infinies des tables s'affichent comme manquantes ; les
  messages d'erreur des nouveaux nœuds sont traduits.

## 0.5.7 (16 octobre 2026)

- Première version des blocs d'analyse exploratoire, en extension (voir 0.5.8 pour leur
  intégration et leur activation par case à cocher).

## 0.5.6 (15 octobre 2026)

- L'interface signale par un bandeau refermable qu'une version plus récente est publiée en
  release. La vérification interroge GitLab au plus une fois par jour, sans aucune donnée
  personnelle (User-Agent générique), échoue en silence hors ligne, et se désactive avec la
  variable d'environnement `KATAML_NO_UPDATE_CHECK=1`.

## 0.5.5 (15 octobre 2026)

- Sept nœuds de remise en forme des données (grammaire des données, en pandas), dans la
  catégorie **Manipulation** : **Dépivoter (format long)** et **Pivoter (format large)** pour
  passer entre format large et long ; **Scinder une colonne** et **Réunir des colonnes** pour
  découper ou recombiner du texte ; **Éclater une liste** pour obtenir une ligne par élément ;
  **Dédoublonner** et **Propager les valeurs** (ffill/bfill).
- Ils complètent les nœuds existants (filtrage, agrégation, jointure, concaténation) pour
  mettre en forme un jeu de données avant l'apprentissage.

## 0.5.4 (15 octobre 2026)

- Deux nouveaux nœuds d'évaluation. **Concordance entre deux colonnes** mesure l'association
  entre deux colonnes catégorielles (table de contingence, V de Cramér, indice de Rand
  ajusté, information mutuelle, V-mesure, Fowlkes–Mallows) ; il compare aussi un clustering à
  une vérité terrain, et ajoute l'accord brut et le kappa de Cohen quand les deux colonnes
  emploient les mêmes catégories. **Qualité du clustering** évalue un clustering sans vérité
  terrain : silhouette (globale et par cluster), Calinski–Harabasz et Davies–Bouldin.
- L'**Évaluation classification** ajoute Jaccard, les pertes de Hamming et 0-1, et, lorsque
  le Prédicteur fournit les probabilités, le log-loss et l'exactitude top-2.
- L'**Évaluation régression** ajoute le score D² (erreur absolue) et, sur cibles positives,
  MSLE/RMSLE et les déviances de Poisson et Gamma.

## 0.5.3 (14 octobre 2026)

- Après un changement de jeu de données, les colonnes qui n'existent plus en entrée d'un
  nœud sont retirées de sa configuration, au lieu de rester affichées « absentes » ; un
  message liste les colonnes retirées, et Ctrl+Z annule l'opération. Pendant une exécution,
  ce nettoyage a lieu avant chaque nœud, et un nœud qui n'est plus configuré n'est pas
  exécuté.
- Les listes de colonnes de l'inspecteur se mettent à jour après chaque exécution, sans
  avoir à resélectionner le nœud.

## 0.5.2 (11 octobre 2026)

- Le nœud **Recherche d'hyperparamètres** a une troisième sortie, **Recherche
  (configuration)**. Reliée à une validation croisée (ou à une comparaison, une courbe…),
  elle donne une validation croisée imbriquée, dont la vue liste les hyperparamètres
  retenus dans chaque pli.
- L'exemple « Réglage d'hyperparamètres » et le tutoriel 6 comparent les deux évaluations.

## 0.5.1 (11 octobre 2026)

- « Créer un Pipeline » réunit le Pipeline et ses étapes en un seul nœud contracté, avec la
  liste des étapes en sous-titre ; un double-clic le déplie. Un Pipeline existant se
  contracte par clic droit › « Contracter le Pipeline ».
- L'inspecteur des nœuds de validation croisée signale un modèle entraîné sur une table
  transformée et propose « Créer le Pipeline et l'utiliser ».
- Quand un transformeur reçoit une colonne texte (souvent la cible), le message d'erreur
  nomme les colonnes en cause et indique la correction.

## 0.5.0 (11 octobre 2026)

- Katanime devient KataML (*Keen-edged Analytics Toolkit for Applied Machine Learning*) :
  paquet Python et commande `kataml`, variables d'environnement `KATAML_*`, groupe
  d'extensions `kataml.extensions`, espace de travail `~/kataml`. Nouveau dépôt :
  <https://gitlab.com/fredbl/kataml>.
- Nouvelle couleur principale, vert sarcelle.
- Thèmes : boîte « Apparence » (mode automatique, clair ou sombre, sept couleurs
  principales ou une couleur personnalisée, fond du canevas) et fichier `theme.css` dans
  l'espace de travail pour redéfinir les couleurs de l'interface et des rapports.

## 0.4.1 (11 octobre 2026)

- Documentation en français et en anglais, publiée sur GitLab Pages, avec captures d'écran
  automatiques et référence des nœuds générée depuis scikit-learn.
- Dix tutoriels et trois nouveaux exemples (fuite d'information, non supervisé, comprendre
  un modèle).
- Exemple « Texte » corrigé : la colonne `note` du fichier d'avis donnait la réponse au
  modèle ; les nouvelles données sont plus réalistes.
- Traductions anglaises complétées.

## 0.4.0 (11 octobre 2026)

- Tous les estimateurs publics de scikit-learn sont disponibles comme nœuds
  (classifieurs, régresseurs, clustering, transformeurs, anomalies, covariance, densité,
  voisins, plongements, méta-estimateurs) ; les exceptions sont justifiées et un test
  vérifie la couverture.
- Le dépôt de nœuds suit le guide de l'utilisateur de scikit-learn (vue *Guide*), ou les
  modules de l'API (vue *API*).
- Interface en anglais au choix, avec des noms proches de ceux de scikit-learn ; rapports
  et ligne de commande bilingues.
- Toutes les stratégies de validation croisée (groupes, séries temporelles, répétitions).

## 0.3.0 (10 octobre 2026)

- Rapports HTML autonomes : schéma, vues des nœuds, blocs « Texte du rapport » en Markdown,
  script en annexe ; impression en PDF ; génération en ligne de commande.
- Blocs personnalisés (« Mes blocs ») : nœuds écrits en Python dans l'éditeur intégré,
  conversion d'un Script Python en bloc, distribution d'extensions sous forme de paquets.

## 0.2.0 (10 octobre 2026)

- Pipeline sans fuite d'information ; méta-estimateurs (vote, empilement, bagging…).
- Comparaison de modèles, test de permutation, courbe de validation.
- Frontières de décision, arbres, dépendance partielle.
- Export en notebook Jupyter, annulation des calculs en cours, cache disque.
- Composants réutilisables, organisation automatique du graphe.
- Texte (TF-IDF), caractéristiques de dates, jeux de données OpenML.

## 0.1.0 (10 octobre 2026)

- Canevas de nœuds, inspecteur, panneau des sorties, nœuds générés depuis scikit-learn.
- Lecture de CSV, manipulations pandas, graphiques, évaluation, recherche
  d'hyperparamètres.
- Export en script Python.
- Versions portables (AppImage, zip Windows) et installation avec uv.
