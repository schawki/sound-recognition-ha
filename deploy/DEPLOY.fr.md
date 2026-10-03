# Déploiement de test (LXC Proxmox)

Recette courte pour faire tourner le service dans son propre conteneur Debian 13 non privilégié. Le tutoriel utilisateur complet viendra quand le projet sera terminé.

## 1. Sur l'hôte Proxmox

Téléchargez le script et lancez-le en root (il clone le dépôt GitHub dans le conteneur) :

```bash
curl -fsSLO https://raw.githubusercontent.com/schawki/sound-recognition-ha/main/deploy/create-lxc.sh
bash create-lxc.sh
```

Il demande confirmation, crée le conteneur (2 vCPU, 1 Go de RAM, 8 Go de disque, démarrage automatique), installe git et ffmpeg, clone le projet, installe le service et le modèle YAMNet, puis le démarre. Les valeurs par défaut se changent par variables d'environnement, par exemple :

```bash
CTID=210 STORAGE=local-zfs BRIDGE=vmbr0 IP=192.168.1.50/24 GATEWAY=192.168.1.1 bash create-lxc.sh
```

(toutes les variables sont listées en tête du script, dont `REPO_URL`/`REF` pour installer une autre branche ou un fork). Sans accès à GitHub, copiez le dépôt sur le nœud et lancez `SOURCE=local bash deploy/create-lxc.sh` depuis celui-ci. À la fin, le script affiche l'adresse du conteneur et le jeton d'API.

## 2. Vérifier

```bash
curl http://<ip-du-conteneur>:8765/api/v1/health   # {"status": "ok", ...}
pct exec <CTID> -- journalctl -u soundrec -f       # journaux
```

## 3. Home Assistant

Installez l'intégration via HACS (trois points → *Dépôts personnalisés* → `https://github.com/schawki/sound-recognition-ha`, catégorie *Intégration*) ou en copiant `custom_components/sound_recognition` dans `/config/custom_components/`, redémarrez HA, puis *Paramètres → Appareils et services → Ajouter une intégration → Sound recognition* avec l'adresse du conteneur (port 8765) et le jeton. Une entrée *Sound recognition* apparaît dans la barre latérale (administrateurs uniquement).

## Où se trouvent les choses dans le conteneur

| Quoi | Où |
|---|---|
| Configuration (YAML, source de vérité) | `/etc/soundrec/config.yaml` |
| Code, venv, catalogue, modèle | `/opt/soundrec/` |
| Extraits et base d'événements | `/var/lib/soundrec/` |
| Service | `systemctl status soundrec` |

Mise à jour (le projet est cloné dans `/opt/sound-recognition-ha` ; config et données conservées) :

```bash
pct exec <CTID> -- bash -c 'git -C /opt/sound-recognition-ha pull && bash /opt/sound-recognition-ha/deploy/install.sh'
```


Redémarrage après modification manuelle du YAML : `systemctl restart soundrec`.

## Dépannage

- Le service échoue avec `226/NAMESPACE` : l'installeur bascule déjà sur un réglage sans sandbox ; voir `journalctl -u soundrec`.
- Pas de modèle Debian 13 : `pveam update` sur l'hôte, ou mettre Proxmox à jour.
- Une IP statique exige `GATEWAY`.
