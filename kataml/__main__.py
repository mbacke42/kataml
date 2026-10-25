"""Point d'entrée : ``kataml`` (interface) ou ``kataml run workflow.json`` (ligne de commande)."""

import argparse
import os
import sys
from pathlib import Path


def _perf_options(parser):
    parser.add_argument("--jobs", type=int, default=None,
                        help="cœurs pour validation croisée, recherche d'hyperparamètres… "
                             "(-1 = tous, défaut ; 1 = un seul ; variable KATAML_N_JOBS)")
    parser.add_argument("--cache-mb", type=int, default=None,
                        help="taille maximale du cache des résultats en Mo (défaut 1024 ; variable KATAML_CACHE_MB)")


def _apply_perf(args):
    # Variables d'environnement : héritées par le processus de calcul.
    if args.jobs is not None:
        os.environ["KATAML_N_JOBS"] = str(args.jobs)
    if args.cache_mb is not None:
        os.environ["KATAML_CACHE_MB"] = str(max(64, args.cache_mb))


def main():
    from . import __version__
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        p = argparse.ArgumentParser(prog="kataml run", description="Exécute un workflow sans interface.")
        p.add_argument("workflow", type=Path, help="fichier .json du workflow")
        p.add_argument("--rapport", type=Path, help="génère un rapport HTML")
        p.add_argument("--script", type=Path, help="exporte le script Python équivalent")
        p.add_argument("--notebook", type=Path, help="exporte un notebook Jupyter")
        p.add_argument("--workspace", type=Path, default=None,
                       help="dossier de travail (données, cache, extensions)")
        p.add_argument("-q", "--quiet", action="store_true", help="n'affiche que les erreurs")
        p.add_argument("--lang", choices=["fr", "en"], default="fr", help="langue du rapport (fr ou en)")
        _perf_options(p)
        from .cli import main as run_main
        args = p.parse_args(sys.argv[2:])
        _apply_perf(args)
        run_main(args)
        return
    parser = argparse.ArgumentParser(
        prog="kataml", description="Workflows ML visuels sur scikit-learn.",
        epilog="Exécution sans interface : kataml run workflow.json --rapport rapport.html")
    parser.add_argument("--version", action="version", version=f"kataml {__version__}")
    parser.add_argument("--port", type=int, default=8765, help="port HTTP (défaut : 8765)")
    parser.add_argument("--host", default="127.0.0.1",
                        help="adresse d'écoute (défaut : 127.0.0.1, accès local uniquement)")
    parser.add_argument("--workspace", type=Path, default=None,
                        help="dossier des données, workflows et exports (défaut : ./workspace depuis le dépôt, ~/kataml une fois installé)")
    parser.add_argument("--no-browser", action="store_true", help="ne pas ouvrir le navigateur")
    _perf_options(parser)
    args = parser.parse_args()
    _apply_perf(args)
    from .server import serve
    serve(args.host, args.port, args.workspace, not args.no_browser)


if __name__ == "__main__":
    main()
