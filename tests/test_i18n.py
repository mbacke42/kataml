"""Traduction anglaise : tous les nœuds, libellés et ports doivent être traduits."""

import unittest

from kataml import i18n
from kataml.nodes import REGISTRY, catalog


class English(unittest.TestCase):
    def test_every_custom_node_is_translated(self):
        custom = [t for t, nt in REGISTRY.items() if not t.startswith(("sk.", "meta.", "text.")) and not nt.extension]
        self.assertEqual([t for t in custom if t not in i18n.NODES], [])

    def test_labels_and_ports_are_translated(self):
        missing = set()
        for nt in REGISTRY.values():
            if nt.extension:
                continue
            for name, _ in nt.inputs + nt.outputs:
                if name not in i18n.PHRASES:
                    missing.add(f"port: {name}")
            for p in nt.params:
                if p.get("group") == "Hyperparamètres":
                    continue
                if p["label"] not in i18n.PHRASES:
                    missing.add(f"label: {p['label']}")
                for v in (p.get("choice_labels") or {}).values():
                    if v not in i18n.PHRASES and not v.isascii():
                        missing.add(f"choice: {v}")
        self.assertEqual(sorted(missing), [])

    def test_catalog_en(self):
        specs = {s["type"]: s for s in catalog("en")}
        self.assertEqual(specs["manip.partition"]["name"], "train_test_split")
        self.assertEqual(specs["tune.cross_validation"]["name"], "cross_validate")
        self.assertEqual(specs["sk.classifier.RandomForestClassifier"]["category"], "Supervised learning")
        self.assertIn("Learner (classification)", specs["sk.classifier.RandomForestClassifier"]["description"])
        self.assertEqual(specs["sk.classifier.LogisticRegression"]["params"][0]["label"], "Target column")

    def test_payload(self):
        out = i18n.translate_payload({"error": "Port d'entrée « Table » non connecté.",
                                      "blocks": [{"type": "metrics", "items": [{"label": "Exactitude", "value": 1}]}],
                                      "rows": [["Exactitude"]]}, "en")
        self.assertEqual(out["error"], "Input port “Table” is not connected.")
        self.assertEqual(out["blocks"][0]["items"][0]["label"], "Accuracy")
        self.assertEqual(out["rows"], [["Exactitude"]])          # données jamais traduites


if __name__ == "__main__":
    unittest.main()
