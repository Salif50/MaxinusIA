#!/bin/zsh
cd "${0:A:h}"
echo "Réinitialisation du service audio macOS…"
echo "Votre mot de passe administrateur peut être demandé (il ne s'affichera pas)."
sudo killall coreaudiod
sleep 4
echo
echo "CoreAudio a redémarré. Vous pouvez fermer cette fenêtre et relancer Maxinus."
read -k 1
