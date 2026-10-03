# -*- coding: utf-8 -*-
"""Annotations de jugement, partie A : voix, corps, foule, animaux, musique.

IMPORTANT : les valeurs (intérêt, risque de faux positifs, seuil, durée de conservation)
sont des SUGGESTIONS DE DÉPART fondées sur la connaissance générale du modèle et de
l'ontologie AudioSet. Rien ici n'a été mesuré chez l'utilisateur.
"""

def o(interet=None, role=None, type=None, fp=None, causes=None, vp=None,
      seuil=None, jours=None, usages=None, note=None, ctx=None):
    d = dict(interet=interet, role=role, type_son=type, fp_niveau=fp, fp_causes=causes,
             vie_privee=vp, seuil=seuil, jours=jours, usages=usages, note=note, ctx=ctx)
    return {k: v for k, v in d.items() if v is not None}

TV = ["télévision", "radio", "musique"]
CTX_TV = ["Television", "Radio", "Music"]

# Valeurs par défaut par catégorie (modifiables par classe ci-dessous)
CAT_DEF = {
    'voix':                dict(interet='optionnel', role='evenement', type_son='variable', fp_niveau='moyen', vie_privee='sensible', seuil=0.5, jours=0),
    'corps':               dict(interet='ignorer',   role='evenement', type_son='variable', fp_niveau='moyen', vie_privee='sensible', seuil=0.5, jours=0),
    'foule':               dict(interet='ignorer',   role='contexte',  type_son='continu',  fp_niveau='eleve', vie_privee='confidentielle', seuil=0.5, jours=0),
    'animaux_domestiques': dict(interet='optionnel', role='evenement', type_son='impulsif', fp_niveau='moyen', vie_privee='normale', seuil=0.5, jours=7),
    'animaux_ferme':       dict(interet='ignorer',   role='evenement', type_son='variable', fp_niveau='moyen', vie_privee='normale', seuil=0.5, jours=0),
    'animaux_sauvages':    dict(interet='ignorer',   role='evenement', type_son='variable', fp_niveau='moyen', vie_privee='normale', seuil=0.5, jours=0),
    'musique':             dict(interet='ignorer',   role='evenement', type_son='continu',  fp_niveau='eleve', vie_privee='normale', seuil=0.5, jours=0),
}

OV = {}

# ---------------------------------------------------------------- VOIX
# Parole : jamais de clip. Sert au mieux de contexte (« quelqu'un parle »).
for n in ['Speech', 'Conversation', 'Child speech, kid speaking', 'Narration, monologue', 'Babbling']:
    OV[n] = o(interet='contexte', role='contexte', type='continu', fp='eleve', vp='confidentielle', jours=0,
              causes=["télévision", "radio", "visioconférence", "assistant vocal"],
              usages=['presence', 'contexte'],
              note=("Parole : aucun clip ne doit être conservé. Utile uniquement comme contexte (« quelqu'un parle ») pour relever les seuils des autres classes."
                    if n == 'Speech' else "Mêmes précautions que « Parole » : aucun clip, contexte seulement."))
OV['Whispering'] = o(interet='ignorer', role='evenement', type='continu', fp='eleve', vp='confidentielle', jours=0,
                     note="Chuchotement : confidentiel, très peu fiable. Ne pas conserver de clip.")
OV['Speech synthesizer'] = o(interet='contexte', role='contexte', type='continu', fp='moyen', vp='normale', jours=0,
                             causes=["assistant vocal", "télévision", "GPS"],
                             usages=['contexte'],
                             note="Voix de synthèse (assistant vocal, annonces). Peut servir à ignorer les sons produits par vos propres assistants.")

for n in ['Shout', 'Yell', 'Screaming']:
    OV[n] = o(interet='surveiller' if n == 'Screaming' else 'optionnel', role='evenement', type='impulsif', fp='eleve', vp='sensible', seuil=0.6, jours=7,
              causes=["télévision (films, jeux vidéo)", "enfants qui jouent", "voisinage", "radio"],
              ctx=CTX_TV, usages=['securite'],
              note="Utile pour la sécurité, mais très sensible aux fausses alertes (TV, enfants qui jouent). Relever le seuil quand la télévision tourne ; ne pas enclencher d'action automatique lourde.")
OV['Screaming']['note'] = ("Cris stridents : le plus utile pour la sécurité mais aussi le plus sujet aux fausses alertes (films, jeux, enfants qui s'amusent). "
                           "À confirmer par un second signal (présence, porte, caméra) avant toute action.")
OV['Children shouting'] = o(interet='optionnel', type='continu', fp='eleve', vp='sensible', seuil=0.6, jours=0,
                            causes=["jeux d'enfants", "cour d'école voisine", "télévision"], ctx=CTX_TV,
                            note="Presque toujours un son normal. Peu utile pour une alerte.")
OV['Bellow'] = o(interet='ignorer', fp='eleve', jours=0)
OV['Whoop'] = o(interet='ignorer', fp='eleve', jours=0, causes=TV)

for n in ['Laughter', 'Baby laughter', 'Giggle', 'Snicker', 'Belly laugh', 'Chuckle, chortle']:
    OV[n] = o(interet='ignorer', fp='eleve', vp='sensible', jours=0, causes=TV,
              note="Pas d'intérêt pour une alerte ; sensible côté vie privée.")

OV['Baby cry, infant cry'] = o(interet='surveiller', role='evenement', type='repete', fp='moyen', vp='sensible', seuil=0.5, jours=3,
                               causes=["miaulements de chat", "télévision", "enfants plus grands"],
                               ctx=CTX_TV, usages=['bebe'],
                               note="Pleurs de bébé : cas d'usage très demandé. Se confond parfois avec les miaulements (voir « Pleurs et cris aigus »). "
                                    "Exiger au moins 2 secondes de détection continue réduit les fausses alertes.")
OV['Crying, sobbing'] = o(interet='optionnel', type='repete', fp='moyen', vp='sensible', seuil=0.55, jours=0, causes=TV, ctx=CTX_TV,
                          note="Pleurs d'enfant ou d'adulte. Redondant avec « Pleurs de bébé » pour surveiller un enfant en bas âge.")
OV['Whimper'] = o(interet='optionnel', type='repete', fp='eleve', vp='sensible', seuil=0.6, jours=0,
                  note="Gémissement plaintif : proche des pleurs faibles et de « Gémissement de chien ». Très flou.")
OV['Wail, moan'] = o(interet='optionnel', type='repete', fp='eleve', vp='sensible', seuil=0.6, jours=0, causes=TV,
                     note="Lamentation, gémissement : intéressant en théorie pour une détresse, mais trop peu fiable pour déclencher seul une alerte.")
OV['Groan'] = o(interet='optionnel', type='impulsif', fp='eleve', vp='sensible', seuil=0.6, jours=0, causes=TV,
                note="Gémissement sourd. À ne pas utiliser seul pour une détection de chute ou de détresse.")
OV['Grunt'] = o(interet='ignorer', fp='eleve', vp='sensible', jours=0)
OV['Sigh'] = o(interet='ignorer', fp='eleve', vp='sensible', jours=0)
OV['Whistling'] = o(interet='optionnel', type='tonal', fp='moyen', vp='normale', seuil=0.5, jours=0,
                    note="Sifflement de la bouche. Proche du sifflet (bouilloire, sifflet à vapeur) : voir « Sifflets ».")

# Chant, musique vocale : fréquents faux positifs (haut-parleurs, TV, appel à la prière diffusé…)
for n in ['Singing', 'Choir', 'Yodeling', 'Chant', 'Mantra', 'Child singing', 'Synthetic singing', 'Rapping', 'Humming']:
    OV[n] = o(interet='ignorer', type='continu', fp='eleve', vp='sensible', jours=0,
              causes=["télévision", "radio", "musique", "voix diffusée par haut-parleur (appel à la prière, annonces)"],
              ctx=CTX_TV)
OV['Singing']['note'] = ("Chant : intéressant surtout comme contexte (activité musicale). Une voix chantée diffusée par haut-parleur "
                         "(appel à la prière, annonces) peut aussi le déclencher.")
OV['Chant']['note'] = ("« Psalmodie » : une psalmodie ou un appel à la prière diffusé à l'extérieur peut déclencher cette classe, "
                       "ainsi que « Parole » et « Musique du Moyen-Orient ».")

# ---------------------------------------------------------------- CORPS
OV['Cough'] = o(interet='optionnel', type='impulsif', fp='moyen', vp='sensible', seuil=0.5, jours=0, causes=TV,
                usages=['presence'], note="Toux : donnée de santé potentielle, donc sensible. Ne pas conserver de clip.")
OV['Sneeze'] = o(interet='optionnel', type='impulsif', fp='moyen', vp='sensible', seuil=0.5, jours=0, causes=TV, usages=['presence'])
OV['Snoring'] = o(interet='optionnel', type='repete', fp='moyen', vp='sensible', seuil=0.5, jours=0, usages=['presence'],
                  note="Ronflement : indique qu'une personne dort dans la pièce ; sensible, ne pas conserver de clip.")
OV['Throat clearing'] = o(interet='ignorer', fp='moyen', jours=0)
for n in ['Walk, footsteps', 'Run', 'Shuffle']:
    OV[n] = o(interet='optionnel', type='repete', fp='moyen', vp='normale', seuil=0.5, jours=0,
              causes=["télévision", "voisinage (plafond, escaliers)", "animaux"], usages=['presence'],
              note="Pas : complète un capteur de présence mais ne le remplace pas ; dépend beaucoup du revêtement et du micro.")
OV['Finger snapping'] = o(interet='optionnel', type='impulsif', fp='moyen', vp='normale', seuil=0.55, jours=0, usages=['commande'],
                          note="Peut servir de commande sans voix (claquement de doigts), à tester.")
OV['Clapping'] = o(interet='optionnel', type='repete', fp='moyen', vp='normale', seuil=0.55, jours=0, causes=TV, usages=['commande'],
                   note="Claquements de mains : peut servir de commande sans voix. Confusion avec les applaudissements et certains chocs secs.")
for n in ['Heart sounds, heartbeat', 'Heart murmur']:
    OV[n] = o(interet='ignorer', fp='eleve', vp='sensible', jours=0,
              note="Peu pertinent en pratique : se confond avec des basses ou des battements.")

# ---------------------------------------------------------------- FOULE (indices 61-66)
OV['Crowd'] = o(interet='contexte', role='contexte', type='continu', fp='eleve', vp='confidentielle', jours=0,
                usages=['contexte'], note="Foule : souvent la télévision ou la rue. À utiliser seulement comme contexte.")
OV['Chatter'] = o(interet='contexte', role='contexte', type='continu', fp='eleve', vp='confidentielle', jours=0, usages=['contexte'])
OV['Hubbub, speech noise, speech babble'] = o(interet='contexte', role='contexte', type='continu', fp='eleve', vp='confidentielle', jours=0,
                                              usages=['contexte'], note="Brouhaha : plusieurs voix en même temps. Contexte seulement.")
OV['Cheering'] = o(interet='ignorer', fp='eleve', causes=["télévision (sport)"], jours=0, vp='sensible')
OV['Applause'] = o(interet='ignorer', fp='eleve', causes=["télévision"], jours=0, vp='sensible')
OV['Children playing'] = o(interet='optionnel', role='evenement', type='continu', fp='eleve', vp='sensible', jours=0,
                           causes=["cour d'école voisine", "télévision", "rue"],
                           note="Enfants qui jouent : normal dans la plupart des cas. Peut servir à calmer d'autres classes (cris).")

# ---------------------------------------------------------------- ANIMAUX DOMESTIQUES
OV['Bark'] = o(interet='surveiller', type='impulsif', fp='moyen', seuil=0.5, jours=7,
               causes=["chiens des voisins", "télévision", "rue"], ctx=CTX_TV, usages=['animaux', 'securite'],
               note="Aboiement : la classe la plus utile pour les chiens. Préférer « Aboiement » seul plutôt que « Chien » + « Aboiement » (doublon).")
OV['Dog'] = o(interet='optionnel', role='generique', type='variable', fp='moyen', seuil=0.5, jours=0, usages=['animaux'],
              note="Classe parente : englobe aboiement, hurlement, grondement, etc. Choisir plutôt les classes précises.")
OV['Canidae, dogs, wolves'] = o(interet='ignorer', role='generique', fp='moyen', jours=0,
                                note="Classe « chiens et loups » : ne contient que « Grondement » et « Hurlement » (pas « Aboiement »). Redondante avec « Chien » et plus bruyante.")
for n in ['Yip', 'Bow-wow', 'Howl', 'Growling', 'Whimper (dog)']:
    OV[n] = o(interet='optionnel', fp='moyen', jours=0, usages=['animaux'],
              note="Sous-classe de « Chien » : redondant si « Aboiement » est déjà surveillé.")
OV['Domestic animals, pets'] = o(interet='ignorer', role='generique', jours=0, note="Classe parente : ne pas choisir seule.")
OV['Cat'] = o(interet='optionnel', role='generique', fp='moyen', jours=0, usages=['animaux'],
              note="Classe parente : englobe miaulement, ronronnement, feulement.")
OV['Meow'] = o(interet='optionnel', type='impulsif', fp='moyen', seuil=0.5, jours=0, usages=['animaux'],
               note="Miaulement : se confond parfois avec des pleurs de bébé.")
OV['Purr'] = o(interet='ignorer', type='continu', fp='moyen', jours=0)
OV['Hiss'] = o(interet='optionnel', type='impulsif', fp='eleve', jours=0,
               note="Feulement : proche d'un jet d'air ou de vapeur (« Vapeur », « Pulvérisation »).")
OV['Caterwaul'] = o(interet='optionnel', type='repete', fp='moyen', jours=0, usages=['animaux'],
                    note="Miaulements de bagarre : forts, proches de cris ou de pleurs.")

# ---------------------------------------------------------------- ANIMAUX DE FERME : tous ignorer par défaut
OV['Livestock, farm animals, working animals'] = o(role='generique', jours=0, note="Classe parente.")
OV['Crowing, cock-a-doodle-doo'] = o(interet='ignorer', type='repete', fp='moyen', jours=0,
                                     note="Chant du coq : utile seulement si vous en élevez ; sinon source de bruit extérieur.")

# ---------------------------------------------------------------- ANIMAUX SAUVAGES, OISEAUX, INSECTES
OV['Animal'] = o(role='generique', jours=0, note="Classe racine : à ne pas choisir directement.")
OV['Wild animals'] = o(role='generique', jours=0, note="Classe parente : à ne pas choisir directement.")
OV['Bird'] = o(interet='contexte', role='generique', type='variable', fp='moyen', jours=0, usages=['ambiance'],
               note="Oiseaux en général : sert d'indicateur d'ambiance extérieure (micro proche d'une fenêtre ouverte).")
OV['Bird vocalization, bird call, bird song'] = o(interet='contexte', role='contexte', type='variable', fp='moyen', jours=0, usages=['ambiance'])
OV['Mouse'] = o(interet='optionnel', type='repete', fp='eleve', jours=0, usages=['nuisibles'],
                note="Souris : possible en grenier ou cave, mais très flou ; à tester avant d'en tirer une alerte.")
OV['Rodents, rats, mice'] = o(interet='optionnel', role='generique', type='repete', fp='eleve', jours=0, usages=['nuisibles'])
OV['Patter'] = o(interet='optionnel', type='repete', fp='eleve', jours=0,
                 note="Trottinement : confusion fréquente avec la pluie fine ou des pas légers.")
for n in ['Mosquito', 'Fly, housefly', 'Buzz', 'Bee, wasp, etc.', 'Insect', 'Cricket']:
    OV[n] = o(interet='ignorer', type='continu', fp='eleve', jours=0,
              note="Insectes : peu fiable en intérieur ; se confond avec des bourdonnements d'appareils.")
OV['Roar'] = o(interet='ignorer', fp='eleve', causes=TV, jours=0)
OV['Roaring cats (lions, tigers)'] = o(interet='ignorer', fp='eleve', causes=TV, jours=0)
OV['Whale vocalization'] = o(interet='ignorer', fp='eleve', jours=0, note="Sans intérêt domestique ; déclenche surtout sur des sons tonals graves.")
OV['Snake'] = o(interet='ignorer', role='generique', jours=0)
OV['Rattle'] = o(interet='ignorer', jours=0)
OV['Bird flight, flapping wings'] = o(interet='ignorer', type='repete', fp='moyen', jours=0)

# ---------------------------------------------------------------- MUSIQUE
OV['Music'] = o(interet='contexte', role='contexte', type='continu', fp='eleve', vp='normale', jours=0,
                causes=["télévision", "radio", "enceintes connectées"],
                usages=['contexte'],
                note="Classe la plus utile du groupe musique : un seul signal « de la musique joue » pour relever les seuils des autres classes. "
                     "Les 140+ autres classes musicales (instruments, genres) sont ignorées par défaut.")
OV['Middle Eastern music'] = o(interet='ignorer', type='continu', fp='eleve', jours=0,
                               causes=["télévision", "radio", "voix diffusée par haut-parleur (appel à la prière, annonces)"],
                               note="Peut se déclencher sur un appel à la prière ou une psalmodie diffusés par haut-parleur.")
OV['Vocal music'] = o(interet='ignorer', type='continu', fp='eleve', jours=0)
OV['Church bell'] = o(interet='ignorer', type='tonal', fp='moyen', jours=0, note="Cloche d'église : sons extérieurs ; proche d'une sonnette selon le micro.")
OV['Bell'] = o(interet='ignorer', role='generique', type='tonal', fp='moyen', jours=0,
               note="Classe parente des cloches (église, vélo, grelot, carillon, diapason, cloche de vache). Ne contient pas « Sonnette de porte » mais s'en approche à l'oreille.")
OV['Chime'] = o(interet='ignorer', type='tonal', fp='moyen', jours=0)
OV['Jingle bell'] = o(interet='ignorer', type='tonal', fp='moyen', jours=0)
OV['Wind chime'] = o(interet='ignorer', type='tonal', fp='moyen', jours=0)
OV['Bicycle bell'] = o(interet='ignorer', type='tonal', fp='moyen', jours=0)
OV['Tuning fork'] = o(interet='ignorer', jours=0)
OV['Singing bowl'] = o(interet='ignorer', jours=0)
OV['Lullaby'] = o(interet='ignorer', jours=0, note="Berceuse : sans intérêt pour la détection ; fait partie de l'ensemble « Musique ».")

OV['Shout']['note'] = ("Cri : classe parente de « Appel crié », « Cri de joie », « Beuglement » et « Enfants qui crient ». "
                       "Choisir « Hurlements stridents » comme alerte principale, et ne garder « Cri » qu'en option.")
OV['Yell']['note'] = "Appel crié : sous-classe de « Cri ». Doublon si « Cri » est choisi ; très sensible à la télévision et aux enfants."

# usages des classes optionnelles qui n'en avaient pas
for _n, _u in [('Children shouting', ['presence']), ('Children playing', ['presence']),
               ('Crying, sobbing', ['bebe']), ('Whimper', ['bebe']),
               ('Wail, moan', ['securite']), ('Groan', ['securite']),
               ('Whistling', ['autres']), ('Hiss', ['animaux']), ('Patter', ['nuisibles'])]:
    OV[_n]['usages'] = _u
