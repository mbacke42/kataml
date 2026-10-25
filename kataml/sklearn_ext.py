"""Petits estimateurs compatibles scikit-learn utilisés par KataML."""

from __future__ import annotations

import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin, clone


class TextColumnVectorizer(TransformerMixin, BaseEstimator):
    """Vectorise une colonne de texte d'un DataFrame et conserve les autres colonnes.

    Les valeurs manquantes sont traitées comme des textes vides et la sortie est
    un DataFrame dense : l'objet s'insère donc dans un Pipeline pandas.
    """

    def __init__(self, column: str = "text", vectorizer=None):
        self.column = column
        self.vectorizer = vectorizer

    def _docs(self, X):
        return X[self.column].fillna("").astype(str)

    def fit(self, X, y=None):
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.vectorizer_ = clone(self.vectorizer) if self.vectorizer is not None else TfidfVectorizer()
        self.vectorizer_.fit(self._docs(X), y)
        try:
            self.terms_ = [str(t) for t in self.vectorizer_.get_feature_names_out()]
        except Exception:      # HashingVectorizer : pas de vocabulaire
            n = self.vectorizer_.transform([""]).shape[1]
            self.terms_ = [f"{self.column}_{i}" for i in range(n)]
        self.rest_ = [c for c in X.columns if c != self.column]
        clash = set(self.terms_) & set(map(str, self.rest_))
        if clash:
            raise ValueError(f"Termes en conflit avec des colonnes existantes : {', '.join(sorted(clash)[:5])}")
        return self

    def transform(self, X):
        mat = self.vectorizer_.transform(self._docs(X))
        words = pd.DataFrame(mat.toarray(), columns=self.terms_, index=X.index)
        return pd.concat([words, X[[c for c in self.rest_ if c in X.columns]]], axis=1)

    def get_feature_names_out(self, input_features=None):
        return [*self.terms_, *map(str, self.rest_)]

    def set_output(self, *, transform=None):
        return self
