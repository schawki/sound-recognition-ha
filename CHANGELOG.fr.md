# Journal des modifications

Les versions sont étiquetées `vX.Y.Z` ; le service se met à jour depuis Home Assistant vers la dernière étiquette.

## 0.11.0

- **Durée de conservation des clips, par type de son.** Quatre réglages (sons courants, sons sensibles, sons de contexte comme la musique et la télévision, conversations), globaux (onglet *Clips*) ou par source (formulaire de la source). Le réglage propre à un son l'emporte toujours, et le maximum et l'interrupteur « autoriser les clips » de chaque source s'appliquent encore. Rien ne change tant que vous ne les réglez pas.
- **Les conversations peuvent être conservées, en connaissance de cause.** L'interdiction du catalogue devient une simple valeur par défaut (0 jour). Le panneau et les conseils avertissent des paroles privées et de la loi dès que des clips de conversations sont conservés.
- **La détection est bonne.** Un nouveau bouton à côté de « La détection n'est pas bonne », sur les détections qui ont un clip (*En direct* et *Clips*). L'*Aperçu* montre les détections confirmées et la part de bonnes détections parmi celles que vous avez jugées ; *Clips* filtre sur l'avis.
- **Pas d'avis sans clip.** Une détection sans clip ne peut pas être vérifiée : le contrôle n'est pas proposé, et sa ligne « Pas de clip » dit pourquoi.
- **Effacer les détections sans clip** (*Clips*), selon les filtres. Celles que vous avez marquées fausses ou confirmées restent.
- API du service niveau 8 : mettez le service à jour depuis Home Assistant après avoir mis l'intégration à jour.

## 0.10.1

- **« Pas de clip » dit maintenant pourquoi.** Dans *En direct*, une détection sans clip explique la vraie cause : vous avez désactivé les clips pour ce son ou cette source, le son n'est pas enregistré par défaut (son de contexte), c'est un son privé, la durée maximale est de 0 jour, ou le clip a été supprimé ou a expiré. Seules les causes réellement enregistrées par le service sont affichées ; une détection plus ancienne reçoit une phrase neutre.
- **« La détection n'est pas bonne »** remplace « Ce n'est pas un vrai son », et le même contrôle est disponible sur chaque clip de l'onglet *Clips*.

## 0.10.0

- **Micros ESP32 (ESPHome) comme sources.** Un petit composant ESPHome (`esphome/components/sound_recognition_stream`) diffuse sur le réseau l'audio d'un micro I2S (INMP441…) ; le service s'y connecte, le lit et se reconnecte tout seul si le Wi-Fi coupe. Guide : `docs/esphome-microphone.fr.md`.
- **Un mot de passe protège le flux.** Il est obligatoire dans la configuration ESPHome (8 caractères ou plus, dans `secrets.yaml`). Le service prouve qu'il le connaît sans jamais l'envoyer, et l'appareil n'envoie aucun son à qui ne le prouve pas. Le service ne ré-affiche jamais le mot de passe (l'API et le panneau montrent `***`). L'audio n'est **pas chiffré** sur le réseau : voir le guide pour un réseau séparé pour les objets connectés.
- **Trouvés automatiquement.** Dans *Sources → Ajouter → Micro ESP32*, les appareils qui font tourner le composant sont listés (Home Assistant connaît déjà leur adresse et leur pièce) avec un bouton *Utiliser*. Pour un appareil pas encore flashé, le formulaire montre la configuration ESPHome à copier.
- API du service niveau 7 : mettez à jour le service depuis Home Assistant après celle de l'intégration.
- Le composant est vérifié sur PC face au client du service (audio, mauvais mot de passe, reprise par un second client) et compilé pour un ESP32 par la CI. Il n'a pas encore été essayé avec un vrai micro.

## 0.9.2

- Le conseil *parent et enfant* ne concerne plus du tout un contexte (*Fireworks*, *Television*, *Music*…) : un contexte ne fait que relever les seuils, il n'a donc pas de règle d'alerte qui puisse entrer en conflit avec son parent ou son enfant. La 0.9.1 ne couvrait que deux contextes ensemble.
- Un test suit maintenant les gestes des conseils l'un après l'autre, depuis les sons de chaque règle et de chaque paire de règles, avec les recommandations de la maison qui activent des contextes, et vérifie que cela se termine toujours : aucun conseil ne défait ce que demande un autre. Il retrouve la boucle de la 0.9.1 avant la correction, et aucune après.

## 0.9.1

- Correction : activer *Fireworks* et *Firecracker* (ce que font le conseil sur les feux d'artifice et celui tiré d'un jardin voisin) provoquait un conseil *parent et enfant* sur ces deux mêmes sons, et choisir l'un de ses boutons faisait revenir le premier conseil. Deux sons qui ne sont que des contextes, servant à relever les seuils, ne sont plus traités comme des alertes en conflit.

## 0.9.0

- Un conseil entre sons proches offre maintenant un choix au lieu d'un simple texte : un bouton par son activé, *Garder X seul*, qui désactive les autres. Le son que recommande le catalogue passe en premier, en bouton principal. Cela couvre les sons de sonnette proches, les sons de chien (*Dog*, *Bark*, canidés), les sons de verre, les cris et les hurlements, et toute classe qui en contient une autre (parent et enfant, sans recommandation).
- *Music* : un bouton, garder *Music* comme contexte et désactiver ses sous-classes. Une classe trop large (par exemple *Dog*) : un bouton qui la désactive et active ses sous-classes.
- Après un choix, le conseil quitte *À faire* et apparaît dans *Appliqués* avec sa date et *Annuler*. Les sons que le choix a désactivés le restent après *Annuler*, car leur valeur de base est « désactivé » : la carte le dit avant le clic, et on les réactive depuis l'onglet Sons.
- Niveau d'API 6 du service (`choices` sur les avertissements) : mettez à jour le service depuis Home Assistant après l'intégration. Sans cela le panneau fonctionne mais n'affiche pas les boutons de choix. Dans les Réparations, ces conseils restent de simples alertes.
- Les règles du catalogue le disent une seule fois : `choose: {recommended: <son>}` pour un choix entre les sons de la règle, `fix` pour un geste unique ; `tools/validate.py` vérifie les deux.

## 0.8.1

- Correction de la validation de Home Assistant (hassfest, rouge depuis la 0.6.4) : une alerte des Réparations est soit réparable, soit accompagnée d'une description, jamais les deux. Le conseil qui a un bouton *Réparer* a maintenant sa propre entrée, dont la confirmation montre le conseil puis ce qui va changer. Un test garde désormais cette règle.

## 0.8.0

- L'onglet Conseils est reconstruit autour des décisions. Un résumé en haut (*3 à faire · 5 appliqués · 2 masqués*) et un filtre par source, puis quatre sections : *À faire*, *Informations*, *Appliqués*, *Masqués*.
- Chaque conseil dit maintenant **pourquoi** (le problème), **ce que change son bouton** (une ligne par réglage, par exemple *Smoke detector : durée minimale 3 s*) et **où il en est**.
- **Annuler** sur chaque conseil appliqué : cela retire les réglages du conseil de la source, donc la valeur de base du catalogue (ou votre réglage global) s'applique de nouveau ; la carte dit ce qui va revenir avant que vous cliquiez. Ensuite le conseil retourne dans *À faire* et vous pouvez le masquer tout de suite. Pour un conseil qui a désactivé un son, la valeur de base est *désactivé* : annuler ne le réactive pas (passez par l'onglet Sons).
- Un conseil appliqué avec son bouton laisse une petite trace sur sa source (`applied_advice` dans la configuration : règle, message, date, réglages). C'est ce qui garde un conseil visible dans *Appliqués* une fois sa cause disparue de la liste, avec sa date. La même trace est écrite par le bouton *Réparer* des Réparations de Home Assistant. Un conseil appliqué avant cette version n'a pas de date ; il est montré tant que son avertissement l'est, et s'annule de la même façon.
- Le masquage sort des réglages repliés : *Masquer* sur la carte, *Réafficher* dans la section *Masqués*. Le niveau de chaque conseil (information, avertissement, danger) reste réglable, replié sous *Importance*.
- Aucun changement d'API du service : il ne fait que vérifier la trace dans la configuration.

## 0.7.0

- Davantage de conseils ont un bouton *Appliquer* (et un bouton *Réparer* dans les Réparations de Home Assistant), quand l'avertissement dit exactement quoi faire :
  - un seuil trop bas pour un son souvent déclenché à tort revient au seuil conseillé ;
  - un son de sécurité dont l'horaire de la source a des trous reçoit son propre horaire continu ;
  - un son sensible à la télévision, à la radio ou à la musique voit ses contextes inhibiteurs activés (*Télévision* et *Radio* pour les sons qui y réagissent) ;
  - *Baby cry* doit tenir 2 secondes quand un chat est aussi écouté ;
  - *Beep* est désactivé et 3 secondes sont exigées pour *Smoke detector* ; *Fire* et *Crackle* sont désactivés comme alertes incendie ;
  - une rétention de clip que le catalogue interdit est retirée de la source (si le réglage global ne la demande pas aussi).
- Quand le geste active quelque chose ou fixe une durée, le conseil reste, marqué *Déjà appliqué*. Quand il supprime la cause (un son désactivé, un seuil corrigé), le conseil quitte la liste.
- La confirmation du correctif des Réparations liste maintenant chaque changement (*Beep : désactivé*, *Smoke detector : durée minimale 3 s*...), et plus seulement les sons activés.
- Les règles du catalogue peuvent porter un geste fait de `enable`, `disable` et `set` (durée, seuil, délai, rétention) ; `tools/validate.py` le vérifie. Le format de l'API des conseils ne change pas : aucune mise à jour du service n'est nécessaire hormis la version.

## 0.6.5

- L'alerte en haut de la vue En direct compte ce que l'onglet Conseils montre en premier (conseils à faire et avertissements), et plus les conseils déjà appliqués : elle annonçait un conseil introuvable. Un conseil masqué n'est jamais compté.
- L'alerte est un lien : un clic ouvre l'onglet Conseils sur le premier conseil et le met en surbrillance. Chaque ligne du résumé de l'Aperçu mène de la même façon à son propre conseil.

## 0.6.4

- Réparations : un conseil déjà appliqué ne crée plus d'alerte dans Home Assistant (l'avertissement sur les feux d'artifice et les pétards revenait même une fois ces deux sons activés).
- Réparations : un conseil qui a un geste est maintenant réparable. Le bouton *Corriger* de l'alerte ouvre une confirmation qui dit ce qui va être activé, puis l'enregistre sur la source, comme le bouton *Appliquer* du panneau. Les avertissements sans geste restent de simples alertes.

## 0.6.3

- Une seule liste de conseils : les recommandations de l'Aperçu et les avertissements de l'onglet Conseils sont maintenant dans l'onglet Conseils. Ce qui se fait en un clic a un bouton *Appliquer* ; ce qui est déjà en place indique *Déjà appliqué* et reste dans un groupe replié en bas, pour vérifier que cela a pris effet. Les avertissements sans geste restent des informations, avec leurs réglages d'affichage repliés sous *Affichage*. L'Aperçu se contente de résumer ce qui demande de l'attention et ouvre l'onglet.
- L'avertissement sur les feux d'artifice et les pétards pris pour des coups de feu a maintenant son geste (activer ces deux sons comme contextes) et ne contredit plus la recommandation tirée du logement : c'est un seul conseil, affiché une fois.
- Service niveau d'API 5 (`applied` et `apply` sur les avertissements, `applied` sur les recommandations) : mettez le service à jour depuis Home Assistant après avoir mis à jour l'intégration.

## 0.6.2

- Correction : une recommandation tirée de la maison (par exemple activer les sons d'une TV voisine) restait dans la liste après avoir été appliquée. La liste lit maintenant la configuration enregistrée plutôt qu'une copie gardée avant le rechargement de l'intégration, et reconnaît un son activé sous son nom AudioSet comme sous son identifiant ; un choix fait sur la source l'emporte sur le choix global, comme dans le service.

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
