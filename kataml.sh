#!/usr/bin/env sh
# Lance KataML. Seul prérequis : uv (https://docs.astral.sh/uv/).
# Au premier lancement, uv crée .venv dans ce dossier et y installe les dépendances.
DIR="$(cd "$(dirname "$0")" && pwd)"
if ! command -v uv >/dev/null 2>&1; then
  echo "uv est introuvable. Installation sans droits administrateur :"
  echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi
cd "$DIR" && exec uv run --project "$DIR" python -m kataml "$@"
