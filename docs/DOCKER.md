# Déployer Maxinus Live avec Docker et Open WebUI

Ce guide explique ce qui tourne dans Docker, ce qui reste installé sur l’ordinateur,
comment installer une instance neuve et comment vérifier chaque partie. Il s’adresse à une
personne qui veut l’interface Open WebUI et les fonctions vocales locales.

> **À savoir :** dans la configuration actuelle, Open WebUI, l’API vocale, Whisper et
> Kokoro tournent dans des conteneurs. **Ollama et le modèle de langage restent sur
> l’ordinateur hôte** et sont utilisés par Open WebUI à travers le réseau Docker. Ainsi,
> Ollama peut profiter de l’accélération et du réglage de la machine. Ce n’est pas un
> déploiement où tous les services, Ollama compris, sont dans Compose.

## 1. Architecture et circulation des données

```text
Navigateur et microphone
        │ HTTP sur 127.0.0.1:3000
        ▼
Open WebUI (conteneur maxinus-webui)
        ├── Ollama sur l’ordinateur hôte (host.docker.internal:11434)
        └── API vocale (conteneur maxinus-stt, réseau Docker privé)
              ├── Whisper : audio → texte
              └── Kokoro : texte → audio français

Volume Docker open-webui : comptes, conversations, réglages et cache Whisper
Répertoire local models/ : poids Kokoro montés en lecture seule dans le service vocal
```

Le micro est capturé par le navigateur. Le fichier audio est envoyé à Open WebUI, puis au
service Whisper local. La transcription est transmise au modèle Ollama. Le texte de la
réponse est renvoyé au navigateur et Kokoro le transforme en audio. Le Compose ne publie
que le port de l’interface sur `127.0.0.1:3000`; l’API STT/TTS reste privée au réseau Docker.

Après le téléchargement initial des images, du modèle Ollama, du modèle Whisper et des
poids Kokoro, l’usage courant n’appelle pas d’API vocale cloud. L’installation et les
mises à jour ont besoin d’Internet. Respectez la licence propre à chaque modèle et à chaque
composant tiers.

## 2. Prérequis

- macOS Apple Silicon/Intel ou Linux avec Docker fonctionnel ; sous Windows, utilisez WSL2
  avec Docker Desktop et un terminal Linux pour les commandes de ce guide ;
- Docker Desktop (Mac/Windows) ou Docker Engine et le plugin Docker Compose (Linux) ;
- Ollama installé et démarré sur la même machine que Compose ;
- un modèle Ollama adapté à la mémoire disponible ;
- un navigateur récent avec accès au microphone ;
- une connexion Internet au premier démarrage et de l’espace disque pour les modèles.

Pour une première installation, prévoyez au minimum environ 15–25 Go libres, puis ajoutez
la taille du modèle Ollama sélectionné. Whisper et Kokoro, les images Docker et le volume
de données prennent aussi de la place. Les besoins exacts varient selon les modèles et les
versions téléchargés.

Vérifiez les prérequis :

```bash
docker --version
docker compose version
docker info
ollama --version
curl http://127.0.0.1:11434/api/tags
```

Sur macOS, ouvrez les applications Ollama et Docker Desktop avant de continuer. Sur Linux,
vérifiez que le service Docker fonctionne et que votre compte a le droit d’utiliser Docker.

## 3. Installation recommandée sur Mac

Le script d’installation automatise la création de la clé, le téléchargement des poids
Kokoro, la création du volume et le lancement. Depuis le dossier du projet :

```bash
MAXINUS_MODEL=qwen2.5:7b ./setup.sh live
```

Pour conserver le 14B comme modèle par défaut :

```bash
./setup.sh live
```

Le script vérifie Ollama et Docker, télécharge le modèle Ollama s’il manque, récupère les
fichiers Kokoro dans `models/`, crée `.env` avec une clé locale, construit l’image
`maxinus/open-webui:local-voice`, crée le volume `open-webui`, démarre les services et
préchauffe Whisper ainsi que Kokoro. L’opération initiale peut prendre du temps : les
modèles sont volumineux.

Puis lancez l’interface :

```bash
./maxinus-live.command
```

Ouvrez [http://127.0.0.1:3000](http://127.0.0.1:3000) si le navigateur ne s’ouvre pas
automatiquement.

## 4. Installation manuelle avec Docker Compose

Cette procédure est utile pour Linux, pour comprendre le déploiement ou si le script Mac ne
convient pas. Elle suppose qu’Ollama est déjà installé sur la machine hôte et accessible
sur le port `11434`.

### 4.1 Télécharger un modèle de langage

```bash
git clone https://github.com/Salif50/MaxinusIA.git
cd MaxinusIA

ollama pull qwen2.5:7b
ollama list
curl http://127.0.0.1:11434/api/tags
```

Sur une machine Linux, Ollama doit accepter les connexions venant du réseau Docker. Suivez
la documentation Ollama pour configurer `OLLAMA_HOST` et restreignez l’écoute au réseau
privé/pare-feu de confiance. Ne publiez pas le port `11434` sur Internet.

### 4.2 Préparer les fichiers vocaux

Le conteneur STT monte `models/` en lecture seule et s’attend à trouver :

```text
models/kokoro-v1.0.onnx
models/voices-v1.0.bin
```

Sur Mac, `./setup.sh live` les télécharge automatiquement. Pour le processus manuel,
téléchargez les deux fichiers de modèle depuis la page des [releases de kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx/releases),
placez-les exactement sous ces noms dans `models/`, puis vérifiez leur présence :

```bash
ls -lh models/kokoro-v1.0.onnx models/voices-v1.0.bin
```

### 4.3 Créer le secret et le volume persistant

À la racine du dépôt, créez `.env` sans copier celui d’une autre personne :

```bash
umask 077
printf 'WEBUI_SECRET_KEY=%s\n' "$(openssl rand -hex 32)" > .env
```

Si `openssl` n’est pas installé, générez une chaîne aléatoire longue avec un gestionnaire
de mots de passe et enregistrez uniquement `WEBUI_SECRET_KEY=...` dans `.env`. Ce fichier
ne doit jamais être envoyé sur GitHub ou transmis avec une copie du dépôt.

Le volume est déclaré `external` dans Compose : créez-le une fois avant le premier
lancement. Il conserve la base Open WebUI entre les redémarrages.

```bash
docker volume create open-webui
```

### 4.4 Construire et lancer les services

```bash
docker compose --env-file .env -f docker/compose.yaml config --quiet
docker compose --env-file .env -f docker/compose.yaml build
docker compose --env-file .env -f docker/compose.yaml up -d
```

Le premier build installe les dépendances vocales dans l’image locale. L’image Open WebUI
de base vient de GHCR et peut être mise à jour indépendamment du code Maxinus. Compose
crée un réseau privé pour que le service `webui` appelle le service `stt` par son nom DNS
`stt`.

### 4.5 Vérifier les conteneurs et les connexions

```bash
docker compose --env-file .env -f docker/compose.yaml ps
curl http://127.0.0.1:3000/health
docker exec maxinus-stt python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health').read().decode())"
docker exec maxinus-webui python -c "import urllib.request; print(urllib.request.urlopen('http://host.docker.internal:11434/api/tags').status)"
docker exec maxinus-webui python -c "import urllib.request; print(urllib.request.urlopen('http://stt:8000/health').status)"
```

Résultats attendus : les deux services sont `Up`, le service STT est `healthy`, l’interface
répond avec HTTP 200 et les deux derniers tests affichent `200`. Si le conteneur ne résout
pas `host.docker.internal` sous Linux, gardez l’entrée `extra_hosts` du Compose et vérifiez
que votre version de Docker Engine/Compose gère `host-gateway`.

## 5. Premier compte et configuration audio Open WebUI

1. Ouvrez l’interface sur `http://127.0.0.1:3000`.
2. Créez le premier compte. Il reçoit les droits d’administrateur ; choisissez un mot de
   passe unique et gardez-le dans un gestionnaire de mots de passe.
3. Créez une nouvelle conversation et choisissez `qwen2.5:7b` dans le sélecteur de modèle.
   Envoyez un message texte avant de tester la voix.
4. Vérifiez la configuration globale dans **Settings → Admin Settings → Audio**. Le STT et
   le TTS doivent utiliser le fournisseur compatible OpenAI configuré par Maxinus ; leurs
   adresses internes sont `http://stt:8000/v1`. Ce nom fonctionne depuis le conteneur WebUI,
   pas depuis le navigateur de l’utilisateur.
5. Dans les préférences utilisateur **Settings → Audio**, définissez le français si le
   réglage de langue est disponible.
6. Ouvrez une conversation avec un seul modèle sélectionné, cliquez sur le bouton Voice
   Mode/Appel vocal et autorisez le microphone du navigateur.
7. Pour que l’assistant lise sa réponse, activez la lecture vocale/Auto-play si elle est
   proposée dans cette version d’Open WebUI. Vous pouvez choisir la voix Kokoro `ff_siwis`.
8. Activez **Allow Voice Interruption in Call** dans les préférences d’interface si vous
   voulez couper la réponse en parlant.

Pour une petite installation familiale, chaque personne peut utiliser son propre compte
Open WebUI. L’administrateur peut gérer les comptes depuis les paramètres d’administration.
Chaque compte peut avoir ses conversations et préférences ; les données restent sur le
volume partagé de cette instance. Un compte n’est pas un bac à sable de sécurité pour des
personnes qui ne se font pas confiance : ne rendez pas cette instance accessible à des
inconnus sans configuration serveur adaptée.

Les libellés peuvent varier avec les versions d’Open WebUI. Le script de démarrage configure
les clés STT/TTS dans la base de données existante à partir des variables du Compose. Ne
remplacez pas l’adresse interne `stt` par `localhost` : dans Docker, `localhost` désigne le
conteneur Open WebUI lui-même.

Le mode vocal standard attend une pause à la fin de votre phrase, transcrit l’audio, puis
génère la réponse. Le texte peut s’afficher au fil de la génération et être prononcé par
segments. Le silence, le temps de génération du modèle et les réglages de découpage
influencent la latence. Ce pipeline n’est pas un modèle audio natif full-duplex comparable
à une expérience voix-à-voix cloud.

## 6. Utilisation et commandes d’administration

```bash
# État des services
docker compose --env-file .env -f docker/compose.yaml ps

# Journaux en direct (Ctrl+C quitte seulement le suivi)
docker compose --env-file .env -f docker/compose.yaml logs -f

# Journaux d'un service précis
docker compose --env-file .env -f docker/compose.yaml logs -f webui
docker compose --env-file .env -f docker/compose.yaml logs -f stt

# Redémarrer ou arrêter sans effacer les conversations
docker compose --env-file .env -f docker/compose.yaml restart
docker compose --env-file .env -f docker/compose.yaml stop

# Redémarrer ensuite
docker compose --env-file .env -f docker/compose.yaml up -d
```

Sur Mac, `./maxinus-live.command` ouvre l’interface et `./stop-maxinus.command` arrête
les conteneurs sans supprimer le volume.

## 7. Données, mise à jour et désinstallation

Le volume Docker `open-webui` contient les comptes, conversations, réglages et cache
Whisper. Les poids Kokoro sont dans le dossier local `models/`. Le modèle Ollama appartient
au magasin local géré par Ollama. Arrêter ou reconstruire les conteneurs ne supprime pas
ces données.

Avant une mise à jour importante, faites une sauvegarde, puis :

```bash
docker compose --env-file .env -f docker/compose.yaml build --pull
docker compose --env-file .env -f docker/compose.yaml up -d
```

Pour arrêter et enlever les conteneurs sans effacer les données :

```bash
docker compose --env-file .env -f docker/compose.yaml down
```

Ne régénérez pas `.env` à chaque démarrage : gardez la même clé secrète pour une instance
existante. Régénérer cette clé peut invalider les sessions et certaines données chiffrées.

> **Attention, perte définitive :** `docker volume rm open-webui` supprime les comptes,
> conversations, réglages et caches du volume. Ne lancez cette commande que si vous avez
> réellement décidé d’effacer les données et vérifié le nom du volume.

Pour une sauvegarde ou une migration vers une autre machine, suivez
[le guide de déploiement](DEPLOYMENT.md), qui décrit aussi le chiffrement et la restauration.

## 8. Dépannage

### Open WebUI ne s’ouvre pas

```bash
docker compose --env-file .env -f docker/compose.yaml ps
docker compose --env-file .env -f docker/compose.yaml logs --tail 100 webui
curl -v http://127.0.0.1:3000/health
```

Vérifiez que Docker est démarré, que le port 3000 n’est pas déjà utilisé et que `.env`
contient `WEBUI_SECRET_KEY`.

### La liste des modèles est vide ou Ollama est inaccessible

```bash
ollama list
curl http://127.0.0.1:11434/api/tags
docker exec maxinus-webui python -c "import urllib.request; print(urllib.request.urlopen('http://host.docker.internal:11434/api/tags', timeout=5).status)"
```

Ollama doit tourner sur l’hôte. Ne mettez pas `http://localhost:11434` dans la connexion
faite par le conteneur : ce `localhost` n’est pas le Mac/Linux hôte. Si Ollama est sur une
autre machine, il faut une adresse réseau joignable depuis Docker, une configuration
Ollama qui accepte ce trafic et un pare-feu strictement réglé.

### La transcription échoue, est vide ou affiche une erreur de connexion

```bash
docker compose --env-file .env -f docker/compose.yaml ps
docker compose --env-file .env -f docker/compose.yaml logs --tail 150 stt
docker compose --env-file .env -f docker/compose.yaml logs --tail 150 webui
docker exec maxinus-stt python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health').status)"
```

Attendez l’état `healthy`, essayez une phrase courte, vérifiez le microphone et la langue
française. Whisper peut télécharger ses poids à la première utilisation si le préchargement
n’a pas été exécuté ; cette première requête prend plus longtemps et nécessite Internet.
Une erreur `Connection reset by peer` répétée peut indiquer un service STT redémarré,
manquant ou à court de mémoire : vérifiez `ps`, puis les journaux des deux conteneurs.

### Pas de son, voix trop lente ou Kokoro indisponible

- vérifiez le volume du système et la sortie audio du navigateur ;
- vérifiez la présence des deux fichiers Kokoro dans `models/` ;
- consultez `docker compose ... logs stt` ;
- évitez les longues réponses et réduisez la taille du modèle Ollama si la machine manque de
  mémoire.

### Le navigateur ne donne pas accès au micro

Le Compose lie volontairement l’interface à `127.0.0.1`; ouvrez-la depuis le navigateur du
même ordinateur. Les navigateurs exigent généralement HTTPS ou `localhost` pour autoriser
le microphone. Accéder directement à `http://IP-DU-SERVEUR:3000` depuis un téléphone n’est
pas une méthode de déploiement vocal distant adaptée. Pour un accès distant, configurez un
nom DNS, HTTPS et un proxy inverse sécurisé, ou un VPN adapté ; ne publiez pas les ports
3000, 8000 ou 11434 directement sur Internet.

## 9. Repères et documentation officielle

- [Open WebUI — démarrage et connexion à Ollama](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-ollama/)
- [Open WebUI — mode vocal](https://docs.openwebui.com/features/chat-conversations/chat-features/voice-mode/)
- [Open WebUI — configuration de la reconnaissance vocale](https://docs.openwebui.com/features/chat-conversations/audio/speech-to-text/stt-config/)
- [Open WebUI — protection et rotation de la clé secrète](https://docs.openwebui.com/getting-started/advanced-topics/hardening/)
- [Docker — réseau et résolution des services Compose](https://docs.docker.com/compose/how-tos/networking/)
- [Docker Desktop — installation sur Mac](https://docs.docker.com/desktop/setup/install/mac-install/)
