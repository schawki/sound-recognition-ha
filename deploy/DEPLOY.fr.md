# Déploiement de test (LXC Proxmox)

Recette courte pour faire tourner le service dans son propre conteneur Debian 13 non privilégié. Guide pas à pas, avec Docker et les autres options : [docs/install-service.fr.md](../docs/install-service.fr.md).

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


### Mettre à jour depuis Home Assistant

À partir de la version 0.2.0, l'intégration affiche une entité **Mise à jour** pour le service (*Paramètres → Appareils et services → Sound Recognition*) et une bannière dans le panneau quand une version plus récente existe, ou quand le service est trop ancien pour l'intégration. Appuyez sur *Mettre à jour* (entité ou bannière) : le service redémarre, le panneau suit l'avancement et Home Assistant envoie une notification quand le service est de nouveau en ligne (ou quand la mise à jour a échoué, avec la fin du journal).

Comment cela fonctionne, et ce que c'est autorisé à faire :

- Le service lui-même reste sans privilège. Il dépose seulement un fichier de demande ; un petit assistant root (`soundrec-update`, lancé par l'unité systemd `soundrec-update.path`) fait le travail. L'assistant ne lit que son propre fichier `/etc/soundrec-updater.env` (propriété de root), jamais le contenu de la demande, et écrit son avancement dans `/var/lib/soundrec-update/`, un dossier que le service peut lire mais pas modifier.
- Seules les **versions publiées** (`vX.Y.Z`) sont installées, jamais le bout de `main`. L'assistant avance le clone jusqu'à la dernière étiquette et lance `install.sh` ; en cas d'échec, la version précédente est remise et l'échec est signalé.
- La configuration et les données sont conservées. Après une mise à jour, le clone reste sur `main`, avancé jusqu'à l'étiquette : la commande manuelle `git pull` ci-dessus continue donc de fonctionner.
- Il faut Debian/Ubuntu avec systemd (le LXC de ce guide, ou tout hôte installé avec `install.sh`). Avec Docker, on met à jour en tirant une nouvelle image : l'entité Mise à jour se contente alors d'informer.
- Pour le désactiver : `SOUNDREC_REMOTE_UPDATE=0 bash deploy/install.sh` (l'assistant est retiré). Il est activé par défaut.

**Une mise à jour manuelle est nécessaire** pour installer l'assistant la première fois (l'ancien service ne l'a pas) : lancez une fois la commande de mise à jour ci-dessus, puis mettez à jour l'intégration (HACS + redémarrage de Home Assistant). Ensuite, les mises à jour se lancent depuis Home Assistant. D'ici là, l'entité Mise à jour informe seulement et affiche la commande à lancer.

Redémarrage après modification manuelle du YAML : `systemctl restart soundrec`.

### Déplacer les clips depuis Home Assistant

L'onglet *Réglages* (carte *Stockage*) peut déplacer les clips vers un autre dossier ; voir [Stockage des clips](../docs/storage.fr.md#moving-the-clips). Même principe que la mise à jour : le service sans privilège dépose seulement une demande (`/var/lib/soundrec/update-request/move`, qui porte un chemin de destination) ; un assistant root (`soundrec-move`, lancé par `soundrec-move.path`) fait le travail. Contrairement à l'assistant de mise à jour, il lit bien la destination dans la demande, donc il ne lui fait pas confiance : il revérifie selon des règles que le service ne peut pas changer (le fichier `/etc/soundrec-updater.env`, propriété de root : emplacements autorisés dans `MOVE_ROOTS`, par défaut `/var/lib/soundrec`, `/mnt`, `/media`, `/srv`), n'accepte qu'un dossier absolu, simple, existant et vide (ni lien, ni espace, ni `..`), copie avec le compte du service, vérifie la copie, modifie `clips_dir` dans la configuration, ajoute le dossier au bac à sable (`/etc/systemd/system/soundrec.service.d/clips-path.conf`, reconstruit par `install.sh` d'après la configuration) et redémarre le service. Il ne **supprime jamais** rien et rétablit la configuration précédente si le service ne revient pas. Avancement et journal : `/var/lib/soundrec-update/move.json` et `move.log`. Après un déplacement il mémorise aussi l'ancien dossier dans sa propre liste, propriété de root (`/var/lib/soundrec-update/move-old`) ; une seconde demande (`move-delete`, qui porte l'un de ces dossiers) supprime les clips qui y restent : seulement les dossiers par jour et leurs fichiers `.wav`/`.json`, avec le compte du service (jamais `rm -r`), puis le dossier lui-même s'il est vide. Il refuse le dossier en service, un dossier absent de sa liste, et le cas où le dossier en service ne contient aucun clip alors que l'ancien en contient (état dans `clean.json`, journal `clean.log`).

- Première installation avec les clips ailleurs : `SOUNDREC_CLIPS=/mnt/clips bash deploy/install.sh`, ou `CLIPS_HOST=/mnt/storage/soundrec-clips bash deploy/create-lxc.sh` sur l'hôte Proxmox (point de montage et droits sont gérés).
- `SOUNDREC_REMOTE_MOVE=0` retire l'assistant ; `SOUNDREC_MOVE_ROOTS=/data:/backup` ajoute des emplacements autorisés.

## Dépannage

- Le service échoue avec `226/NAMESPACE` : l'installeur bascule déjà sur un réglage sans sandbox ; voir `journalctl -u soundrec`.
- Pas de modèle Debian 13 : `pveam update` sur l'hôte, ou mettre Proxmox à jour.
- Une IP statique exige `GATEWAY`.
