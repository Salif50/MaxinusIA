# Déployer Maxinus chez une autre personne

Ce guide installe une copie indépendante de Maxinus sur un autre Mac. Ne copiez pas votre
`.env`, vos conversations ou votre base personnelle, sauf demande explicite du propriétaire
et transfert sécurisé.

Pour l’architecture des conteneurs, une installation Docker manuelle et la configuration
pas à pas d’Open WebUI et du mode vocal, consultez aussi
[Déployer Maxinus Live avec Docker et Open WebUI](DOCKER.md).

## 1. Préparer le paquet

Le plus simple est de laisser la personne cloner le dépôt public :

```bash
git clone https://github.com/Salif50/MaxinusIA.git
cd MaxinusIA
```

Ou transférez une copie propre en excluant les éléments propres à votre machine :

```text
.env
config.json
.venv/
data/
models/
backups/
__pycache__/
*.egg-info/
```

Ces exclusions sont déjà dans `.gitignore`. Utilisez de préférence un dépôt Git privé ou
une archive créée depuis une copie propre.

## 2. Préparer le Mac destinataire

Installez Docker Desktop et Ollama, puis ouvrez une première fois les deux applications.
Vérifiez :

```bash
docker info
ollama --version
curl http://127.0.0.1:11434/api/tags
```

Prévoyez environ 15 Go d'espace libre. Une machine de 16 Go de RAM peut utiliser le 14B,
mais le 7B sera plus réactif.

## 3. Installer le projet

Placez le dossier, par exemple dans `~/Applications/MaxinusIA`, puis :

```bash
cd ~/Applications/MaxinusIA
chmod +x setup.sh scripts/*.sh *.command scripts/macos/*.command
./setup.sh live
```

La commande télécharge le modèle Ollama et les poids Kokoro si nécessaire, construit
l'image Docker locale, génère une nouvelle clé propre à cette machine et précharge Whisper.

Pour installer directement la variante 7B, définissez le modèle au lancement :

```bash
MAXINUS_MODEL=qwen2.5:7b ./setup.sh live
```

Sans cette variable, l'installateur choisit `qwen2.5:14b`.

## 4. Initialiser le compte et la voix

```bash
./maxinus-live.command
```

La personne destinataire doit elle-même créer le premier compte administrateur, choisir le
modèle Ollama, autoriser le microphone et activer la lecture automatique ainsi que
l'interruption vocale. Kokoro `ff_siwis` est configuré comme voix française locale. Ne créez
pas son mot de passe à sa place.

## 5. Vérifier la livraison

```bash
docker compose --env-file .env -f docker/compose.yaml ps
curl http://127.0.0.1:3000/health
curl http://127.0.0.1:11434/api/tags
```

Les services `maxinus-stt` et `maxinus-webui` doivent être actifs, et le STT doit être
`healthy`. Testez ensuite la transcription française, la réponse de Qwen, la lecture vocale
et l'interruption en parlant.

## 6. Sécurité réseau

La configuration publie Open WebUI uniquement sur `127.0.0.1`. Elle convient à un usage
personnel sur le Mac, pas à un serveur Internet.

N'exposez jamais directement les ports `3000` ou `11434` sur Internet. Un accès distant
demande HTTPS, un proxy inverse, une authentification forte et un pare-feu ; cette
configuration n'est volontairement pas incluse.

## 7. Sauvegarder les conversations

```bash
mkdir -p backups
docker run --rm -v open-webui:/data:ro -v "$PWD/backups:/backup" alpine sh -c 'tar -czf /backup/open-webui.tar.gz -C /data .'
```

Le fichier obtenu contient des données personnelles. Chiffrez-le avant tout transfert et
ne le placez pas dans Git.

## 8. Restaurer une sauvegarde

```bash
./stop-maxinus.command
docker run --rm -v open-webui:/data -v "$PWD/backups:/backup:ro" alpine sh -c 'tar -xzf /backup/open-webui.tar.gz -C /data'
./maxinus-live.command
```

La restauration doit être effectuée uniquement pour le propriétaire des données.

## 9. Maintenance

```bash
# Mise à jour
docker compose --env-file .env -f docker/compose.yaml build --pull
docker compose --env-file .env -f docker/compose.yaml up -d

# Arrêt
./stop-maxinus.command

# Journaux
docker compose --env-file .env -f docker/compose.yaml logs --tail 200
```

Ne lancez jamais `docker volume rm open-webui` pendant une maintenance : cette commande
supprimerait définitivement les comptes, conversations, réglages et caches.
