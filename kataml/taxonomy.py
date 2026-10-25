"""Classement des nœuds, calqué sur le guide utilisateur de scikit-learn.

Chaque nœud reçoit une *section* (chapitre du guide : apprentissage supervisé,
non supervisé, sélection et évaluation de modèles, inspection, transformations de
données…) et une *famille* (section du guide : modèles linéaires, ensembles,
clustering…). Les libellés existent en français et en anglais.
"""

from __future__ import annotations

# Ordre d'affichage et libellés (fr, en) des sections.
SECTIONS = {
    "data": ("Données", "Dataset loading"),
    "manip": ("Manipulation (pandas)", "Data manipulation (pandas)"),
    "viz": ("Visualisation", "Visualization"),
    "transform": ("Transformations de données", "Dataset transformations"),
    "supervised": ("Apprentissage supervisé", "Supervised learning"),
    "unsupervised": ("Apprentissage non supervisé", "Unsupervised learning"),
    "predict": ("Prédiction", "Prediction"),
    "model_selection": ("Sélection et évaluation de modèles", "Model selection and evaluation"),
    "inspection": ("Inspection", "Inspection"),
    "report": ("Rapport", "Report"),
}

# Anciennes catégories (et noms courants) acceptées pour les blocs personnalisés.
ALIASES = {
    "Entrées / Sorties": "data", "Données": "data", "Data": "data", "Manipulation": "manip",
    "Visualisation": "viz", "Prétraitement": "transform", "Preprocessing": "transform",
    "Classification": "supervised", "Régression": "supervised", "Regression": "supervised",
    "Clustering": "unsupervised", "Évaluation": "model_selection", "Evaluation": "model_selection",
    "Explicabilité": "inspection", "Validation & réglage": "model_selection",
}

FAMILIES = {
    # 1. Apprentissage supervisé
    "linear_model": ("Modèles linéaires", "Linear models"),
    "discriminant_analysis": ("Analyse discriminante", "Linear and quadratic discriminant analysis"),
    "kernel_ridge": ("Régression ridge à noyau", "Kernel ridge regression"),
    "svm": ("Machines à vecteurs de support", "Support vector machines"),
    "neighbors": ("Plus proches voisins", "Nearest neighbors"),
    "gaussian_process": ("Processus gaussiens", "Gaussian processes"),
    "cross_decomposition": ("Décomposition croisée", "Cross decomposition"),
    "naive_bayes": ("Bayésien naïf", "Naive Bayes"),
    "tree": ("Arbres de décision", "Decision trees"),
    "ensemble": ("Ensembles", "Ensembles"),
    "multiclass": ("Multiclasse et multisortie", "Multiclass and multioutput"),
    "feature_selection": ("Sélection de variables", "Feature selection"),
    "semi_supervised": ("Semi-supervisé", "Semi-supervised learning"),
    "isotonic": ("Régression isotonique", "Isotonic regression"),
    "calibration": ("Calibration des probabilités", "Probability calibration"),
    "neural_network": ("Réseaux de neurones", "Neural network models"),
    "dummy": ("Estimateurs de référence", "Dummy estimators"),
    # 2. Apprentissage non supervisé
    "mixture": ("Mélanges gaussiens", "Gaussian mixture models"),
    "manifold": ("Apprentissage de variétés", "Manifold learning"),
    "cluster": ("Clustering", "Clustering"),
    "decomposition": ("Décomposition (ACP, NMF…)", "Decomposing signals in components"),
    "covariance": ("Estimation de covariance", "Covariance estimation"),
    "outlier": ("Détection de nouveautés et d'anomalies", "Novelty and outlier detection"),
    "density": ("Estimation de densité", "Density estimation"),
    "neural_network_unsup": ("Réseaux de neurones (non supervisé)", "Neural network models (unsupervised)"),
    # 3. Sélection et évaluation de modèles
    "cv": ("Validation croisée", "Cross-validation"),
    "tuning": ("Réglage des hyperparamètres", "Tuning the hyper-parameters"),
    "threshold": ("Seuil de décision", "Tuning the decision threshold"),
    "metrics": ("Métriques et scores", "Metrics and scoring"),
    "curves": ("Courbes de validation", "Validation curves"),
    # 4. Inspection
    "pdp": ("Dépendance partielle", "Partial dependence"),
    "permutation": ("Importance par permutation", "Permutation feature importance"),
    "model_viz": ("Visualisation des modèles", "Model visualization"),
    # 6. Transformations de données
    "compose": ("Pipelines et estimateurs composites", "Pipelines and composite estimators"),
    "feature_extraction": ("Extraction de caractéristiques", "Feature extraction"),
    "preprocessing": ("Prétraitement", "Preprocessing data"),
    "impute": ("Imputation des valeurs manquantes", "Imputation of missing values"),
    "random_projection": ("Projections aléatoires", "Random projection"),
    "kernel_approximation": ("Approximation de noyaux", "Kernel approximation"),
}

# Nœuds propres à KataML : type exact ou préfixe → (section, famille).
CUSTOM = {
    "io.": ("data", ""), "manip.": ("manip", ""), "view.": ("viz", ""), "report.": ("report", ""),
    "text.": ("transform", "feature_extraction"), "compose.pipeline": ("transform", "compose"),
    "apply.": ("predict", ""),
    "score.importance": ("inspection", "permutation"), "score.": ("model_selection", "metrics"),
    "tune.grid_search": ("model_selection", "tuning"),
    "tune.learning_curve": ("model_selection", "curves"), "tune.validation_curve": ("model_selection", "curves"),
    "tune.": ("model_selection", "cv"),
    "explain.partial_dependence": ("inspection", "pdp"), "explain.": ("inspection", "model_viz"),
    "meta.Voting": ("supervised", "ensemble"), "meta.Stacking": ("supervised", "ensemble"),
    "meta.FixedThreshold": ("model_selection", "threshold"), "meta.TunedThreshold": ("model_selection", "threshold"),
    "meta.RFE": ("supervised", "feature_selection"), "meta.SelectFromModel": ("supervised", "feature_selection"),
    "meta.SequentialFeatureSelector": ("supervised", "feature_selection"),
    "meta.": ("supervised", "multiclass"),
}

SUPERVISED_MODULES = {
    "linear_model", "discriminant_analysis", "kernel_ridge", "svm", "neighbors", "gaussian_process",
    "cross_decomposition", "naive_bayes", "tree", "ensemble", "feature_selection", "semi_supervised",
    "isotonic", "calibration", "neural_network", "dummy", "multiclass", "multioutput",
}
UNSUPERVISED_MODULES = {"mixture", "manifold", "cluster", "decomposition", "covariance"}
TRANSFORM_MODULES = {"preprocessing", "impute", "random_projection", "kernel_approximation",
                     "feature_extraction", "compose"}


def classify(node_type: str, module: str | None, kind: str | None) -> tuple[str, str]:
    """(section, famille) d'un nœud."""
    for key in sorted(CUSTOM, key=len, reverse=True):
        if node_type.startswith(key):
            return CUSTOM[key]
    mod = (module or "").split(".")[1] if module and "." in module else ""
    if kind == "outlier":
        return "unsupervised", "outlier"
    if kind == "density":
        return "unsupervised", "density"
    if kind == "covariance":
        return "unsupervised", "covariance"
    if mod == "neural_network" and kind == "transformer":
        return "unsupervised", "neural_network_unsup"
    if mod == "multioutput":
        return "supervised", "multiclass"
    if mod == "model_selection":
        return "model_selection", "threshold"
    if mod in SUPERVISED_MODULES:
        return "supervised", mod
    if mod in UNSUPERVISED_MODULES:
        return "unsupervised", mod
    if mod in TRANSFORM_MODULES:
        return "transform", mod
    return "transform", "preprocessing" if kind == "transformer" else ""


def label(table: dict, key: str, lang: str) -> str:
    fr, en = table.get(key, (key, key))
    return en if lang == "en" else fr


def section_order(lang: str) -> list[str]:
    return [label(SECTIONS, k, lang) for k in SECTIONS]
