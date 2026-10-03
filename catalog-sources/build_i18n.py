# -*- coding: utf-8 -*-
"""Complète fr.yaml (conditions des règles auto, UI) et génère en.yaml à partir de en_texts.py."""
import yaml, json
import en_texts as T

cat = json.load(open('catalog/catalog.json', encoding='utf-8'))
class D(yaml.SafeDumper):
    def ignore_aliases(self, data): return True
def dump(o, p): yaml.dump(o, open(p, 'w', encoding='utf-8'), Dumper=D, allow_unicode=True, sort_keys=False, width=110)

fr = yaml.safe_load(open('catalog/i18n/fr.yaml', encoding='utf-8'))
FIX = [("« Beuglement »", "« Beuglement (voix) »"), ("« Hurlement »", "« Hurlement de chien ou de loup »"),
       ("« Canidés »", "« Canidés (chiens, loups) »"), ("« Micro-ondes »", "« Four à micro-ondes »"),
       ("Classe « chiens et loups » :", "Classe regroupant chiens et loups :"),
       ("un « ronflement du secteur » constant", "un « Ronflement du secteur (50/60 Hz) » constant")]
def fx(t):
    for a, b in FIX: t = t.replace(a, b)
    return t
fr['notes'] = {k: fx(v) for k, v in fr['notes'].items()}
fr['rules'] = {k: fx(v) for k, v in fr['rules'].items()}
fr['groups'] = {k: {kk: fx(vv) for kk, vv in v.items()} for k, v in fr['groups'].items()}
fr['auto_rules'] = {k: {'condition': T.AUTO_RULES_DESC['fr'][k], 'message': (v['message'] if isinstance(v, dict) else v)} for k, v in fr['auto_rules'].items()}
fr['auto_rules'].update({k: {'condition': v[0], 'message': v[1]} for k, v in T.AUTO_RULES_FR_EXTRA.items()})
fr['ui'] = T.UI['fr']
fr['usages'] = {'security': "Sécurité", 'fire': "Incendie", 'door': "Porte et visiteurs", 'baby': "Bébé", 'animals': "Animaux",
    'leaks': "Eau et fuites", 'kitchen': "Cuisine", 'presence': "Présence", 'voiceless_command': "Commande sans voix",
    'outdoor': "Extérieur", 'weather': "Météo", 'garage': "Garage et voiture", 'pests': "Nuisibles", 'comfort': "Confort",
    'ambience': "Ambiance", 'context': "Contexte", 'diagnostic': "Diagnostic du micro", 'other': "Autres usages"}
dump(fr, 'catalog/i18n/fr.yaml')

names = {}
for c in cat['classes']:
    names[c['mid']] = T.NAME_OVERRIDES.get(c['yamnet_index'], c['audioset_name'])
en = {
    'language': 'en', 'classes': names, 'notes': T.NOTES, 'categories': T.CATEGORIES, 'usages': T.USAGES, 'causes': T.CAUSES,
    'groups': {k: {'name': v[0], 'risk': v[1], 'advice': v[2]} for k, v in T.GROUPS.items()},
    'rules': T.RULES,
    'auto_rules': {k: {'condition': T.AUTO_RULES_DESC['en'][k], 'message': v} for k, v in T.AUTO_RULES.items()},
    'enum_help': T.ENUM_HELP, 'setting_help': T.SETTING_HELP, 'ui': T.UI['en'],
}
# ordre des groupes / règles identique au FR
en['groups'] = {k: en['groups'][k] for k in fr['groups']}
en['rules'] = {k: en['rules'][k] for k in fr['rules']}
en['auto_rules'] = {k: en['auto_rules'][k] for k in fr['auto_rules']}
en['notes'] = {k: en['notes'][k] for k in fr['notes'] if k in en['notes']}
dump(en, 'catalog/i18n/en.yaml')
print('en.yaml ok')
