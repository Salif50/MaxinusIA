#!/bin/zsh

set -euo pipefail
cd "${0:A:h}"

mode="${1:-live}"
case "$mode" in
  live)
    exec ./scripts/install-live.sh
    ;;
  cli)
    exec ./scripts/install-cli.sh
    ;;
  all)
    ./scripts/install-cli.sh
    exec ./scripts/install-live.sh
    ;;
  *)
    echo "Usage : ./setup.sh [live|cli|all]"
    echo "  live : interface vocale navigateur recommandée"
    echo "  cli  : ancien assistant vocal dans le Terminal"
    echo "  all  : installe les deux interfaces"
    exit 2
    ;;
esac
