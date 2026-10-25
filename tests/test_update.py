"""Vérification de version : comparaison, désactivation, cache, silence hors ligne."""

import json
import os
import tempfile
import unittest
from pathlib import Path

from kataml import __version__, update


class UpdateCheck(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp(prefix="kataml-upd-"))
        self._orig_fetch = update._fetch_latest

    def tearDown(self):
        update._fetch_latest = self._orig_fetch

    def test_version_compare(self):
        self.assertTrue(update._is_newer("0.6.0", "0.5.5"))
        self.assertTrue(update._is_newer("v0.5.10", "v0.5.9"))
        self.assertTrue(update._is_newer("1.0.0", "0.9.9"))
        self.assertFalse(update._is_newer("0.5.5", "0.5.5"))
        self.assertFalse(update._is_newer("0.5.4", "0.5.5"))
        self.assertFalse(update._is_newer("", "0.5.5"))
        self.assertEqual(update._parse("v0.5.6-rc1"), (0, 5, 6))

    def test_disabled_by_env(self):
        os.environ["KATAML_NO_UPDATE_CHECK"] = "1"
        try:
            r = update.check(self.ws)
        finally:
            del os.environ["KATAML_NO_UPDATE_CHECK"]
        self.assertTrue(r["disabled"])
        self.assertFalse((self.ws / ".update_check.json").exists())  # aucune requête, aucun cache

    def test_offline_is_silent(self):
        def boom():
            raise OSError("pas de réseau")
        update._fetch_latest = boom
        r = update.check(self.ws)
        self.assertFalse(r["available"])
        self.assertEqual(r["current"], __version__)
        self.assertEqual(r["url"], update.RELEASES_URL)
        # Échec réseau : on ne fige pas l'horodatage, pour réessayer plus tard.
        self.assertFalse((self.ws / ".update_check.json").exists())

    def test_newer_then_cached(self):
        calls = []
        update._fetch_latest = lambda: (calls.append(1), "v99.0.0")[1]
        r = update.check(self.ws)
        self.assertTrue(r["available"])
        self.assertEqual(r["latest"], "v99.0.0")
        self.assertEqual(json.loads((self.ws / ".update_check.json").read_text())["latest"], "v99.0.0")
        update.check(self.ws)                 # cache récent : aucune requête supplémentaire
        self.assertEqual(len(calls), 1)
        update.check(self.ws, force=True)      # force=True relance la requête
        self.assertEqual(len(calls), 2)

    def test_cache_invalidated_on_version_change(self):
        (self.ws / ".update_check.json").write_text(json.dumps(
            {"checked_at": 9e18, "latest": "0.0.1", "current_checked": "0.0.0-autre"}))
        update._fetch_latest = lambda: "v1.2.3"
        r = update.check(self.ws)
        # current_checked ne correspond plus à la version installée : on réinterroge.
        self.assertEqual(r["latest"], "v1.2.3")


if __name__ == "__main__":
    unittest.main()
