"""Moteur dans un processus séparé : annulation d'un calcul et reprise depuis le cache."""

import tempfile
import threading
import time
import unittest
from pathlib import Path

from kataml.worker import Cancelled, EngineProcess

N = lambda i, t, **p: {"id": i, "type": t, "params": p}  # noqa: E731
E = lambda a, ap, b, bp: {"from": a, "fromPort": ap, "to": b, "toPort": bp}  # noqa: E731


class WorkerCancel(unittest.TestCase):
    def test_cancel_and_recover(self):
        ws = Path(tempfile.mkdtemp(prefix="kataml-worker-"))
        ep = EngineProcess(ws)
        try:
            wf = {"nodes": [N("d", "io.dataset", dataset="wine"),
                            N("slow", "manip.python", code="import time\ntime.sleep(60)\nout = df")],
                  "edges": [E("d", 0, "slow", 0)]}
            self.assertTrue(ep.call("execute", wf=wf, node="d")["ok"])
            res = {}

            def run():
                try:
                    res["r"] = ep.call("execute", wf=wf, node="slow")
                except Cancelled as e:
                    res["cancel"] = str(e)

            th = threading.Thread(target=run)
            th.start()
            time.sleep(1.5)
            # Le moteur reste disponible pendant un calcul long.
            self.assertEqual(ep.call("status", wf=wf)["states"]["d"]["state"], "executed")
            t0 = time.time()
            self.assertTrue(ep.cancel())
            th.join(15)
            self.assertIn("cancel", res)
            self.assertLess(time.time() - t0, 15)
            # Le nœud déjà calculé est relu depuis le cache disque par le nouveau processus.
            st = ep.call("status", wf=wf)["states"]
            self.assertEqual(st["d"]["state"], "executed")
            self.assertEqual(st["slow"]["state"], "idle")
            self.assertEqual(ep.call("port", node="d", port=0, limit=2)["total"], 178)
        finally:
            ep.close()


if __name__ == "__main__":
    unittest.main()
