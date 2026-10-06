# Micro ESP32 (ESPHome)

Un ESP32 avec un micro I2S devient une source de Sound Recognition : il diffuse son audio sur votre réseau et le service l'écoute, comme une caméra. Cette page traite de l'appareil ; le service lui-même s'installe avec [Installer le service](install-service.fr.md).

> **État : pas encore essayé avec un vrai micro.** Le code de l'appareil est vérifié sur PC face au service (audio, mauvais mot de passe, reprise) et compilé par la CI du projet, mais le premier essai sur du vrai matériel reste à faire. Si quelque chose ne marche pas, ouvrez un ticket avec le journal ESPHome.

## Ce qu'il faut

- Une carte **ESP32 ou ESP32-S3** (framework ESP-IDF ; les autres puces ne sont pas couvertes) et l'add-on ESPHome ou un autre moyen de la flasher.
- Un **micro MEMS I2S**, par exemple un INMP441.
- Home Assistant avec l'intégration **ESPHome**, et l'intégration Sound Recognition connectée au service.

## Câblage (INMP441)

| INMP441 | ESP32-S3 (exemple) |
|---|---|
| VDD | 3,3 V |
| GND | GND |
| SCK | GPIO4 |
| WS | GPIO5 |
| SD | GPIO6 |
| L/R | GND (canal gauche) |

Toutes les broches libres conviennent : changez-les dans le YAML. Gardez les fils courts et évitez les broches que votre carte utilise pour la flash ou la PSRAM.

## Configuration ESPHome

Copiez [esphome/example.yaml](../esphome/example.yaml) (le panneau le montre aussi, dans *Sources → Ajouter → Micro ESP32*) dans un nouvel appareil ESPHome, puis ajoutez à `secrets.yaml` :

```yaml
wifi_ssid: "votre Wi-Fi"
wifi_password: "mot de passe du Wi-Fi"
sound_recognition_password: "un mot de passe à vous, 8 caractères ou plus"
```

Flashez. Le bloc `sound_recognition_stream` accepte :

| Option | Sens |
|---|---|
| `microphone` | Le micro `i2s_audio` à diffuser (obligatoire). |
| `password` | Obligatoire, 8 caractères ou plus. Gardez-le dans `secrets.yaml`. |
| `port` | Port TCP du flux, 6055 par défaut. |
| `gain` | Multiplicateur pour un micro faible, 1,0 par défaut (jusqu'à 32). Montez-le si le niveau affiché dans le panneau reste très bas. |

## L'ajouter à Sound Recognition

Ouvrez le panneau, *Sources → Ajouter*, choisissez **Micro ESP32 (ESPHome)**. Les appareils qui font tourner le composant sont listés (Home Assistant connaît déjà leur adresse et leur pièce) : appuyez sur **Utiliser**, saisissez le mot de passe du flux, choisissez les sons comme pour n'importe quelle source, et enregistrez. Un appareil ajouté à la main demande son adresse `tcp://adresse:port`.

Si la liste est vide, l'appareil n'est sans doute pas encore flashé ou pas connecté à Home Assistant. La détection cherche, sur les appareils ESPHome, un capteur de diagnostic nommé *Sound Recognition stream*.

## Comment le flux est protégé

- L'appareil attend sur son port ; **le service s'y connecte**. Personne d'autre ne reçoit d'audio.
- Le mot de passe est **obligatoire**, et il ne circule jamais sur le réseau : l'appareil envoie un nombre aléatoire, le service répond avec une signature de ce nombre calculée avec le mot de passe, et l'appareil la vérifie. Une mauvaise réponse ferme la connexion avant tout son.
- Une nouvelle connexion qui prouve le mot de passe remplace la précédente, pour qu'un service qui redémarre puisse se reconnecter aussitôt.
- Le service garde le mot de passe dans sa configuration et ne l'affiche plus jamais.

**Ce que ça ne fait pas :** l'audio lui-même n'est **pas chiffré** sur le réseau. Quelqu'un qui peut intercepter le trafic de votre réseau local pourrait l'entendre. À la maison, le risque est faible ; pour aller plus loin, mettez vos objets connectés sur leur propre réseau (VLAN, réseau invité) et n'autorisez le port du flux que depuis l'adresse du service. Le chiffrement du flux pourra venir plus tard.

## Problèmes

- *La source reste « Déconnectée »* : vérifiez l'adresse et le port (`tcp://…:6055`), que l'appareil est en ligne, et le mot de passe. Le panneau montre la raison ; le journal ESPHome de l'appareil montre les tentatives avec un mauvais mot de passe.
- *« the device refused the password »* : le mot de passe du panneau diffère de `secrets.yaml` (majuscules et espaces comptent). Après l'avoir changé dans `secrets.yaml`, flashez de nouveau l'appareil.
- *Peu de détections ou niveau très bas* : montez `gain`, ou vérifiez que la broche L/R de l'INMP441 est câblée comme `channel: left`.
- *Son haché* : Wi-Fi faible. Le flux demande environ 32 ko/s.
