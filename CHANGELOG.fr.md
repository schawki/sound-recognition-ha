# Journal des modifications

Les versions sont étiquetées `vX.Y.Z` ; le service se met à jour depuis Home Assistant vers la dernière étiquette.

## 0.20.0

- **Le volume minimum en cours est désormais visible.** Dans la liste des sources, chaque ligne indique le volume minimum en cours et qui l'a réglé : *automatique*, *réglé à la main*, *d'un préréglage* ou *par défaut*. Le tableau par source des réglages d'un son montre la même valeur.
- **Volume minimum automatique (facultatif).** Chaque source peut laisser le service suivre toute seule les mesures de bruit : *Qui règle le volume minimum* → *Automatique* (ou *Suivre la valeur par défaut*, avec le défaut activé dans *Réglages → Valeurs par défaut* pour toutes les sources d'un coup). Le manuel reste le défaut. Une fois par jour, le service applique la suggestion, seulement après 6 heures de calme et seulement si elle diffère d'au moins 3 dB de la valeur en cours ; la valeur saisie à la main n'est jamais écrasée et sert de nouveau si vous revenez à *Manuel*. Le formulaire de la source montre la valeur en cours et les derniers changements. Voir [Assistant de bruit](docs/noise-assistant.fr.md#mode-automatique).
- Niveau d'API du service 14 : mettez le service à jour depuis Home Assistant après avoir mis à jour l'intégration. Avec un service plus ancien, le réglage est enregistré mais sans effet, et la liste montre les valeurs de la configuration.

## 0.19.0

- **Assistant de bruit.** Sous *Volume minimum* dans le formulaire d'une source, le service mesure désormais le niveau ambiant de la pièce (un chiffre par minute, jamais d'audio) et, après 6 heures de calme, **suggère un volume minimum** : le niveau de la pièce au repos plus 6 dB, jamais au-dessus de -50 dBFS pour qu'une alarme lointaine soit encore entendue. Un graphique montre le niveau calme selon l'heure de la journée. *Utiliser cette valeur* remplit seulement le champ ; **vous pouvez toujours taper votre propre valeur**, qui l'emporte, et rien n'est gardé tant que vous n'enregistrez pas la source. Voir [Assistant de bruit](docs/noise-assistant.fr.md).
- **Des mesures que vous contrôlez.** *Réglages → Mesures de bruit* montre combien de mesures chaque source a, depuis quand et la place qu'elles prennent, avec des boutons pour les effacer (une source ou toutes, avec confirmation) et le nombre de jours de conservation (7 par défaut ; 0 ne mesure rien).
- API du service niveau 13 : mettez le service à jour depuis Home Assistant après avoir mis à jour l'intégration. Avec un service plus ancien, l'assistant n'apparaît simplement pas.

## 0.18.0

- **Conditions sur des états de Home Assistant.** On peut demander à une source ou à un son de **n'écouter que si une condition est vraie**, par exemple « seulement quand personne n'est à la maison » ou « seulement quand l'alarme est désarmée ». La condition s'ajoute à l'horaire : un son est entendu quand l'horaire l'autorise *et* que la condition est vraie. Elle se règle dans le formulaire de la source et dans les réglages d'un son (toutes les sources, ou une seule), avec l'ordre habituel : source × son, son, source, défauts. Règles : l'état d'une entité quelconque (« est » / « n'est pas » un état), ou les raccourcis *personne n'est à la maison* / *quelqu'un est à la maison* (les entités `person`) ; « toutes les règles » ou « au moins une règle ». Voir [Conditions](docs/conditions.fr.md).
- **Quand un état n'est pas connu** (Home Assistant qui redémarre, entité supprimée, liaison coupée), l'écoute continue par défaut, car une alarme manquée est pire qu'une détection de trop ; chaque condition peut choisir de rester en pause à la place. L'onglet *En direct* indique quand un son est en pause à cause de sa condition ou quand un état est inconnu. On peut donner une condition aux sons de sécurité (incendie, sécurité, bébé), avec un avertissement dans le panneau.
- API du service niveau 12 (`PUT /conditions`) : mettez le service à jour depuis Home Assistant après avoir mis à jour l'intégration. Avec un service plus ancien, l'intégration continue de fonctionner et ignore simplement les conditions.

## 0.17.0

- **Déplacer les clips depuis Home Assistant.** Dans *Réglages → Stockage*, saisissez le nouveau dossier (autre disque, partage NAS) et appuyez sur *Déplacer les clips…* : après votre confirmation, un petit assistant sur la machine du service copie les clips, vérifie la copie, fait pointer le service sur le nouveau dossier et le redémarre, l'avancement s'affichant dans la carte. **Le déplacement ne supprime rien** : l'ancien dossier reste, et la carte propose alors un bouton **Supprimer les anciens clips…** (avec confirmation) tant qu'il existe. Quand le dossier ne peut pas être retiré complètement (disque ou partage monté, autres fichiers dedans, pas le droit de supprimer), la carte dit quoi faire à la main. Pendant la copie les détections continuent sans garder de nouveaux clips. Détails et limites (Docker exclu) : [Stockage des clips](docs/storage.fr.md#moving-the-clips).
- **Des clips ailleurs dès le départ.** `CLIPS_HOST=/mnt/storage/soundrec-clips bash deploy/create-lxc.sh` sur Proxmox monte le dossier dans le conteneur et le donne au service ; `SOUNDREC_CLIPS` fait de même avec `install.sh`.
- **L'intégration est testée contre un service en retard d'une version** (chargement, panneau, entité *Update*, commandes du panneau), et chaque route du service doit dire comment l'intégration s'en passe. C'est ce qui aurait détecté le problème de la 0.16.0.
- API du service niveau 11 : mettez le service à jour depuis Home Assistant après avoir mis à jour l'intégration (le panneau le signale tant que ce n'est pas fait ; l'intégration fonctionne en attendant, seul le bouton *Déplacer les clips* attend le nouveau service).

## 0.16.1

- **Correction : le panneau pouvait disparaître quand on mettait à jour l'intégration avant le service.** La 0.16.0 demandait au service une information que seul le nouveau service connaît ; avec l'ancien service elle ne démarrait pas : plus de raccourci dans la barre latérale, plus de bouton *Mettre à jour*. Elle démarre maintenant avec l'ancien service et affiche le bandeau « service obsolète », ce qui permet de mettre le service à jour depuis Home Assistant comme d'habitude. Si vous êtes dans ce cas : mettez l'intégration à jour en 0.16.1 par HACS, redémarrez Home Assistant, puis utilisez *Mettre à jour*.

## 0.16.0

- **Préréglages.** Des réglages prêts à l'emploi par type de pièce (salon, cuisine, chambre, chambre de bébé, bureau, salle de bains, buanderie, salle de sport, rangement, entrée, extérieur, garage) et par situation (TV à proximité, bruit extérieur, bébé, animaux, maison vide). Choisissez-en plusieurs pour une source : ils s'additionnent, celui qui est plus bas dans la liste l'emporte sur une valeur commune, et ce que vous réglez vous-même l'emporte toujours. Créez les vôtres dans *Réglages → Préréglages*, avec n'importe quel son détectable, ou dupliquez-en un. Voir [Préréglages](docs/presets.fr.md).
- Les sons de sécurité (incendie, effraction, bébé) ne sont jamais rendus plus difficiles à détecter par un préréglage, et un préréglage ne peut pas fixer un son le plus faible au-dessus de -50 dBFS.
- L'onglet *Conseils* propose le préréglage qui convient à la pièce d'une source, avec un bouton et Annuler. L'onglet *Sons* indique quand une valeur vient d'un préréglage, et les *Réglages* listent les préréglages de chaque source.
- Home Assistant crée les entités des sons qu'un préréglage active.
- API du service niveau 10 : mettez le service à jour depuis Home Assistant après avoir mis à jour l'intégration (le panneau le signale tant que ce n'est pas fait).

## 0.15.1

- **Plus de choses dans l'onglet *Réglages*.** La conservation des clips par type de son quitte l'onglet *Clips* pour y venir ; la **sensibilité aux contextes** (de combien une TV, une radio ou de la musique relèvent les seuils des sons semblables), qui n'était plus modifiable depuis la 0.15.0, revient parmi les valeurs par défaut ; l'**adresse de go2rtc** peut y être essayée et enregistrée (elle reste proposée quand vous ajoutez une source).
- **Les sources avec des réglages particuliers** sont listées dans *Réglages*, avec ce que chacune règle pour elle-même (sensibilité, volume, horaires, clips, lieu, sons, conseils) et un bouton *Ouvrir*. Les conseils que vous avez modifiés ou masqués pour toutes les sources y sont aussi, avec *Rétablir*.
- Aucun changement du service : seul le numéro de version bouge. Mettez à jour l'intégration par HACS et redémarrez Home Assistant.

## 0.15.0

- **Un nouvel onglet *Réglages*** rassemble sur une seule page ce qui se règle une fois et change rarement : la **connexion** (adresse du service, sa version, bouton **Changer le jeton**), le **stockage** (les deux limites), les **valeurs par défaut** (son le plus faible pris en compte, clips gardés par défaut, durée maximale), le **lien avec Home Structure** (et pourquoi Reconnaissance de sons l'utilise) et les micros ESP32 mis de côté (avec *Ne plus ignorer*). Les sources, les sons et les conseils gardent leurs onglets.
- La carte *Stockage* de l'onglet *Clips* n'affiche plus que les chiffres, avec un bouton *Modifier les limites* qui mène aux *Réglages*.
- **Le formulaire *Configurer* de Home Assistant se réduit à l'adresse du service**, avec un texte qui dit où se règle le reste. Les sources, les sons, les conseils et les valeurs par défaut étaient déjà dans le panneau ; les valeurs par défaut (qui n'étaient que dans ce formulaire) sont maintenant dans les *Réglages*.
- Aucun changement du service : seul le numéro de version bouge. Mettez à jour l'intégration par HACS et redémarrez Home Assistant.

## 0.14.0

- **Une carte Stockage dans l'onglet Clips.** Elle indique où sont les clips, ce qu'ils occupent, l'espace libre, leur croissance, le temps avant que le disque soit plein et la place que prendrait votre rétention. Un conseil apparaît quand il reste moins de 2 Go ou que le disque serait plein sous deux semaines. Nouveau guide : [Stockage des clips](docs/storage.fr.md), avec la façon de garder les clips sur un autre disque ou un NAS.
- **Deux limites facultatives, désactivées par défaut :** ne plus garder de clips quand l'espace libre passe sous une taille que vous choisissez, et supprimer automatiquement les plus anciens clips pour les garder sous une taille que vous choisissez (ceux que vous avez jugés partent en dernier). L'historique dit pourquoi une détection n'a pas de clip.
- **Un bouton « Changer le jeton »** sur la même carte : le service fabrique un nouveau jeton, Home Assistant l'enregistre et se recharge, rien à copier. L'ancien jeton fonctionne encore une minute.
- La section « Protéger le service » du guide d'installation devient « Garder le service privé » : aucun réglage de pare-feu ne vous est demandé.
- Service au niveau d'API 9 : mettez à jour le service depuis Home Assistant après avoir mis à jour l'intégration (le panneau le dit tant que ce n'est pas fait).

## 0.13.0

- **Les clips sont réservés aux administrateurs.** Un utilisateur de Home Assistant qui n'est pas administrateur ne peut plus récupérer un clip par son adresse, car un clip peut contenir de la parole privée. Les liens donnés par le panneau et par les notifications (liens signés) continuent de fonctionner.
- **Le jeton du service n'est accepté que dans l'en-tête `Authorization`**, plus dans l'adresse (`?token=`), où il finit dans des journaux. L'intégration utilisait déjà l'en-tête ; rien à changer, sauf si vous avez écrit votre propre client.
- **Nouvelle section « Protéger le service »** dans le guide d'installation : règles de pare-feu (Proxmox ou `ufw`) pour que seul Home Assistant joigne le port 8765, et les autres précautions.
- Mettez à jour l'intégration par HACS, redémarrez Home Assistant, puis mettez à jour le service depuis Home Assistant.

## 0.12.1

- **Un micro ajouté n'est plus jamais affiché comme « ignoré ».** Un ESP32 ignoré (par exemple avec *Envoyer* dans l'alerte des Réparations) puis ajouté comme source restait marqué ignoré. Il est maintenant oublié de la liste des ignorés dès qu'il est une source : le retirer plus tard le fait proposer de nouveau.
- L'historique (`/events`) répond une erreur claire, et non une erreur du serveur, quand `since` ou `limit` n'est pas un nombre.
- Petits nettoyages issus d'une revue du code (imports et variables inutilisés, un hachage signalé comme non destiné à la sécurité).
- **Documentation :** nouvelle page [Pourquoi et comment Home Structure est utilisée](docs/home-structure.fr.md) ; le README ne dit plus que les micros ESP32 n'ont jamais été essayés sur du vrai matériel.
- Mettez à jour l'intégration par HACS, redémarrez Home Assistant, puis mettez à jour le service depuis Home Assistant.

## 0.12.0

- **Vous êtes prévenu quand un micro ESP32 est prêt à être ajouté.** Sound Recognition reconnaît maintenant les appareils ESPHome qui exécutent le composant micro et ne sont pas encore une source, et le signale par un bandeau en haut du panneau (il ouvre *Sources → Ajouter → Micro ESP32*), un compteur sur l'onglet *Sources*, un conseil, et une alerte dans les *Réparations* de Home Assistant. Cette alerte est la seule que Sound Recognition envoie volontairement aux Réparations, et seulement pour les micros à ajouter.
- **Ignorer un appareil.** Une carte qui ne doit pas devenir un micro peut être ignorée depuis la liste (ou avec *Envoyer* dans l'alerte des Réparations) ; *Ne plus ignorer* la fait revenir. Les appareils ajoutés ne sont plus signalés d'eux-mêmes.
- Mettez à jour l'intégration par HACS, redémarrez Home Assistant, puis mettez à jour le service depuis Home Assistant.

## 0.11.4

- **Les micros ESP32 sont maintenant trouvés tout seuls.** La liste de *Sources → Ajouter → Micro ESP32* restait vide, même pour un appareil qui exécute le composant : Home Assistant range les capteurs texte d'ESPHome dans le domaine `sensor`, et la recherche regardait ailleurs. Découvert avec le premier vrai micro. L'ajout à la main avec l'adresse a toujours fonctionné.

## 0.11.3

- **Plus facile de vérifier que le lien avec Home Structure fonctionne.** Avec les journaux de débogage activés pour Sound Recognition, le journal indique quand Home Structure a annoncé un changement et combien de liens ont été relus. Aucun changement de comportement.

## 0.11.2

- **Le service annonce maintenant la bonne version.** Après la mise à jour du service en 0.11.1, il disait encore 0.11.0 et Home Assistant continuait à proposer la même mise à jour. Le service et l'intégration portent désormais le même numéro. Mettez le service à jour une fois depuis Home Assistant : la proposition disparaît.

## 0.11.1

- **Sound Recognition relit le logement dès que Home Structure annonce un changement** (événement `home_structure_changed`), au lieu d'attendre son prochain rafraîchissement. Plusieurs événements de suite ne donnent qu'une relecture, et rien ne casse si Home Structure n'est pas encore chargé. Rien à régler ; il faut Home Structure 0.9.0 ou plus pour que ce soit immédiat (les versions plus anciennes restent relues toutes les 20 secondes).

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
