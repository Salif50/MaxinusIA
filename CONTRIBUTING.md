# Contribuer à Maxinus

Les contributions sont les bienvenues : corrections de bugs, amélioration de la voix,
compatibilité matérielle, documentation et installation.

## Avant d’ouvrir une pull request

1. Ouvrez une issue pour les changements importants afin de discuter de leur portée.
2. Gardez les traitements vocaux locaux par défaut et documentez clairement toute option
   qui envoie des données à un fournisseur distant.
3. N’ajoutez jamais de clés, fichiers `.env`, conversations, enregistrements audio ou poids
   de modèles au dépôt.
4. Mettez à jour le README ou les guides dans `docs/` lorsque les commandes ou le
   comportement utilisateur changent.
5. Décrivez les changements et la façon dont vous les avez vérifiés dans la pull request.

## Vérifications locales

```bash
python -m compileall -q src services scripts
zsh -n setup.sh scripts/install-live.sh scripts/install-cli.sh
docker compose --env-file .env -f docker/compose.yaml config --quiet
```

GitHub Actions exécute les vérifications de syntaxe et valide le fichier Compose pour chaque
push et pull request.
