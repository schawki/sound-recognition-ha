# Sound Recognition pour Home Assistant

Reconnaît des sons (alarme incendie, pleurs de bébé, sonnette, bris de verre, aboiements…) à partir de micros réseau, de caméras et de Raspberry Pi, et les signale à Home Assistant. Pensez à « la détection audio de Frigate », mais pour n'importe quelle source audio et avec tous les réglages gérés depuis l'interface de Home Assistant.

*English: [README.md](README.md)*

![L'onglet En direct](docs/images/live.png)

## Ce que vous obtenez

- **Toute source audio** : caméras et flux go2rtc (RTSP), Raspberry Pi, et micros ESP32 avec un petit composant ESPHome.
- **521 sons reconnaissables** (YAMNet / AudioSet) avec noms français et anglais, classés par catégorie et par usage, chacun avec un seuil suggéré et des avertissements sur les sons qui se ressemblent.
- **Des réglages par source, par son et par source × son** : seuil, volume minimal, horaires ou écoute continue, durée minimale, délai de repos, extraits et leur conservation. Le panneau montre d'où vient chaque valeur.
- **Moins de fausses alertes** : une télévision, de la musique ou des feux d'artifice relèvent les seuils des sons qui leur ressemblent tant qu'on les entend (les sons de sécurité ne sont relevés que d'un petit montant plafonné). Sensibilité adaptative facultative dans les pièces bruyantes. Rien de ce qui est masqué n'est perdu en silence : c'est compté.
- **Des conseils avec un bouton** : le panneau vous dit ce qui est risqué ou manquant et le règle en un clic, avec Annuler. Voir [l'onglet Conseils](docs/advice.fr.md).
- **Vie privée** : les extraits de conversations ne sont jamais conservés (le catalogue l'interdit et le service l'impose) ; les extraits des autres sons expirent après la durée choisie.
- **Un panneau dans la barre latérale de Home Assistant**, thèmes clair et sombre, sur téléphone, au clavier.
- Des entités, des événements et des Réparations dans Home Assistant, utilisables dans vos automatisations.

## Comment ça s'articule

Deux parties, parce que l'analyse audio ne doit pas tourner dans Home Assistant :

1. **Le service** (`service/`) écoute. Il tourne dans son propre conteneur ou sa propre machine, lit vos flux avec ffmpeg, exécute YAMNet et garde de courts extraits. Il a une API HTTP/WebSocket locale.
2. **L'intégration** (`custom_components/`) s'installe avec HACS. Elle se connecte au service et vous donne le panneau, les entités et les conseils dans Home Assistant.

Le catalogue (`catalog/`) contient les sons, leurs textes français et anglais et les conseils, neutres en langue pour pouvoir en ajouter.

Elle fonctionne avec **[Home Structure](https://github.com/schawki/ha-home-structure)**, une intégration compagnon qui décrit votre logement (quelles pièces sont voisines, ce qui les sépare, si les portes sont ouvertes). Quand Home Structure est installée, Sound Recognition s'en sert pour estimer combien un son passe d'une pièce à l'autre (une porte ouverte le laisse passer, fermée elle l'étouffe), et pour trouver les lecteurs multimédias et aspirateurs d'une pièce. Home Structure est facultative : sans elle, les pièces sont simplement considérées comme séparées.

## Démarrage rapide

1. **Installer le service** (une dizaine de minutes). Sur un hôte Proxmox, une commande crée un conteneur prêt à l'emploi ; toute machine Debian ou Ubuntu convient aussi, et une image Docker est fournie. Pas à pas : **[Installer le service](docs/install-service.fr.md)** ([English](docs/install-service.en.md)).
2. **Installer l'intégration.** HACS → trois points → *Dépôts personnalisés* → `https://github.com/schawki/sound-recognition-ha` (catégorie *Intégration*) → installer **Sound Recognition**, redémarrer Home Assistant.
3. **Les relier.** *Paramètres → Appareils et services → Ajouter une intégration → Sound Recognition* : l'adresse du service, le port 8765 et le jeton affiché à la fin de l'installation.
4. **Ajouter une source et choisir des sons.** Ouvrez **Sound Recognition** dans la barre latérale : *Sources → Ajouter* (l'URL d'un flux RTSP/go2rtc, le micro d'un Raspberry Pi, ou un [micro ESP32 trouvé automatiquement](docs/esphome-microphone.fr.md)), puis *Sons* pour activer ceux qui vous intéressent. L'onglet *Conseils* vous dit ensuite quoi vérifier.
5. **Rester à jour.** Une fois connecté, le service se met à jour depuis Home Assistant : une entité *Mise à jour* et un bandeau du panneau annoncent chaque nouvelle version, et un clic l'installe en gardant vos réglages (installations Proxmox/Debian ; voir [Installer le service](docs/install-service.fr.md#rester-à-jour)).

## Le panneau

| | |
|---|---|
| **En direct** | Sources avec niveau et état de connexion, sons actifs, détections récentes avec lecture de l'extrait et bouton « La détection n'est pas bonne » (aussi sur chaque clip dans Clips). |
| **Aperçu** | Ce que chaque source entend, comment ses seuils réagissent en ce moment, les dernières 24 heures et une chronologie en direct. |
| **Sources** | Ajouter, modifier, désactiver et supprimer des sources ; une grille de semaine pour les horaires d'écoute. |
| **Sons** | Chercher parmi les 521 sons, les activer partout ou par source, régler chacun avec l'origine de chaque valeur. |
| **Conseils** | Ce qui est risqué ou manquant, avec Appliquer, Annuler et Masquer ([détails](docs/advice.fr.md)). |
| **Clips** | Retrouver et écouter les extraits ; en supprimer un, une sélection ou tous, après une confirmation qui montre le nombre et la taille. |

![Aperçu](docs/images/overview.png)
![Sons](docs/images/sounds.png)
![Conseils (démo, textes de conseil en anglais)](docs/images/advice.png)

## État du projet

Version 0.9, utilisée sur une installation réelle et testée (les tests du service, de l'intégration et du panneau tournent à chaque commit). Les micros ESP32 (ESPHome) sont pris en charge mais pas encore essayés sur du vrai matériel. L'image Docker est fournie mais pas encore testée. Retours et tickets bienvenus.

## Limites connues

- Les micros ESP32 (ESPHome) sont nouveaux et pas encore essayés avec un vrai micro. Leur audio est protégé par un mot de passe mais pas chiffré sur votre réseau local ([détails](docs/esphome-microphone.fr.md#comment-le-flux-est-protégé)).
- *Annuler* un conseil ne réactive pas un son que le conseil avait désactivé (sa valeur de base dans le catalogue est « désactivé »). La carte le dit ; réactivez-le dans l'onglet Sons.
- Les conseils qui demandent de choisir entre deux sons (« Garder X seulement ») n'ont pas de bouton dans la page *Réparations* de Home Assistant ; choisissez dans l'onglet Conseils.
- Les recommandations ne peuvent pas être masquées (seuls les avertissements le peuvent).
- L'image Docker est fournie mais n'a pas encore été construite ni testée. Le conteneur Proxmox et l'installation Debian/Ubuntu classique sont les voies testées.
- La mise à jour du service depuis Home Assistant demande l'installation Proxmox/Debian (systemd) ; avec Docker, reconstruisez l'image.

## Documentation

- [Installer le service](docs/install-service.fr.md) · [Détails Proxmox et mises à jour](deploy/DEPLOY.fr.md)
- [Micro ESP32 (ESPHome)](docs/esphome-microphone.fr.md)
- [L'onglet Conseils](docs/advice.fr.md)
- [Réglages par source](docs/source-settings.fr.md) · [Contextes, pièces et sensibilité adaptative](docs/context-and-adaptive.fr.md)
- [API du service et développement](docs/api.md) (en anglais) · [Exemple de configuration](examples/config.example.yaml)
- [Journal des modifications](CHANGELOG.fr.md) · [Publier une version](RELEASING.md)

## Mesures

Sur une machine de test à 2 cœurs, dix sources simultanées (en continu, 12 classes activées) ont utilisé environ 12 % d'un cœur et environ 0,6 Go de RAM au total, ffmpeg compris. Une inférence prend environ 2 ms. Les vrais flux RTSP ajoutent le décodage audio ; à re-mesurer sur votre matériel.

## Crédits et licences

Code : MIT. YAMNet : Google, Apache-2.0 ([source](https://github.com/tensorflow/models/tree/master/research/audioset/yamnet)) ; ontologie AudioSet : Google, CC BY-SA 4.0. La conversion TFLite de YAMNet utilisée par défaut vient d'un fork public ; sa somme de contrôle est figée dans l'installeur et le Dockerfile.
