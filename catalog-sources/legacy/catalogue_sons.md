# Catalogue des classes de sons (YAMNet)

Ce document est la version lisible du fichier `catalogue_sons.yaml`. Il décrit les 521 classes de sons que reconnaît YAMNet, avec pour chacune un nom français, un classement et des suggestions de réglage.

## Ce qui est sûr et ce qui est un jugement

- **Sûr (données officielles)** : la liste des 521 classes, leur numéro, leurs noms anglais et la hiérarchie parent/enfant (par exemple « Aboiement » fait partie de « Chien »). Elles viennent du fichier `yamnet_class_map.csv` de YAMNet et de l'ontologie AudioSet.
- **Jugement (suggestions de départ)** : l'intérêt pour une maison, le risque de fausses alertes, la sensibilité pour la vie privée, les seuils, les durées, la conservation des clips, les groupes de classes proches et les règles d'avertissement. Ils reposent sur une connaissance générale de ces sons, **rien n'a été mesuré dans une maison réelle**. Les scores de YAMNet ne sont pas des probabilités calibrées : les seuils sont à ajuster avec vos propres enregistrements.

## En bref

Sur 521 classes, **8** sont recommandées comme alertes, **71** sont optionnelles selon votre situation, **35** servent de contexte ou de diagnostic, et **407** sont ignorées par défaut (dont 143 classes de musique, d'instruments et de genres).

### Comment lire les champs

- **Intérêt** : *À surveiller* = recommandée comme alerte ; *Optionnelle* = selon votre situation ; *Contexte* = ne sert pas d'alerte mais permet de relever les seuils des autres classes ; *Ignorée* = désactivée par défaut.
- **Faux positifs** : fréquence à laquelle la classe se déclenche à tort (télévision, voisinage, appareils…).
- **Vie privée** : *confidentielle* = conversations, aucun clip ne doit être conservé ; *sensible* = peut révéler des informations personnelles.
- **Seuil, durée min., ré-armement** : seuil de score (0 à 1), durée de détection soutenue avant de signaler, délai avant un nouveau signalement.
- **Conservation** : durée de conservation des clips audio (0 = aucun clip).

## 1. Les classes à surveiller en priorité

Ce sont les classes les plus utiles comme alertes. Même celles-ci produiront des fausses alertes : le champ « Faux positifs » dit lesquelles et pourquoi.

### Détecteur de fumée — `Smoke detector, smoke alarm` (n° 393)

- Catégorie : Alarmes, sonnettes et signaux · type de son : ton soutenu
- Faux positifs : **moyen** (causes : bips d'appareils (micro-ondes, four, lave-linge), alarmes d'autres appareils, télévision)
- Suggestions : seuil 0.4, détection soutenue d'au moins 3 s, ré-armement 60 s, clip de 5 s avant à 10 s après, conservé 90 jours
- Fait partie de : Alarme
- Le cas d'usage le plus utile. Exiger une détection soutenue d'au moins 3 secondes : un bip isolé ne doit pas déclencher. Ce n'est PAS un remplacement d'un vrai détecteur de fumée : c'est une redondance qui entend un détecteur existant.

### Alarme incendie — `Fire alarm` (n° 394)

- Catégorie : Alarmes, sonnettes et signaux · type de son : ton soutenu
- Faux positifs : **moyen** (causes : bips d'appareils, télévision, alarme d'immeuble voisin ou exercice)
- Suggestions : seuil 0.4, détection soutenue d'au moins 3 s, ré-armement 60 s, clip de 5 s avant à 10 s après, conservé 90 jours
- Fait partie de : Alarme
- Alarme incendie (sirène d'immeuble par exemple). Proche de « Détecteur de fumée » : en choisir un seul comme alerte principale, l'autre en confirmation.

### Verre brisé — `Shatter` (n° 437)

- Catégorie : Chocs, casse et détonations · type de son : bref
- Faux positifs : **moyen** (causes : vaisselle ou bouteille qui tombe, télévision, travaux)
- Suggestions : seuil 0.5, détection soutenue d'au moins 1 s, ré-armement 15 s, clip de 5 s avant à 5 s après, conservé 30 jours
- Fait partie de : Verre
- Contextes qui devraient relever le seuil : Télévision, Radio, Musique
- Verre brisé : utile pour la sécurité (vitre cassée). À confirmer avec un capteur de fenêtre ou une caméra : les chutes de vaisselle sont fréquentes.

### Hurlements stridents — `Screaming` (n° 11)

- Catégorie : Voix humaine · type de son : bref
- Faux positifs : **élevé** (causes : télévision (films, jeux vidéo), enfants qui jouent, voisinage, radio)
- Suggestions : seuil 0.6, détection soutenue d'au moins 1 s, ré-armement 15 s, clip de 5 s avant à 5 s après, conservé 7 jours
- Contextes qui devraient relever le seuil : Télévision, Radio, Musique
- Cris stridents : le plus utile pour la sécurité mais aussi le plus sujet aux fausses alertes (films, jeux, enfants qui s'amusent). À confirmer par un second signal (présence, porte, caméra) avant toute action.

### Aboiement — `Bark` (n° 70)

- Catégorie : Animaux domestiques · type de son : bref
- Faux positifs : **moyen** (causes : chiens des voisins, télévision, rue)
- Suggestions : seuil 0.5, détection soutenue d'au moins 1 s, ré-armement 15 s, clip de 5 s avant à 5 s après, conservé 7 jours
- Fait partie de : Animal, Chien, Animaux domestiques
- Contextes qui devraient relever le seuil : Télévision, Radio, Musique
- Aboiement : la classe la plus utile pour les chiens. Préférer « Aboiement » seul plutôt que « Chien » + « Aboiement » (doublon).

### Sonnette de porte — `Doorbell` (n° 349)

- Catégorie : Alarmes, sonnettes et signaux · type de son : répété
- Faux positifs : **moyen** (causes : sonnettes de télévision, téléphones, sonnettes de voisins, carillons)
- Suggestions : seuil 0.5, détection soutenue d'au moins 2 s, ré-armement 30 s, clip de 5 s avant à 10 s après, conservé 7 jours
- Fait partie de : Alarme, Porte
- Contient : Ding-dong
- Contextes qui devraient relever le seuil : Télévision, Radio, Musique
- Sonnette de porte : utile pour notifier et pour déclencher une caméra. Les sonnettes électroniques à mélodie sont mieux détectées que les simples bips.

### Coups à la porte — `Knock` (n° 353)

- Catégorie : Sons de la maison · type de son : bref
- Faux positifs : **moyen** (causes : télévision, travaux chez les voisins, meubles)
- Suggestions : seuil 0.5, détection soutenue d'au moins 1 s, ré-armement 15 s, clip de 5 s avant à 5 s après, conservé 7 jours
- Fait partie de : Porte
- Contextes qui devraient relever le seuil : Télévision, Radio, Musique
- Coups à la porte : utile pour notifier une visite quand la sonnette est absente ou en panne.

### Pleurs de bébé — `Baby cry, infant cry` (n° 20)

- Catégorie : Voix humaine · type de son : répété
- Faux positifs : **moyen** (causes : miaulements de chat, télévision, enfants plus grands)
- Suggestions : seuil 0.5, détection soutenue d'au moins 2 s, ré-armement 30 s, clip de 5 s avant à 10 s après, conservé 3 jours
- Fait partie de : Pleurs, sanglots
- Contextes qui devraient relever le seuil : Télévision, Radio, Musique
- Pleurs de bébé : cas d'usage très demandé. Se confond parfois avec les miaulements (voir « Pleurs et cris aigus »). Exiger au moins 2 secondes de détection continue réduit les fausses alertes.

## 2. Classes optionnelles, par usage

Utiles selon votre situation (animaux, bébé, cuisine, fuites…). Elles sont désactivées tant que vous ne les activez pas.

### Sécurité

| Classe | Faux positifs | Vie privée | Seuil | Remarque |
|---|---|---|---|---|
| Cri (Shout) | élevé | sensible | 0.6 | Cri : classe parente de « Appel crié », « Cri de joie », « Beuglement » et « Enfants qui crient ». Choisir « Hurlements stridents » comme alerte principale, et ne garder « Cri » qu'en option. |
| Appel crié (Yell) | élevé | sensible | 0.6 | Appel crié : sous-classe de « Cri ». Doublon si « Cri » est choisi ; très sensible à la télévision et aux enfants. |
| Lamentation, gémissement (Wail, moan) | élevé | sensible | 0.6 | Lamentation, gémissement : intéressant en théorie pour une détresse, mais trop peu fiable pour déclencher seul une alerte. |
| Gémissement sourd (Groan) | élevé | sensible | 0.6 | Gémissement sourd. À ne pas utiliser seul pour une détection de chute ou de détresse. |
| Explosion | élevé | normale | 0.6 | Explosion : classe parente large de détonations. Bruyante et peu spécifique. |
| Coup de feu (Gunshot, gunfire) | élevé | normale | 0.6 | Coup de feu : ne jamais déclencher d'action automatique lourde sur cette seule classe. Dans les régions où les pétards ou les feux d'artifice sont courants, attendre beaucoup de fausses alertes. |
| Bruit sourd (Thump, thud) | élevé | normale | 0.6 | Bruit sourd : chute d'un objet ou d'une personne, meubles, voisins. Ne pas utiliser seul pour une détection de chute. |
| Fracas (Smash, crash) | élevé | normale | 0.55 |  |
| Casse (Breaking) | élevé | normale | 0.55 | Casse en général (pas seulement du verre) : plus large, donc plus de fausses alertes. |
| Fracas (cliquetis) (Clatter) | élevé | normale | 0.5 | Fracas d'objets qui tombent ou s'entrechoquent. |

### Incendie

| Classe | Faux positifs | Vie privée | Seuil | Remarque |
|---|---|---|---|---|
| Feu (Fire) | élevé | normale | 0.6 | Feu : à ne PAS utiliser comme alerte incendie fiable (crépitement très proche d'une friture ou d'une pluie). Réserver au contexte. |

### Porte et visiteurs

| Classe | Faux positifs | Vie privée | Seuil | Remarque |
|---|---|---|---|---|
| Porte (Door) | moyen | normale | 0.5 | Classe parente de « Sonnette de porte », « Coups à la porte », « Claquement de porte » : à ne pas choisir en même temps que ses enfants. |
| Ding-dong | moyen | normale | 0.5 | Sous-classe de « Sonnette de porte » : doublon si celle-ci est déjà surveillée. Utile en complément pour les sonnettes à deux tons. |
| Porte coulissante (Sliding door) | moyen | normale | 0.5 |  |
| Claquement de porte (Slam) | moyen | normale | 0.55 | Claquement de porte : confusion avec détonations (pétards) et chutes d'objets. |
| Cliquetis de clés (Keys jangling) | moyen | normale | 0.5 | Cliquetis de clés : indice d'arrivée à la porte, mais peu fiable seul. |
| Buzzer | élevé | normale | 0.55 | Buzzer : interphone, ouverture de porte d'immeuble, minuteries. Très proche des bips d'appareils. |
| Ding | élevé | normale | 0.6 | Ding : se confond avec la sonnette de porte et les minuteurs. |

### Bébé

| Classe | Faux positifs | Vie privée | Seuil | Remarque |
|---|---|---|---|---|
| Pleurs, sanglots (Crying, sobbing) | moyen | sensible | 0.55 | Pleurs d'enfant ou d'adulte. Redondant avec « Pleurs de bébé » pour surveiller un enfant en bas âge. |
| Gémissement plaintif (Whimper) | élevé | sensible | 0.6 | Gémissement plaintif : proche des pleurs faibles et de « Gémissement de chien ». Très flou. |

### Animaux

| Classe | Faux positifs | Vie privée | Seuil | Remarque |
|---|---|---|---|---|
| Chien (Dog) | moyen | normale | 0.5 | Classe parente : englobe aboiement, hurlement, grondement, etc. Choisir plutôt les classes précises. |
| Jappement (Yip) | moyen | normale | 0.5 | Sous-classe de « Chien » : redondant si « Aboiement » est déjà surveillé. |
| Hurlement de chien ou de loup (Howl) | moyen | normale | 0.5 | Sous-classe de « Chien » : redondant si « Aboiement » est déjà surveillé. |
| Ouaf (Bow-wow) | moyen | normale | 0.5 | Sous-classe de « Chien » : redondant si « Aboiement » est déjà surveillé. |
| Grondement (Growling) | moyen | normale | 0.5 | Sous-classe de « Chien » : redondant si « Aboiement » est déjà surveillé. |
| Gémissement de chien (Whimper (dog)) | moyen | normale | 0.5 | Sous-classe de « Chien » : redondant si « Aboiement » est déjà surveillé. |
| Chat (Cat) | moyen | normale | 0.5 | Classe parente : englobe miaulement, ronronnement, feulement. |
| Miaulement (Meow) | moyen | normale | 0.5 | Miaulement : se confond parfois avec des pleurs de bébé. |
| Feulement (Hiss) | élevé | normale | 0.5 | Feulement : proche d'un jet d'air ou de vapeur (« Vapeur », « Pulvérisation »). |
| Miaulements de bagarre (Caterwaul) | moyen | normale | 0.5 | Miaulements de bagarre : forts, proches de cris ou de pleurs. |

### Eau et fuites

| Classe | Faux positifs | Vie privée | Seuil | Remarque |
|---|---|---|---|---|
| Robinet (Water tap, faucet) | moyen | normale | 0.5 | Eau qui coule : à relier à une durée (robinet resté ouvert). Se confond avec la douche et le bruit blanc. |
| Évier (Sink (filling or washing)) | moyen | normale | 0.5 | Eau qui coule : à relier à une durée (robinet resté ouvert). Se confond avec la douche et le bruit blanc. |
| Baignoire (Bathtub (filling or washing)) | moyen | normale | 0.5 | Eau qui coule : à relier à une durée (robinet resté ouvert). Se confond avec la douche et le bruit blanc. |
| Chasse d'eau (Toilet flush) | moyen | normale | 0.5 | Chasse d'eau : une chasse qui coule en continu est détectable avec une durée. |
| Goutte à goutte (Drip) | moyen | normale | 0.5 | Goutte à goutte : peut signaler un robinet ou une fuite, à condition d'avoir un micro proche et un environnement calme. |
| Filet d'eau (Trickle, dribble) | moyen | normale | 0.5 |  |
| Jaillissement (Gush) | moyen | normale | 0.5 | Jaillissement : possible indice d'une fuite importante. Détecte le bruit, pas la fuite : à doubler d'un capteur d'eau. |
| Remplissage (liquide) (Fill (with liquid)) | moyen | normale | 0.5 | Remplissage : utile pour une baignoire ou un seau qui se remplit. Combiner avec une durée (par exemple plus de 10 minutes). |

### Cuisine

| Classe | Faux positifs | Vie privée | Seuil | Remarque |
|---|---|---|---|---|
| Four à micro-ondes (Microwave oven) | moyen | normale | 0.5 | Micro-ondes (surtout ses bips de fin). Source de FAUSSES alertes sur « Détecteur de fumée » : voir les règles de combinaison. |
| Sifflet (Whistle) | moyen | normale | 0.5 | Sifflet : peut détecter une bouilloire à sifflet, mais se confond avec un sifflement de bouche. |
| Sifflet à vapeur (Steam whistle) | moyen | normale | 0.5 | Sifflet à vapeur : bouilloire ou cocotte-minute. À tester. |
| Ébullition (Boiling) | moyen | normale | 0.5 | Ébullition : peut signaler une casserole ou une bouilloire qui bout. Ne remplace pas une sécurité cuisinière. |
| Bip (Beep, bleep) | élevé | normale | 0.6 | Bips d'appareils (fin de cycle). Très répandus, donc à regrouper avec « Micro-ondes » ; ne pas en faire une alerte incendie. |
| Grésillement (Sizzle) | moyen | normale | 0.5 | Grésillement : cuisson à la poêle. Détecte un bruit de cuisson, pas un danger. |

### Présence

| Classe | Faux positifs | Vie privée | Seuil | Remarque |
|---|---|---|---|---|
| Enfants qui crient (Children shouting) | élevé | sensible | 0.6 | Presque toujours un son normal. Peu utile pour une alerte. |
| Ronflement (Snoring) | moyen | sensible | 0.5 | Ronflement : indique qu'une personne dort dans la pièce ; sensible, ne pas conserver de clip. |
| Toux (Cough) | moyen | sensible | 0.5 | Toux : donnée de santé potentielle, donc sensible. Ne pas conserver de clip. |
| Éternuement (Sneeze) | moyen | sensible | 0.5 |  |
| Course (pas) (Run) | moyen | normale | 0.5 | Pas : complète un capteur de présence mais ne le remplace pas ; dépend beaucoup du revêtement et du micro. |
| Pas traînants (Shuffle) | moyen | normale | 0.5 | Pas : complète un capteur de présence mais ne le remplace pas ; dépend beaucoup du revêtement et du micro. |
| Marche, pas (Walk, footsteps) | moyen | normale | 0.5 | Pas : complète un capteur de présence mais ne le remplace pas ; dépend beaucoup du revêtement et du micro. |
| Enfants qui jouent (Children playing) | élevé | sensible | 0.5 | Enfants qui jouent : normal dans la plupart des cas. Peut servir à calmer d'autres classes (cris). |
| Sonnerie de téléphone (Telephone bell ringing) | élevé | normale | 0.6 | Sonnerie de téléphone fixe. Confusion avec la sonnette de porte. |
| Sonnerie de mobile (Ringtone) | élevé | normale | 0.6 | Sonnerie de mobile : intéressant pour retrouver un téléphone ou savoir qu'il sonne seul, mais très variable (mélodies). |

### Commande sans voix

| Classe | Faux positifs | Vie privée | Seuil | Remarque |
|---|---|---|---|---|
| Claquement de doigts (Finger snapping) | moyen | normale | 0.55 | Peut servir de commande sans voix (claquement de doigts), à tester. |
| Claquements de mains (Clapping) | moyen | normale | 0.55 | Claquements de mains : peut servir de commande sans voix. Confusion avec les applaudissements et certains chocs secs. |

### Extérieur

| Classe | Faux positifs | Vie privée | Seuil | Remarque |
|---|---|---|---|---|
| Alarme de voiture (Car alarm) | moyen | normale | 0.5 | Alarme de voiture : utile seulement si le véhicule est à portée d'écoute. Se répète dans la rue, donc beaucoup d'alertes sans importance. |
| Véhicule d'urgence (Emergency vehicle) | élevé | normale | 0.6 |  |
| Voiture de police (sirène) (Police car (siren)) | élevé | normale | 0.6 |  |
| Ambulance (sirène) (Ambulance (siren)) | élevé | normale | 0.6 |  |
| Camion de pompiers (sirène) (Fire engine, fire truck (siren)) | élevé | normale | 0.6 |  |
| Sirène (Siren) | élevé | normale | 0.6 | Sirène en général : classe parente des sirènes de véhicules. Surtout un indicateur de ce qui se passe dans la rue. |

### Météo

| Classe | Faux positifs | Vie privée | Seuil | Remarque |
|---|---|---|---|---|
| Orage (Thunderstorm) | moyen | normale | 0.5 | Orage : peut servir à des automatisations (fermer les stores, protéger du matériel). Se confond avec de lourds travaux. |
| Tonnerre (Thunder) | moyen | normale | 0.5 | Tonnerre : se confond avec des détonations sourdes. |

### Garage et voiture

| Classe | Faux positifs | Vie privée | Seuil | Remarque |
|---|---|---|---|---|
| Démarrage moteur (Engine starting) | moyen | normale | 0.5 | Démarrage moteur : possible pour un garage ou une voiture proche (arrivée, départ). |
| Moteur au ralenti (Idling) | moyen | normale | 0.5 | Moteur au ralenti : par exemple une voiture qui tourne dans un garage fermé. Détecte le bruit, pas le monoxyde. |

### Nuisibles

| Classe | Faux positifs | Vie privée | Seuil | Remarque |
|---|---|---|---|---|
| Rongeurs (rats, souris) (Rodents, rats, mice) | élevé | normale | 0.5 |  |
| Souris (Mouse) | élevé | normale | 0.5 | Souris : possible en grenier ou cave, mais très flou ; à tester avant d'en tirer une alerte. |
| Trottinement (Patter) | élevé | normale | 0.5 | Trottinement : confusion fréquente avec la pluie fine ou des pas légers. |

### Confort

| Classe | Faux positifs | Vie privée | Seuil | Remarque |
|---|---|---|---|---|
| Réveil (Alarm clock) | moyen | normale | 0.5 | Réveil qui sonne : peut servir à vérifier qu'un réveil a bien sonné ; se confond avec d'autres bips. |

### Autres usages

| Classe | Faux positifs | Vie privée | Seuil | Remarque |
|---|---|---|---|---|
| Sifflement (bouche) (Whistling) | moyen | normale | 0.5 | Sifflement de la bouche. Proche du sifflet (bouilloire, sifflet à vapeur) : voir « Sifflets ». |

## 3. Classes de contexte et de diagnostic

Elles ne servent pas d'alerte. Les classes de **contexte** (télévision, musique, parole, pluie…) permettent de relever les seuils des classes sensibles aux fausses alertes. Les classes de **diagnostic** indiquent un problème de micro (ronflement du secteur, vent, distorsion).

### Contexte

| Classe | Vie privée | Remarque |
|---|---|---|
| Parole (Speech) | confidentielle | Parole : aucun clip ne doit être conservé. Utile uniquement comme contexte (« quelqu'un parle ») pour relever les seuils des autres classes. |
| Parole d'enfant (Child speech, kid speaking) | confidentielle | Mêmes précautions que « Parole » : aucun clip, contexte seulement. |
| Conversation | confidentielle | Mêmes précautions que « Parole » : aucun clip, contexte seulement. |
| Narration, monologue | confidentielle | Mêmes précautions que « Parole » : aucun clip, contexte seulement. |
| Babillage (Babbling) | confidentielle | Mêmes précautions que « Parole » : aucun clip, contexte seulement. |
| Synthèse vocale (Speech synthesizer) | normale | Voix de synthèse (assistant vocal, annonces). Peut servir à ignorer les sons produits par vos propres assistants. |
| Bavardage (Chatter) | confidentielle |  |
| Foule (Crowd) | confidentielle | Foule : souvent la télévision ou la rue. À utiliser seulement comme contexte. |
| Brouhaha (Hubbub, speech noise, speech babble) | confidentielle | Brouhaha : plusieurs voix en même temps. Contexte seulement. |
| Oiseau (Bird) | normale | Oiseaux en général : sert d'indicateur d'ambiance extérieure (micro proche d'une fenêtre ouverte). |
| Chant d'oiseau (Bird vocalization, bird call, bird song) | normale |  |
| Musique (Music) | normale | Classe la plus utile du groupe musique : un seul signal « de la musique joue » pour relever les seuils des autres classes. Les 140+ autres classes musicales (instruments, genres) sont ignorées par défaut. |
| Vent (Wind) | normale | Vent : sert à relativiser les autres détections extérieures. |
| Pluie (Rain) | normale | Pluie : utile comme contexte (fenêtre restée ouverte, linge dehors) et pour relever les seuils des autres classes. Confusion avec bruit blanc et friture. |
| Goutte de pluie (Raindrop) | normale | Pluie : utile comme contexte (fenêtre restée ouverte, linge dehors) et pour relever les seuils des autres classes. Confusion avec bruit blanc et friture. |
| Pluie sur une surface (Rain on surface) | normale | Pluie : utile comme contexte (fenêtre restée ouverte, linge dehors) et pour relever les seuils des autres classes. Confusion avec bruit blanc et friture. |
| Bruit de circulation (Traffic noise, roadway noise) | normale | Circulation : indique l'ambiance extérieure ; utile pour relever les seuils près d'une fenêtre. |
| Aspirateur (Vacuum cleaner) | normale | Aspirateur : très reconnaissable. Utile pour ignorer les autres détections pendant le ménage. |
| Feux d'artifice (Fireworks) | normale | Feux d'artifice : à utiliser comme contexte pour relever les seuils de « Coup de feu », « Explosion » et « Éclatement » pendant les fêtes. |
| Pétard (Firecracker) | normale | Pétard : idem « Feux d'artifice » ; confusion fréquente avec un coup de feu. |
| Intérieur, petite pièce (Inside, small room) | normale | Décrit l'acoustique du lieu (pièce, extérieur) plutôt qu'un événement : utile seulement pour comprendre l'environnement du micro. |
| Intérieur, grande salle (Inside, large room or hall) | normale | Décrit l'acoustique du lieu (pièce, extérieur) plutôt qu'un événement : utile seulement pour comprendre l'environnement du micro. |
| Intérieur, espace public (Inside, public space) | normale | Décrit l'acoustique du lieu (pièce, extérieur) plutôt qu'un événement : utile seulement pour comprendre l'environnement du micro. |
| Extérieur, urbain (Outside, urban or manmade) | normale | Décrit l'acoustique du lieu (pièce, extérieur) plutôt qu'un événement : utile seulement pour comprendre l'environnement du micro. |
| Extérieur, rural ou nature (Outside, rural or natural) | normale | Décrit l'acoustique du lieu (pièce, extérieur) plutôt qu'un événement : utile seulement pour comprendre l'environnement du micro. |
| Télévision (Television) | normale | La télévision est la première cause de fausses alertes. Comme classe de CONTEXTE, elle permet de relever les seuils de cris, coups de feu, aboiements et sonnettes quand elle tourne. |
| Radio | normale | Même usage que « Télévision » : signale qu'un son vient d'un haut-parleur, pas de la pièce. |

### Diagnostic du micro

| Classe | Vie privée | Remarque |
|---|---|---|
| Bruit de vent (dans le micro) (Wind noise (microphone)) | normale | Vent dans le micro : indique que le micro est exposé à un courant d'air (fenêtre ouverte, ventilation). À utiliser pour déplacer le micro. |
| Silence | normale | Silence : si cette classe est constante alors qu'il y a de l'activité, le micro est probablement muet ou mal branché. |
| Parasites (statique) (Static) | normale | Indicateur de qualité du micro : une valeur élevée en continu signale souvent un micro bruyant ou saturé. |
| Ronflement du secteur (50/60 Hz) (Mains hum) | normale | Ronflement du secteur (50/60 Hz) : s'il est élevé en permanence, le micro capte un bruit électrique (alimentation, boucle de masse). À corriger côté câblage. |
| Distorsion (Distortion) | normale | Indicateur de qualité du micro : une valeur élevée en continu signale souvent un micro bruyant ou saturé. |
| Effet local (sidetone) (Sidetone) | normale | Indicateur de qualité du micro : une valeur élevée en continu signale souvent un micro bruyant ou saturé. |
| Bruit blanc (White noise) | normale | Indicateur de qualité du micro : une valeur élevée en continu signale souvent un micro bruyant ou saturé. |
| Bruit rose (Pink noise) | normale | Indicateur de qualité du micro : une valeur élevée en continu signale souvent un micro bruyant ou saturé. |

## 4. Groupes de classes proches

Des classes qui se ressemblent ou se recouvrent. L'intégration affichera ces avertissements quand vous en sélectionnerez plusieurs d'un même groupe.

### Chiens

Classes : Chien, Aboiement, Jappement, Hurlement de chien ou de loup, Ouaf, Grondement, Gémissement de chien, Canidés (chiens, loups)

- **Risque** : « Chien » contient « Aboiement », « Jappement », « Ouaf », « Grondement », « Hurlement » et « Gémissement de chien » : un aboiement active souvent « Chien » en même temps. « Canidés » (chiens et loups) ne contient que « Grondement » et « Hurlement ».
- **Conseil** : Surveiller « Aboiement » seul. Ajouter « Hurlement de chien ou de loup » seulement si les hurlements vous intéressent.

### Chats

Classes : Chat, Miaulement, Ronronnement, Feulement, Miaulements de bagarre

- **Risque** : « Chat » englobe les autres. Les miaulements stridents ressemblent à des pleurs de bébé.
- **Conseil** : Choisir « Miaulement » seul ; ne pas combiner avec une alerte « pleurs de bébé » sans règle de confirmation.

### Pleurs et cris aigus

Classes : Pleurs de bébé, Pleurs, sanglots, Gémissement plaintif, Lamentation, gémissement, Miaulement, Miaulements de bagarre, Hurlements stridents, Cri strident (mécanique)

- **Risque** : Sons aigus et plaintifs qui se confondent entre eux (bébé, chat, cri humain, grincement).
- **Conseil** : Si vous surveillez un bébé : « Pleurs de bébé » avec au moins 2 secondes de détection continue ; ignorez les autres.

### Cris et appels

Classes : Cri, Appel crié, Hurlements stridents, Beuglement (voix), Cri de joie, Enfants qui crient, Enfants qui jouent, Acclamations, Foule

- **Risque** : Les enfants qui jouent, les matchs à la télévision et les films déclenchent souvent ces classes.
- **Conseil** : Garder « Hurlements stridents » (et éventuellement « Cri ») avec un seuil élevé ; utiliser « Télévision » comme contexte.

### Parole, voix et contexte vocal

Classes : Parole, Conversation, Parole d'enfant, Narration, monologue, Babillage, Chuchotement, Bavardage, Brouhaha, Synthèse vocale, Télévision, Radio

- **Risque** : Vie privée : ces classes détectent des conversations. Se confondent avec la télévision et la radio.
- **Conseil** : Ne jamais conserver de clip. Les utiliser comme contexte (« quelqu'un parle ») plutôt que comme alerte.

### Voix chantée, psalmodie et prière diffusée

Classes : Chant, Psalmodie, Mantra, Chorale, Musique vocale, Musique du Moyen-Orient, Fredonnement, Chant d'enfant, Chant synthétique, Parole

- **Risque** : Une voix chantée ou psalmodiée diffusée par haut-parleur (appel à la prière, annonces) active plusieurs de ces classes, ainsi que « Parole ».
- **Conseil** : Ne pas en faire des alertes. Si ces sons sont fréquents chez vous, relever les seuils des autres classes vocales à ces moments.

### Détonations et chocs secs

Classes : Coup de feu, Mitrailleuse, Fusillade, Tir d'artillerie, Pistolet à amorces, Feux d'artifice, Pétard, Explosion, Détonation sourde, Coup sec (bang), Éclatement, Claquement de porte, Bruit sourd, Choc sourd, Tonnerre

- **Risque** : Pétards, feux d'artifice, portes qui claquent et tonnerre sont facilement pris pour un coup de feu.
- **Conseil** : Ne jamais déclencher d'action lourde sur ces classes seules. Utiliser « Feux d'artifice » et « Pétard » comme contexte inhibiteur.

### Verre et casse

Classes : Verre, Verre brisé, Tintement de verre, Casse, Fracas, Vaisselle, casseroles, Couverts, Fracas (cliquetis)

- **Risque** : La vaisselle qui tombe ou s'entrechoque ressemble à un verre brisé.
- **Conseil** : Garder « Verre brisé » seul pour la sécurité ; « Casse » et « Fracas » en option. Confirmer avec un capteur d'ouverture ou une caméra.

### Alarmes incendie et bips d'appareils

Classes : Détecteur de fumée, Alarme incendie, Alarme, Buzzer, Bip, Four à micro-ondes, Bip de marche arrière, Réveil

- **Risque** : Un bip isolé de micro-ondes ou de lave-linge peut ressembler à un détecteur de fumée.
- **Conseil** : Pour l'alerte incendie : « Détecteur de fumée » et « Alarme incendie » avec au moins 3 secondes de détection soutenue. Ne pas ajouter « Bip » comme alerte.

### Sonnettes, sonneries et cloches

Classes : Sonnette de porte, Ding-dong, Ding, Ping, Cloche, Cloche d'église, Carillon, Carillon à vent, Grelot, Sonnette de vélo, Sonnerie de téléphone, Sonnerie de mobile, Téléphone, Tintement, Diapason

- **Risque** : Les sonneries de téléphone, de télévision et les cloches sont proches d'une sonnette de porte.
- **Conseil** : Pour la porte : « Sonnette de porte » seul. Les sonneries de téléphone et les cloches restent hors alerte.

### Sirènes et avertisseurs

Classes : Sirène, Voiture de police (sirène), Ambulance (sirène), Camion de pompiers (sirène), Véhicule d'urgence, Sirène de défense civile, Alarme de voiture, Klaxon, Coup de klaxon bref, Avertisseur pneumatique, Corne de brume

- **Risque** : Sons de rue très fréquents, qui se confondent entre eux et avec la télévision.
- **Conseil** : Utile seulement comme indicateur extérieur ; ne pas déclencher d'alerte maison.

### Sifflets

Classes : Sifflet, Sifflet à vapeur, Sifflement (bouche), Sifflet de train, Feulement, Vapeur

- **Risque** : Une bouilloire à sifflet, un sifflement de bouche ou une fuite de vapeur sont proches.
- **Conseil** : À tester avec votre cuisine avant d'en faire une automatisation.

### Portes, coups et frappes

Classes : Coups à la porte, Porte, Claquement de porte, Tapotement, Porte coulissante, Bruit sourd, Choc sourd, Coup sec (bang), Placard (ouverture, fermeture), Tiroir (ouverture, fermeture), Grincement aigu

- **Risque** : Coups à la porte, tiroirs et meubles se confondent. « Porte » englobe plusieurs sons.
- **Conseil** : Choisir « Coups à la porte » pour une visite, « Claquement de porte » pour les claquements ; éviter « Porte » et « Tapotement ».

### Eau qui coule, fuites

Classes : Robinet, Évier, Baignoire, Verser, Filet d'eau, Jaillissement, Remplissage (liquide), Goutte à goutte, Éclaboussure, Ruisseau, Chasse d'eau, Pluie, Pluie sur une surface, Goutte de pluie, Ébullition, Bruit blanc

- **Risque** : Un robinet, la douche, la pluie et le bruit blanc se ressemblent. Aucune de ces classes ne détecte l'eau : seulement son bruit.
- **Conseil** : Toujours accompagner d'une durée et d'un vrai capteur d'eau pour les fuites.

### Moteurs et appareils continus

Classes : Aspirateur, Sèche-cheveux, Mixeur, Ventilateur mécanique, Climatisation, Moteur, Petit moteur (aigu), Moteur moyen (médium), Gros moteur (grave), Moteur au ralenti, Tondeuse, Outil électrique, Perceuse, Bruit blanc, Bruit rose, Bruit, Bruit ambiant, Vrombissement, Bourdonnement (hum)

- **Risque** : Bruits continus qui se confondent entre eux et masquent les autres sons.
- **Conseil** : Les traiter comme contexte : ils indiquent surtout pourquoi les autres classes sont moins sensibles.

### Pas et présence

Classes : Marche, pas, Course (pas), Pas traînants, Trottinement, Frappe au clavier, Clavier d'ordinateur, Cliquetis de clés, Claquement de doigts, Claquements de mains

- **Risque** : Un capteur de présence fait mieux. Les pas dépendent du revêtement de sol, du micro et des voisins.
- **Conseil** : À utiliser en complément d'un capteur de présence, pas à sa place.

### Toux, éternuements et respiration

Classes : Toux, Raclement de gorge, Éternuement, Reniflement, Ébrouement, Respiration sifflante, Respiration, Ronflement, Souffle coupé, Halètement, Soupir

- **Risque** : Sons proches entre eux ; ils relèvent de la santé donc sensibles.
- **Conseil** : Ne pas conserver de clip. À réserver à des usages de présence discrète.

### Insectes et rongeurs

Classes : Insecte, Moustique, Mouche, Bourdonnement d'insecte, Abeille, guêpe, Grillon, Souris, Rongeurs (rats, souris), Trottinement, Grattement

- **Risque** : Très faibles et très proches de bruits d'appareils ou de tuyauterie.
- **Conseil** : Peu fiables ; à n'essayer qu'avec un micro proche (grenier, cave).

### Oiseaux

Classes : Oiseau, Chant d'oiseau, Pépiement, Criaillement, Pigeon, colombe, Roucoulement, Corbeau, corneille, Croassement, Hibou, chouette, Hululement, Poule, coq, Chant du coq, Battements d'ailes

- **Risque** : « Oiseau » englobe presque toutes les autres classes de ce groupe.
- **Conseil** : Utile seulement comme indicateur d'ambiance extérieure.

### Véhicules dans la rue

Classes : Véhicule, Véhicule à moteur (route), Voiture, Voiture qui passe, Camion, Bus, Moto, Bruit de circulation, Moteur, Démarrage moteur, Moteur au ralenti, Accélération moteur, Dérapage, Crissement de pneus

- **Risque** : Sons de rue omniprésents ; le micro près d'une fenêtre les capte en continu.
- **Conseil** : Les utiliser comme contexte extérieur ; ignorer leurs événements.

### Feu, crépitement et cuisson

Classes : Feu, Crépitement, Friture, Grésillement, Feuilles qui bruissent, Pluie sur une surface, Parasites (statique)

- **Risque** : Le feu, la friture, la pluie et les parasites se ressemblent beaucoup.
- **Conseil** : Ne pas utiliser « Feu » comme alerte incendie. Se fier à un vrai détecteur de fumée.

### Diagnostic de la qualité du micro

Classes : Ronflement du secteur (50/60 Hz), Parasites (statique), Bruit blanc, Bruit rose, Distorsion, Silence, Bruit de vent (dans le micro), Effet local (sidetone), Réverbération

- **Risque** : Ces classes ne décrivent pas un événement de la maison, mais l'état du micro et de son câblage.
- **Conseil** : À surveiller pendant la mise en place : un « ronflement du secteur » constant, du vent ou de la distorsion indiquent un problème matériel.

### Musique

Classes : Musique, Chanson, Musique de fond, Thème musical, Bande originale, Musique pop, Chant, Télévision, Radio

- **Risque** : Une musique de fond active de nombreuses classes (voix, instruments, cloches).
- **Conseil** : Garder « Musique » comme contexte ; ignorer instruments et genres.

## 5. Règles d'avertissement

### Règles sur des combinaisons précises

| Niveau | Classes concernées | Avertissement |
|---|---|---|
| info | Détecteur de fumée, Alarme incendie | « Détecteur de fumée » et « Alarme incendie » sont très proches : un même événement peut déclencher les deux. Utilisez la même action pour les deux et ne comptez qu'une alerte (délai de ré-armement). |
| attention | Détecteur de fumée, Bip | « Bip » se déclenche aussi sur micro-ondes et lave-linge : ne l'utilisez pas comme alerte incendie, et exigez une détection soutenue d'au moins 3 secondes pour « Détecteur de fumée ». |
| attention | Feu, Crépitement | « Feu » et « Crépitement » se confondent avec la friture et la pluie : ne les utilisez pas comme alerte incendie. |
| attention | Coup de feu, Explosion, Feux d'artifice, Pétard | Feux d'artifice et pétards se confondent avec des coups de feu. Utilisez « Feux d'artifice » et « Pétard » en contexte inhibiteur, pas comme événements, et ne déclenchez pas d'action lourde sur « Coup de feu » seul. |
| attention | Sonnette de porte, Ding-dong, Ding, Cloche, Carillon | Plusieurs classes de sonnette/cloche se déclenchent en même temps. Gardez « Sonnette de porte » comme alerte principale. |
| attention | Sonnette de porte, Sonnerie de téléphone, Sonnerie de mobile | Les sonneries de téléphone peuvent déclencher « Sonnette de porte ». Mesurez les confusions chez vous avant d'automatiser. |
| attention | Pleurs de bébé, Miaulement, Miaulements de bagarre | Les miaulements (surtout les cris de chats) sont parfois classés comme pleurs de bébé : exigez une détection soutenue d'au moins 2 secondes et un seuil adapté. |
| info | Cri, Appel crié, Hurlements stridents, Enfants qui crient | Ces classes sont voisines : choisissez-en une comme alerte principale (par exemple « Hurlements stridents »). Les autres produiront des alertes en double. |
| info | Verre, Verre brisé, Casse, Fracas | « Verre » est le parent de « Verre brisé » : choisissez « Verre brisé » seul, et « Casse » ou « Fracas » en option avec un seuil plus élevé. |
| info | Chien, Aboiement, Canidés (chiens, loups) | « Chien » contient « Aboiement » (et « Jappement », « Ouaf », « Grondement », « Hurlement ») : un aboiement déclenche les deux. Gardez « Aboiement ». « Canidés » est redondant et plus bruyant. |
| attention | Parole, Conversation, Chuchotement, Parole d'enfant | Classes de parole : elles détectent des conversations. Aucun clip ne doit être conservé ; utilisez-les seulement comme contexte. |
| attention | Robinet, Jaillissement, Goutte à goutte, Remplissage (liquide) | Ces classes détectent le bruit de l'eau, pas l'eau. Pour une fuite, ajoutez un vrai capteur d'eau et une durée minimale (par exemple 5 à 10 minutes). |
| info | Musique, Chanson, Chant, Musique vocale, Musique pop, Musique de fond | Quand la musique joue, de nombreuses classes (voix, instruments, cloches) s'activent. Surveillez « Musique » comme contexte plutôt que ses sous-classes. |
| info | Hurlements stridents, Coup de feu, Aboiement, Sonnette de porte, Verre brisé | Ces classes sont sensibles à la télévision et à la radio. Ajoutez « Télévision » et « Radio » comme contexte pour relever automatiquement les seuils. |

### Règles appliquées automatiquement

Elles se déduisent des champs de chaque classe, sans liste à maintenir.

- **info** — *une classe sélectionnée est un ancêtre (ancetres_yamnet / descendants_yamnet) d'une autre classe sélectionnée* : « {parent} » contient « {enfant} » : un même son déclenchera les deux. Gardez la plus précise, ou la plus large, mais pas les deux avec des règles différentes (rétention, seuil, action).
- **danger** — *conservation_clip_jours > 0 sur une classe dont clip_interdit vaut vrai* : « {classe} » détecte des conversations : aucun clip ne doit être conservé. La rétention est forcée à 0.
- **attention** — *seuil inférieur au seuil suggéré sur une classe dont faux_positifs.niveau vaut « eleve »* : « {classe} » est souvent déclenchée à tort ; un seuil aussi bas multipliera les fausses alertes. Ajoutez un contexte inhibiteur (télévision, radio, musique).
- **info** — *role vaut « generique »* : « {classe} » est une classe parente large : préférez ses sous-classes ({exemples}).
- **info** — *classe avec contextes_inhibiteurs non vide, sans aucune classe de contexte sélectionnée* : « {classe} » est sensible à la télévision, à la radio ou à la musique : sélectionnez-les comme classes de contexte pour relever automatiquement les seuils.

## 6. Toutes les classes par catégorie

Chaque ligne donne le numéro YAMNet, le nom anglais exact (celui du modèle), le nom français, l'intérêt, le risque de faux positifs et la sensibilité pour la vie privée.

### Voix humaine (36)

| N° | Classe (modèle) | Français | Intérêt | Faux pos. | Vie privée |
|---|---|---|---|---|---|
| 0 | Speech | Parole | Contexte | élevé | confidentielle |
| 1 | Child speech, kid speaking | Parole d'enfant | Contexte | élevé | confidentielle |
| 2 | Conversation | Conversation | Contexte | élevé | confidentielle |
| 3 | Narration, monologue | Narration, monologue | Contexte | élevé | confidentielle |
| 4 | Babbling | Babillage | Contexte | élevé | confidentielle |
| 5 | Speech synthesizer | Synthèse vocale | Contexte | moyen | normale |
| 6 | Shout | Cri | Optionnelle | élevé | sensible |
| 7 | Bellow | Beuglement (voix) | Ignorée | élevé | sensible |
| 8 | Whoop | Cri de joie | Ignorée | élevé | sensible |
| 9 | Yell | Appel crié | Optionnelle | élevé | sensible |
| 10 | Children shouting | Enfants qui crient | Optionnelle | élevé | sensible |
| 11 | Screaming | Hurlements stridents | À surveiller | élevé | sensible |
| 12 | Whispering | Chuchotement | Ignorée | élevé | confidentielle |
| 13 | Laughter | Rire | Ignorée | élevé | sensible |
| 14 | Baby laughter | Rire de bébé | Ignorée | élevé | sensible |
| 15 | Giggle | Gloussement | Ignorée | élevé | sensible |
| 16 | Snicker | Ricanement | Ignorée | élevé | sensible |
| 17 | Belly laugh | Fou rire | Ignorée | élevé | sensible |
| 18 | Chuckle, chortle | Petit rire | Ignorée | élevé | sensible |
| 19 | Crying, sobbing | Pleurs, sanglots | Optionnelle | moyen | sensible |
| 20 | Baby cry, infant cry | Pleurs de bébé | À surveiller | moyen | sensible |
| 21 | Whimper | Gémissement plaintif | Optionnelle | élevé | sensible |
| 22 | Wail, moan | Lamentation, gémissement | Optionnelle | élevé | sensible |
| 23 | Sigh | Soupir | Ignorée | élevé | sensible |
| 24 | Singing | Chant | Ignorée | élevé | sensible |
| 25 | Choir | Chorale | Ignorée | élevé | sensible |
| 26 | Yodeling | Yodel | Ignorée | élevé | sensible |
| 27 | Chant | Psalmodie | Ignorée | élevé | sensible |
| 28 | Mantra | Mantra | Ignorée | élevé | sensible |
| 29 | Child singing | Chant d'enfant | Ignorée | élevé | sensible |
| 30 | Synthetic singing | Chant synthétique | Ignorée | élevé | sensible |
| 31 | Rapping | Rap (voix) | Ignorée | élevé | sensible |
| 32 | Humming | Fredonnement | Ignorée | élevé | sensible |
| 33 | Groan | Gémissement sourd | Optionnelle | élevé | sensible |
| 34 | Grunt | Grognement (voix) | Ignorée | élevé | sensible |
| 35 | Whistling | Sifflement (bouche) | Optionnelle | moyen | normale |

### Corps et activités (25)

| N° | Classe (modèle) | Français | Intérêt | Faux pos. | Vie privée |
|---|---|---|---|---|---|
| 36 | Breathing | Respiration | Ignorée | moyen | sensible |
| 37 | Wheeze | Respiration sifflante | Ignorée | moyen | sensible |
| 38 | Snoring | Ronflement | Optionnelle | moyen | sensible |
| 39 | Gasp | Souffle coupé | Ignorée | moyen | sensible |
| 40 | Pant | Halètement | Ignorée | moyen | sensible |
| 41 | Snort | Ébrouement | Ignorée | moyen | sensible |
| 42 | Cough | Toux | Optionnelle | moyen | sensible |
| 43 | Throat clearing | Raclement de gorge | Ignorée | moyen | sensible |
| 44 | Sneeze | Éternuement | Optionnelle | moyen | sensible |
| 45 | Sniff | Reniflement | Ignorée | moyen | sensible |
| 46 | Run | Course (pas) | Optionnelle | moyen | normale |
| 47 | Shuffle | Pas traînants | Optionnelle | moyen | normale |
| 48 | Walk, footsteps | Marche, pas | Optionnelle | moyen | normale |
| 49 | Chewing, mastication | Mastication | Ignorée | moyen | sensible |
| 50 | Biting | Croquer | Ignorée | moyen | sensible |
| 51 | Gargling | Gargarisme | Ignorée | moyen | sensible |
| 52 | Stomach rumble | Gargouillis d'estomac | Ignorée | moyen | sensible |
| 53 | Burping, eructation | Rot | Ignorée | moyen | sensible |
| 54 | Hiccup | Hoquet | Ignorée | moyen | sensible |
| 55 | Fart | Pet | Ignorée | moyen | sensible |
| 56 | Hands | Bruits de mains | Ignorée | moyen | sensible |
| 57 | Finger snapping | Claquement de doigts | Optionnelle | moyen | normale |
| 58 | Clapping | Claquements de mains | Optionnelle | moyen | normale |
| 59 | Heart sounds, heartbeat | Battements de cœur | Ignorée | élevé | sensible |
| 60 | Heart murmur | Souffle au cœur | Ignorée | élevé | sensible |

### Foule et groupes (6)

| N° | Classe (modèle) | Français | Intérêt | Faux pos. | Vie privée |
|---|---|---|---|---|---|
| 61 | Cheering | Acclamations | Ignorée | élevé | sensible |
| 62 | Applause | Applaudissements | Ignorée | élevé | sensible |
| 63 | Chatter | Bavardage | Contexte | élevé | confidentielle |
| 64 | Crowd | Foule | Contexte | élevé | confidentielle |
| 65 | Hubbub, speech noise, speech babble | Brouhaha | Contexte | élevé | confidentielle |
| 66 | Children playing | Enfants qui jouent | Optionnelle | élevé | sensible |

### Animaux domestiques (13)

| N° | Classe (modèle) | Français | Intérêt | Faux pos. | Vie privée |
|---|---|---|---|---|---|
| 68 | Domestic animals, pets | Animaux domestiques | Ignorée | moyen | normale |
| 69 | Dog | Chien | Optionnelle | moyen | normale |
| 70 | Bark | Aboiement | À surveiller | moyen | normale |
| 71 | Yip | Jappement | Optionnelle | moyen | normale |
| 72 | Howl | Hurlement de chien ou de loup | Optionnelle | moyen | normale |
| 73 | Bow-wow | Ouaf | Optionnelle | moyen | normale |
| 74 | Growling | Grondement | Optionnelle | moyen | normale |
| 75 | Whimper (dog) | Gémissement de chien | Optionnelle | moyen | normale |
| 76 | Cat | Chat | Optionnelle | moyen | normale |
| 77 | Purr | Ronronnement | Ignorée | moyen | normale |
| 78 | Meow | Miaulement | Optionnelle | moyen | normale |
| 79 | Hiss | Feulement | Optionnelle | élevé | normale |
| 80 | Caterwaul | Miaulements de bagarre | Optionnelle | moyen | normale |

### Animaux de ferme (22)

| N° | Classe (modèle) | Français | Intérêt | Faux pos. | Vie privée |
|---|---|---|---|---|---|
| 81 | Livestock, farm animals, working animals | Animaux de ferme | Ignorée | moyen | normale |
| 82 | Horse | Cheval | Ignorée | moyen | normale |
| 83 | Clip-clop | Sabots (clip-clop) | Ignorée | moyen | normale |
| 84 | Neigh, whinny | Hennissement | Ignorée | moyen | normale |
| 85 | Cattle, bovinae | Bovins | Ignorée | moyen | normale |
| 86 | Moo | Meuglement | Ignorée | moyen | normale |
| 87 | Cowbell | Cloche de vache | Ignorée | moyen | normale |
| 88 | Pig | Cochon | Ignorée | moyen | normale |
| 89 | Oink | Grognement de cochon | Ignorée | moyen | normale |
| 90 | Goat | Chèvre | Ignorée | moyen | normale |
| 91 | Bleat | Bêlement | Ignorée | moyen | normale |
| 92 | Sheep | Mouton | Ignorée | moyen | normale |
| 93 | Fowl | Volaille | Ignorée | moyen | normale |
| 94 | Chicken, rooster | Poule, coq | Ignorée | moyen | normale |
| 95 | Cluck | Caquètement | Ignorée | moyen | normale |
| 96 | Crowing, cock-a-doodle-doo | Chant du coq | Ignorée | moyen | normale |
| 97 | Turkey | Dinde | Ignorée | moyen | normale |
| 98 | Gobble | Glouglou de dinde | Ignorée | moyen | normale |
| 99 | Duck | Canard | Ignorée | moyen | normale |
| 100 | Quack | Coin-coin | Ignorée | moyen | normale |
| 101 | Goose | Oie | Ignorée | moyen | normale |
| 102 | Honk | Cri d'oie | Ignorée | moyen | normale |

### Animaux sauvages, oiseaux, insectes (30)

| N° | Classe (modèle) | Français | Intérêt | Faux pos. | Vie privée |
|---|---|---|---|---|---|
| 67 | Animal | Animal | Ignorée | moyen | normale |
| 103 | Wild animals | Animaux sauvages | Ignorée | moyen | normale |
| 104 | Roaring cats (lions, tigers) | Grands félins (rugissements) | Ignorée | élevé | normale |
| 105 | Roar | Rugissement | Ignorée | élevé | normale |
| 106 | Bird | Oiseau | Contexte | moyen | normale |
| 107 | Bird vocalization, bird call, bird song | Chant d'oiseau | Contexte | moyen | normale |
| 108 | Chirp, tweet | Pépiement | Ignorée | moyen | normale |
| 109 | Squawk | Criaillement | Ignorée | moyen | normale |
| 110 | Pigeon, dove | Pigeon, colombe | Ignorée | moyen | normale |
| 111 | Coo | Roucoulement | Ignorée | moyen | normale |
| 112 | Crow | Corbeau, corneille | Ignorée | moyen | normale |
| 113 | Caw | Croassement | Ignorée | moyen | normale |
| 114 | Owl | Hibou, chouette | Ignorée | moyen | normale |
| 115 | Hoot | Hululement | Ignorée | moyen | normale |
| 116 | Bird flight, flapping wings | Battements d'ailes | Ignorée | moyen | normale |
| 117 | Canidae, dogs, wolves | Canidés (chiens, loups) | Ignorée | moyen | normale |
| 118 | Rodents, rats, mice | Rongeurs (rats, souris) | Optionnelle | élevé | normale |
| 119 | Mouse | Souris | Optionnelle | élevé | normale |
| 120 | Patter | Trottinement | Optionnelle | élevé | normale |
| 121 | Insect | Insecte | Ignorée | élevé | normale |
| 122 | Cricket | Grillon | Ignorée | élevé | normale |
| 123 | Mosquito | Moustique | Ignorée | élevé | normale |
| 124 | Fly, housefly | Mouche | Ignorée | élevé | normale |
| 125 | Buzz | Bourdonnement d'insecte | Ignorée | élevé | normale |
| 126 | Bee, wasp, etc. | Abeille, guêpe | Ignorée | élevé | normale |
| 127 | Frog | Grenouille | Ignorée | moyen | normale |
| 128 | Croak | Coassement | Ignorée | moyen | normale |
| 129 | Snake | Serpent | Ignorée | moyen | normale |
| 130 | Rattle | Cliquetis de crécelle | Ignorée | moyen | normale |
| 131 | Whale vocalization | Chant de baleine | Ignorée | élevé | normale |

### Musique (144)

| N° | Classe (modèle) | Français | Intérêt | Faux pos. | Vie privée |
|---|---|---|---|---|---|
| 132 | Music | Musique | Contexte | élevé | normale |
| 133 | Musical instrument | Instrument de musique | Ignorée | élevé | normale |
| 134 | Plucked string instrument | Instrument à cordes pincées | Ignorée | élevé | normale |
| 135 | Guitar | Guitare | Ignorée | élevé | normale |
| 136 | Electric guitar | Guitare électrique | Ignorée | élevé | normale |
| 137 | Bass guitar | Guitare basse | Ignorée | élevé | normale |
| 138 | Acoustic guitar | Guitare acoustique | Ignorée | élevé | normale |
| 139 | Steel guitar, slide guitar | Guitare slide (steel) | Ignorée | élevé | normale |
| 140 | Tapping (guitar technique) | Tapping (guitare) | Ignorée | élevé | normale |
| 141 | Strum | Grattement d'accords | Ignorée | élevé | normale |
| 142 | Banjo | Banjo | Ignorée | élevé | normale |
| 143 | Sitar | Sitar | Ignorée | élevé | normale |
| 144 | Mandolin | Mandoline | Ignorée | élevé | normale |
| 145 | Zither | Cithare | Ignorée | élevé | normale |
| 146 | Ukulele | Ukulélé | Ignorée | élevé | normale |
| 147 | Keyboard (musical) | Clavier (musical) | Ignorée | élevé | normale |
| 148 | Piano | Piano | Ignorée | élevé | normale |
| 149 | Electric piano | Piano électrique | Ignorée | élevé | normale |
| 150 | Organ | Orgue | Ignorée | élevé | normale |
| 151 | Electronic organ | Orgue électronique | Ignorée | élevé | normale |
| 152 | Hammond organ | Orgue Hammond | Ignorée | élevé | normale |
| 153 | Synthesizer | Synthétiseur | Ignorée | élevé | normale |
| 154 | Sampler | Échantillonneur | Ignorée | élevé | normale |
| 155 | Harpsichord | Clavecin | Ignorée | élevé | normale |
| 156 | Percussion | Percussions | Ignorée | élevé | normale |
| 157 | Drum kit | Batterie | Ignorée | élevé | normale |
| 158 | Drum machine | Boîte à rythmes | Ignorée | élevé | normale |
| 159 | Drum | Tambour | Ignorée | élevé | normale |
| 160 | Snare drum | Caisse claire | Ignorée | élevé | normale |
| 161 | Rimshot | Rimshot | Ignorée | élevé | normale |
| 162 | Drum roll | Roulement de tambour | Ignorée | élevé | normale |
| 163 | Bass drum | Grosse caisse | Ignorée | élevé | normale |
| 164 | Timpani | Timbales d'orchestre | Ignorée | élevé | normale |
| 165 | Tabla | Tabla | Ignorée | élevé | normale |
| 166 | Cymbal | Cymbale | Ignorée | élevé | normale |
| 167 | Hi-hat | Charleston | Ignorée | élevé | normale |
| 168 | Wood block | Wood-block | Ignorée | élevé | normale |
| 169 | Tambourine | Tambourin | Ignorée | élevé | normale |
| 170 | Rattle (instrument) | Hochet (instrument) | Ignorée | élevé | normale |
| 171 | Maraca | Maracas | Ignorée | élevé | normale |
| 172 | Gong | Gong | Ignorée | élevé | normale |
| 173 | Tubular bells | Cloches tubulaires | Ignorée | élevé | normale |
| 174 | Mallet percussion | Percussions à maillets | Ignorée | élevé | normale |
| 175 | Marimba, xylophone | Marimba, xylophone | Ignorée | élevé | normale |
| 176 | Glockenspiel | Glockenspiel | Ignorée | élevé | normale |
| 177 | Vibraphone | Vibraphone | Ignorée | élevé | normale |
| 178 | Steelpan | Steel drum | Ignorée | élevé | normale |
| 179 | Orchestra | Orchestre | Ignorée | élevé | normale |
| 180 | Brass instrument | Cuivres | Ignorée | élevé | normale |
| 181 | French horn | Cor d'harmonie | Ignorée | élevé | normale |
| 182 | Trumpet | Trompette | Ignorée | élevé | normale |
| 183 | Trombone | Trombone | Ignorée | élevé | normale |
| 184 | Bowed string instrument | Instrument à archet | Ignorée | élevé | normale |
| 185 | String section | Section de cordes | Ignorée | élevé | normale |
| 186 | Violin, fiddle | Violon | Ignorée | élevé | normale |
| 187 | Pizzicato | Pizzicato | Ignorée | élevé | normale |
| 188 | Cello | Violoncelle | Ignorée | élevé | normale |
| 189 | Double bass | Contrebasse | Ignorée | élevé | normale |
| 190 | Wind instrument, woodwind instrument | Instrument à vent (bois) | Ignorée | élevé | normale |
| 191 | Flute | Flûte | Ignorée | élevé | normale |
| 192 | Saxophone | Saxophone | Ignorée | élevé | normale |
| 193 | Clarinet | Clarinette | Ignorée | élevé | normale |
| 194 | Harp | Harpe | Ignorée | élevé | normale |
| 195 | Bell | Cloche | Ignorée | moyen | normale |
| 196 | Church bell | Cloche d'église | Ignorée | moyen | normale |
| 197 | Jingle bell | Grelot | Ignorée | moyen | normale |
| 199 | Tuning fork | Diapason | Ignorée | élevé | normale |
| 200 | Chime | Carillon | Ignorée | moyen | normale |
| 201 | Wind chime | Carillon à vent | Ignorée | moyen | normale |
| 202 | Change ringing (campanology) | Sonnerie de cloches en volée | Ignorée | élevé | normale |
| 203 | Harmonica | Harmonica | Ignorée | élevé | normale |
| 204 | Accordion | Accordéon | Ignorée | élevé | normale |
| 205 | Bagpipes | Cornemuse | Ignorée | élevé | normale |
| 206 | Didgeridoo | Didgeridoo | Ignorée | élevé | normale |
| 207 | Shofar | Shofar | Ignorée | élevé | normale |
| 208 | Theremin | Thérémine | Ignorée | élevé | normale |
| 209 | Singing bowl | Bol chantant | Ignorée | élevé | normale |
| 210 | Scratching (performance technique) | Scratch (DJ) | Ignorée | élevé | normale |
| 211 | Pop music | Musique pop | Ignorée | élevé | normale |
| 212 | Hip hop music | Hip-hop | Ignorée | élevé | normale |
| 213 | Beatboxing | Beatbox | Ignorée | élevé | normale |
| 214 | Rock music | Rock | Ignorée | élevé | normale |
| 215 | Heavy metal | Heavy metal | Ignorée | élevé | normale |
| 216 | Punk rock | Punk rock | Ignorée | élevé | normale |
| 217 | Grunge | Grunge | Ignorée | élevé | normale |
| 218 | Progressive rock | Rock progressif | Ignorée | élevé | normale |
| 219 | Rock and roll | Rock and roll | Ignorée | élevé | normale |
| 220 | Psychedelic rock | Rock psychédélique | Ignorée | élevé | normale |
| 221 | Rhythm and blues | Rhythm and blues | Ignorée | élevé | normale |
| 222 | Soul music | Soul | Ignorée | élevé | normale |
| 223 | Reggae | Reggae | Ignorée | élevé | normale |
| 224 | Country | Country | Ignorée | élevé | normale |
| 225 | Swing music | Swing | Ignorée | élevé | normale |
| 226 | Bluegrass | Bluegrass | Ignorée | élevé | normale |
| 227 | Funk | Funk | Ignorée | élevé | normale |
| 228 | Folk music | Musique folk | Ignorée | élevé | normale |
| 229 | Middle Eastern music | Musique du Moyen-Orient | Ignorée | élevé | normale |
| 230 | Jazz | Jazz | Ignorée | élevé | normale |
| 231 | Disco | Disco | Ignorée | élevé | normale |
| 232 | Classical music | Musique classique | Ignorée | élevé | normale |
| 233 | Opera | Opéra | Ignorée | élevé | normale |
| 234 | Electronic music | Musique électronique | Ignorée | élevé | normale |
| 235 | House music | House | Ignorée | élevé | normale |
| 236 | Techno | Techno | Ignorée | élevé | normale |
| 237 | Dubstep | Dubstep | Ignorée | élevé | normale |
| 238 | Drum and bass | Drum and bass | Ignorée | élevé | normale |
| 239 | Electronica | Électronica | Ignorée | élevé | normale |
| 240 | Electronic dance music | Musique de danse électronique | Ignorée | élevé | normale |
| 241 | Ambient music | Musique d'ambiance (ambient) | Ignorée | élevé | normale |
| 242 | Trance music | Trance | Ignorée | élevé | normale |
| 243 | Music of Latin America | Musique d'Amérique latine | Ignorée | élevé | normale |
| 244 | Salsa music | Salsa | Ignorée | élevé | normale |
| 245 | Flamenco | Flamenco | Ignorée | élevé | normale |
| 246 | Blues | Blues | Ignorée | élevé | normale |
| 247 | Music for children | Musique pour enfants | Ignorée | élevé | normale |
| 248 | New-age music | New age | Ignorée | élevé | normale |
| 249 | Vocal music | Musique vocale | Ignorée | élevé | normale |
| 250 | A capella | A cappella | Ignorée | élevé | normale |
| 251 | Music of Africa | Musique d'Afrique | Ignorée | élevé | normale |
| 252 | Afrobeat | Afrobeat | Ignorée | élevé | normale |
| 253 | Christian music | Musique chrétienne | Ignorée | élevé | normale |
| 254 | Gospel music | Gospel | Ignorée | élevé | normale |
| 255 | Music of Asia | Musique d'Asie | Ignorée | élevé | normale |
| 256 | Carnatic music | Musique carnatique | Ignorée | élevé | normale |
| 257 | Music of Bollywood | Musique de Bollywood | Ignorée | élevé | normale |
| 258 | Ska | Ska | Ignorée | élevé | normale |
| 259 | Traditional music | Musique traditionnelle | Ignorée | élevé | normale |
| 260 | Independent music | Musique indépendante | Ignorée | élevé | normale |
| 261 | Song | Chanson | Ignorée | élevé | normale |
| 262 | Background music | Musique de fond | Ignorée | élevé | normale |
| 263 | Theme music | Thème musical | Ignorée | élevé | normale |
| 264 | Jingle (music) | Jingle (musique) | Ignorée | élevé | normale |
| 265 | Soundtrack music | Bande originale | Ignorée | élevé | normale |
| 266 | Lullaby | Berceuse | Ignorée | élevé | normale |
| 267 | Video game music | Musique de jeu vidéo | Ignorée | élevé | normale |
| 268 | Christmas music | Musique de Noël | Ignorée | élevé | normale |
| 269 | Dance music | Musique de danse | Ignorée | élevé | normale |
| 270 | Wedding music | Musique de mariage | Ignorée | élevé | normale |
| 271 | Happy music | Musique joyeuse | Ignorée | élevé | normale |
| 272 | Sad music | Musique triste | Ignorée | élevé | normale |
| 273 | Tender music | Musique douce | Ignorée | élevé | normale |
| 274 | Exciting music | Musique entraînante | Ignorée | élevé | normale |
| 275 | Angry music | Musique agressive | Ignorée | élevé | normale |
| 276 | Scary music | Musique effrayante | Ignorée | élevé | normale |

### Alarmes, sonnettes et signaux (26)

| N° | Classe (modèle) | Français | Intérêt | Faux pos. | Vie privée |
|---|---|---|---|---|---|
| 198 | Bicycle bell | Sonnette de vélo | Ignorée | moyen | normale |
| 302 | Vehicle horn, car horn, honking | Klaxon | Ignorée | élevé | normale |
| 303 | Toot | Coup de klaxon bref | Ignorée | élevé | normale |
| 304 | Car alarm | Alarme de voiture | Optionnelle | moyen | normale |
| 312 | Air horn, truck horn | Avertisseur pneumatique | Ignorée | élevé | normale |
| 317 | Police car (siren) | Voiture de police (sirène) | Optionnelle | élevé | normale |
| 318 | Ambulance (siren) | Ambulance (sirène) | Optionnelle | élevé | normale |
| 319 | Fire engine, fire truck (siren) | Camion de pompiers (sirène) | Optionnelle | élevé | normale |
| 349 | Doorbell | Sonnette de porte | À surveiller | moyen | normale |
| 350 | Ding-dong | Ding-dong | Optionnelle | moyen | normale |
| 382 | Alarm | Alarme | Ignorée | élevé | normale |
| 383 | Telephone | Téléphone | Ignorée | élevé | normale |
| 384 | Telephone bell ringing | Sonnerie de téléphone | Optionnelle | élevé | normale |
| 385 | Ringtone | Sonnerie de mobile | Optionnelle | élevé | normale |
| 386 | Telephone dialing, DTMF | Numérotation (DTMF) | Ignorée | moyen | normale |
| 387 | Dial tone | Tonalité | Ignorée | moyen | normale |
| 388 | Busy signal | Tonalité occupé | Ignorée | moyen | normale |
| 389 | Alarm clock | Réveil | Optionnelle | moyen | normale |
| 390 | Siren | Sirène | Optionnelle | élevé | normale |
| 391 | Civil defense siren | Sirène de défense civile | Ignorée | élevé | normale |
| 392 | Buzzer | Buzzer | Optionnelle | élevé | normale |
| 393 | Smoke detector, smoke alarm | Détecteur de fumée | À surveiller | moyen | normale |
| 394 | Fire alarm | Alarme incendie | À surveiller | moyen | normale |
| 395 | Foghorn | Corne de brume | Ignorée | moyen | normale |
| 396 | Whistle | Sifflet | Optionnelle | moyen | normale |
| 397 | Steam whistle | Sifflet à vapeur | Optionnelle | moyen | normale |

### Vent, orage et feu (7)

| N° | Classe (modèle) | Français | Intérêt | Faux pos. | Vie privée |
|---|---|---|---|---|---|
| 277 | Wind | Vent | Contexte | élevé | normale |
| 278 | Rustling leaves | Feuilles qui bruissent | Ignorée | moyen | normale |
| 279 | Wind noise (microphone) | Bruit de vent (dans le micro) | Contexte | élevé | normale |
| 280 | Thunderstorm | Orage | Optionnelle | moyen | normale |
| 281 | Thunder | Tonnerre | Optionnelle | moyen | normale |
| 292 | Fire | Feu | Optionnelle | élevé | normale |
| 293 | Crackle | Crépitement | Ignorée | élevé | normale |

### Eau et liquides (23)

| N° | Classe (modèle) | Français | Intérêt | Faux pos. | Vie privée |
|---|---|---|---|---|---|
| 282 | Water | Eau | Ignorée | moyen | normale |
| 283 | Rain | Pluie | Contexte | moyen | normale |
| 284 | Raindrop | Goutte de pluie | Contexte | moyen | normale |
| 285 | Rain on surface | Pluie sur une surface | Contexte | moyen | normale |
| 286 | Stream | Ruisseau | Ignorée | moyen | normale |
| 287 | Waterfall | Cascade | Ignorée | moyen | normale |
| 288 | Ocean | Océan | Ignorée | moyen | normale |
| 289 | Waves, surf | Vagues | Ignorée | moyen | normale |
| 290 | Steam | Vapeur | Ignorée | élevé | normale |
| 291 | Gurgling | Gargouillis (eau) | Ignorée | moyen | normale |
| 438 | Liquid | Liquide | Ignorée | moyen | normale |
| 439 | Splash, splatter | Éclaboussure | Ignorée | moyen | normale |
| 440 | Slosh | Clapotis | Ignorée | moyen | normale |
| 441 | Squish | Écrasement mou | Ignorée | moyen | normale |
| 442 | Drip | Goutte à goutte | Optionnelle | moyen | normale |
| 443 | Pour | Verser | Ignorée | moyen | normale |
| 444 | Trickle, dribble | Filet d'eau | Optionnelle | moyen | normale |
| 445 | Gush | Jaillissement | Optionnelle | moyen | normale |
| 446 | Fill (with liquid) | Remplissage (liquide) | Optionnelle | moyen | normale |
| 447 | Spray | Pulvérisation | Ignorée | moyen | normale |
| 448 | Pump (liquid) | Pompe (liquide) | Ignorée | moyen | normale |
| 449 | Stir | Remuer | Ignorée | moyen | normale |
| 450 | Boiling | Ébullition | Optionnelle | moyen | normale |

### Véhicules et moteurs (47)

| N° | Classe (modèle) | Français | Intérêt | Faux pos. | Vie privée |
|---|---|---|---|---|---|
| 294 | Vehicle | Véhicule | Ignorée | moyen | normale |
| 295 | Boat, Water vehicle | Bateau | Ignorée | moyen | normale |
| 296 | Sailboat, sailing ship | Voilier | Ignorée | moyen | normale |
| 297 | Rowboat, canoe, kayak | Barque, canoë, kayak | Ignorée | moyen | normale |
| 298 | Motorboat, speedboat | Bateau à moteur | Ignorée | moyen | normale |
| 299 | Ship | Navire | Ignorée | moyen | normale |
| 300 | Motor vehicle (road) | Véhicule à moteur (route) | Ignorée | moyen | normale |
| 301 | Car | Voiture | Ignorée | moyen | normale |
| 305 | Power windows, electric windows | Lève-vitres électriques | Ignorée | moyen | normale |
| 306 | Skidding | Dérapage | Ignorée | moyen | normale |
| 307 | Tire squeal | Crissement de pneus | Ignorée | moyen | normale |
| 308 | Car passing by | Voiture qui passe | Ignorée | moyen | normale |
| 309 | Race car, auto racing | Voiture de course | Ignorée | moyen | normale |
| 310 | Truck | Camion | Ignorée | moyen | normale |
| 311 | Air brake | Frein pneumatique | Ignorée | moyen | normale |
| 313 | Reversing beeps | Bip de marche arrière | Ignorée | élevé | normale |
| 314 | Ice cream truck, ice cream van | Camion de glaces | Ignorée | moyen | normale |
| 315 | Bus | Bus | Ignorée | moyen | normale |
| 316 | Emergency vehicle | Véhicule d'urgence | Optionnelle | élevé | normale |
| 320 | Motorcycle | Moto | Ignorée | moyen | normale |
| 321 | Traffic noise, roadway noise | Bruit de circulation | Contexte | moyen | normale |
| 322 | Rail transport | Transport ferroviaire | Ignorée | moyen | normale |
| 323 | Train | Train | Ignorée | moyen | normale |
| 324 | Train whistle | Sifflet de train | Ignorée | moyen | normale |
| 325 | Train horn | Klaxon de train | Ignorée | moyen | normale |
| 326 | Railroad car, train wagon | Wagon | Ignorée | moyen | normale |
| 327 | Train wheels squealing | Crissement de roues de train | Ignorée | moyen | normale |
| 328 | Subway, metro, underground | Métro | Ignorée | moyen | normale |
| 329 | Aircraft | Aéronef | Ignorée | moyen | normale |
| 330 | Aircraft engine | Moteur d'avion | Ignorée | moyen | normale |
| 331 | Jet engine | Réacteur | Ignorée | moyen | normale |
| 332 | Propeller, airscrew | Hélice | Ignorée | moyen | normale |
| 333 | Helicopter | Hélicoptère | Ignorée | moyen | normale |
| 334 | Fixed-wing aircraft, airplane | Avion | Ignorée | moyen | normale |
| 335 | Bicycle | Vélo | Ignorée | moyen | normale |
| 336 | Skateboard | Skateboard | Ignorée | moyen | normale |
| 337 | Engine | Moteur | Ignorée | moyen | normale |
| 338 | Light engine (high frequency) | Petit moteur (aigu) | Ignorée | moyen | normale |
| 339 | Dental drill, dentist's drill | Fraise de dentiste | Ignorée | moyen | normale |
| 340 | Lawn mower | Tondeuse | Ignorée | moyen | normale |
| 341 | Chainsaw | Tronçonneuse | Ignorée | moyen | normale |
| 342 | Medium engine (mid frequency) | Moteur moyen (médium) | Ignorée | moyen | normale |
| 343 | Heavy engine (low frequency) | Gros moteur (grave) | Ignorée | moyen | normale |
| 344 | Engine knocking | Cognement moteur | Ignorée | moyen | normale |
| 345 | Engine starting | Démarrage moteur | Optionnelle | moyen | normale |
| 346 | Idling | Moteur au ralenti | Optionnelle | moyen | normale |
| 347 | Accelerating, revving, vroom | Accélération moteur | Ignorée | moyen | normale |

### Sons de la maison (32)

| N° | Classe (modèle) | Français | Intérêt | Faux pos. | Vie privée |
|---|---|---|---|---|---|
| 348 | Door | Porte | Optionnelle | moyen | normale |
| 351 | Sliding door | Porte coulissante | Optionnelle | moyen | normale |
| 352 | Slam | Claquement de porte | Optionnelle | moyen | normale |
| 353 | Knock | Coups à la porte | À surveiller | moyen | normale |
| 354 | Tap | Tapotement | Ignorée | élevé | normale |
| 355 | Squeak | Grincement aigu | Ignorée | moyen | normale |
| 356 | Cupboard open or close | Placard (ouverture, fermeture) | Ignorée | moyen | normale |
| 357 | Drawer open or close | Tiroir (ouverture, fermeture) | Ignorée | moyen | normale |
| 358 | Dishes, pots, and pans | Vaisselle, casseroles | Ignorée | moyen | normale |
| 359 | Cutlery, silverware | Couverts | Ignorée | moyen | normale |
| 360 | Chopping (food) | Hacher (cuisine) | Ignorée | moyen | normale |
| 361 | Frying (food) | Friture | Ignorée | moyen | normale |
| 362 | Microwave oven | Four à micro-ondes | Optionnelle | moyen | normale |
| 363 | Blender | Mixeur | Ignorée | moyen | normale |
| 364 | Water tap, faucet | Robinet | Optionnelle | moyen | normale |
| 365 | Sink (filling or washing) | Évier | Optionnelle | moyen | normale |
| 366 | Bathtub (filling or washing) | Baignoire | Optionnelle | moyen | normale |
| 367 | Hair dryer | Sèche-cheveux | Ignorée | moyen | normale |
| 368 | Toilet flush | Chasse d'eau | Optionnelle | moyen | normale |
| 369 | Toothbrush | Brosse à dents | Ignorée | moyen | normale |
| 370 | Electric toothbrush | Brosse à dents électrique | Ignorée | moyen | normale |
| 371 | Vacuum cleaner | Aspirateur | Contexte | faible | normale |
| 372 | Zipper (clothing) | Fermeture éclair | Ignorée | moyen | normale |
| 373 | Keys jangling | Cliquetis de clés | Optionnelle | moyen | normale |
| 374 | Coin (dropping) | Pièce qui tombe | Ignorée | moyen | normale |
| 375 | Scissors | Ciseaux | Ignorée | moyen | normale |
| 376 | Electric shaver, electric razor | Rasoir électrique | Ignorée | moyen | normale |
| 377 | Shuffling cards | Mélange de cartes | Ignorée | moyen | normale |
| 378 | Typing | Frappe au clavier | Ignorée | moyen | sensible |
| 379 | Typewriter | Machine à écrire | Ignorée | moyen | normale |
| 380 | Computer keyboard | Clavier d'ordinateur | Ignorée | moyen | sensible |
| 381 | Writing | Écriture | Ignorée | moyen | normale |

### Outils et mécanismes (22)

| N° | Classe (modèle) | Français | Intérêt | Faux pos. | Vie privée |
|---|---|---|---|---|---|
| 398 | Mechanisms | Mécanismes | Ignorée | moyen | normale |
| 399 | Ratchet, pawl | Cliquet | Ignorée | moyen | normale |
| 400 | Clock | Horloge | Ignorée | moyen | normale |
| 401 | Tick | Tic | Ignorée | moyen | normale |
| 402 | Tick-tock | Tic-tac | Ignorée | moyen | normale |
| 403 | Gears | Engrenages | Ignorée | moyen | normale |
| 404 | Pulleys | Poulies | Ignorée | moyen | normale |
| 405 | Sewing machine | Machine à coudre | Ignorée | moyen | normale |
| 406 | Mechanical fan | Ventilateur mécanique | Ignorée | moyen | normale |
| 407 | Air conditioning | Climatisation | Ignorée | moyen | normale |
| 408 | Cash register | Caisse enregistreuse | Ignorée | moyen | normale |
| 409 | Printer | Imprimante | Ignorée | moyen | normale |
| 410 | Camera | Appareil photo | Ignorée | moyen | normale |
| 411 | Single-lens reflex camera | Appareil reflex | Ignorée | moyen | normale |
| 412 | Tools | Outils | Ignorée | moyen | normale |
| 413 | Hammer | Marteau | Ignorée | moyen | normale |
| 414 | Jackhammer | Marteau-piqueur | Ignorée | moyen | normale |
| 415 | Sawing | Sciage | Ignorée | moyen | normale |
| 416 | Filing (rasp) | Limage (râpe) | Ignorée | moyen | normale |
| 417 | Sanding | Ponçage | Ignorée | moyen | normale |
| 418 | Power tool | Outil électrique | Ignorée | moyen | normale |
| 419 | Drill | Perceuse | Ignorée | moyen | normale |

### Chocs, casse et détonations (33)

| N° | Classe (modèle) | Français | Intérêt | Faux pos. | Vie privée |
|---|---|---|---|---|---|
| 420 | Explosion | Explosion | Optionnelle | élevé | normale |
| 421 | Gunshot, gunfire | Coup de feu | Optionnelle | élevé | normale |
| 422 | Machine gun | Mitrailleuse | Ignorée | élevé | normale |
| 423 | Fusillade | Fusillade | Ignorée | élevé | normale |
| 424 | Artillery fire | Tir d'artillerie | Ignorée | élevé | normale |
| 425 | Cap gun | Pistolet à amorces | Ignorée | élevé | normale |
| 426 | Fireworks | Feux d'artifice | Contexte | moyen | normale |
| 427 | Firecracker | Pétard | Contexte | moyen | normale |
| 428 | Burst, pop | Éclatement | Ignorée | élevé | normale |
| 429 | Eruption | Éruption | Ignorée | élevé | normale |
| 430 | Boom | Détonation sourde | Ignorée | élevé | normale |
| 431 | Wood | Bois | Ignorée | élevé | normale |
| 432 | Chop | Fendre du bois | Ignorée | élevé | normale |
| 433 | Splinter | Éclat de bois | Ignorée | élevé | normale |
| 434 | Crack | Craquement sec | Ignorée | élevé | normale |
| 435 | Glass | Verre | Ignorée | élevé | normale |
| 436 | Chink, clink | Tintement de verre | Ignorée | élevé | normale |
| 437 | Shatter | Verre brisé | À surveiller | moyen | normale |
| 454 | Thump, thud | Bruit sourd | Optionnelle | élevé | normale |
| 455 | Thunk | Choc sourd | Ignorée | élevé | normale |
| 459 | Basketball bounce | Rebond de ballon de basket | Ignorée | élevé | normale |
| 460 | Bang | Coup sec (bang) | Ignorée | élevé | normale |
| 461 | Slap, smack | Gifle, claque | Ignorée | élevé | normale |
| 462 | Whack, thwack | Frappe sèche | Ignorée | élevé | normale |
| 463 | Smash, crash | Fracas | Optionnelle | élevé | normale |
| 464 | Breaking | Casse | Optionnelle | élevé | normale |
| 465 | Bouncing | Rebond | Ignorée | élevé | normale |
| 466 | Whip | Fouet | Ignorée | élevé | normale |
| 467 | Flap | Battement (claquement) | Ignorée | élevé | normale |
| 468 | Scratch | Grattement | Ignorée | élevé | normale |
| 469 | Scrape | Raclement | Ignorée | élevé | normale |
| 470 | Rub | Frottement | Ignorée | élevé | normale |
| 471 | Roll | Roulement | Ignorée | élevé | normale |

### Sons génériques (onomatopées) (20)

| N° | Classe (modèle) | Français | Intérêt | Faux pos. | Vie privée |
|---|---|---|---|---|---|
| 453 | Whoosh, swoosh, swish | Souffle d'air (whoosh) | Ignorée | élevé | normale |
| 475 | Beep, bleep | Bip | Optionnelle | élevé | normale |
| 476 | Ping | Ping | Ignorée | élevé | normale |
| 477 | Ding | Ding | Optionnelle | élevé | normale |
| 478 | Clang | Choc métallique (clang) | Ignorée | élevé | normale |
| 479 | Squeal | Cri strident (mécanique) | Ignorée | élevé | normale |
| 480 | Creak | Grincement | Ignorée | élevé | normale |
| 481 | Rustle | Bruissement | Ignorée | élevé | normale |
| 482 | Whir | Vrombissement | Ignorée | élevé | normale |
| 483 | Clatter | Fracas (cliquetis) | Optionnelle | élevé | normale |
| 484 | Sizzle | Grésillement | Optionnelle | moyen | normale |
| 485 | Clicking | Cliquetis | Ignorée | élevé | normale |
| 486 | Clickety-clack | Clic-clac | Ignorée | élevé | normale |
| 487 | Rumble | Grondement sourd | Ignorée | élevé | normale |
| 488 | Plop | Plouf | Ignorée | élevé | normale |
| 489 | Jingle, tinkle | Tintement | Ignorée | élevé | normale |
| 490 | Hum | Bourdonnement (hum) | Ignorée | élevé | normale |
| 491 | Zing | Sifflement vif (zing) | Ignorée | élevé | normale |
| 492 | Boing | Boing | Ignorée | élevé | normale |
| 493 | Crunch | Craquement (croquant) | Ignorée | élevé | normale |

### Bruit, acoustique et diagnostic du micro (24)

| N° | Classe (modèle) | Français | Intérêt | Faux pos. | Vie privée |
|---|---|---|---|---|---|
| 494 | Silence | Silence | Contexte | faible | normale |
| 495 | Sine wave | Onde sinusoïdale | Ignorée | élevé | normale |
| 496 | Harmonic | Harmonique | Ignorée | élevé | normale |
| 497 | Chirp tone | Tonalité glissante | Ignorée | élevé | normale |
| 498 | Sound effect | Effet sonore | Ignorée | élevé | normale |
| 499 | Pulse | Impulsion | Ignorée | élevé | normale |
| 500 | Inside, small room | Intérieur, petite pièce | Contexte | moyen | normale |
| 501 | Inside, large room or hall | Intérieur, grande salle | Contexte | moyen | normale |
| 502 | Inside, public space | Intérieur, espace public | Contexte | moyen | normale |
| 503 | Outside, urban or manmade | Extérieur, urbain | Contexte | moyen | normale |
| 504 | Outside, rural or natural | Extérieur, rural ou nature | Contexte | moyen | normale |
| 505 | Reverberation | Réverbération | Ignorée | élevé | normale |
| 506 | Echo | Écho | Ignorée | élevé | normale |
| 507 | Noise | Bruit | Ignorée | élevé | normale |
| 508 | Environmental noise | Bruit ambiant | Ignorée | élevé | normale |
| 509 | Static | Parasites (statique) | Contexte | moyen | normale |
| 510 | Mains hum | Ronflement du secteur (50/60 Hz) | Contexte | faible | normale |
| 511 | Distortion | Distorsion | Contexte | moyen | normale |
| 512 | Sidetone | Effet local (sidetone) | Contexte | moyen | normale |
| 513 | Cacophony | Cacophonie | Ignorée | élevé | normale |
| 514 | White noise | Bruit blanc | Contexte | moyen | normale |
| 515 | Pink noise | Bruit rose | Contexte | moyen | normale |
| 516 | Throbbing | Pulsation | Ignorée | élevé | normale |
| 517 | Vibration | Vibration | Ignorée | élevé | normale |

### Sons reproduits (télévision, radio) (3)

| N° | Classe (modèle) | Français | Intérêt | Faux pos. | Vie privée |
|---|---|---|---|---|---|
| 518 | Television | Télévision | Contexte | moyen | normale |
| 519 | Radio | Radio | Contexte | moyen | normale |
| 520 | Field recording | Enregistrement de terrain | Ignorée | élevé | normale |

### Divers (8)

| N° | Classe (modèle) | Français | Intérêt | Faux pos. | Vie privée |
|---|---|---|---|---|---|
| 451 | Sonar | Sonar | Ignorée | élevé | normale |
| 452 | Arrow | Flèche | Ignorée | élevé | normale |
| 456 | Electronic tuner | Accordeur électronique | Ignorée | élevé | normale |
| 457 | Effects unit | Unité d'effets | Ignorée | élevé | normale |
| 458 | Chorus effect | Effet chorus | Ignorée | élevé | normale |
| 472 | Crushing | Écrasement | Ignorée | élevé | normale |
| 473 | Crumpling, crinkling | Froissement | Ignorée | élevé | normale |
| 474 | Tearing | Déchirement | Ignorée | élevé | normale |

## Sources

- https://github.com/tensorflow/models/tree/master/research/audioset/yamnet (yamnet_class_map.csv)
- https://github.com/audioset/ontology (ontology.json)
