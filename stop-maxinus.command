#!/bin/zsh

set -u
cd "${0:A:h}"

if command -v docker >/dev/null 2>&1 && [[ -f .env ]]; then
  docker compose --env-file .env -f docker/compose.yaml stop
fi

pkill -f '/bin/maxinus (live|voice|wake)' 2>/dev/null || true
echo "Maxinus est arrêté."
