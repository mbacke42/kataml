// Traduction de l'interface : français par défaut, anglais au choix (bouton FR / EN).
//
// Les textes sont écrits en français dans le code ; en anglais, un observateur du DOM
// remplace les textes et attributs connus (dictionnaire exact + motifs pour les textes
// composés). Les données (tables, code, saisies, noms donnés par l'utilisateur) ne sont
// jamais traduites.
import { LANG } from "./api.js";

export const lang = LANG;

const EN = {
  // Mise à jour disponible
  "KataML {latest} est disponible (vous avez {current}).": "KataML {latest} is available (you have {current}).",
  "Notes de version": "Release notes", "Ignorer": "Dismiss", "Ne plus signaler cette version": "Stop reporting this version",
  // Extensions fournies (Mes blocs)
  "Extensions fournies": "Bundled extensions", "Fournies avec KataML, à activer d'un clic.": "Bundled with KataML, enable with one click.",
  "Extension activée": "Extension enabled", "Extension désactivée": "Extension disabled",
  "Analyse exploratoire": "Exploratory data analysis", "Exemple (préparation)": "Example (preparation)",
  "Vue d'ensemble, valeurs manquantes, fréquences, relation avec la cible, distributions, valeurs extrêmes.":
    "Overview, missing values, frequencies, relationship with the target, distributions, outliers.",
  "Écrêtage des valeurs extrêmes et encodage par fréquence.": "Winsorizing of extreme values and frequency encoding.",
  // Barre d'outils et panneaux
  "Nouveau": "New", "Ouvrir": "Open", "Enregistrer": "Save", "Annotation": "Annotation", "Exporter": "Export",
  "Organiser": "Arrange", "Rapport": "Report", "Réinitialiser": "Reset", "Tout exécuter": "Run all", "Arrêter": "Stop",
  "Nœuds": "Nodes", "Guide": "Guide", "API": "API", "Mes blocs": "My blocks", "Sorties": "Outputs", "Vue": "View",
  "Table": "Table", "Profil": "Profile", "Sans titre": "Untitled",
  "Nouveau workflow": "New workflow", "Ouvrir un workflow ou un exemple": "Open a workflow or an example",
  "Enregistrer (Ctrl+S)": "Save (Ctrl+S)", "Annuler (Ctrl+Z)": "Undo (Ctrl+Z)", "Rétablir (Ctrl+Y)": "Redo (Ctrl+Y)",
  "Ajouter une annotation (A)": "Add an annotation (A)",
  "Exporter en script Python ou en notebook Jupyter": "Export as a Python script or a Jupyter notebook",
  "Générer un rapport HTML (imprimable en PDF)": "Generate an HTML report (printable as PDF)",
  "Organiser automatiquement (L) — la sélection, ou tout le workflow": "Auto-arrange (L) — the selection, or the whole workflow",
  "Réinitialiser tous les nœuds": "Reset all nodes", "Exécuter tout le workflow (Maj+F7)": "Run the whole workflow (Shift+F7)",
  "Arrêter après le nœud en cours": "Stop the running computation", "Aide et raccourcis (F1)": "Help and shortcuts (F1)",
  "Thème clair / sombre": "Light / dark theme", "Quitter KataML (arrête le serveur)": "Quit KataML (stops the server)",
  "Créer et gérer vos propres blocs (extensions)": "Create and manage your own blocks (extensions)",
  "Classement des nœuds": "Node organisation", "Chapitres du guide utilisateur de scikit-learn": "Chapters of the scikit-learn user guide",
  "Modules de l'API scikit-learn (sklearn.linear_model…)": "Modules of the scikit-learn API (sklearn.linear_model…)",
  "Rechercher (ex. forêt, pca, roc)…": "Search (e.g. forest, pca, roc)…",
  "Construisez votre workflow": "Build your workflow",
  "Glissez des nœuds depuis le dépôt de gauche, puis reliez une sortie à une entrée.\n               Double-cliquez un nœud du dépôt pour l'ajouter et le relier au nœud sélectionné.":
    "Drag nodes from the repository on the left, then connect an output to an input. Double-click a node in the repository to add it and connect it to the selected node.",
  "Ouvrir un exemple": "Open an example", "Prise en main": "Getting started",
  "Zoom arrière": "Zoom out", "Zoom avant": "Zoom in", "Zoom 100 %": "Zoom 100 %", "Ajuster à l'écran (F)": "Fit to screen (F)",
  "Agrandir / réduire": "Expand / collapse", "Dépôt de nœuds": "Node repository", "Éditeur de workflow": "Workflow editor",
  "Sorties du nœud": "Node outputs", "Configuration du nœud": "Node configuration", "Actions du workflow": "Workflow actions",
  "Nom du workflow": "Workflow name", "Modifications non enregistrées": "Unsaved changes",
  "Essentiels": "Essentials", "Mes composants": "My components", "Extensions": "Extensions",
  "Aucun nœud ne correspond.": "No matching node.", "résultat(s)": "result(s)",
  // Canevas et nœuds
  "Prêt": "Ready", "Exécution…": "Running…", "En attente…": "Queued…", "modèle entraîné": "fitted model",
  "vue disponible": "view available", "Exécuter (F7)": "Run (F7)", "Exécuter le composant (F7)": "Run the component (F7)",
  "Double-clic pour modifier": "Double-click to edit", "Annotation\nDouble-cliquez pour modifier.": "Annotation\nDouble-click to edit.",
  "Glisser pour déplacer le composant": "Drag to move the component", "Réduire": "Collapse", "Déplier": "Expand",
  "Réduire en un seul nœud": "Collapse into a single node", "Exécuté": "Executed",
  "Ajouter un nœud…": "Add a node…", "Ajouter une annotation": "Add an annotation", "Coller": "Paste",
  "Tout sélectionner": "Select all", "Ajuster à l'écran": "Fit to screen", "Supprimer la connexion": "Delete connection",
  "Modifier le texte": "Edit text", "Couleur": "Colour", "Jaune": "Yellow", "Bleu": "Blue", "Vert": "Green", "Rose": "Pink", "Gris": "Grey",
  "Supprimer": "Delete", "Copier": "Copy", "Dupliquer": "Duplicate", "Configurer": "Configure",
  "Exécuter": "Run", "Exécuter jusqu'en aval": "Run downstream", "Afficher la vue": "Show view",
  "Grouper en composant": "Group as component", "Créer un Pipeline": "Create a Pipeline", "Organiser la sélection": "Arrange selection",
  "Convertir en bloc réutilisable…": "Convert into a reusable block…",
  "Exécuter le composant": "Run the component", "Renommer…": "Rename…",
  "Enregistrer comme composant réutilisable…": "Save as reusable component…", "Dissocier": "Ungroup",
  // Inspecteur
  "Configuration": "Configuration", "Description": "Description", "Paramètres": "Parameters", "Données": "Data",
  "Hyperparamètres": "Hyperparameters", "Validation croisée": "Cross-validation", "Avancés": "Advanced",
  "Non configuré": "Not configured", "Configuré": "Configured", "Erreur": "Error", "En cours": "Running", "En attente": "Queued",
  "Réinit.": "Reset", "Réinitialiser (F8)": "Reset (F8)", "défaut": "default", "Cliquer pour développer": "Click to expand",
  "Annotation du nœud (ex. « modèle final »)": "Node annotation (e.g. “final model”)",
  "Aucun nœud sélectionné": "No node selected",
  "Sélectionnez un nœud pour le configurer et lire sa documentation.": "Select a node to configure it and read its documentation.",
  "Exécutez-les avec F7, supprimez-les avec Suppr ou copiez-les avec Ctrl+C.": "Run them with F7, delete them with Del or copy them with Ctrl+C.",
  "Glissez un nœud du dépôt sur le canevas, ou double-cliquez sur le canevas pour en chercher un.": "Drag a node from the repository onto the canvas, or double-click the canvas to search for one.",
  "Tirez une connexion depuis une sortie ▸ vers une entrée. Relâchée dans le vide, elle propose les nœuds compatibles.": "Drag a connection from an output ▸ to an input. Dropped on empty space, it offers compatible nodes.",
  "Les feux indiquent l'état : rouge = à configurer, orange = prêt, vert = exécuté.": "Traffic lights show the state: red = needs configuration, orange = ready, green = executed.",
  "Cliquez sur une sortie d'un nœud exécuté pour voir la table ou le modèle.": "Click an output of an executed node to see its table or model.",
  "Modèle": "Model", "Ce nœud n'a aucun paramètre.": "This node has no parameters.",
  "Documentation scikit-learn": "scikit-learn documentation", "Entrées": "Inputs", "table": "table", "modèle": "model", "optionnel": "optional",
  "Colonnes inconnues : le nœud amont n'est pas exécuté.": "Unknown columns: the upstream node has not been executed.",
  "Connectez d'abord une table en entrée.": "Connect an input table first.", "Charger": "Load",
  "col1, col2…": "col1, col2…", "nom de colonne": "column name", "(aucune)": "(none)", "— choisir —": "— choose —",
  "Filtrer…": "Filter…", "Tout": "All", "Aucun": "None", "Num.": "Num.", "Tout cocher (filtrées)": "Check all (filtered)",
  "Tout décocher": "Uncheck all", "Cocher les colonnes numériques": "Check numeric columns", "Aucune sélection": "No selection",
  "Aucune sélection : toutes les colonnes utilisables": "No selection: all usable columns",
  "Chargement…": "Loading…", "Aucun fichier importé": "No imported file", "— choisir un fichier importé —": "— choose an imported file —",
  "Importer": "Import", "Importer un fichier CSV dans workspace/data": "Import a CSV file into workspace/data",
  "…ou chemin absolu /chemin/vers/fichier.csv": "…or absolute path /path/to/file.csv", "Oui": "Yes", "Non": "No",
  "(par défaut)": "(default)", "(absente)": "(missing)", "Langue : français / English": "Language: français / English", "Glissez ce nœud sur le canevas, ou double-cliquez pour l'ajouter.": "Drag this node onto the canvas, or double-click to add it.",
  "Nœuds du composant": "Component nodes", "Enregistrer comme composant": "Save as component",
  "Les ports du composant sont les entrées et sorties de ses nœuds qui ne sont pas reliées à l'intérieur du groupe. Enregistré, il apparaît dans le dépôt (« Mes composants ») et se réutilise dans d'autres workflows.":
    "The component's ports are the inputs and outputs of its nodes that are not connected inside the group. Once saved, it appears in the repository (“My components”) and can be reused in other workflows.",
  "Afficher et configurer ce nœud": "Show and configure this node",
  // Sorties
  "Sélectionnez un nœud exécuté pour afficher ses tables, son modèle ou sa vue.": "Select an executed node to show its tables, model or view.",
  "Exécution en cours…": "Running…", "Ce nœud n'a pas de sortie.": "This node has no output.", "Erreur : ": "Error: ",
  "Début": "First", "Précédent": "Previous", "Suivant": "Next", "Fin": "Last",
  "Estimateur": "Estimator", "Type": "Type", "Cible": "Target", "Variables": "Features", "Colonnes transformées": "Transformed columns",
  "Classes": "Classes", "Colonnes produites": "Output columns", "Représentation Python": "Python representation",
  "Classifieur": "Classifier", "Régresseur": "Regressor", "Clustering": "Clustering", "Transformeur": "Transformer",
  "Par composante": "Per component", "Cumulée": "Cumulative", "Feuille": "Leaf", "oui": "yes", "non": "no",
  // Boîtes de dialogue
  "Fermer (Échap)": "Close (Esc)", "Annuler": "Cancel", "Valider": "OK", "Confirmer": "Confirm", "Continuer": "Continue",
  "Ouvrir un workflow": "Open a workflow", "Exemples": "Examples", "Mes workflows (workspace/workflows)": "My workflows (workspace/workflows)",
  "Aucun workflow enregistré pour l'instant.": "No saved workflow yet.", "Importer un fichier .json": "Import a .json file", "Importer un script Python (.py)": "Import a Python script (.py)",
  "Ajouter": "Add",
  "Plus tard": "Later",
  "Fichier": "File",
  "Au canevas": "To canvas",
  "Voir / modifier": "View / edit",
  "Enregistré.": "Saved.",
  "Données et scripts : fichiers de données, bases SQLite et bibliothèque de scripts Python": "Data and scripts: data files, SQLite databases and Python script library",
  "Données et scripts": "Data and scripts",
  "Rassemblez ici les données et les scripts d'un projet. Déposez des fichiers dans cette fenêtre, ou importez tout un dossier : les scripts rejoignent la bibliothèque, les données utiles sont importées au moment de créer le schéma.": "Gather a project's data and scripts here. Drop files in this window, or import a whole folder: scripts join the library, and the data files that are needed are imported when the workflow is created.",
  "Données (workspace/data)": "Data (workspace/data)",
  "CSV, Parquet, Excel ou base SQLite. Pour PostgreSQL ou MySQL, ajoutez un nœud « Lecteur SQL ».": "CSV, Parquet, Excel or SQLite database. For PostgreSQL or MySQL, add a “SQL reader” node.",
  "Aucun fichier pour l'instant.": "No file yet.",
  "Scripts (workspace/scripts)": "Scripts (workspace/scripts)",
  "Cochez le ou les scripts à convertir. Les autres servent de modules s'ils sont importés (constantes, fonctions).": "Tick the script(s) to convert. The others are used as modules when imported (constants, functions).",
  "Aucun script. Ajoutez vos fichiers .py ou partez d'un modèle avec « Nouveau ».": "No script. Add your .py files or start from a template with “New”.",
  "Importer un dossier de projet": "Import a project folder",
  "Choisir le dossier d'un projet : scripts .py et fichiers de données (les dossiers .venv, .git… sont ignorés)": "Choose a project folder: .py scripts and data files (.venv, .git… folders are ignored)",
  "Crée le lecteur adapté sur le canevas": "Creates the matching reader on the canvas",
  "Retirer de workspace/data": "Remove from workspace/data",
  "Retirer le fichier": "Remove the file",
  "Retirer le script": "Remove the script",
  "Retirer de la bibliothèque": "Remove from the library",
  "Script à convertir en schéma": "Script to convert into a workflow",
  "Créer le schéma": "Create the workflow",
  "Données à importer": "Data to import",
  "Le schéma lit ces fichiers, qui ne sont pas encore dans workspace/data :": "The workflow reads these files, which are not in workspace/data yet:",
  "Importez-les maintenant (même nom de fichier), ou plus tard en les déposant sur le canevas ou depuis la fenêtre « Données ».": "Import them now (same file name), or later by dropping them on the canvas or from the “Data” window.",
  "Importer ces fichiers": "Import these files",
  "Enregistrer et créer le schéma": "Save and create the workflow",
  "Nouveau script": "New script",
  "Nom du fichier": "File name",
  "Importer une base SQLite dans workspace/data": "Import a SQLite database into workspace/data",
  "…ou URL : postgresql+psycopg://utilisateur@hote/base, ou $DATABASE_URL": "…or URL: postgresql+psycopg://user@host/db, or $DATABASE_URL", "Importer un fichier Parquet ou Excel dans workspace/data": "Import a Parquet or Excel file into workspace/data", "…ou chemin absolu /chemin/vers/fichier.parquet": "…or absolute path /path/to/file.parquet",
  "Reconstruit le schéma à partir d'un script pandas / scikit-learn. Sélectionnez aussi les modules qu'il importe (constantes, fonctions).": "Rebuilds the workflow from a pandas / scikit-learn script. Also select the modules it imports (constants, functions).",
  "Exporter le workflow courant (.json)": "Export the current workflow (.json)",
  "Les modifications non enregistrées seront perdues.": "Unsaved changes will be lost.",
  "Enregistrer le workflow": "Save workflow", "Nom (enregistré dans workspace/workflows)": "Name (saved in workspace/workflows)",
  "Exporter en Python": "Export to Python", "Copier ": "Copy ",
  "Le workflow est reproduit avec pandas et scikit-learn uniquement. Le notebook Jupyter contient une cellule par nœud ; les annotations deviennent du texte.":
    "The workflow is reproduced with pandas and scikit-learn only. The Jupyter notebook has one cell per node; annotations become text.",
  "Prise en main de KataML": "Getting started with KataML",
  "Dans KataML, un workflow est un graphe de nœuds reliés par des ports. Chaque nœud se configure, s'exécute, puis expose ses sorties. Tout le calcul repose sur pandas et scikit-learn ; chaque workflow s'exporte en script Python.":
    "In KataML, a workflow is a graph of nodes connected by ports. Each node is configured, executed, then exposes its outputs. All computation relies on pandas and scikit-learn; every workflow can be exported as a Python script.",
  "À configurer ou en erreur": "Needs configuration or failed", "Configuré, prêt à exécuter": "Configured, ready to run",
  "Port table (DataFrame)": "Table port (DataFrame)", "Port modèle (estimateur ajusté)": "Model port (fitted estimator)",
  "Démarche type": "Typical steps", "Raccourcis": "Shortcuts",
  "Lire les données (Lecteur CSV ou Jeu de données scikit-learn).": "Load data (CSV reader or scikit-learn dataset).",
  "Explorer (Statistiques, Nuage de points, Corrélations).": "Explore (Statistics, Scatter plot, Correlations).",
  "Partitionner en apprentissage / test.": "Split into train / test (train_test_split).",
  "Prétraiter (StandardScaler, OneHotEncoder…) et appliquer le même transformeur au test.": "Preprocess (StandardScaler, OneHotEncoder…) and apply the same transformer to the test set.",
  "Entraîner un modèle, le connecter à un Prédicteur avec la table de test.": "Fit a model and connect it to a Predictor with the test table.",
  "Pour une évaluation sans fuite, regrouper prétraitements et modèle dans un nœud Pipeline (clic droit sur la sélection → « Créer un Pipeline »).":
    "For leak-free evaluation, group preprocessing and model in a Pipeline node (right-click the selection → “Create a Pipeline”).",
  "Évaluer (Évaluation classification / régression, Courbe ROC, Validation croisée, Comparer des modèles).":
    "Evaluate (classification / regression metrics, ROC curve, cross-validation, model comparison).",
  "Comprendre le modèle (Frontière de décision, Visualiser l'arbre, Dépendance partielle, Importance).":
    "Understand the model (decision boundary, tree plot, partial dependence, importance).",
  "Exécuter la sélection": "Run selection", "Réinitialiser la sélection": "Reset selection", "Nouvelle annotation": "New annotation",
  "Chercher et ajouter un nœud": "Search and add a node", "Organiser automatiquement": "Auto-arrange", "Générer un rapport": "Generate a report",
  "Créer vos propres blocs": "Create your own blocks", "Molette": "Wheel", "Zoomer": "Zoom", "Glisser le fond": "Drag background",
  "Se déplacer": "Pan", "Maj": "Shift", "glisser": "drag", "Sélection rectangulaire": "Rectangle selection", "Alt": "Alt",
  "Déplacer sans grille": "Move without grid", "Double-clic": "Double-click", "Suppr": "Del",
  "Rapports, blocs personnalisés, ligne de commande": "Reports, custom blocks, command line",
  "« Rapport » produit un fichier HTML autonome (imprimable en PDF) avec le schéma du workflow, les vues des nœuds choisis et les blocs « Texte du rapport ». « Mes blocs » permet d'écrire vos propres nœuds en Python, ou de convertir un nœud Script Python en bloc réutilisable. Sans interface : kataml run workflow.json --rapport rapport.html.":
    "“Report” produces a standalone HTML file (printable as PDF) with the workflow diagram, the views of the selected nodes and the “Report text” blocks. “My blocks” lets you write your own nodes in Python, or convert a Python script node into a reusable block. Without the interface: kataml run workflow.json --rapport report.html.",
  "Les fichiers importés sont copiés dans workspace/data ; les workflows enregistrés vont dans workspace/workflows et les exports dans workspace/exports. Vous pouvez aussi glisser un fichier CSV directement sur le canevas.":
    "Imported files are copied to workspace/data; saved workflows go to workspace/workflows and exports to workspace/exports. You can also drop a CSV file directly onto the canvas.",
  "Quitter KataML": "Quit KataML", "Quitter": "Quit", "Documentation complète et tutoriels": "Full documentation and tutorials",
  "Le serveur KataML va s'arrêter. Vous pourrez fermer cet onglet.": "The KataML server will stop. You can then close this tab.",
  "Le workflow courant reste sauvegardé dans ce navigateur, mais n'est pas enregistré dans l'espace de travail. Arrêter quand même ?":
    "The current workflow stays saved in this browser but is not saved in the workspace. Quit anyway?",
  "KataML est arrêté": "KataML has stopped",
  "Vous pouvez fermer cet onglet. Relancez l'application pour reprendre : le dernier workflow sera restauré.": "You can close this tab. Restart the application to continue: the last workflow will be restored.",
  "Grouper": "Group", "Nom du composant": "Component name", "Composant": "Component",
  "Composant réutilisable": "Reusable component", "Nom (enregistré dans workspace/components)": "Name (saved in workspace/components)",
  "Renommer le composant": "Rename component", "Nom": "Name", "Supprimer le composant": "Delete component",
  // Rapport
  "Générer le rapport": "Generate report", "Titre": "Title", "Auteur": "Author", "Facultatif": "Optional",
  "Schéma du workflow": "Workflow diagram", "Annotations": "Annotations", "Aperçu des tables (nœuds sans vue)": "Table previews (nodes without a view)",
  "Script Python en annexe": "Python script appendix", "Contenu et ordre des sections": "Content and order of sections",
  "Ajoutez des blocs « Texte du rapport » pour commenter.": "Add “Report text” blocks to comment.",
  "Monter": "Move up", "Descendre": "Move down", "texte": "text", "exécuté": "executed", "à exécuter": "to run",
  "incomplet": "incomplete", "erreur": "error", "en cours": "running", "en attente": "queued",
  "Rapports récents (workspace/reports)": "Recent reports (workspace/reports)", "Rapport prêt": "Report ready",
  "Télécharger": "Download", "Ouvrir le rapport": "Open report", "Imprimer / PDF": "Print / PDF",
  "Annexe : script Python équivalent": "Appendix: equivalent Python script", "Reproduit le workflow avec pandas et scikit-learn.": "Reproduces the workflow with pandas and scikit-learn.",
  "Nœud non exécuté au moment de la génération du rapport.": "Node not executed when the report was generated.",
  // Mes blocs
  "Nouveau bloc": "New block", "Recharger": "Reload", "Modifier": "Edit", "Retour": "Back", "Créer": "Create",
  "Aucun bloc personnalisé pour l'instant.": "No custom block yet.", "Extensions installées (paquets Python)": "Installed extensions (Python packages)",
  "Écrivez vos propres nœuds en Python : ils apparaissent dans le dépôt comme les autres. Chaque bloc est un fichier de ": "Write your own nodes in Python: they appear in the repository like the others. Each block is a file of ",
  ". Partez d'un modèle commenté, ou convertissez un nœud « Script Python » (clic droit sur le nœud).": ". Start from a commented template, or convert a “Python script” node (right-click the node).",
  "Une table": "One table", "Deux tables": "Two tables", "Un modèle et une table": "A model and a table", "Aucune (bloc source)": "None (source block)",
  "Ce que fait le bloc (affiché dans la description)": "What the block does (shown in the description)",
  "Un fichier Python commenté est créé ; vous le complétez ensuite dans l'éditeur.": "A commented Python file is created; you then complete it in the editor.",
  "Retour à la liste": "Back to the list", "Enregistrer et recharger (Ctrl+S)": "Save and reload (Ctrl+S)",
  "Convertir en bloc réutilisable": "Convert into a reusable block", "Nom du bloc": "Block name", "Convertir": "Convert",
  "Supprimer le bloc": "Delete block", "Blocs rechargés": "Blocks reloaded",
  "Le bloc a été créé mais ne se charge pas : ouvrez « Mes blocs ».": "The block was created but does not load: open “My blocks”.",
  // Messages
  "Copié": "Copied", "Copie impossible": "Copy failed", "Le workflow est vide.": "The workflow is empty.",
  "Une exécution est déjà en cours.": "A run is already in progress.", "Tout est déjà exécuté.": "Everything is already executed.",
  "Exécution arrêtée.": "Run stopped.", "Arrêt demandé.": "Stop requested.", "Calcul interrompu ; le moteur redémarre…": "Computation interrupted; the engine restarts…",
  "Workflow réinitialisé": "Workflow reset", "Fichier JSON invalide.": "Invalid JSON file.", "JSON invalide": "Invalid JSON",
  "Sélectionnez au moins deux nœuds.": "Select at least two nodes.", "Échec de l'import": "Import failed",
  "Type de nœud inconnu": "Unknown node type", "Nouveau workflow ": "New workflow ",
  "{n} nœuds · composant": "{n} nodes · component",
  "Colonnes absentes de la table d'entrée retirées de la configuration : {list} (Ctrl+Z pour annuler)":
    "Columns missing from the input table removed from the configuration: {list} (Ctrl+Z to undo)",
  "{n} nœud(s) à reconfigurer après le retrait de colonnes absentes : non exécuté(s).":
    "{n} node(s) to reconfigure after removing missing columns: not run.",
  // Pipeline et validation croisée
  "Le modèle « {model} » a été entraîné sur la sortie de {preps}. La validation croisée réentraîne le modèle sur chaque pli, mais pas ce prétraitement : il a vu toutes les données (fuite d'information). Réunissez-les dans un Pipeline.":
    "The model “{model}” was trained on the output of {preps}. Cross-validation refits the model on each fold, but not this preprocessing: it has seen all the data (data leakage). Combine them in a Pipeline.",
  "Créer le Pipeline et l'utiliser": "Create and use the Pipeline",
  "Pipeline créé et branché sur la validation croisée": "Pipeline created and connected to the cross-validation",
  "Pipeline créé et contracté : double-clic pour voir ses étapes": "Pipeline created and collapsed: double-click to see its steps",
  "Contracter le Pipeline": "Collapse the Pipeline", "Pipeline contracté": "Collapsed Pipeline",
  // Apparence
  "Apparence": "Appearance", "Apparence : couleurs, mode, canevas": "Appearance: colours, mode, canvas",
  "Automatique": "Automatic", "Clair": "Light", "Sombre": "Dark",
  "« Automatique » suit le réglage clair / sombre du système.": "“Automatic” follows the system's light / dark setting.",
  "Couleur principale": "Main colour", "Par défaut": "Default", "Sarcelle": "Teal", "Framboise": "Raspberry", "Ardoise": "Slate",
  "Personnalisée": "Custom", "Couleur personnalisée": "Custom colour",
  "Boutons, sélection, liens et onglets actifs. La couleur des familles de nœuds ne change pas.": "Buttons, selection, links and active tabs. Node family colours do not change.",
  "Fond du canevas": "Canvas background", "Points": "Dots", "Grille": "Grid", "Uni": "Plain", "Fermer": "Close",
  "Pour aller plus loin, un fichier theme.css placé dans l'espace de travail peut redéfinir toutes les couleurs de l'interface et des rapports (variables CSS).": "To go further, a theme.css file placed in the workspace can redefine every colour of the interface and reports (CSS variables).",
};

// Textes composés : [motif, remplacement].
const PATTERNS = [
  [/^Créer le schéma \((\d+) scripts?\)$/, "Create the workflow ($1 script(s))"],
  [/^(.+) · repéré dans le dossier, pas encore importé$/, "$1 · found in the folder, not imported yet"],
  [/^(.+) · script principal \(if __name__ == "__main__"\)$/, "$1 · main script (if __name__ == \"__main__\")"],
  [/^Supprimer (.+) de workspace\/data \? Les nœuds qui le lisent ne trouveront plus le fichier\.$/, "Delete $1 from workspace/data? Nodes reading it will no longer find the file."],
  [/^Supprimer (.+) de la bibliothèque de scripts \?$/, "Delete $1 from the script library?"],
  [/^(\d+) script\(s\) ajouté\(s\) à la bibliothèque, (\d+) fichier\(s\) de données repéré\(s\)\.$/, "$1 script(s) added to the library, $2 data file(s) found."],
  [/^Import de (\d+) fichier\(s\) de données du dossier…$/, "Importing $1 data file(s) from the folder…"],
  [/^(\d+) nœuds reconstruits — (\d+) point\(s\) à vérifier \(voir la note sur le canevas\)\.$/, "$1 nodes rebuilt — $2 point(s) to check (see the note on the canvas)."],
  [/^(\d+) nœuds reconstruits à partir du script\.$/, "$1 nodes rebuilt from the script."],
  [/^Paramètre « (.+) » requis$/, "Parameter “$1” required"], [/^Entrée « (.+) » non connectée$/, "Input “$1” not connected"],
  [/^modèle entraîné · (.+)$/, "fitted model · $1"], [/^vue disponible · (.+)$/, "view available · $1"],
  [/^(\d+) nœud\(s\) exécuté\(s\) en ([\d.]+) s$/, "$1 node(s) run in $2 s"],
  [/^(\d+) nœud\(s\) non configuré\(s\) ignoré\(s\)\.$/, "$1 unconfigured node(s) skipped."],
  [/^(\d+) nœud\(s\) de type inconnu \(version de scikit-learn différente \?\)$/, "$1 node(s) of unknown type (different scikit-learn version?)"],
  [/^(\d+) nœuds sélectionnés$/, "$1 nodes selected"], [/^(\d+) sélectionnée\(s\)$/, "$1 selected"],
  [/^(\d+) nœuds · composant$/, "$1 nodes · component"], [/^(\d+)\/(\d+) exécutés$/, "$1/$2 executed"],
  [/^(\d+) nœuds$/, "$1 nodes"], [/^Composant · (\d+) nœuds$/, "Component · $1 nodes"],
  [/^(.+) — composant de (\d+) nœuds \(double-clic pour déplier\)$/, "$1 — component of $2 nodes (double-click to expand)"],
  [/^Sortie : (.+) — clic pour afficher$/, "Output: $1 — click to show"],
  [/^Exécuter \((\d+)\)$/, "Run ($1)"], [/^Sortie : (.+)$/, "Output: $1"], [/^Télécharger : (.+)$/, "Download: $1"],
  [/^Entrée : (.+)$/, "Input: $1"],
  [/^Enregistré : (.+)$/, "Saved: $1"], [/^« (.+) » ouvert$/, "“$1” opened"], [/^« (.+) » importé dans workspace\/data$/, "“$1” imported into workspace/data"],
  [/^Composant « (.+) » ajouté au dépôt \(Mes composants\)$/, "Component “$1” added to the repository (My components)"],
  [/^Extension\(s\) en erreur : (.+) — voir « Mes blocs »$/, "Extension(s) failing: $1 — see “My blocks”"],
  [/^Script (.+)\.py$/, "Script $1.py"], [/^Notebook (.+)\.ipynb$/, "Notebook $1.ipynb"],
  [/^Exécution de (\d+) nœud\(s\) avant le rapport…$/, "Running $1 node(s) before the report…"],
  [/^« (.+) » n'est pas encore exécuté\. $/, "“$1” has not been executed yet. "],
  [/^(.+) lignes · (\d+) colonnes$/, "$1 rows · $2 columns"], [/^(.+) valeurs distinctes · (.+)$/, "$1 distinct values · $2"],
  [/^(.+) manquantes$/, "$1 missing"], [/^aucune manquante$/, "none missing"], [/^(\d+) modalité\(s\) principales$/, "$1 main categories"],
  [/^Hyperparamètres \((\d+)\)$/, "Hyperparameters ($1)"], [/^Attributs appris \((\d+)\)$/, "Fitted attributes ($1)"],
  [/^Filtrer (\d+) hyperparamètres…$/, "Filter $1 hyperparameters…"], [/^Tout réinitialiser \((\d+)\)$/, "Reset all ($1)"],
  [/^Revenir à la valeur par défaut \((.+)\)$/, "Back to default ($1)"], [/^(.+)  \(défaut\)$/, "$1  (default)"],
  [/^(.+) \(absente\)$/, "$1 (missing)"], [/^Bloc personnalisé · extension « (.+) »$/, "Custom block · extension “$1”"],
  [/^Modifier (.+\.py)$/, "Edit $1"], [/^Enregistré et rechargé : (\d+) nœud\(s\)\.$/, "Saved and reloaded: $1 node(s)."],
  [/^(.+\.py) · (\d+) nœud\(s\)(.*)$/, "$1 · $2 node(s)$3"], [/^(\d+) nœud\(s\) · (.+)$/, "$1 node(s) · $2"],
  [/^Supprimer (.+\.py) \? Les nœuds de ce type deviendront inconnus\.$/, "Delete $1? Nodes of this type will become unknown."],
  [/^Bloc « (.+) » créé dans « Mes blocs » et utilisé à la place du script$/, "Block “$1” created in “My blocks” and used instead of the script"],
  [/^« (.+) » est enregistré dans workspace\/reports\. (.*)$/, "“$1” is saved in workspace/reports. Open it in a new tab to read or print it as PDF, or download it: it is a standalone HTML file that works offline."],
  [/^Rapport généré par KataML le (.+)\.$/, "Report generated by KataML on $1."], [/^Auteur : (.+)$/, "Author: $1"],
  [/^Workflow « (.+) »$/, "Workflow “$1”"], [/^Supprimer « (.+) » du dépôt \? (.*)$/, "Delete “$1” from the repository? Workflows using it are not modified."],
];

export function t(s, vars) {
  let out = LANG === "en" ? translate(s) : s;
  if (vars) for (const [k, v] of Object.entries(vars)) out = out.replaceAll(`{${k}}`, v);
  return out;
}

function translate(s) {
  if (typeof s !== "string" || !s.trim()) return s;
  if (EN[s] !== undefined) return EN[s];
  const trimmed = s.trim();
  if (EN[trimmed] !== undefined) return s.replace(trimmed, EN[trimmed]);
  for (const [re, rep] of PATTERNS) {
    if (rep !== null && re.test(trimmed)) return s.replace(trimmed, trimmed.replace(re, rep));
  }
  return s;
}

// Zones jamais traduites : données, code, saisies, noms choisis par l'utilisateur.
const SKIP = ".dtable, pre, code, textarea, input, [data-raw], .node .label, .node .title, .repo-item .nm, .wf-name input, [data-raw], .markdown, .err, .insp-error";
const ATTRS = ["title", "placeholder", "aria-label"];

function translateTree(root) {
  if (root.nodeType === Node.TEXT_NODE) {
    if (!root.parentElement?.closest(SKIP)) {
      const next = translate(root.nodeValue);
      if (next !== root.nodeValue) root.nodeValue = next;
    }
    return;
  }
  if (root.nodeType !== Node.ELEMENT_NODE) return;
  const tag = root.tagName;
  if (root.matches?.(SKIP) && tag !== "INPUT" && tag !== "TEXTAREA") return;
  for (const a of ATTRS) {
    const v = root.getAttribute?.(a);
    if (v) { const next = translate(v); if (next !== v) root.setAttribute(a, next); }
  }
  if (tag === "INPUT" || tag === "TEXTAREA") return;   // seuls les attributs, jamais la valeur
  for (const child of root.childNodes) translateTree(child);
}

export function startTranslation() {
  if (LANG !== "en") return;
  document.documentElement.lang = "en";
  translateTree(document.body);
  new MutationObserver((records) => {
    for (const r of records) {
      if (r.type === "characterData") translateTree(r.target);
      else if (r.type === "attributes") translateTree(r.target);
      else r.addedNodes.forEach(translateTree);
    }
  }).observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRS });
}
