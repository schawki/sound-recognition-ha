# Déploiement de test (LXC Proxmox)

Recette courte pour faire tourner le service dans son propre conteneur Debian 13 non privilégié. Le tutoriel utilisateur complet viendra quand le projet sera terminé.

## 1. Sur l'hôte Proxmox

Copiez le dépôt (par ex. `sound-recognition-ha.zip`) sur le nœud, décompressez-le puis lancez le script en root :

```bash
python3 -m zipfile -e sound-recognition-ha.zip /root/     # ou : unzip sound-recognition-ha.zip -d /root
cd /root/sound-recognition-ha
bash deploy/create-lxc.sh
```

Il demande confirmation, crée le conteneur (2 vCPU, 1 Go de RAM, 8 Go de disque, démarrage automatique), installe ffmpeg, le service et le modèle YAMNet, puis le démarre. Les valeurs par défaut se changent par variables d'environnement, par exemple :

```bash
CTID=210 STORAGE=local-zfs BRIDGE=vmbr0 IP=192.168.1.50/24 GATEWAY=192.168.1.1 bash deploy/create-lxc.sh
```

(toutes les variables sont listées en tête de `deploy/create-lxc.sh`). À la fin, il affiche l'adresse du conteneur et le jeton d'API.

## 2. Vérifier

```bash
curl http://<ip-du-conteneur>:8765/api/v1/health   # {"status": "ok", ...}
pct exec <CTID> -- journalctl -u soundrec -f       # journaux
```

## 3. Home Assistant

Installez l'intégration via HACS (dépôt personnalisé, catégorie *Intégration*) ou en copiant `custom_components/sound_recognition` dans `/config/custom_components/`, redémarrez HA, puis *Paramètres → Appareils et services → Ajouter une intégration → Sound recognition* avec l'adresse du conteneur (port 8765) et le jeton. Une entrée *Sound recognition* apparaît dans la barre latérale (administrateurs uniquement).

## Où se trouvent les choses dans le conteneur

| Quoi | Où |
|---|---|
| Configuration (YAML, source de vérité) | `/etc/soundrec/config.yaml` |
| Code, venv, catalogue, modèle | `/opt/soundrec/` |
| Extraits et base d'événements | `/var/lib/soundrec/` |
| Service | `systemctl status soundrec` |

Mise à jour : copiez la nouvelle version dans le conteneur et relancez `bash deploy/install.sh` (config et données conservées).
Redémarrage après modification manuelle du YAML : `systemctl restart soundrec`.

## Dépannage

- Le service échoue avec `226/NAMESPACE` : l'installeur bascule déjà sur un réglage sans sandbox ; voir `journalctl -u soundrec`.
- Pas de modèle Debian 13 : `pveam update` sur l'hôte, ou mettre Proxmox à jour.
- Une IP statique exige `GATEWAY`.
