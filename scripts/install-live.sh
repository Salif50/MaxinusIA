#!/bin/zsh

set -euo pipefail
cd "${0:A:h}/.."

MAXINUS_MODEL="${MAXINUS_MODEL:-qwen2.5:14b}"

for command_name in docker ollama curl openssl; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Commande requise absente : $command_name"
    exit 1
  fi
done

if ! docker info >/dev/null 2>&1; then
  echo "Démarrage de Docker Desktop…"
  open -a Docker
  for _ in {1..90}; do
    docker info >/dev/null 2>&1 && break
    sleep 1
  done
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker Desktop ne répond pas. Ouvrez-le puis relancez l'installation."
  exit 1
fi

if ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "Ollama ne répond pas sur le port 11434. Ouvrez l'application Ollama."
  exit 1
fi

if ! ollama list | awk 'NR > 1 {print $1}' | grep -Fqx "$MAXINUS_MODEL"; then
  echo "Téléchargement du modèle $MAXINUS_MODEL…"
  ollama pull "$MAXINUS_MODEL"
fi

mkdir -p models
if [[ ! -s models/kokoro-v1.0.onnx ]]; then
  echo "Téléchargement du modèle vocal Kokoro…"
  curl -fL --retry 3 "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx" -o models/kokoro-v1.0.onnx
fi
if [[ ! -s models/voices-v1.0.bin ]]; then
  echo "Téléchargement des voix Kokoro…"
  curl -fL --retry 3 "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin" -o models/voices-v1.0.bin
fi

if [[ ! -f .env ]]; then
  umask 077
  printf 'WEBUI_SECRET_KEY=%s\n' "$(openssl rand -hex 32)" > .env
fi

# Migre automatiquement l'ancien conteneur lancé manuellement. Le volume open-webui,
# qui contient les comptes et conversations, n'est jamais supprimé.
if docker inspect maxinus-webui >/dev/null 2>&1; then
  compose_project="$(docker inspect --format '{{index .Config.Labels "com.docker.compose.project"}}' maxinus-webui 2>/dev/null || true)"
  if [[ "$compose_project" != "maxinus" ]]; then
    docker rm -f maxinus-webui >/dev/null
  fi
fi

docker volume inspect open-webui >/dev/null 2>&1 || docker volume create open-webui >/dev/null
docker compose --env-file .env -f docker/compose.yaml build
docker compose --env-file .env -f docker/compose.yaml up -d

echo "Préchargement de Whisper base…"
for _ in {1..60}; do
  docker exec maxinus-stt python -c 'import faster_whisper' >/dev/null 2>&1 && break
  sleep 1
done
docker exec maxinus-stt python -c "import os; from faster_whisper import WhisperModel; WhisperModel(os.environ['WHISPER_MODEL'], device='cpu', compute_type=os.environ['WHISPER_COMPUTE_TYPE'], download_root=os.environ['WHISPER_MODEL_DIR'])"
docker exec maxinus-stt python -c "import os; from kokoro_onnx import Kokoro; Kokoro(os.environ['KOKORO_MODEL_PATH'], os.environ['KOKORO_VOICES_PATH'])"

echo
echo "Maxinus Live est installé : http://127.0.0.1:3000"
echo "Lancez-le ensuite avec : ./maxinus-live.command"
