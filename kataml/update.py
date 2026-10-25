"""Vérification discrète d'une version plus récente publiée en release (GitLab).

Tout tient ici pour rester facile à relire. Une seule requête sortante : un GET
vers l'API publique de GitLab, avec un User-Agent générique (nom de l'outil et
URL du projet) et aucune donnée personnelle (ni e-mail, ni identifiant, ni
paramètre de suivi). La vérification est :

- désactivable par la variable d'environnement KATAML_NO_UPDATE_CHECK ;
- silencieuse hors ligne (toute erreur réseau est ignorée) ;
- mise en cache (workspace/.update_check.json) pour n'interroger qu'une fois
  par jour ;
- déclenchée par l'interface, jamais au démarrage du serveur ni en ligne de
  commande, pour ne pas imposer d'accès réseau à une utilisation hors ligne.
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path

from . import __version__

RELEASES_URL = "https://gitlab.com/fredbl/kataml/-/releases"
API_URL = "https://gitlab.com/api/v4/projects/fredbl%2Fkataml/releases?per_page=1"
USER_AGENT = f"KataML/{__version__} (+https://gitlab.com/fredbl/kataml)"
INTERVAL = 24 * 3600  # une vérification par jour au plus
TIMEOUT = 3.0


def _parse(v: str) -> tuple:
    """(0, 5, 6) à partir de « v0.5.6 », « 0.5.6 », « 0.5.6-rc1 »… ; s'arrête au premier champ non entier."""
    out = []
    for part in str(v).lstrip("vV").split("."):
        num = ""
        for ch in part:
            if ch.isdigit():
                num += ch
            else:
                break
        if not num:
            break
        out.append(int(num))
    return tuple(out)


def _is_newer(latest: str, current: str) -> bool:
    a = _parse(latest)
    return bool(a) and a > _parse(current)


def _fetch_latest() -> str | None:
    req = urllib.request.Request(API_URL, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:  # URL fixe, https
        data = json.loads(r.read().decode("utf-8"))
    if isinstance(data, list) and data:
        return (str(data[0].get("tag_name") or "").strip()) or None
    return None


def check(workspace: Path | None = None, force: bool = False) -> dict:
    """Renvoie {current, latest, available, url} (et disabled si désactivée)."""
    base = {"current": __version__, "latest": None, "available": False, "url": RELEASES_URL}
    if os.environ.get("KATAML_NO_UPDATE_CHECK"):
        return {**base, "disabled": True}

    cache = (workspace / ".update_check.json") if workspace else None
    cached: dict = {}
    if cache and cache.is_file():
        try:
            cached = json.loads(cache.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            cached = {}

    latest = cached.get("latest")
    fresh = (not force and cached.get("current_checked") == __version__
             and isinstance(cached.get("checked_at"), (int, float))
             and time.time() - cached["checked_at"] < INTERVAL)
    if not fresh:
        try:
            latest = _fetch_latest()
        except Exception:
            # Hors ligne ou API indisponible : on garde la dernière valeur connue
            # et on ne réécrit pas l'horodatage, pour réessayer au prochain lancement.
            return {**base, "latest": latest, "available": _is_newer(latest, __version__) if latest else False}
        if cache:
            try:
                cache.write_text(json.dumps(
                    {"checked_at": time.time(), "latest": latest, "current_checked": __version__},
                    ensure_ascii=False), encoding="utf-8")
            except OSError:
                pass

    return {**base, "latest": latest, "available": _is_newer(latest, __version__) if latest else False}
