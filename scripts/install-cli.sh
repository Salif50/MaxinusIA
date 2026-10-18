#!/bin/zsh
set -e
cd "${0:A:h}/.."

PYTHON_BIN="${MAXINUS_PYTHON:-/opt/homebrew/bin/python3.12}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python 3.12 est requis. Installez-le avec: brew install python@3.12"
  exit 1
fi

echo "Création de l'environnement Maxinus…"
"$PYTHON_BIN" -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools wheel
.venv/bin/pip install -e .

[[ -f config.json ]] || cp config.example.json config.json
.venv/bin/python scripts/download_models.py

echo
echo "Installation CLI terminée. Lancez : ./maxinus.command"
