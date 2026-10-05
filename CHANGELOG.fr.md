# Journal des modifications

Les versions sont étiquetées `vX.Y.Z` ; le service se met à jour depuis Home Assistant vers la dernière étiquette.

## 0.6.1

- Correction : ouvrir un panneau juste après une mise à jour ne produit plus l'erreur « custom element already defined » dans le navigateur.
- Correction : la recherche dans le registre d'appareils, dépréciée dans les versions récentes de Home Assistant, est remplacée.

## 0.6.0

- L'environnement d'une source vient désormais de Home Structure : le type de sa pièce (ou le genre de son espace) le donne automatiquement et suit tout changement là-bas. Choisir un environnement dans la source le remplace toujours. Une pièce sans type est invitée à en recevoir un dans Home Structure. Nécessite Home Structure 0.6.0, qui ajoute des types de pièce (chambre parentale, chambre d'enfant, chambre de bébé, chambre d'amis, salle de jeux, salle de cinéma, salle de sport, atelier, cellier, cave, grenier, escalier) organisés en groupes.
- Cinq nouveaux types de lieu pour que chaque type de pièce de Home Structure en ait un : salle à manger, salle de bains (et toilettes), buanderie et local technique, salle de sport, rangement (cave, grenier, cellier, dressing).
- Le formulaire d'une source affiche un résumé des appareils pris en compte (dans la pièce, dans les pièces reliées, avec la part du son qui atteint la source) ; la liste détaillée et ses réglages sont repliés dans des réglages expert.
- Correction : les pièces atteintes depuis une source pouvaient dépasser deux liaisons et proposer des appareils de pièces lointaines.
- API du service niveau 4 (`PUT /sources/{id}/place`) : mettez le service à jour depuis Home Assistant après avoir mis à jour l'intégration.

## 0.5.0

- Onglet Clips : la taille de chaque clip, le total de la sélection et la place prise par tous les clips sur le disque (avec l'espace libre). Filtres par source, son, catégorie (animaux, incendie…) et période.
- Suppression d'un clip, d'une sélection, de tout ce que montrent les filtres, ou de tous les clips, après une confirmation qui indique le nombre de clips et la place libérée. Les détections restent dans l'historique ; seul l'audio disparaît.
- API du service niveau 3 (`GET /clips`, `POST /clips/delete`) : mettez le service à jour depuis Home Assistant après avoir mis à jour l'intégration.

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
