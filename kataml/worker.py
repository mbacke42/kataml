"""Moteur dans un processus séparé : permet d'interrompre un calcul en cours.

Le serveur HTTP dialogue avec le processus de calcul par un tube (multiprocessing).
Les requêtes sont traitées en parallèle côté calcul : on peut afficher une table
pendant qu'un modèle s'entraîne. « Arrêter » termine le processus et en relance un
nouveau ; les résultats déjà calculés sont relus depuis le cache disque.
"""

from __future__ import annotations

import itertools
import multiprocessing as mp
import threading
from pathlib import Path

from .nodes import NodeError


class Cancelled(NodeError):
    pass


def _serve(conn, workspace: str):
    """Boucle du processus de calcul."""
    from .engine import EngineService, WorkflowError
    service = EngineService(Path(workspace))
    send_lock = threading.Lock()
    conn.send(("ready", True, None))

    def handle(rid, method, kwargs):
        try:
            result, ok = getattr(service, method)(**kwargs), True
        except (NodeError, WorkflowError) as e:
            result, ok = ("user", str(e)), False
        except Exception as e:
            import traceback
            traceback.print_exc()
            result, ok = ("internal", f"{type(e).__name__} : {e}"), False
        with send_lock:
            conn.send((rid, ok, result))

    while True:
        try:
            rid, method, kwargs = conn.recv()
        except (EOFError, OSError):
            break
        threading.Thread(target=handle, args=(rid, method, kwargs), daemon=True).start()


class EngineProcess:
    """Mandataire du moteur. ``call("execute", wf=…, node=…)`` → résultat sérialisable."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.ctx = mp.get_context("spawn")
        self.lock = threading.Lock()
        self.ids = itertools.count()
        self._start()

    def _start(self):
        parent, child = self.ctx.Pipe()
        proc = self.ctx.Process(target=_serve, args=(child, str(self.workspace)), daemon=True,
                                name="kataml-moteur")
        proc.start()
        child.close()
        self.conn, self.proc = parent, proc
        self.pending: dict[int, list] = {}
        self.ready = threading.Event()
        self.busy = 0
        threading.Thread(target=self._receive, args=(parent, self.pending), daemon=True).start()

    def _receive(self, conn, pending):
        while True:
            try:
                rid, ok, result = conn.recv()
            except (EOFError, OSError):
                break
            if rid == "ready":
                self.ready.set()
                continue
            slot = pending.pop(rid, None)
            if slot:
                slot[1], slot[2] = ok, result
                slot[0].set()
        # Processus terminé : les requêtes en attente échouent, les suivantes ne bloquent pas.
        self.ready.set()
        for slot in list(pending.values()):
            slot[1], slot[2] = False, ("cancel", "Exécution interrompue.")
            slot[0].set()
        pending.clear()

    def call(self, method: str, **kwargs):
        self.ready.wait(180)
        if not self.proc.is_alive():
            raise NodeError("Le moteur de calcul s'est arrêté ; relancez KataML.")
        slot = [threading.Event(), None, None]
        with self.lock:
            rid = next(self.ids)
            pending = self.pending
            pending[rid] = slot
            try:
                self.conn.send((rid, method, kwargs))
            except (OSError, ValueError):
                pending.pop(rid, None)
                raise Cancelled("Le moteur redémarre, réessayez.")
            if method == "execute":
                self.busy += 1
        try:
            slot[0].wait()
        finally:
            if method == "execute":
                with self.lock:
                    self.busy = max(0, self.busy - 1)
        ok, result = slot[1], slot[2]
        if ok:
            return result
        kind, msg = result
        if kind == "cancel":
            raise Cancelled(msg)
        raise NodeError(msg)

    def cancel(self) -> bool:
        """Interrompt le calcul en cours en relançant le processus de calcul."""
        with self.lock:
            if not self.busy:
                return False
            old = self.proc
            old.terminate()
        old.join(5)
        if old.is_alive():
            old.kill()
        with self.lock:
            self._start()
        return True

    def close(self):
        try:
            self.proc.terminate()
        except Exception:
            pass
