# Questions fréquentes

## Utilisation

??? question "Un nœud reste rouge : que faire ?"
    Lisez sa ligne d'information, ou l'inspecteur : le message indique le paramètre
    obligatoire manquant (« Paramètre « Colonne cible » requis ») ou l'entrée non connectée.
    Après une erreur d'exécution, le message complet est affiché dans l'inspecteur.

??? question "« Les variables doivent être numériques »"
    Les modèles de scikit-learn n'acceptent que des nombres. Encodez les colonnes de texte
    (**OneHotEncoder**, **OrdinalEncoder**), vectorisez le texte libre (**TfidfVectorizer**),
    extrayez les éléments des dates (**Caractéristiques de dates**), ou excluez ces colonnes
    des **Variables explicatives**. Voir le [tutoriel 3](tutorials/03-csv-cleaning.md).

??? question "« StandardScaler n'accepte que des colonnes numériques »"
    Sans colonnes choisies, un transformeur s'applique à toutes les colonnes, y compris la
    cible si elle est textuelle (`species`…). Indiquez la cible dans son champ **Cible**,
    choisissez les **Colonnes à transformer**, ou encodez d'abord les colonnes texte
    (**OneHotEncoder**). Le message nomme les colonnes en cause.

??? question "Comment faire une validation croisée sur StandardScaler + un modèle ?"
    Réunissez-les dans un **Pipeline** et branchez celui-ci sur la validation croisée, avec
    la table brute : voir [Le Pipeline](concepts/pipeline.md). Si vous branchez directement
    le modèle, l'inspecteur de la validation croisée propose **Créer le Pipeline et
    l'utiliser**.

??? question "Comment faire une validation croisée imbriquée ?"
    Branchez la sortie **Recherche (configuration)** du nœud **Recherche d'hyperparamètres**
    sur une **Validation croisée** : voir [Validation croisée imbriquée](concepts/cross-validation.md#validation-croisee-imbriquee).

??? question "« Valeurs manquantes »"
    La plupart des estimateurs refusent les `NaN`. Utilisez **SimpleImputer** (ou
    **KNNImputer**, **IterativeImputer**) dans un Pipeline, supprimez les lignes avec
    **Lignes incomplètes**, ou choisissez un modèle qui les accepte
    (**HistGradientBoostingClassifier / Regressor**).

??? question "Le résultat ne change pas quand je modifie mon fichier CSV"
    Le cache tient compte de la date de modification du fichier : réexécutez le Lecteur
    CSV. Si le fichier a été remplacé par une copie à la même date, utilisez
    **Réinit.** (++f8++) sur le nœud.

??? question "Mon score d'apprentissage est de 100 %, est-ce bien ?"
    Non, pas en soi : c'est souvent le signe d'un modèle qui a appris par cœur. Seul le
    score sur des données non vues (test, validation croisée) compte. Voir le
    [tutoriel 5](tutorials/05-overfitting.md).

??? question "Quelle différence entre Partitionnement et Validation croisée ?"
    Le partitionnement fait **un** découpage apprentissage / test : simple, mais le score
    de test dépend du hasard du découpage. La validation croisée en fait **plusieurs** et
    donne une moyenne et un écart-type. On combine souvent les deux : validation croisée
    sur l'apprentissage pour choisir, test final pour confirmer.

??? question "Un calcul est trop long"
    **Arrêter** (barre d'outils) l'interrompt immédiatement. Réduisez la taille des
    données (**Échantillonnage**), le nombre de plis, la taille de la grille (ou passez en
    recherche aléatoire), ou réglez `n_jobs` = `-1` sur les modèles qui le proposent pour
    utiliser tous les cœurs.

??? question "Où sont mes fichiers ?"
    Dans l'espace de travail, dont le chemin est affiché au démarrage dans le terminal
    (« Espace de travail : … ») ; la boîte **Mes blocs** affiche aussi le dossier des
    blocs. Voir [Espace de travail](concepts/workspace.md).

## scikit-learn

??? question "Tout scikit-learn est-il disponible ?"
    Tous les estimateurs publics de scikit-learn sont des nœuds, à l'exception de ceux qui
    n'ont pas de sens comme nœud autonome ; chacune de ces exceptions est justifiée dans la
    [référence](reference/index.md#excluded) (par exemple
    `GridSearchCV` est un nœud dédié, `Pipeline` aussi). Un test automatique vérifie cette
    couverture à chaque version de scikit-learn.

??? question "Quelle version de scikit-learn est utilisée ?"
    Celle de l'environnement : elle est affichée en bas du dépôt, au démarrage dans le
    terminal et dans l'en-tête des rapports. Les nœuds, leurs hyperparamètres et leurs aides sont lus dans scikit-learn
    au démarrage : ils suivent la version installée.

??? question "Puis-je utiliser XGBoost, LightGBM, SHAP… ?"
    Pas directement : KataML ne dépend que de scikit-learn et pandas. Mais un
    [bloc personnalisé](blocks.md) peut utiliser n'importe quelle bibliothèque installée
    dans le même environnement (par exemple `uv tool install … --with xgboost`).

## Installation et sécurité

??? question "Faut-il une connexion Internet ?"
    Non, sauf pour installer KataML et pour le nœud **Jeu de données OpenML** (premier
    téléchargement d'un jeu). Les jeux de données intégrés de scikit-learn sont inclus.
    L'interface interroge aussi GitLab au plus une fois par jour pour signaler une version
    plus récente ; cet appel échoue en silence hors ligne et se désactive (voir ci-dessous).

??? question "Mes données sont-elles envoyées quelque part ?"
    Non. Le serveur tourne sur votre machine et n'écoute que sur `127.0.0.1` ; les
    requêtes doivent porter un jeton généré au démarrage. Vos tables et vos workflows ne
    quittent jamais votre machine. La seule requête sortante est la vérification de version :
    un appel à l'API publique de GitLab, avec un User-Agent générique (nom de l'outil et URL
    du projet), sans aucune donnée personnelle. Pour la désactiver, lancez KataML avec la
    variable d'environnement `KATAML_NO_UPDATE_CHECK=1`.

??? question "Puis-je installer KataML sur un serveur pour une classe ?"
    On peut le faire avec `--host 0.0.0.0`, mais c'est déconseillé hors d'un réseau de confiance :
    le nœud Script Python et les blocs personnalisés exécutent du code sur le serveur, et
    tous les utilisateurs partageraient le même espace de travail. Préférez une
    installation par poste (versions portables ou uv).

??? question "Le port 8765 est déjà pris"
    KataML prend automatiquement le port libre suivant (et l'affiche). Vous pouvez aussi
    choisir : `kataml --port 9000`.

??? question "Le navigateur ne s'ouvre pas"
    Ouvrez l'adresse affichée dans le terminal (elle contient le jeton d'accès). Avec
    `--no-browser`, c'est le comportement attendu.
