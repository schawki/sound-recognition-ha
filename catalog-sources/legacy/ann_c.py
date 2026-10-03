# -*- coding: utf-8 -*-
"""Groupes de classes proches et règles d'avertissement sur les combinaisons.

Les groupes (parenté acoustique ou risque de confusion) sont un JUGEMENT fondé sur la connaissance
générale ; la hiérarchie parent/enfant, elle, est calculée à partir de l'ontologie AudioSet
(voir build_catalog.py) et n'est pas écrite ici.
"""

TYPE_PARAMS = {
    'impulsif': dict(duree_min_s=1, rearmement_s=15,  tampon_avant_s=5, tampon_apres_s=5),
    'repete':   dict(duree_min_s=2, rearmement_s=30,  tampon_avant_s=5, tampon_apres_s=10),
    'tonal':    dict(duree_min_s=3, rearmement_s=60,  tampon_avant_s=5, tampon_apres_s=10),
    'continu':  dict(duree_min_s=5, rearmement_s=120, tampon_avant_s=5, tampon_apres_s=10),
    'variable': dict(duree_min_s=2, rearmement_s=30,  tampon_avant_s=5, tampon_apres_s=5),
}

CATEGORIES_FR = {
    'voix': "Voix humaine",
    'corps': "Corps et activités",
    'foule': "Foule et groupes",
    'animaux_domestiques': "Animaux domestiques",
    'animaux_ferme': "Animaux de ferme",
    'animaux_sauvages': "Animaux sauvages, oiseaux, insectes",
    'musique': "Musique",
    'alarmes': "Alarmes, sonnettes et signaux",
    'nature': "Vent, orage et feu",
    'eau': "Eau et liquides",
    'vehicules': "Véhicules et moteurs",
    'maison': "Sons de la maison",
    'outils_mecanismes': "Outils et mécanismes",
    'impacts_explosions': "Chocs, casse et détonations",
    'onomatopees': "Sons génériques (onomatopées)",
    'bruit_ambiance': "Bruit, acoustique et diagnostic du micro",
    'reproduction': "Sons reproduits (télévision, radio)",
    'divers': "Divers",
}

# id, nom, membres (noms YAMNet exacts), risque, conseil
GROUPES = [
    ("chiens", "Chiens",
     ["Dog", "Bark", "Yip", "Howl", "Bow-wow", "Growling", "Whimper (dog)", "Canidae, dogs, wolves"],
     "« Chien » contient « Aboiement », « Jappement », « Ouaf », « Grondement », « Hurlement » et « Gémissement de chien » : un aboiement active souvent « Chien » en même temps. « Canidés » (chiens et loups) ne contient que « Grondement » et « Hurlement ».",
     "Surveiller « Aboiement » seul. Ajouter « Hurlement de chien ou de loup » seulement si les hurlements vous intéressent."),

    ("chats", "Chats",
     ["Cat", "Meow", "Purr", "Hiss", "Caterwaul"],
     "« Chat » englobe les autres. Les miaulements stridents ressemblent à des pleurs de bébé.",
     "Choisir « Miaulement » seul ; ne pas combiner avec une alerte « pleurs de bébé » sans règle de confirmation."),

    ("pleurs_cris_aigus", "Pleurs et cris aigus",
     ["Baby cry, infant cry", "Crying, sobbing", "Whimper", "Wail, moan", "Meow", "Caterwaul", "Screaming", "Squeal"],
     "Sons aigus et plaintifs qui se confondent entre eux (bébé, chat, cri humain, grincement).",
     "Si vous surveillez un bébé : « Pleurs de bébé » avec au moins 2 secondes de détection continue ; ignorez les autres."),

    ("cris", "Cris et appels",
     ["Shout", "Yell", "Screaming", "Bellow", "Whoop", "Children shouting", "Children playing", "Cheering", "Crowd"],
     "Les enfants qui jouent, les matchs à la télévision et les films déclenchent souvent ces classes.",
     "Garder « Hurlements stridents » (et éventuellement « Cri ») avec un seuil élevé ; utiliser « Télévision » comme contexte."),

    ("parole", "Parole, voix et contexte vocal",
     ["Speech", "Conversation", "Child speech, kid speaking", "Narration, monologue", "Babbling", "Whispering",
      "Chatter", "Hubbub, speech noise, speech babble", "Speech synthesizer", "Television", "Radio"],
     "Vie privée : ces classes détectent des conversations. Se confondent avec la télévision et la radio.",
     "Ne jamais conserver de clip. Les utiliser comme contexte (« quelqu'un parle ») plutôt que comme alerte."),

    ("voix_chantee", "Voix chantée, psalmodie et prière diffusée",
     ["Singing", "Chant", "Mantra", "Choir", "Vocal music", "Middle Eastern music", "Humming", "Child singing",
      "Synthetic singing", "Speech"],
     "Une voix chantée ou psalmodiée diffusée par haut-parleur (appel à la prière, annonces) active plusieurs de ces classes, ainsi que « Parole ».",
     "Ne pas en faire des alertes. Si ces sons sont fréquents chez vous, relever les seuils des autres classes vocales à ces moments."),

    ("detonations", "Détonations et chocs secs",
     ["Gunshot, gunfire", "Machine gun", "Fusillade", "Artillery fire", "Cap gun", "Fireworks", "Firecracker",
      "Explosion", "Boom", "Bang", "Burst, pop", "Slam", "Thump, thud", "Thunk", "Thunder"],
     "Pétards, feux d'artifice, portes qui claquent et tonnerre sont facilement pris pour un coup de feu.",
     "Ne jamais déclencher d'action lourde sur ces classes seules. Utiliser « Feux d'artifice » et « Pétard » comme contexte inhibiteur."),

    ("casse_verre", "Verre et casse",
     ["Glass", "Shatter", "Chink, clink", "Breaking", "Smash, crash", "Dishes, pots, and pans", "Cutlery, silverware", "Clatter"],
     "La vaisselle qui tombe ou s'entrechoque ressemble à un verre brisé.",
     "Garder « Verre brisé » seul pour la sécurité ; « Casse » et « Fracas » en option. Confirmer avec un capteur d'ouverture ou une caméra."),

    ("bips_incendie", "Alarmes incendie et bips d'appareils",
     ["Smoke detector, smoke alarm", "Fire alarm", "Alarm", "Buzzer", "Beep, bleep", "Microwave oven", "Reversing beeps", "Alarm clock"],
     "Un bip isolé de micro-ondes ou de lave-linge peut ressembler à un détecteur de fumée.",
     "Pour l'alerte incendie : « Détecteur de fumée » et « Alarme incendie » avec au moins 3 secondes de détection soutenue. Ne pas ajouter « Bip » comme alerte."),

    ("sonnettes_cloches", "Sonnettes, sonneries et cloches",
     ["Doorbell", "Ding-dong", "Ding", "Ping", "Bell", "Church bell", "Chime", "Wind chime", "Jingle bell", "Bicycle bell",
      "Telephone bell ringing", "Ringtone", "Telephone", "Jingle, tinkle", "Tuning fork"],
     "Les sonneries de téléphone, de télévision et les cloches sont proches d'une sonnette de porte.",
     "Pour la porte : « Sonnette de porte » seul. Les sonneries de téléphone et les cloches restent hors alerte."),

    ("sirenes", "Sirènes et avertisseurs",
     ["Siren", "Police car (siren)", "Ambulance (siren)", "Fire engine, fire truck (siren)", "Emergency vehicle",
      "Civil defense siren", "Car alarm", "Vehicle horn, car horn, honking", "Toot", "Air horn, truck horn", "Foghorn"],
     "Sons de rue très fréquents, qui se confondent entre eux et avec la télévision.",
     "Utile seulement comme indicateur extérieur ; ne pas déclencher d'alerte maison."),

    ("sifflets", "Sifflets",
     ["Whistle", "Steam whistle", "Whistling", "Train whistle", "Hiss", "Steam"],
     "Une bouilloire à sifflet, un sifflement de bouche ou une fuite de vapeur sont proches.",
     "À tester avec votre cuisine avant d'en faire une automatisation."),

    ("portes_coups", "Portes, coups et frappes",
     ["Knock", "Door", "Slam", "Tap", "Sliding door", "Thump, thud", "Thunk", "Bang", "Cupboard open or close", "Drawer open or close", "Squeak"],
     "Coups à la porte, tiroirs et meubles se confondent. « Porte » englobe plusieurs sons.",
     "Choisir « Coups à la porte » pour une visite, « Claquement de porte » pour les claquements ; éviter « Porte » et « Tapotement »."),

    ("eau_coule", "Eau qui coule, fuites",
     ["Water tap, faucet", "Sink (filling or washing)", "Bathtub (filling or washing)", "Pour", "Trickle, dribble", "Gush",
      "Fill (with liquid)", "Drip", "Splash, splatter", "Stream", "Toilet flush", "Rain", "Rain on surface", "Raindrop", "Boiling", "White noise"],
     "Un robinet, la douche, la pluie et le bruit blanc se ressemblent. Aucune de ces classes ne détecte l'eau : seulement son bruit.",
     "Toujours accompagner d'une durée et d'un vrai capteur d'eau pour les fuites."),

    ("moteurs_continus", "Moteurs et appareils continus",
     ["Vacuum cleaner", "Hair dryer", "Blender", "Mechanical fan", "Air conditioning", "Engine", "Light engine (high frequency)",
      "Medium engine (mid frequency)", "Heavy engine (low frequency)", "Idling", "Lawn mower", "Power tool", "Drill",
      "White noise", "Pink noise", "Noise", "Environmental noise", "Whir", "Hum"],
     "Bruits continus qui se confondent entre eux et masquent les autres sons.",
     "Les traiter comme contexte : ils indiquent surtout pourquoi les autres classes sont moins sensibles."),

    ("pas_presence", "Pas et présence",
     ["Walk, footsteps", "Run", "Shuffle", "Patter", "Typing", "Computer keyboard", "Keys jangling", "Finger snapping", "Clapping"],
     "Un capteur de présence fait mieux. Les pas dépendent du revêtement de sol, du micro et des voisins.",
     "À utiliser en complément d'un capteur de présence, pas à sa place."),

    ("toux_souffle", "Toux, éternuements et respiration",
     ["Cough", "Throat clearing", "Sneeze", "Sniff", "Snort", "Wheeze", "Breathing", "Snoring", "Gasp", "Pant", "Sigh"],
     "Sons proches entre eux ; ils relèvent de la santé donc sensibles.",
     "Ne pas conserver de clip. À réserver à des usages de présence discrète."),

    ("insectes_rongeurs", "Insectes et rongeurs",
     ["Insect", "Mosquito", "Fly, housefly", "Buzz", "Bee, wasp, etc.", "Cricket", "Mouse", "Rodents, rats, mice", "Patter", "Scratch"],
     "Très faibles et très proches de bruits d'appareils ou de tuyauterie.",
     "Peu fiables ; à n'essayer qu'avec un micro proche (grenier, cave)."),

    ("oiseaux", "Oiseaux",
     ["Bird", "Bird vocalization, bird call, bird song", "Chirp, tweet", "Squawk", "Pigeon, dove", "Coo", "Crow", "Caw",
      "Owl", "Hoot", "Chicken, rooster", "Crowing, cock-a-doodle-doo", "Bird flight, flapping wings"],
     "« Oiseau » englobe presque toutes les autres classes de ce groupe.",
     "Utile seulement comme indicateur d'ambiance extérieure."),

    ("vehicules_rue", "Véhicules dans la rue",
     ["Vehicle", "Motor vehicle (road)", "Car", "Car passing by", "Truck", "Bus", "Motorcycle", "Traffic noise, roadway noise",
      "Engine", "Engine starting", "Idling", "Accelerating, revving, vroom", "Skidding", "Tire squeal"],
     "Sons de rue omniprésents ; le micro près d'une fenêtre les capte en continu.",
     "Les utiliser comme contexte extérieur ; ignorer leurs événements."),

    ("feu_crepitement", "Feu, crépitement et cuisson",
     ["Fire", "Crackle", "Frying (food)", "Sizzle", "Rustling leaves", "Rain on surface", "Static"],
     "Le feu, la friture, la pluie et les parasites se ressemblent beaucoup.",
     "Ne pas utiliser « Feu » comme alerte incendie. Se fier à un vrai détecteur de fumée."),

    ("diagnostic_micro", "Diagnostic de la qualité du micro",
     ["Mains hum", "Static", "White noise", "Pink noise", "Distortion", "Silence", "Wind noise (microphone)", "Sidetone", "Reverberation"],
     "Ces classes ne décrivent pas un événement de la maison, mais l'état du micro et de son câblage.",
     "À surveiller pendant la mise en place : un « ronflement du secteur » constant, du vent ou de la distorsion indiquent un problème matériel."),

    ("musique_generale", "Musique",
     ["Music", "Song", "Background music", "Theme music", "Soundtrack music", "Pop music", "Singing", "Television", "Radio"],
     "Une musique de fond active de nombreuses classes (voix, instruments, cloches).",
     "Garder « Musique » comme contexte ; ignorer instruments et genres."),
]

# type : 'tous' = la règle s'applique si TOUTES les classes sont sélectionnées,
#        'un_parmi' = si au moins DEUX des classes listées sont sélectionnées
REGLES = [
    dict(id="incendie_double", type='tous', classes=["Smoke detector, smoke alarm", "Fire alarm"], niveau='info',
         message="« Détecteur de fumée » et « Alarme incendie » sont très proches : un même événement peut déclencher les deux. "
                 "Utilisez la même action pour les deux et ne comptez qu'une alerte (délai de ré-armement)."),
    dict(id="incendie_bips", type='tous', classes=["Smoke detector, smoke alarm", "Beep, bleep"], niveau='attention',
         message="« Bip » se déclenche aussi sur micro-ondes et lave-linge : ne l'utilisez pas comme alerte incendie, et exigez une détection soutenue d'au moins 3 secondes pour « Détecteur de fumée »."),
    dict(id="feu_seul", type='un_parmi', classes=["Fire", "Crackle"], niveau='attention',
         message="« Feu » et « Crépitement » se confondent avec la friture et la pluie : ne les utilisez pas comme alerte incendie."),
    dict(id="detonations_feux", type='un_parmi', classes=["Gunshot, gunfire", "Explosion", "Fireworks", "Firecracker"], niveau='attention',
         message="Feux d'artifice et pétards se confondent avec des coups de feu. Utilisez « Feux d'artifice » et « Pétard » en contexte inhibiteur, pas comme événements, et ne déclenchez pas d'action lourde sur « Coup de feu » seul."),
    dict(id="sonnette_doublons", type='un_parmi', classes=["Doorbell", "Ding-dong", "Ding", "Bell", "Chime"], niveau='attention',
         message="Plusieurs classes de sonnette/cloche se déclenchent en même temps. Gardez « Sonnette de porte » comme alerte principale."),
    dict(id="sonnette_telephone", type='un_parmi', classes=["Doorbell", "Telephone bell ringing", "Ringtone"], niveau='attention',
         message="Les sonneries de téléphone peuvent déclencher « Sonnette de porte ». Mesurez les confusions chez vous avant d'automatiser."),
    dict(id="bebe_chat", type='un_parmi', classes=["Baby cry, infant cry", "Meow", "Caterwaul"], niveau='attention',
         message="Les miaulements (surtout les cris de chats) sont parfois classés comme pleurs de bébé : exigez une détection soutenue d'au moins 2 secondes et un seuil adapté."),
    dict(id="cris_multiples", type='un_parmi', classes=["Shout", "Yell", "Screaming", "Children shouting"], niveau='info',
         message="Ces classes sont voisines : choisissez-en une comme alerte principale (par exemple « Hurlements stridents »). Les autres produiront des alertes en double."),
    dict(id="verre_doublons", type='un_parmi', classes=["Glass", "Shatter", "Breaking", "Smash, crash"], niveau='info',
         message="« Verre » est le parent de « Verre brisé » : choisissez « Verre brisé » seul, et « Casse » ou « Fracas » en option avec un seuil plus élevé."),
    dict(id="chiens_doublons", type='un_parmi', classes=["Dog", "Bark", "Canidae, dogs, wolves"], niveau='info',
         message="« Chien » contient « Aboiement » (et « Jappement », « Ouaf », « Grondement », « Hurlement ») : un aboiement déclenche les deux. Gardez « Aboiement ». « Canidés » est redondant et plus bruyant."),
    dict(id="parole_cible", type='un_parmi', classes=["Speech", "Conversation", "Whispering", "Child speech, kid speaking"], niveau='attention',
         message="Classes de parole : elles détectent des conversations. Aucun clip ne doit être conservé ; utilisez-les seulement comme contexte."),
    dict(id="eau_fuite", type='un_parmi', classes=["Water tap, faucet", "Gush", "Drip", "Fill (with liquid)"], niveau='attention',
         message="Ces classes détectent le bruit de l'eau, pas l'eau. Pour une fuite, ajoutez un vrai capteur d'eau et une durée minimale (par exemple 5 à 10 minutes)."),
    dict(id="musique_classes", type='un_parmi', classes=["Music", "Song", "Singing", "Vocal music", "Pop music", "Background music"], niveau='info',
         message="Quand la musique joue, de nombreuses classes (voix, instruments, cloches) s'activent. Surveillez « Musique » comme contexte plutôt que ses sous-classes."),
    dict(id="contexte_recommande", type='un_parmi', classes=["Screaming", "Gunshot, gunfire", "Bark", "Doorbell", "Shatter"], niveau='info',
         message="Ces classes sont sensibles à la télévision et à la radio. Ajoutez « Télévision » et « Radio » comme contexte pour relever automatiquement les seuils."),
]

# Règles appliquées automatiquement par l'intégration, à partir des champs de chaque classe
REGLES_AUTOMATIQUES = [
    dict(id="parent_enfant", niveau='info',
         condition="une classe sélectionnée est un ancêtre (ancetres_yamnet / descendants_yamnet) d'une autre classe sélectionnée",
         message="« {parent} » contient « {enfant} » : un même son déclenchera les deux. Gardez la plus précise, ou la plus large, mais pas les deux avec des règles différentes (rétention, seuil, action)."),
    dict(id="clip_interdit", niveau='danger',
         condition="conservation_clip_jours > 0 sur une classe dont clip_interdit vaut vrai",
         message="« {classe} » détecte des conversations : aucun clip ne doit être conservé. La rétention est forcée à 0."),
    dict(id="seuil_bas_fp_eleve", niveau='attention',
         condition="seuil inférieur au seuil suggéré sur une classe dont faux_positifs.niveau vaut « eleve »",
         message="« {classe} » est souvent déclenchée à tort ; un seuil aussi bas multipliera les fausses alertes. Ajoutez un contexte inhibiteur (télévision, radio, musique)."),
    dict(id="classe_generique", niveau='info',
         condition="role vaut « generique »",
         message="« {classe} » est une classe parente large : préférez ses sous-classes ({exemples})."),
    dict(id="sans_contexte", niveau='info',
         condition="classe avec contextes_inhibiteurs non vide, sans aucune classe de contexte sélectionnée",
         message="« {classe} » est sensible à la télévision, à la radio ou à la musique : sélectionnez-les comme classes de contexte pour relever automatiquement les seuils."),
]
