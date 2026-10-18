# Installation et fonctionnement de Maxinus

Ce document explique le projet depuis une machine neuve jusqu'à une conversation vocale
fonctionnelle. Le mode **Maxinus Live** est recommandé. Le mode Terminal est conservé pour
le développement et les outils agentiques locaux.

## 1. Architecture

Une conversation Maxinus Live suit cette chaîne :

```text
Microphone du navigateur
        ↓
Whisper base (service local maxinus-stt)
        ↓
Qwen 2.5 14B (raisonnement local dans Ollama)
        ↓
Open WebUI (conversation, streaming et interruption)
        ↓
Kokoro ONNX français (voix ff_siwis dans le conteneur local)
```

Cette séparation évite que Python contrôle directement le périphérique audio macOS. Elle
contourne notamment les plantages `PaMacCore (AUHAL) err=-50` rencontrés avec certains
pilotes USB comme ZW-PG02.

## 2. Prérequis

- macOS sur Apple Silicon ;
- un modèle adapté à la mémoire selon le tableau du `README.md` ;
- environ 15 Go d'espace libre pour Ollama, Docker et les caches ;
- Docker Desktop, Ollama et un navigateur récent ;
- Internet uniquement pour l'installation initiale.

Vérifications :

```bash
docker --version
ollama --version
curl http://127.0.0.1:11434/api/tags
```

Ouvrez Docker Desktop et l'application Ollama si les deux services ne répondent pas.

## 3. Installation recommandée

Depuis la racine du projet :

```bash
chmod +x setup.sh scripts/*.sh *.command scripts/macos/*.command
MAXINUS_MODEL=qwen2.5:7b ./setup.sh live
```

Cette commande choisit un modèle plus léger pour 16 Go de mémoire. Pour utiliser le 14B par
défaut :

```bash
./setup.sh live
```

L'installateur :

1. vérifie Docker, Ollama, `curl` et `openssl` ;
2. démarre Docker Desktop si nécessaire ;
3. vérifie l'API locale Ollama ;
4. télécharge le modèle demandé avec `MAXINUS_MODEL` s'il est absent (14B par défaut) ;
5. génère une clé locale dans `.env` ;
6. construit l'image `maxinus/open-webui:local-voice` ;
7. lance `maxinus-stt`, puis `maxinus-webui` ;
8. précharge Whisper `base` dans le volume persistant.

Open WebUI slim exige un moteur STT « externe ». Maxinus satisfait cette exigence avec une
API compatible OpenAI dans `maxinus-stt`. La synthèse vocale passe aussi par ce service et
Kokoro ONNX en français (`ff_siwis`). Les deux modèles restent locaux, et aucun port audio
ou STT n'est publié sur le Mac.

Les fichiers `.env`, `models/` et `data/` sont volontairement exclus de Git.

## 4. Premier lancement

```bash
./maxinus-live.command
```

Le script démarre Docker Desktop si nécessaire, lance le service et ouvre
`http://127.0.0.1:3000`.

Dans l'interface :

1. créez le premier compte local ; ce compte devient administrateur ;
2. sélectionnez le modèle choisi à l'installation (14B par défaut) ;
3. autorisez le navigateur à utiliser le microphone ;
4. ouvrez les paramètres audio ;
5. activez la lecture automatique et l'interruption vocale ;
6. ouvrez le mode vocal et commencez à parler.

Les moteurs STT et TTS sont déjà configurés par l'installateur vers l'API locale. Dans les
paramètres administrateur, `openai` désigne ici le protocole compatible utilisé en interne ;
les URL sont `http://stt:8000/v1`, sans appel au service OpenAI. Le TTS utilise Kokoro
français `ff_siwis`.

Le mode Standard attend une courte période de silence avant d'envoyer la phrase. Qwen
génère ensuite la réponse en streaming. Ce n'est pas un modèle audio natif full-duplex,
mais l'interruption permet de couper la réponse en parlant.

## 5. Utilisation quotidienne

```bash
./maxinus-live.command       # démarrer et ouvrir l'interface
./stop-maxinus.command       # arrêter Maxinus
```

Administration :

```bash
docker compose --env-file .env -f docker/compose.yaml ps
docker compose --env-file .env -f docker/compose.yaml logs -f
docker compose --env-file .env -f docker/compose.yaml restart
docker compose --env-file .env -f docker/compose.yaml stop
```

Les conversations, comptes, paramètres et le cache Whisper survivent à l'arrêt grâce au
volume Docker `open-webui`. Le service `maxinus-stt` démarre automatiquement avant
`maxinus-webui`.

## 6. Mode CLI historique

```bash
./setup.sh cli              # installer seulement le CLI
./setup.sh all              # installer Live et CLI
./maxinus.command           # conversation live dans le Terminal
.venv/bin/maxinus text
.venv/bin/maxinus voice
.venv/bin/maxinus wake
.venv/bin/maxinus doctor
```

Le mode CLI utilise `config.json`, `models/` et `data/`. Si CoreAudio se bloque, le
correctif historique se trouve dans `scripts/macos/fix_audio.command`. Le mode navigateur
reste préférable, car il ne dépend pas de PortAudio pour la lecture.

## 7. Réglages principaux

Pour Maxinus Live :

- `docker/compose.yaml` contient les ports, le modèle Whisper, la langue et le volume ;
- `docker/Dockerfile.open-webui` construit Open WebUI avec `faster-whisper` ;
- `.env` contient la clé secrète locale et ne doit jamais être partagé.

Le port `3000` est lié à `127.0.0.1` : l'interface n'est pas exposée au réseau local.

Pour le CLI, copiez `config.example.json` vers `config.json`, puis adaptez le modèle, les
périphériques audio, la voix, le dossier `workspace` et la taille du contexte.

## 8. Diagnostic

```bash
ollama list
curl http://127.0.0.1:11434/api/tags
curl http://127.0.0.1:3000/health
docker logs --tail 100 maxinus-webui
docker logs --tail 100 maxinus-stt
docker exec maxinus-stt python -c "import faster_whisper; print(faster_whisper.__version__)"
docker exec maxinus-webui python -c "import urllib.request; print(urllib.request.urlopen('http://stt:8000/health').status)"
docker exec maxinus-webui python -c "import urllib.request; print(urllib.request.urlopen('http://host.docker.internal:11434/api/tags').status)"
```

Si le 14B répond trop lentement sur une machine de 16 Go, installez `qwen2.5:7b` et
sélectionnez-le dans l'interface pour les conversations rapides.

Les fichiers `models/kokoro-v1.0.onnx` et `models/voices-v1.0.bin` sont téléchargés lors de
l'installation Live s'ils sont absents. La voix `ff_siwis` est la voix française de Kokoro.

## 9. Mise à jour

Sauvegardez d'abord le volume comme expliqué dans `docs/DEPLOYMENT.md`, puis :

```bash
docker compose --env-file .env -f docker/compose.yaml build --pull
docker compose --env-file .env -f docker/compose.yaml up -d
```

Ne supprimez pas le volume `open-webui` sauf si vous souhaitez effacer définitivement les
comptes, conversations, réglages et caches.
