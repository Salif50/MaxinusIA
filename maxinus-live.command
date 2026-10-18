#!/bin/zsh

set -u
cd "${0:A:h}"

WEB_URL="http://127.0.0.1:3000"
CONTAINER="maxinus-webui"
COMPOSE=(docker compose --env-file .env -f docker/compose.yaml)

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker Desktop n'est pas installé."
  read -k 1
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Démarrage de Docker Desktop…"
  open -a Docker
  for _ in {1..90}; do
    docker info >/dev/null 2>&1 && break
    sleep 1
  done
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker Desktop n'a pas démarré. Ouvrez-le puis réessayez."
  read -k 1
  exit 1
fi

if [[ ! -f .env ]]; then
  echo "Maxinus Live n'est pas configuré. Lancez d'abord : ./setup.sh live"
  read -k 1
  exit 1
fi

"${COMPOSE[@]}" up -d >/dev/null
echo "Préparation de Maxinus Live…"

for _ in {1..120}; do
  if curl -fsS "$WEB_URL/health" >/dev/null 2>&1; then
    open "$WEB_URL"
    exit 0
  fi
  sleep 1
done

echo "Maxinus Live ne répond pas encore. Vérifiez Docker Desktop."
read -k 1
exit 1
