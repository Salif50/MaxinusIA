#!/bin/zsh
cd "${0:A:h}"
if [[ ! -x .venv/bin/maxinus ]]; then
  echo "Maxinus CLI n'est pas encore installé. Lancez d'abord : ./setup.sh cli"
  read -k 1
  exit 1
fi
exec .venv/bin/maxinus live
