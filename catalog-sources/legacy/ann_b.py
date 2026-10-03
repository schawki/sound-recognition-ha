# -*- coding: utf-8 -*-
"""Annotations de jugement, partie B : alarmes, nature, eau, véhicules, maison, outils,
chocs et détonations, onomatopées, bruit et acoustique, sons reproduits, divers.

Mêmes réserves que la partie A : suggestions de départ, non mesurées.
"""
from ann_a import o, TV, CTX_TV

CAT_DEF_B = {
    'alarmes':            dict(interet='optionnel', role='evenement', type_son='tonal',    fp_niveau='moyen', vie_privee='normale', seuil=0.5, jours=7),
    'nature':             dict(interet='ignorer',   role='evenement', type_son='continu',  fp_niveau='moyen', vie_privee='normale', seuil=0.5, jours=0),
    'eau':                dict(interet='ignorer',   role='evenement', type_son='continu',  fp_niveau='moyen', vie_privee='normale', seuil=0.5, jours=0),
    'vehicules':          dict(interet='ignorer',   role='evenement', type_son='continu',  fp_niveau='moyen', vie_privee='normale', seuil=0.5, jours=0),
    'maison':             dict(interet='ignorer',   role='evenement', type_son='impulsif', fp_niveau='moyen', vie_privee='normale', seuil=0.5, jours=0),
    'outils_mecanismes':  dict(interet='ignorer',   role='evenement', type_son='continu',  fp_niveau='moyen', vie_privee='normale', seuil=0.5, jours=0),
    'impacts_explosions': dict(interet='ignorer',   role='evenement', type_son='impulsif', fp_niveau='eleve', vie_privee='normale', seuil=0.5, jours=0),
    'onomatopees':        dict(interet='ignorer',   role='evenement', type_son='variable', fp_niveau='eleve', vie_privee='normale', seuil=0.5, jours=0),
    'bruit_ambiance':     dict(interet='ignorer',   role='contexte',  type_son='continu',  fp_niveau='eleve', vie_privee='normale', seuil=0.5, jours=0),
    'reproduction':       dict(interet='contexte',  role='contexte',  type_son='continu',  fp_niveau='eleve', vie_privee='normale', seuil=0.5, jours=0),
    'divers':             dict(interet='ignorer',   role='evenement', type_son='variable', fp_niveau='eleve', vie_privee='normale', seuil=0.5, jours=0),
}

OV = {}

# ================================================================ ALARMES, SONNERIES, SIGNAUX
OV['Smoke detector, smoke alarm'] = o(
    interet='surveiller', type='tonal', fp='moyen', seuil=0.4, jours=90, usages=['incendie', 'securite'],
    causes=["bips d'appareils (micro-ondes, four, lave-linge)", "alarmes d'autres appareils", "télévision"],
    note="Le cas d'usage le plus utile. Exiger une détection soutenue d'au moins 3 secondes : un bip isolé ne doit pas déclencher. "
         "Ce n'est PAS un remplacement d'un vrai détecteur de fumée : c'est une redondance qui entend un détecteur existant.")
OV['Fire alarm'] = o(
    interet='surveiller', type='tonal', fp='moyen', seuil=0.4, jours=90, usages=['incendie', 'securite'],
    causes=["bips d'appareils", "télévision", "alarme d'immeuble voisin ou exercice"],
    note="Alarme incendie (sirène d'immeuble par exemple). Proche de « Détecteur de fumée » : en choisir un seul comme alerte principale, l'autre en confirmation.")
OV['Alarm'] = o(
    interet='ignorer', role='generique', type='tonal', fp='eleve', jours=0,
    note="Classe parente de presque tous les signaux d'alarme : très large, donc très bruyante. Préférer les classes précises.")
OV['Siren'] = o(
    interet='optionnel', role='generique', type='tonal', fp='eleve', seuil=0.6, jours=3, usages=['exterieur'],
    causes=["ambulances et police dans la rue", "télévision", "musique"],
    note="Sirène en général : classe parente des sirènes de véhicules. Surtout un indicateur de ce qui se passe dans la rue.")
for n in ['Police car (siren)', 'Ambulance (siren)', 'Fire engine, fire truck (siren)', 'Emergency vehicle']:
    OV[n] = o(interet='optionnel', type='tonal', fp='eleve', seuil=0.6, jours=0, usages=['exterieur'], causes=TV + ["rue"], ctx=CTX_TV)
OV['Civil defense siren'] = o(interet='ignorer', type='tonal', fp='eleve', jours=0)
OV['Car alarm'] = o(
    interet='optionnel', type='tonal', fp='moyen', seuil=0.5, jours=3, usages=['exterieur', 'securite'],
    causes=["alarmes de voisinage", "télévision"],
    note="Alarme de voiture : utile seulement si le véhicule est à portée d'écoute. Se répète dans la rue, donc beaucoup d'alertes sans importance.")
for n in ['Vehicle horn, car horn, honking', 'Toot', 'Air horn, truck horn']:
    OV[n] = o(interet='ignorer', type='impulsif', fp='eleve', jours=0, note="Klaxons : sons de rue, sans intérêt pour la maison.")

OV['Doorbell'] = o(
    interet='surveiller', type='repete', fp='moyen', seuil=0.5, jours=7, usages=['porte'],
    causes=["sonnettes de télévision", "téléphones", "sonnettes de voisins", "carillons"],
    ctx=CTX_TV,
    note="Sonnette de porte : utile pour notifier et pour déclencher une caméra. Les sonnettes électroniques à mélodie sont mieux détectées que les simples bips.")
OV['Ding-dong'] = o(
    interet='optionnel', type='tonal', fp='moyen', seuil=0.5, jours=7, usages=['porte'],
    note="Sous-classe de « Sonnette de porte » : doublon si celle-ci est déjà surveillée. Utile en complément pour les sonnettes à deux tons.")
OV['Telephone'] = o(interet='ignorer', role='generique', type='tonal', fp='eleve', jours=0,
                    note="Classe parente de toutes les sonneries de téléphone.")
OV['Telephone bell ringing'] = o(interet='optionnel', type='repete', fp='eleve', seuil=0.6, jours=0, usages=['presence'],
                                 causes=["télévision", "sonnette"],
                                 note="Sonnerie de téléphone fixe. Confusion avec la sonnette de porte.")
OV['Ringtone'] = o(interet='optionnel', type='repete', fp='eleve', seuil=0.6, jours=0, usages=['presence'], causes=TV,
                   note="Sonnerie de mobile : intéressant pour retrouver un téléphone ou savoir qu'il sonne seul, mais très variable (mélodies).")
OV['Telephone dialing, DTMF'] = o(interet='ignorer', fp='moyen', jours=0)
OV['Dial tone'] = o(interet='ignorer', jours=0)
OV['Busy signal'] = o(interet='ignorer', jours=0)
OV['Alarm clock'] = o(interet='optionnel', type='repete', fp='moyen', seuil=0.5, jours=0, usages=['confort'],
                      note="Réveil qui sonne : peut servir à vérifier qu'un réveil a bien sonné ; se confond avec d'autres bips.")
OV['Buzzer'] = o(interet='optionnel', type='tonal', fp='eleve', seuil=0.55, jours=0, usages=['porte'],
                 note="Buzzer : interphone, ouverture de porte d'immeuble, minuteries. Très proche des bips d'appareils.")
OV['Foghorn'] = o(interet='ignorer', type='tonal', jours=0)
OV['Whistle'] = o(interet='optionnel', type='tonal', fp='moyen', seuil=0.5, jours=0, usages=['cuisine'],
                  note="Sifflet : peut détecter une bouilloire à sifflet, mais se confond avec un sifflement de bouche.")
OV['Steam whistle'] = o(interet='optionnel', type='tonal', fp='moyen', seuil=0.5, jours=0, usages=['cuisine'],
                        note="Sifflet à vapeur : bouilloire ou cocotte-minute. À tester.")

# ================================================================ NATURE
OV['Wind'] = o(interet='contexte', role='contexte', type='continu', fp='eleve', jours=0, usages=['contexte'],
               note="Vent : sert à relativiser les autres détections extérieures.")
OV['Wind noise (microphone)'] = o(interet='contexte', role='diagnostic', type='continu', fp='eleve', jours=0, usages=['diagnostic'],
                                  note="Vent dans le micro : indique que le micro est exposé à un courant d'air (fenêtre ouverte, ventilation). À utiliser pour déplacer le micro.")
OV['Rustling leaves'] = o(interet='ignorer', jours=0)
OV['Thunderstorm'] = o(interet='optionnel', role='generique', type='variable', fp='moyen', seuil=0.5, jours=0, usages=['meteo'],
                       note="Orage : peut servir à des automatisations (fermer les stores, protéger du matériel). Se confond avec de lourds travaux.")
OV['Thunder'] = o(interet='optionnel', type='impulsif', fp='moyen', seuil=0.5, jours=0, usages=['meteo'],
                  note="Tonnerre : se confond avec des détonations sourdes.")
OV['Fire'] = o(interet='optionnel', role='generique', type='continu', fp='eleve', seuil=0.6, jours=0, usages=['incendie'],
               causes=["cuisson (friture)", "cheminée", "télévision"],
               note="Feu : à ne PAS utiliser comme alerte incendie fiable (crépitement très proche d'une friture ou d'une pluie). Réserver au contexte.")
OV['Crackle'] = o(interet='ignorer', type='continu', fp='eleve', jours=0,
                  note="Crépitement : se confond avec la pluie, la friture et les parasites.")

# ================================================================ EAU ET LIQUIDES
# Détecte le BRUIT d'une fuite ou d'un robinet, jamais l'eau elle-même.
for n in ['Rain', 'Rain on surface', 'Raindrop']:
    OV[n] = o(interet='contexte', role='contexte', type='continu', fp='moyen', jours=0, usages=['meteo', 'contexte'],
              note="Pluie : utile comme contexte (fenêtre restée ouverte, linge dehors) et pour relever les seuils des autres classes. Confusion avec bruit blanc et friture.")
OV['Water'] = o(interet='ignorer', role='generique', jours=0, note="Classe parente de l'eau : ne pas choisir directement.")
OV['Liquid'] = o(interet='ignorer', role='generique', jours=0, note="Classe parente large : ne pas choisir directement.")
OV['Drip'] = o(interet='optionnel', type='repete', fp='moyen', seuil=0.5, jours=0, usages=['fuite'],
               note="Goutte à goutte : peut signaler un robinet ou une fuite, à condition d'avoir un micro proche et un environnement calme.")
OV['Gush'] = o(interet='optionnel', type='continu', fp='moyen', seuil=0.5, jours=0, usages=['fuite'],
               note="Jaillissement : possible indice d'une fuite importante. Détecte le bruit, pas la fuite : à doubler d'un capteur d'eau.")
OV['Trickle, dribble'] = o(interet='optionnel', type='continu', fp='moyen', jours=0, usages=['fuite'])
OV['Pour'] = o(interet='ignorer', type='impulsif', fp='moyen', jours=0)
OV['Fill (with liquid)'] = o(interet='optionnel', type='continu', fp='moyen', jours=0, usages=['fuite', 'confort'],
                             note="Remplissage : utile pour une baignoire ou un seau qui se remplit. Combiner avec une durée (par exemple plus de 10 minutes).")
OV['Boiling'] = o(interet='optionnel', type='continu', fp='moyen', jours=0, usages=['cuisine'],
                  note="Ébullition : peut signaler une casserole ou une bouilloire qui bout. Ne remplace pas une sécurité cuisinière.")
OV['Splash, splatter'] = o(interet='ignorer', type='impulsif', jours=0)
OV['Steam'] = o(interet='ignorer', type='continu', fp='eleve', jours=0, note="Vapeur : se confond avec les jets d'air et le bruit blanc.")
for n in ['Stream', 'Waterfall', 'Ocean', 'Waves, surf', 'Gurgling', 'Slosh', 'Squish', 'Spray', 'Pump (liquid)', 'Stir']:
    OV[n] = o(interet='ignorer', jours=0)

# ================================================================ VÉHICULES
OV['Traffic noise, roadway noise'] = o(interet='contexte', role='contexte', type='continu', fp='moyen', jours=0, usages=['contexte'],
                                       note="Circulation : indique l'ambiance extérieure ; utile pour relever les seuils près d'une fenêtre.")
OV['Engine starting'] = o(interet='optionnel', type='impulsif', fp='moyen', jours=0, usages=['garage'],
                          note="Démarrage moteur : possible pour un garage ou une voiture proche (arrivée, départ).")
OV['Idling'] = o(interet='optionnel', type='continu', fp='moyen', jours=0, usages=['garage'],
                 note="Moteur au ralenti : par exemple une voiture qui tourne dans un garage fermé. Détecte le bruit, pas le monoxyde.")
OV['Reversing beeps'] = o(interet='ignorer', type='repete', fp='eleve', jours=0, note="Bip de recul : se confond avec d'autres bips.")
OV['Car'] = o(interet='ignorer', role='generique', jours=0)
OV['Motor vehicle (road)'] = o(interet='ignorer', role='generique', jours=0)
OV['Vehicle'] = o(interet='ignorer', role='generique', jours=0, note="Classe racine des véhicules : à ne pas choisir.")
OV['Engine'] = o(interet='ignorer', role='generique', jours=0, note="Classe parente des moteurs : très large.")

# ================================================================ MAISON
OV['Knock'] = o(interet='surveiller', type='impulsif', fp='moyen', seuil=0.5, jours=7, usages=['porte', 'securite'],
                causes=["télévision", "travaux chez les voisins", "meubles"], ctx=CTX_TV,
                note="Coups à la porte : utile pour notifier une visite quand la sonnette est absente ou en panne.")
OV['Door'] = o(interet='optionnel', role='generique', type='impulsif', fp='moyen', seuil=0.5, jours=0, usages=['porte'],
               note="Classe parente de « Sonnette de porte », « Coups à la porte », « Claquement de porte » : à ne pas choisir en même temps que ses enfants.")
OV['Slam'] = o(interet='optionnel', type='impulsif', fp='moyen', seuil=0.55, jours=0, usages=['porte', 'securite'],
               note="Claquement de porte : confusion avec détonations (pétards) et chutes d'objets.")
OV['Sliding door'] = o(interet='optionnel', type='impulsif', fp='moyen', jours=0, usages=['porte'])
OV['Tap'] = o(interet='ignorer', type='impulsif', fp='eleve', jours=0, note="Tapotement : trop général (clavier, doigts, table).")
OV['Microwave oven'] = o(interet='optionnel', type='repete', fp='moyen', seuil=0.5, jours=0, usages=['cuisine'],
                         note="Micro-ondes (surtout ses bips de fin). Source de FAUSSES alertes sur « Détecteur de fumée » : voir les règles de combinaison.")
for n in ['Water tap, faucet', 'Sink (filling or washing)', 'Bathtub (filling or washing)']:
    OV[n] = o(interet='optionnel', type='continu', fp='moyen', jours=0, usages=['fuite', 'confort'],
              note="Eau qui coule : à relier à une durée (robinet resté ouvert). Se confond avec la douche et le bruit blanc.")
OV['Toilet flush'] = o(interet='optionnel', type='continu', fp='moyen', jours=0, usages=['fuite'],
                       note="Chasse d'eau : une chasse qui coule en continu est détectable avec une durée.")
OV['Vacuum cleaner'] = o(interet='contexte', role='contexte', type='continu', fp='faible', jours=0, usages=['contexte'],
                         note="Aspirateur : très reconnaissable. Utile pour ignorer les autres détections pendant le ménage.")
OV['Keys jangling'] = o(interet='optionnel', type='impulsif', fp='moyen', seuil=0.5, jours=0, usages=['porte', 'presence'],
                        note="Cliquetis de clés : indice d'arrivée à la porte, mais peu fiable seul.")
OV['Typing'] = o(interet='ignorer', type='repete', vp='sensible', jours=0, note="Frappe au clavier : indique une présence ; sensible.")
OV['Computer keyboard'] = o(interet='ignorer', type='repete', vp='sensible', jours=0)
OV['Typewriter'] = o(interet='ignorer', jours=0)
OV['Writing'] = o(interet='ignorer', jours=0)

# ================================================================ OUTILS ET MÉCANISMES
OV['Mechanisms'] = o(interet='ignorer', role='generique', jours=0)
OV['Tools'] = o(interet='ignorer', role='generique', jours=0)
OV['Air conditioning'] = o(interet='ignorer', type='continu', fp='moyen', jours=0, usages=['diagnostic'],
                           note="Climatisation : bruit continu. Sert surtout à comprendre pourquoi un micro capte du bruit de fond constant.")
OV['Mechanical fan'] = o(interet='ignorer', type='continu', jours=0)
for n in ['Clock', 'Tick', 'Tick-tock']:
    OV[n] = o(interet='ignorer', type='repete', fp='moyen', jours=0)
for n in ['Drill', 'Jackhammer', 'Power tool', 'Sawing', 'Hammer', 'Sanding', 'Filing (rasp)']:
    OV[n] = o(interet='ignorer', type='continu', fp='moyen', jours=0,
              note="Outils et travaux : plutôt des bruits de voisinage que des événements utiles.")

# ================================================================ CHOCS, CASSE, DÉTONATIONS
OV['Shatter'] = o(interet='surveiller', type='impulsif', fp='moyen', seuil=0.5, jours=30, usages=['securite'],
                  causes=["vaisselle ou bouteille qui tombe", "télévision", "travaux"], ctx=CTX_TV,
                  note="Verre brisé : utile pour la sécurité (vitre cassée). À confirmer avec un capteur de fenêtre ou une caméra : les chutes de vaisselle sont fréquentes.")
OV['Glass'] = o(interet='ignorer', role='generique', type='impulsif', fp='eleve', jours=0,
                note="Classe parente de « Verre brisé » et « Tintement de verre » : choisir plutôt « Verre brisé ».")
OV['Chink, clink'] = o(interet='ignorer', type='repete', fp='eleve', jours=0, note="Tintement de verre : repas, verres qui s'entrechoquent. Très fréquent, peu utile.")
OV['Breaking'] = o(interet='optionnel', type='impulsif', fp='eleve', seuil=0.55, jours=0, usages=['securite'],
                   note="Casse en général (pas seulement du verre) : plus large, donc plus de fausses alertes.")
OV['Smash, crash'] = o(interet='optionnel', type='impulsif', fp='eleve', seuil=0.55, jours=0, usages=['securite'])
OV['Gunshot, gunfire'] = o(interet='optionnel', type='impulsif', fp='eleve', seuil=0.6, jours=7, usages=['securite'],
                           causes=["feux d'artifice et pétards", "claquement de porte", "télévision et jeux vidéo", "travaux"],
                           ctx=CTX_TV + ["Fireworks", "Firecracker"],
                           note="Coup de feu : ne jamais déclencher d'action automatique lourde sur cette seule classe. Dans les régions où les pétards ou les feux d'artifice sont courants, attendre beaucoup de fausses alertes.")
for n in ['Machine gun', 'Fusillade', 'Artillery fire', 'Cap gun']:
    OV[n] = o(interet='ignorer', type='impulsif', fp='eleve', jours=0, causes=TV + ["feux d'artifice"])
OV['Explosion'] = o(interet='optionnel', role='generique', type='impulsif', fp='eleve', seuil=0.6, jours=0,
                    causes=["feux d'artifice", "tonnerre", "travaux", "télévision"],
                    note="Explosion : classe parente large de détonations. Bruyante et peu spécifique.")
OV['Fireworks'] = o(interet='contexte', role='contexte', type='repete', fp='moyen', jours=0, usages=['contexte'],
                    note="Feux d'artifice : à utiliser comme contexte pour relever les seuils de « Coup de feu », « Explosion » et « Éclatement » pendant les fêtes.")
OV['Firecracker'] = o(interet='contexte', role='contexte', type='impulsif', fp='moyen', jours=0, usages=['contexte'],
                      note="Pétard : idem « Feux d'artifice » ; confusion fréquente avec un coup de feu.")
for n in ['Burst, pop', 'Boom', 'Bang']:
    OV[n] = o(interet='ignorer', type='impulsif', fp='eleve', jours=0, causes=["porte qui claque", "chocs", "télévision"])
OV['Eruption'] = o(interet='ignorer', jours=0)
OV['Thump, thud'] = o(interet='optionnel', type='impulsif', fp='eleve', seuil=0.6, jours=0, usages=['securite', 'presence'],
                      note="Bruit sourd : chute d'un objet ou d'une personne, meubles, voisins. Ne pas utiliser seul pour une détection de chute.")
OV['Thunk'] = o(interet='ignorer', type='impulsif', fp='eleve', jours=0)
for n in ['Wood', 'Chop', 'Splinter', 'Crack']:
    OV[n] = o(interet='ignorer', fp='eleve', jours=0)
for n in ['Basketball bounce', 'Bouncing', 'Slap, smack', 'Whack, thwack', 'Whip', 'Flap', 'Scratch', 'Scrape', 'Rub', 'Roll']:
    OV[n] = o(interet='ignorer', fp='eleve', jours=0)

# ================================================================ ONOMATOPÉES
OV['Beep, bleep'] = o(interet='optionnel', type='repete', fp='eleve', seuil=0.6, jours=0, usages=['cuisine', 'confort'],
                      causes=["micro-ondes", "lave-linge et lave-vaisselle", "détecteurs", "télévision"],
                      note="Bips d'appareils (fin de cycle). Très répandus, donc à regrouper avec « Micro-ondes » ; ne pas en faire une alerte incendie.")
OV['Ding'] = o(interet='optionnel', type='tonal', fp='eleve', seuil=0.6, jours=0, note="Ding : se confond avec la sonnette de porte et les minuteurs.")
OV['Ping'] = o(interet='ignorer', type='tonal', fp='eleve', jours=0)
OV['Sizzle'] = o(interet='optionnel', type='continu', fp='moyen', jours=0, usages=['cuisine'],
                 note="Grésillement : cuisson à la poêle. Détecte un bruit de cuisson, pas un danger.")
OV['Clatter'] = o(interet='optionnel', type='impulsif', fp='eleve', jours=0, usages=['securite'],
                  note="Fracas d'objets qui tombent ou s'entrechoquent.")
for n in ['Whoosh, swoosh, swish', 'Clang', 'Squeal', 'Creak', 'Rustle', 'Whir', 'Clicking', 'Clickety-clack', 'Rumble',
          'Plop', 'Jingle, tinkle', 'Hum', 'Zing', 'Boing', 'Crunch']:
    OV[n] = o(interet='ignorer', fp='eleve', jours=0)

# ================================================================ BRUIT ET ACOUSTIQUE : outils de DIAGNOSTIC du micro
OV['Silence'] = o(interet='contexte', role='diagnostic', type='continu', fp='faible', jours=0, usages=['diagnostic'],
                  note="Silence : si cette classe est constante alors qu'il y a de l'activité, le micro est probablement muet ou mal branché.")
OV['Mains hum'] = o(interet='contexte', role='diagnostic', type='continu', fp='faible', jours=0, usages=['diagnostic'],
                    note="Ronflement du secteur (50/60 Hz) : s'il est élevé en permanence, le micro capte un bruit électrique (alimentation, boucle de masse). À corriger côté câblage.")
for n in ['Static', 'Distortion', 'White noise', 'Pink noise', 'Sidetone']:
    OV[n] = o(interet='contexte', role='diagnostic', type='continu', fp='moyen', jours=0, usages=['diagnostic'],
              note="Indicateur de qualité du micro : une valeur élevée en continu signale souvent un micro bruyant ou saturé.")
for n in ['Noise', 'Environmental noise', 'Cacophony', 'Throbbing', 'Vibration', 'Pulse', 'Harmonic', 'Sine wave', 'Chirp tone',
          'Sound effect', 'Reverberation', 'Echo', 'Field recording']:
    OV[n] = o(interet='ignorer', jours=0)
for n in ['Inside, small room', 'Inside, large room or hall', 'Inside, public space', 'Outside, urban or manmade', 'Outside, rural or natural']:
    OV[n] = o(interet='contexte', role='contexte', fp='moyen', jours=0, usages=['contexte'],
              note="Décrit l'acoustique du lieu (pièce, extérieur) plutôt qu'un événement : utile seulement pour comprendre l'environnement du micro.")

# ================================================================ SONS REPRODUITS (indices 518-520)
OV['Television'] = o(interet='contexte', role='contexte', type='continu', fp='moyen', vp='normale', jours=0, usages=['contexte'],
                     note="La télévision est la première cause de fausses alertes. Comme classe de CONTEXTE, elle permet de relever les seuils de cris, coups de feu, aboiements et sonnettes quand elle tourne.")
OV['Radio'] = o(interet='contexte', role='contexte', type='continu', fp='moyen', vp='normale', jours=0, usages=['contexte'],
                note="Même usage que « Télévision » : signale qu'un son vient d'un haut-parleur, pas de la pièce.")

OV['Explosion']['usages'] = ['securite']
OV['Ding']['usages'] = ['porte']
