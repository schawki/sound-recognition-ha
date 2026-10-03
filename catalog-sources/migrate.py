# -*- coding: utf-8 -*-
"""Migre le catalogue legacy (clés françaises) vers :
   catalog/catalog.yaml|json  : données neutres (clés anglaises, clé = AudioSet mid)
   catalog/i18n/fr.yaml       : textes français (extraits de l'existant)
   catalog/i18n/en.template.yaml : gabarit anglais (à compléter dans en_texts.py)
"""
import json, re, csv, os, unicodedata
import yaml

SRC = json.load(open('catalogue_sons.json', encoding='utf-8'))
OUT = 'catalog'
os.makedirs(OUT + '/i18n', exist_ok=True)

INTEREST = {'surveiller': 'monitor', 'optionnel': 'optional', 'contexte': 'context', 'ignorer': 'ignore'}
ROLE = {'evenement': 'event', 'contexte': 'context', 'diagnostic': 'diagnostic', 'generique': 'generic'}
STYPE = {'impulsif': 'impulsive', 'repete': 'repeated', 'tonal': 'tonal', 'continu': 'continuous', 'variable': 'variable'}
FPL = {'faible': 'low', 'moyen': 'medium', 'eleve': 'high'}
PRIV = {'normale': 'normal', 'sensible': 'sensitive', 'confidentielle': 'confidential'}
LEVEL = {'info': 'info', 'attention': 'warning', 'danger': 'danger'}
CAT = {'voix': 'voice', 'corps': 'body', 'foule': 'crowd', 'animaux_domestiques': 'pets', 'animaux_ferme': 'farm_animals',
       'animaux_sauvages': 'wildlife', 'musique': 'music', 'alarmes': 'alarms', 'nature': 'nature', 'eau': 'water',
       'vehicules': 'vehicles', 'maison': 'home', 'outils_mecanismes': 'tools_mechanisms',
       'impacts_explosions': 'impacts_explosions', 'onomatopees': 'onomatopoeia', 'bruit_ambiance': 'noise_ambience',
       'reproduction': 'reproduced_sound', 'divers': 'misc'}
USE = {'securite': 'security', 'incendie': 'fire', 'porte': 'door', 'bebe': 'baby', 'animaux': 'animals', 'fuite': 'leaks',
       'cuisine': 'kitchen', 'presence': 'presence', 'commande': 'voiceless_command', 'exterieur': 'outdoor',
       'meteo': 'weather', 'garage': 'garage', 'nuisibles': 'pests', 'confort': 'comfort', 'ambiance': 'ambience',
       'contexte': 'context', 'diagnostic': 'diagnostic', 'autres': 'other'}
GRP = {'chiens': 'dogs', 'chats': 'cats', 'pleurs_cris_aigus': 'cries_and_screams', 'cris': 'shouts', 'parole': 'speech',
       'voix_chantee': 'sung_voice', 'detonations': 'detonations', 'casse_verre': 'glass_breaking',
       'bips_incendie': 'fire_alarms_and_beeps', 'sonnettes_cloches': 'doorbells_and_bells', 'sirenes': 'sirens_and_horns',
       'sifflets': 'whistles', 'portes_coups': 'doors_and_knocks', 'eau_coule': 'running_water',
       'moteurs_continus': 'continuous_motors', 'pas_presence': 'footsteps_presence', 'toux_souffle': 'coughs_and_breathing',
       'insectes_rongeurs': 'insects_rodents', 'oiseaux': 'birds', 'vehicules_rue': 'street_vehicles',
       'feu_crepitement': 'fire_crackle', 'diagnostic_micro': 'mic_diagnostics', 'musique_generale': 'music_general'}
RULE = {'incendie_double': 'fire_double', 'incendie_bips': 'fire_beeps', 'feu_seul': 'fire_only',
        'detonations_feux': 'detonations_fireworks', 'sonnette_doublons': 'doorbell_duplicates',
        'sonnette_telephone': 'doorbell_phone', 'bebe_chat': 'baby_cat', 'cris_multiples': 'multiple_shouts',
        'verre_doublons': 'glass_duplicates', 'chiens_doublons': 'dog_duplicates', 'parole_cible': 'speech_target',
        'eau_fuite': 'water_leak', 'musique_classes': 'music_classes', 'contexte_recommande': 'context_recommended'}
# 'un_parmi' signifiait « au moins deux » ; plusieurs messages valent pour une seule classe -> 'any'
RULE_MATCH = {'fire_double': 'all', 'fire_beeps': 'all', 'fire_only': 'any', 'detonations_fireworks': 'any',
              'doorbell_duplicates': 'at_least_two', 'doorbell_phone': 'at_least_two', 'baby_cat': 'at_least_two',
              'multiple_shouts': 'at_least_two', 'glass_duplicates': 'at_least_two', 'dog_duplicates': 'at_least_two',
              'speech_target': 'any', 'water_leak': 'any', 'music_classes': 'at_least_two', 'context_recommended': 'any'}
AUTO = {'parent_enfant': 'parent_child', 'clip_interdit': 'clip_forbidden', 'seuil_bas_fp_eleve': 'low_threshold_high_fp',
        'classe_generique': 'generic_class', 'sans_contexte': 'missing_context'}

CAUSE = {
 'télévision': 'television', 'télévision (films, jeux vidéo)': 'television', 'télévision (sport)': 'television',
 'télévision et jeux vidéo': 'television', 'radio': 'radio', 'musique': 'music',
 'voix diffusée par haut-parleur (appel à la prière, annonces)': 'broadcast_voice', 'assistant vocal': 'voice_assistant',
 'enceintes connectées': 'smart_speakers', 'rue': 'street', 'visioconférence': 'video_calls',
 'feux d\'artifice': 'fireworks', "feux d'artifice et pétards": 'fireworks', 'enfants qui jouent': 'children_playing',
 "jeux d'enfants": 'children_playing', 'enfants plus grands': 'children_playing', 'cour d\'école voisine': 'schoolyard',
 'voisinage': 'neighbors', 'voisinage (plafond, escaliers)': 'neighbors', 'travaux chez les voisins': 'works',
 'travaux': 'works', 'animaux': 'animals', 'chiens des voisins': 'neighbor_dogs', 'miaulements de chat': 'cat_meows',
 'porte qui claque': 'door_slam', 'claquement de porte': 'door_slam', 'chocs': 'impacts', 'GPS': 'gps',
 'cuisson (friture)': 'frying', 'cheminée': 'fireplace', 'alarmes de voisinage': 'neighbor_alarms',
 'alarme d\'immeuble voisin ou exercice': 'building_alarm_drill', "alarmes d'autres appareils": 'other_device_alarms',
 'sonnettes de télévision': 'tv_doorbells', 'téléphones': 'phones', 'sonnettes de voisins': 'neighbor_doorbells',
 'sonnette': 'doorbells', 'carillons': 'chimes', 'meubles': 'furniture',
 'ambulances et police dans la rue': 'emergency_sirens',
 "bips d'appareils (micro-ondes, four, lave-linge)": 'appliance_beeps', "bips d'appareils": 'appliance_beeps',
 'micro-ondes': 'microwave', 'lave-linge et lave-vaisselle': 'washing_machines',
 'vaisselle ou bouteille qui tombe': 'dropped_dishes', 'tonnerre': 'thunder', 'détecteurs': 'detectors',
}
CAUSE_FR = {  # libellé français canonique par id
 'television': 'télévision', 'radio': 'radio', 'music': 'musique', 'broadcast_voice': 'voix diffusée par haut-parleur (appel à la prière, annonces)',
 'voice_assistant': 'assistant vocal', 'smart_speakers': 'enceintes connectées', 'street': 'rue', 'video_calls': 'visioconférence',
 'fireworks': "feux d'artifice et pétards", 'children_playing': "enfants qui jouent", 'schoolyard': "cour d'école voisine",
 'neighbors': 'voisinage', 'works': 'travaux', 'animals': 'animaux', 'neighbor_dogs': 'chiens des voisins', 'cat_meows': 'miaulements de chat',
 'door_slam': 'porte qui claque', 'impacts': 'chocs', 'gps': 'GPS', 'frying': 'cuisson (friture)', 'fireplace': 'cheminée',
 'neighbor_alarms': 'alarmes de voisinage', 'building_alarm_drill': "alarme d'immeuble voisin ou exercice",
 'other_device_alarms': "alarmes d'autres appareils", 'tv_doorbells': 'sonnettes de télévision', 'phones': 'téléphones',
 'neighbor_doorbells': 'sonnettes de voisins', 'doorbells': 'sonnette', 'chimes': 'carillons', 'furniture': 'meubles',
 'emergency_sirens': 'ambulances et police dans la rue', 'appliance_beeps': "bips d'appareils (micro-ondes, four, lave-linge)",
 'microwave': 'micro-ondes', 'washing_machines': 'lave-linge et lave-vaisselle', 'dropped_dishes': 'vaisselle ou bouteille qui tombe',
 'thunder': 'tonnerre', 'detectors': 'détecteurs',
}
assert set(CAUSE.values()) == set(CAUSE_FR), set(CAUSE.values()) ^ set(CAUSE_FR)

# ------------------------------------------------------------------ helpers
by_name = {c['nom']: c for c in SRC['classes']}
mid = lambda name: by_name[name]['id']

def slug(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '_', s.lower()).strip('_')

def tr(s):
    """Texte FR : rend les placeholders anglais."""
    return (s.replace('{classe}', '{class}').replace('{enfant}', '{child}')
             .replace('{parent}', '{parent}').replace('{exemples}', '{examples}'))

# notes : id par texte identique
note_text, note_users = {}, {}
for c in SRC['classes']:
    if c['note']:
        note_users.setdefault(c['note'], []).append(c)
note_id = {}
used = set()
for text, users in note_users.items():
    base = slug(users[0]['nom'])
    nid = base + ('_shared' if len(users) > 1 else '')
    while nid in used:
        nid += '_2'
    used.add(nid)
    note_id[text] = nid

classes, fr_classes, fr_notes = [], {}, {}
for c in sorted(SRC['classes'], key=lambda x: x['index']):
    s = c['suggestions']
    classes.append({
        'mid': c['id'], 'yamnet_index': c['index'], 'audioset_name': c['nom'],
        'category': CAT[c['categorie']],
        'audioset_path': c['chemin_audioset'],
        'parents': [mid(n) for n in c['parents']] if all(n in by_name for n in c['parents']) else None,
        'ancestors': [mid(n) for n in c['ancetres_yamnet']],
        'descendants': [mid(n) for n in c['descendants_yamnet']],
        'role': ROLE[c['role']], 'interest': INTEREST[c['interet']], 'sound_type': STYPE[c['type_son']],
        'false_positives': {'level': FPL[c['faux_positifs']['niveau']],
                            'causes': sorted({CAUSE[x] for x in c['faux_positifs']['causes']})},
        'privacy': PRIV[c['vie_privee']], 'clip_forbidden': c['clip_interdit'],
        'suggestions': {'threshold': s['seuil'], 'min_duration_s': s['duree_min_s'], 'cooldown_s': s['rearmement_s'],
                        'pre_roll_s': s['tampon_avant_s'], 'post_roll_s': s['tampon_apres_s'],
                        'clip_retention_days': s['conservation_clip_jours']},
        'inhibiting_contexts': [mid(n) for n in c['contextes_inhibiteurs']],
        'usages': [USE[u] for u in c['usages']],
        'groups': [GRP[g] for g in c['groupes']],
        'note': note_id.get(c['note']),
    })
    fr_classes[c['id']] = c['nom_fr']
    if c['note']:
        fr_notes[note_id[c['note']]] = c['note']
# 'parents' : les parents AudioSet hors YAMNet n'ont pas de mid -> on garde les noms dans audioset_path ; champ retiré
for k in classes:
    del k['parents']

# vérifie que le nom de chaque mid est unique
assert len({k['mid'] for k in classes}) == 521

groups = [{'id': GRP[g['id']], 'members': [mid(m) for m in g['membres']]} for g in SRC['groupes']]
rules = [{'id': RULE[r['id']], 'match': RULE_MATCH[RULE[r['id']]], 'classes': [mid(m) for m in r['classes']],
          'level': LEVEL[r['niveau']]} for r in SRC['regles_combinaison']]
auto_rules = [{'id': AUTO[r['id']], 'level': LEVEL[r['niveau']]} for r in SRC['regles_automatiques']]
auto_rules += [{'id': 'schedule_gap_safety', 'level': 'warning'}, {'id': 'volume_gate_safety', 'level': 'warning'}, {'id': 'clip_source_disallowed', 'level': 'info'}]

meta = {
    'schema_version': 2, 'model': 'yamnet', 'num_classes': 521,
    'key': 'AudioSet mid (stable across YAMNet / PANNs / BEATs; model index differs)',
    'sources': SRC['meta']['sources'],
    'languages': ['en', 'fr'], 'fallback_language': 'en',
}
catalog = {
    'meta': meta,
    'enums': {
        'interest': ['monitor', 'optional', 'context', 'ignore'],
        'role': ['event', 'context', 'diagnostic', 'generic'],
        'sound_type': ['impulsive', 'repeated', 'tonal', 'continuous', 'variable'],
        'false_positive_level': ['low', 'medium', 'high'],
        'privacy': ['normal', 'sensitive', 'confidential'],
        'rule_match': ['all', 'at_least_two', 'any'],
        'level': ['info', 'warning', 'danger'],
    },
    'categories': list(CAT.values()),
    'usages': list(USE.values()),
    'causes': sorted(CAUSE_FR),
    'groups': groups, 'rules': rules, 'auto_rules': auto_rules, 'classes': classes,
}

# ------------------------------------------------------------------ textes FR
leg = SRC['meta']['legende']
fr = {
    'language': 'fr',
    'classes': fr_classes,
    'notes': fr_notes,
    'categories': {CAT[k]: v for k, v in SRC['categories'].items()},
    'causes': CAUSE_FR,
    'groups': {GRP[g['id']]: {'name': g['nom'], 'risk': tr(g['risque']), 'advice': tr(g['conseil'])} for g in SRC['groupes']},
    'rules': {RULE[r['id']]: tr(r['message']) for r in SRC['regles_combinaison']},
    'auto_rules': {AUTO[r['id']]: tr(r['message']) for r in SRC['regles_automatiques']},
    'enum_help': {
        'interest': {INTEREST[k]: v for k, v in leg['interet'].items()},
        'role': {ROLE[k]: v for k, v in leg['role'].items()},
        'sound_type': {STYPE[k]: v for k, v in leg['type_son'].items()},
        'false_positive_level': {FPL[k]: v for k, v in leg['faux_positifs.niveau'].items()},
        'privacy': {PRIV[k]: v for k, v in leg['vie_privee'].items()},
    },
    'setting_help': {
        'threshold': leg['suggestions']['seuil'], 'min_duration_s': leg['suggestions']['duree_min_s'],
        'cooldown_s': leg['suggestions']['rearmement_s'], 'pre_roll_s': leg['suggestions']['tampon_avant_s'],
        'post_roll_s': leg['suggestions']['tampon_apres_s'], 'clip_retention_days': leg['suggestions']['conservation_clip_jours'],
    },
}
open('/dev/null', 'w')

class D(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True

def dump(obj, path, **kw):
    yaml.dump(obj, open(path, 'w', encoding='utf-8'), Dumper=D, allow_unicode=True, sort_keys=False, width=110, **kw)

dump(catalog, OUT + '/catalog.yaml', default_flow_style=None)
json.dump(catalog, open(OUT + '/catalog.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
dump(fr, OUT + '/i18n/fr.yaml')
# références pour l'écriture de l'anglais
json.dump({'notes': {nid: {'fr': fr_notes[nid], 'classes': [u['nom'] for u in note_users[t]]}
                     for t, nid in note_id.items()}}, open('en_reference.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('ok', len(classes), 'classes,', len(fr_notes), 'notes distinctes')
