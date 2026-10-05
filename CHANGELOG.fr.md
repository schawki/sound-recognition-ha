# Journal des modifications

Les versions sont étiquetées `vX.Y.Z` ; le service se met à jour depuis Home Assistant vers la dernière étiquette.

## 0.4.0

- Sound Recognition ne décrit plus de pièces : l'éditeur intégré de « pièces reliées » est supprimé (rien n'est transféré ; décrivez le logement dans Home Structure). Sans Home Structure, une source ne voit que les appareils de sa propre pièce. Nécessite Home Structure 0.5.0 pour les nouvelles recommandations.
- Recommandations issues du logement : l'environnement d'une source est proposé d'après le type de sa pièce, et des règles fondées sur les espaces qui lui sont reliés (rue, jardin, salon, garage…) proposent le réglage adaptatif ou les sons à activer. Les règles sont un fichier de données lisible, `home_rules.yaml`.
- Le plan de l'onglet Sources affiche le type de chaque pièce et le genre de chaque espace extérieur.

## 0.3.0

- L'onglet Sources dessine le plan de votre logement tel qu'il est disposé dans Home Structure (lecture seule, avec l'état en direct de chaque séparation) et renvoie vers son éditeur. Nécessite Home Structure 0.4.0.
- Nouveau type de séparation *grille* (grille de sécurité ou porte grillagée : presque aucune atténuation du son) ; un volet indiqué sur une fenêtre ou une porte précise de Home Structure n'abaisse plus que cette séparation.
- La bannière de mise à jour affiche le numéro de version sans « v » devant.

## 0.2.1

- Correction d'un avertissement de dépréciation de Home Assistant : les appareils des sources audio sont désormais rattachés à l'appareil du service par son identifiant de registre (`via_device_id`).

## 0.2.0

- Mise à jour du service depuis Home Assistant : une entité Mise à jour et une bannière du panneau signalent qu'une version plus récente existe, un clic l'installe, et une notification dit quand le service est de nouveau en ligne (ou pourquoi la mise à jour a échoué).
- Le service indique son `api_level` ; une réparation demande une mise à jour quand le service est trop ancien pour l'intégration.
- Sensibilité qui tient compte du contexte grâce aux appareils (TV, musique, aspirateur…) et aux pièces de Home Assistant, avec un contexte partagé entre pièces reliées.
- Home Structure (intégration séparée) est utilisée pour les pièces, séparations et capteurs d'ouverture quand elle est installée ; la description interne reste en secours.
- La mise à jour manuelle reste possible : `git -C /opt/sound-recognition-ha pull && bash /opt/sound-recognition-ha/deploy/install.sh` (nécessaire une fois pour installer l'assistant de mise à jour).

## 0.1.0

- Première version : service YAMNet, intégration Home Assistant, panneau latéral.
