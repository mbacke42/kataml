"""Génère kataml/examples/data/avis.csv : avis clients synthétiques (exemple 07).

Les avis mêlent compliments et reproches, négations (« pas terrible », « pas mal »)
et une part d'étiquettes bruitées, pour qu'un classifieur de texte ait un vrai travail
à faire (exactitude attendue autour de 85-90 %).

    uv run python tools/gen_avis.py
"""

import csv
import random
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "kataml" / "examples" / "data" / "avis.csv"

SUJETS = ["la livraison", "le produit", "l'emballage", "le service client", "la qualité",
          "le prix", "la notice", "le montage", "l'application", "le remboursement"]
POS = ["impeccable", "rapide", "excellent", "parfait", "très correct", "au top", "soigné",
       "conforme à la description", "agréable", "efficace", "pas mal", "pas cher"]
NEG = ["décevant", "lent", "médiocre", "cassé", "pas terrible", "pas conforme", "bâclé",
       "trop cher", "introuvable", "compliqué", "jamais arrivé", "inutilisable"]
FIN_POS = ["Je recommande.", "Je rachèterai.", "Très satisfait.", "Merci !", "Cinq étoiles.", ""]
FIN_NEG = ["Je ne recommande pas.", "Plus jamais.", "Très déçu.", "À éviter.", "Remboursement demandé.", ""]
FIN_NEUTRE = ["Sans plus.", "Bof.", "Peut mieux faire.", "Correct dans l'ensemble.", ""]


def phrase(rng, mots):
    return f"{rng.choice(SUJETS).capitalize()} {rng.choice(['est', 'était', 'a été'])} {rng.choice(mots)}"


def avis(rng):
    sentiment = rng.random() < 0.55          # 55 % d'avis positifs
    major, minor = (POS, NEG) if sentiment else (NEG, POS)
    parts = [phrase(rng, major)]
    if rng.random() < 0.45:                  # avis nuancé : un reproche ou un compliment
        parts.append(f"{rng.choice(['mais', 'par contre', 'en revanche'])} {phrase(rng, minor).lower()}")
    if rng.random() < 0.5:
        parts.append(f"et {phrase(rng, major).lower()}")
    fin = rng.choice(FIN_NEUTRE if rng.random() < 0.3 else (FIN_POS if sentiment else FIN_NEG))
    texte = ", ".join(parts) + ". " + fin
    if rng.random() < 0.07:                  # étiquette bruitée (erreur d'annotation)
        sentiment = not sentiment
    return texte.strip(), "positif" if sentiment else "négatif"


def main():
    rng = random.Random(7)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["avis", "sentiment"])
        for _ in range(900):
            w.writerow(avis(rng))
    print(f"{OUT} écrit")


if __name__ == "__main__":
    main()
