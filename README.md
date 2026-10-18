# Maxinus — assistant vocal local

[![CI](https://github.com/Salif50/MaxinusIA/actions/workflows/ci.yml/badge.svg)](https://github.com/Salif50/MaxinusIA/actions/workflows/ci.yml)
[![Licence MIT](https://img.shields.io/badge/licence-MIT-green.svg)](LICENSE)
[![macOS Apple Silicon](https://img.shields.io/badge/macOS-Apple%20Silicon-lightgrey.svg)](https://ollama.com/download/mac)

Maxinus permet de parler à un assistant en français depuis un navigateur, en utilisant un
modèle de langage exécuté localement par Ollama. Le parcours vocal recommandé utilise
Open WebUI pour la conversation, Whisper pour reconnaître la parole, Qwen (ou un autre modèle
Ollama) pour raisonner et Kokoro pour répondre à voix haute.

Le projet a été développé et réglé sur un **MacBook Pro avec puce Apple M5 et 16 Go de mémoire**.
Les performances dépendent du modèle choisi et de la machine : un modèle plus petit répond
plus vite, un modèle plus grand demande davantage de mémoire.

## Sommaire

- [Ce qu’il faut avant de commencer](#ce-quil-faut-avant-de-commencer)
- [Choisir un modèle selon son ordinateur](#choisir-un-modèle-selon-son-ordinateur)
- [Installer Ollama et télécharger un modèle](#installer-ollama-et-télécharger-un-modèle)
- [Installer et lancer Maxinus en local](#installer-et-lancer-maxinus-en-local)
- [Changer de modèle](#changer-de-modèle)
- [Commandes utiles](#commandes-utiles)
- [Confidentialité et fonctionnement vocal](#confidentialité-et-fonctionnement-vocal)
- [Dépannage](#dépannage)
- [Alternatives pour une conversation encore plus « live »](#alternatives-pour-une-conversation-encore-plus-live)
- [Organisation du dépôt](#organisation-du-dépôt)

## Ce qu’il faut avant de commencer

Le chemin d’installation décrit ici concerne macOS Apple Silicon. Pour le mode Maxinus Live,
installez :

1. **Ollama**, qui exécute les modèles de langage sur l’ordinateur ;
2. **Docker Desktop**, qui lance Open WebUI et le service vocal local ;
3. un navigateur récent autorisé à accéder au microphone ;
4. le dépôt Maxinus et une connexion Internet pour le premier téléchargement.

Prévoir environ **15 à 25 Go d’espace libre** pour les modèles et images Docker. Le modèle
choisi s’ajoute à cet espace. Après l’installation et le téléchargement des modèles, le
dialogue vocal courant peut fonctionner sans envoyer l’audio à un service cloud.

Téléchargements officiels : [Ollama pour macOS](https://ollama.com/download/mac) et
[Docker Desktop pour Mac](https://docs.docker.com/desktop/setup/install/mac-install/).
Docker Desktop demande une version macOS prise en charge par Docker ; suivez la version
indiquée sur sa page d’installation.

## Choisir un modèle selon son ordinateur

La taille indiquée dans le tableau est la taille approximative du téléchargement Ollama en
quantification par défaut. Pendant l’utilisation, le modèle, son contexte et les autres
applications consomment aussi de la mémoire. Gardez de la marge pour macOS, Docker, Whisper
et Kokoro.

| Mémoire de l’ordinateur | Choix de départ | À quoi s’attendre |
| --- | --- | --- |
| 8 Go | `qwen2.5:3b` (~1,9 Go) | Plus léger, adapté aux petites tâches ; qualité et raisonnement plus limités. |
| 16 Go | `qwen2.5:7b` (~4,7 Go) | Bon compromis pour parler sans trop saturer la mémoire. |
| 16 Go, comme la machine de développement | `qwen2.5:14b` (~9 Go) | Plus capable, mais peut ralentir ou utiliser la mémoire virtuelle quand Docker et la voix tournent ensemble. |
| 24–32 Go ou plus | `qwen2.5:14b` ou modèle plus grand | Plus de marge pour le contexte et le multitâche ; choisir selon la vitesse voulue. |

Ces profils sont des repères, pas une garantie de vitesse. Sur un ordinateur de 16 Go, essayez
d’abord le 7B si le 14B met trop de temps à répondre. Les modèles disponibles, leurs tailles
et leurs tags évoluent : vérifiez le catalogue Ollama avant d’en choisir un.

Quelques modèles gratuits à télécharger depuis le catalogue Ollama :

| Modèle | Taille Ollama indicative | Exemple de commande |
| --- | ---: | --- |
| Qwen 2.5 3B | ~1,9 Go | `ollama pull qwen2.5:3b` |
| Qwen 2.5 7B | ~4,7 Go | `ollama pull qwen2.5:7b` |
| Qwen 2.5 14B | ~9 Go | `ollama pull qwen2.5:14b` |
| Gemma 4 E2B | ~4–6 Go selon variante | `ollama pull gemma4:e2b` |
| Gemma 4 E4B | vérifier la taille courante | `ollama pull gemma4:e4b` |

« Gratuit » signifie ici que les poids sont téléchargeables sans payer une API à chaque
message. Chaque famille de modèles garde sa propre licence et ses conditions d’utilisation.
Consultez la fiche du modèle avant un usage professionnel.

Références : [catalogue Ollama Qwen 2.5](https://ollama.com/library/qwen2.5/tags),
[catalogue Ollama Gemma 4](https://ollama.com/library/gemma4/tags) et
[catalogue complet Ollama](https://ollama.com/library).

## Installer Ollama et télécharger un modèle

### Installer Ollama sur macOS

Téléchargez Ollama depuis [ollama.com/download/mac](https://ollama.com/download/mac), ouvrez
l’application et suivez les étapes d’installation. Ollama doit tourner avant de lancer
Maxinus.

Si Homebrew est déjà installé, l’application et son binaire CLI peuvent aussi être installés
avec :

```bash
brew install --cask ollama-app
```

Docker Desktop peut être installé avec Homebrew également :

```bash
brew install --cask docker
```

Sinon, utilisez les installateurs graphiques officiels indiqués dans les prérequis. Après
l’installation, ouvrez Ollama et Docker Desktop depuis le dossier Applications.

Dans Terminal, vérifiez son installation :

```bash
ollama --version
```

### Télécharger et essayer un modèle

Choisissez **un** modèle correspondant à votre mémoire. Exemple recommandé pour commencer
sur une machine de 16 Go :

```bash
ollama pull qwen2.5:7b
ollama run qwen2.5:7b
```

Posez une question dans le terminal Ollama. Pour terminer la session, tapez `/bye`. Si vous
préférez le 14B :

```bash
ollama pull qwen2.5:14b
ollama run qwen2.5:14b
```

Pour voir les modèles installés et leur espace disque :

```bash
ollama list
```

Pour vérifier que l’API locale répond :

```bash
curl http://127.0.0.1:11434/api/tags
```

Si la commande indique que le serveur Ollama est arrêté, ouvrez l’application Ollama depuis
Applications et réessayez. Ne lancez pas une seconde instance `ollama serve` si l’application
Ollama sert déjà l’API.

Les modèles du catalogue sont gérés par Ollama. Pour en installer un autre :

```bash
ollama pull nom-du-modele:tag
ollama run nom-du-modele:tag
```

Par exemple, selon la mémoire disponible :

```bash
ollama pull qwen2.5:3b
ollama pull qwen2.5:7b
ollama pull qwen2.5:14b
ollama pull gemma4:e2b
```

N’installez pas toutes les variantes par défaut : chaque modèle utilise de l’espace disque.

## Installer et lancer Maxinus en local

1. Placez le dossier du projet sur le Mac et ouvrez Terminal dans ce dossier.
2. Confirmez qu’Ollama répond (`curl http://127.0.0.1:11434/api/tags`).
3. Ouvrez Docker Desktop et attendez qu’il soit démarré.
4. Lancez l’installateur avec le modèle choisi.

Exemple pour le 7B :

```bash
MAXINUS_MODEL=qwen2.5:7b ./setup.sh live
```

Exemple pour le 14B :

```bash
MAXINUS_MODEL=qwen2.5:14b ./setup.sh live
```

Si `MAXINUS_MODEL` est omis, l’installation utilise `qwen2.5:14b`. L’installateur
télécharge le modèle Ollama s’il manque, télécharge les poids Kokoro français si nécessaire,
crée une clé privée dans `.env`, construit les images Docker et lance les services locaux
Whisper et Kokoro.

Une fois l’installation finie, ouvre Maxinus :

```bash
./maxinus-live.command
```

L’adresse locale est [http://127.0.0.1:3000](http://127.0.0.1:3000). Au premier lancement,
créez le compte administrateur, choisissez le modèle Ollama dans la liste, autorisez le
microphone dans le navigateur, puis ouvrez le mode vocal.

L’installation complète et les détails de configuration sont dans [docs/SETUP.md](docs/SETUP.md).

## Changer de modèle

Une fois Maxinus installé, téléchargez un autre modèle :

```bash
ollama pull qwen2.5:7b
```

Puis, dans Open WebUI, sélectionnez le modèle téléchargé dans le sélecteur de modèle en haut
de la conversation. Vous n’avez pas besoin de réinstaller Maxinus. Le modèle doit apparaître
dans `ollama list` avant d’être sélectionnable.

Dans le mode CLI historique, le modèle se règle dans `config.json` :

```json
{
  "ollama_model": "qwen2.5:7b"
}
```

Gardez les autres paramètres de `config.example.json` si vous n’avez pas besoin de les
modifier.

## Commandes utiles

```bash
./maxinus-live.command       # démarrer Maxinus Live et ouvrir le navigateur
./stop-maxinus.command       # arrêter Maxinus Live proprement
docker compose --env-file .env -f docker/compose.yaml ps
docker compose --env-file .env -f docker/compose.yaml logs -f
ollama list                  # modèles Ollama disponibles localement
```

Le mode Terminal historique s’installe séparément :

```bash
./setup.sh cli
./maxinus.command
```

Le mode CLI accède directement aux périphériques audio macOS via PortAudio. Si un pilote USB
provoque une erreur CoreAudio, utilisez plutôt Maxinus Live, qui passe par le navigateur.

## Confidentialité et fonctionnement vocal

Maxinus Live utilise cette chaîne :

```text
Micro du navigateur → Whisper local → modèle Ollama local → Kokoro français → haut-parleurs
```

Le serveur STT et TTS tourne dans Docker, sans port publié sur le réseau. Open WebUI est lié
à `127.0.0.1:3000`, et Ollama répond sur `127.0.0.1:11434`. Le premier compte, les réglages
et les conversations sont conservés dans le volume Docker `open-webui`.

Après les téléchargements initiaux, la chaîne ci-dessus n’a pas besoin d’une API payante.
Pour une confidentialité stricte, déconnectez Internet après l’installation et vérifiez
qu’Ollama n’utilise pas un modèle cloud. Les fonctionnalités qui cherchent des informations
sur le Web ne fonctionneront alors pas.

## Dépannage

**Ollama n’est pas joignable**

Ouvrez l’application Ollama, puis lancez :

```bash
curl http://127.0.0.1:11434/api/tags
ollama list
```

**Le modèle choisi n’apparaît pas dans Open WebUI**

Téléchargez-le avec `ollama pull nom:tag`, actualisez la page et vérifiez que le service
Ollama tourne.

**Maxinus Live ne démarre pas**

Ouvrez Docker Desktop puis vérifiez les services et les journaux :

```bash
docker compose --env-file .env -f docker/compose.yaml ps
docker compose --env-file .env -f docker/compose.yaml logs --tail 100
curl http://127.0.0.1:3000/health
```

**Le navigateur n’entend pas le microphone**

Dans les réglages macOS, autorisez l’accès au microphone pour votre navigateur. Vérifiez
également que le bon microphone est sélectionné dans macOS et dans le navigateur.

**La transcription ou la réponse est lente**

Vérifiez d’abord si le modèle 14B utilise toute la mémoire. Essayez `qwen2.5:7b`, fermez les
applications lourdes, puis relancez la conversation. Le 7B est généralement un meilleur choix
pour la latence sur 16 Go.

**Consulter les journaux des composants vocaux**

```bash
docker logs --tail 100 maxinus-stt
docker logs --tail 100 maxinus-webui
```

Pour une installation sur un autre Mac, une sauvegarde ou une mise à jour, consultez
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Alternatives pour une conversation encore plus « live »

Maxinus par défaut est une chaîne locale en plusieurs étapes : Whisper transcrit la phrase,
Ollama génère le texte, puis Kokoro le prononce. Elle garde les données sur la machine et
permet de remplacer chaque composant, mais l’IA attend généralement la fin de la phrase et
la synthèse vocale est moins expressive qu’un modèle audio natif.

### OpenAI Realtime API — voix la plus naturelle, traitement cloud

L’API Realtime d’OpenAI accepte et renvoie l’audio directement, sans étape séparée de
transcription puis de synthèse. Elle est conçue pour une conversation vocale à faible latence,
avec des échanges plus naturels. Elle nécessite une connexion Internet et une clé API ; le
son et les requêtes sont traités par le fournisseur, et la facturation dépend des tarifs en
vigueur. Dans cette configuration, Qwen local ne serait plus le moteur qui répond à l’oral.

Documentation : [OpenAI Realtime conversations](https://developers.openai.com/api/docs/guides/realtime-conversations)
et [tarifs API OpenAI](https://openai.com/api/pricing/).

### LiveKit Agents — framework pour construire un vrai agent vocal

LiveKit Agents permet de construire une application vocale dédiée. On peut garder une
chaîne Whisper + Ollama + Kokoro, ou brancher un modèle speech-to-speech comme OpenAI
Realtime. Le framework gère le transport audio, les tours de parole et les interruptions.
Il offre plus de contrôle que l’interface actuelle, mais demande de développer et déployer
un service agent supplémentaire.

Documentation : [LiveKit voice pipelines](https://docs.livekit.io/agents/models/pipelines/),
[gestion des tours de parole](https://docs.livekit.io/agents/logic/turns/) et
[intégration OpenAI](https://docs.livekit.io/agents/integrations/openai/).

| Option | Où tourne le raisonnement et la voix | Réactivité et naturel | Travail à prévoir |
| --- | --- | --- | --- |
| Maxinus actuel | Local : Ollama, Whisper, Kokoro | Bonne confidentialité ; délai lié au modèle local et aux étapes STT/LLM/TTS. | Installé et prêt avec ce dépôt. |
| Maxinus avec un modèle local plus petit | Local, par exemple Qwen 7B | Réponses plus rapides sur une machine limitée ; raisonnement un peu moins puissant que 14B. | Télécharger le modèle puis le sélectionner. |
| OpenAI Realtime | Cloud OpenAI, audio de bout en bout | Le plus proche d’une conversation voix-à-voix fluide et expressive. | Clé API, coût d’usage et transfert audio au fournisseur. |
| LiveKit Agents + modèles au choix | Local ou cloud selon les composants | Peut approcher une expérience temps réel ; beaucoup de contrôle. | Développer un agent et choisir le transport et les fournisseurs. |

Pour rester strictement local, gardez le pipeline Maxinus et essayez d’abord un modèle plus
petit. Pour obtenir un rendu voix-à-voix comparable aux assistants vocaux cloud, l’API
Realtime est l’option la plus directe, avec les compromis de confidentialité et de coût
décrits ci-dessus.

## Organisation du dépôt

```text
MaxinusIA/
├── src/maxinus/                 application Python du mode CLI
├── services/stt/                API locale Whisper + Kokoro compatible OpenAI
├── docker/                      Dockerfile, Compose et démarrage Open WebUI
├── scripts/                      installateurs et outils de configuration
├── scripts/macos/               outil CoreAudio du mode CLI
├── docs/SETUP.md                guide complet de fonctionnement
├── docs/DEPLOYMENT.md            guide pour un autre ordinateur
├── models/                       poids locaux, ignorés par Git
├── data/                         mémoire et cache du mode CLI, ignorés par Git
├── setup.sh                      installateur principal : live, cli ou all
├── maxinus-live.command          lanceur navigateur
├── maxinus.command               lanceur Terminal historique
└── stop-maxinus.command          arrêt de Maxinus Live
```

Les fichiers locaux `.env`, `config.json`, `models/` et `data/` ne doivent pas être ajoutés
au dépôt public. La clé `.env` est générée pour chaque installation.

Le code original de Maxinus est sous licence MIT. Open WebUI, Ollama, les bibliothèques
Python et les poids des modèles tiers gardent leurs licences respectives ; consultez leurs
pages officielles avant toute redistribution ou usage commercial.

## Licence

Voir [LICENSE](LICENSE). Vérifiez également la licence du modèle Ollama que vous choisissez.
