# Installer le service de reconnaissance

Le **service** est la partie qui écoute : il lit vos flux audio, fait tourner le modèle YAMNet et envoie à Home Assistant ce qu'il entend. Il tourne **en dehors** de Home Assistant, dans son propre conteneur ou sa propre machine, pour que l'analyse audio ne ralentisse jamais Home Assistant. L'intégration (installée avec HACS) s'y connecte ensuite.

## Ce qu'il faut

- Une machine ou un conteneur Linux toujours allumé : **2 cœurs, 1 Go de RAM et 8 Go de disque** suffisent (dix sources simultanées ont utilisé environ 12 % d'un cœur et 0,6 Go de RAM lors de nos mesures). Pas de carte graphique nécessaire.
- Des sources audio lisibles en flux : une caméra ou un flux go2rtc (RTSP), un Raspberry Pi avec un micro, ou toute URL qu'ffmpeg sait ouvrir. Voir [Ajouter une source audio](#ajouter-une-source-audio).
- Un accès réseau de Home Assistant vers le service sur le port **8765**.
- Un accès internet pendant l'installation seulement (ffmpeg, paquets Python et modèle YAMNet, dont le SHA-256 est vérifié).

## Option A : conteneur Proxmox (recommandé, une commande)

Sur l'hôte Proxmox, en root :

```bash
curl -fsSLO https://raw.githubusercontent.com/schawki/sound-recognition-ha/main/deploy/create-lxc.sh
bash create-lxc.sh
```

Le script demande confirmation, crée un conteneur Debian 13 non privilégié, installe le service, le démarre et affiche à la fin l'**adresse** et le **jeton d'accès**. Gardez-les pour l'étape Home Assistant. Les options (numéro de conteneur, stockage, réseau, IP fixe) sont dans [deploy/DEPLOY.fr.md](../deploy/DEPLOY.fr.md#dépannage).

## Option B : n'importe quelle machine Debian ou Ubuntu

```bash
apt-get update && apt-get install -y git
git clone https://github.com/schawki/sound-recognition-ha /opt/sound-recognition-ha
bash /opt/sound-recognition-ha/deploy/install.sh
```

L'installeur met en place ffmpeg, un environnement Python, le modèle et un service systemd nommé `soundrec`. Relancez-le plus tard pour mettre à jour ; votre configuration (`/etc/soundrec/config.yaml`) et vos données (`/var/lib/soundrec/`) sont conservées. Le jeton est généré au premier démarrage et écrit dans le fichier de configuration :

```bash
grep token /etc/soundrec/config.yaml
```

## Option C : Docker

Un `Dockerfile` est fourni (il télécharge et vérifie le modèle pendant la construction). **Cette voie n'a pas encore été testée** : signalez tout problème.

```bash
git clone https://github.com/schawki/sound-recognition-ha && cd sound-recognition-ha
docker build -f service/Dockerfile -t sound-recognition-ha .
docker run -d --name soundrec --restart unless-stopped -p 8765:8765 \
  -v soundrec-config:/config -v soundrec-data:/data sound-recognition-ha
docker exec soundrec grep token /config/config.yaml
```

Avec Docker, le service ne peut pas être mis à jour depuis Home Assistant : reconstruisez l'image.

## Vérifier que ça tourne

```bash
curl http://<adresse-du-service>:8765/api/v1/health     # {"status": "ok", ...}
journalctl -u soundrec -f                               # journaux (options A et B)
```

## Connecter Home Assistant

1. Dans HACS, trois points → *Dépôts personnalisés* → `https://github.com/schawki/sound-recognition-ha`, catégorie *Intégration* ; installez **Sound Recognition**, puis redémarrez Home Assistant.
2. *Paramètres → Appareils et services → Ajouter une intégration → Sound Recognition*. Saisissez l'adresse du service, le port 8765 et le jeton.
3. Une entrée **Sound Recognition** apparaît dans la barre latérale (administrateurs uniquement).

## Protéger le service (recommandé)

Le service écoute sur le port 8765 en HTTP simple, et le jeton est son seul verrou. Rien d'autre que Home Assistant n'a besoin de l'atteindre : fermez-le au reste de votre réseau.

1. **Seul Home Assistant peut joindre le port 8765.** Sur Proxmox : le conteneur → *Pare-feu* → *Ajouter* : direction `in`, action `ACCEPT`, protocole `tcp`, port de destination `8765`, source = l'adresse de votre machine Home Assistant ; puis *Pare-feu → Options* : activez le pare-feu et mettez la *politique d'entrée* sur `DROP`. Gardez une règle qui vous laisse joindre le conteneur pour l'administration (SSH, port 22) depuis votre ordinateur, sinon vous vous enfermerez dehors. Sans Proxmox, la même chose avec `ufw` : `ufw allow from <adresse de HA> to any port 8765 proto tcp`, `ufw allow from <votre ordinateur> to any port 22 proto tcp`, puis `ufw enable`.
2. **Ne redirigez jamais le port 8765 sur votre box** et ne le publiez pas par un reverse proxy : passez par Home Assistant, qui relaie ce dont le panneau a besoin.
3. **Gardez le jeton secret**, et changez-le (`token:` dans `/etc/soundrec/config.yaml`, puis redémarrez le service et saisissez le nouveau dans l'intégration) s'il a fuité. Le service ne l'accepte que dans l'en-tête `Authorization`, jamais dans une adresse.
4. **Facultatif : limiter ce que le service peut joindre.** Il n'a besoin que de vos caméras ou de go2rtc, de vos micros ESP32 et de GitHub (pour les mises à jour). Une règle `out` sur le conteneur qui n'autorise que cela et bloque le reste l'empêche de servir à sonder le reste de votre réseau.
5. **Protégez le compte GitHub du dépôt dont le service se met à jour** (double authentification) : une mise à jour installe la dernière version avec les droits d'administrateur sur le conteneur.

## Ajouter une source audio

Dans le panneau, *Sources → Ajouter*. Une source est l'URL d'un flux :

| Source | URL du type |
|---|---|
| Caméra ou flux go2rtc | `rtsp://<hôte>:8554/<flux>` |
| Raspberry Pi avec micro | un flux go2rtc du Pi, `rtsp://<pi>:8554/mic` |
| Fichier de test | un chemin ou une URL qu'ffmpeg sait lire |

Micros ESP32 (ESPHome) : voir [Micro ESP32](esphome-microphone.fr.md).

## Rester à jour

Avec les options A et B, une entité **Mise à jour** et un bandeau du panneau annoncent les nouvelles versions ; *Mettre à jour* installe la dernière version publiée et garde vos réglages. La première fois, lancez une fois la commande de mise à jour manuelle (voir [deploy/DEPLOY.fr.md](../deploy/DEPLOY.fr.md)).

## Problèmes

- *L'intégration n'arrive pas à se connecter* : vérifiez l'adresse, le port 8765 et le jeton ; testez `/api/v1/health` depuis la machine de Home Assistant.
- *Le service ne démarre pas* : `journalctl -u soundrec`. Autres cas dans [deploy/DEPLOY.fr.md](../deploy/DEPLOY.fr.md#dépannage).
- *Une source reste « Démarrage » ou « Déconnectée »* : testez son URL avec `ffprobe <url>` depuis la machine du service ; si cela échoue, c'est le flux le problème, pas le service.
