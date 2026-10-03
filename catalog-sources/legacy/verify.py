import json, csv, yaml, sys
from collections import Counter
cat = json.load(open('catalogue_sons.json', encoding='utf-8'))
y = yaml.safe_load(open('catalogue_sons.yaml', encoding='utf-8'))
cl = cat['classes']
rows = list(csv.DictReader(open('yamnet_class_map.csv', encoding='utf-8')))
onto = {o['id']: o for o in json.load(open('ontology.json', encoding='utf-8'))}
errs = []
if len(cl) != 521: errs.append("nombre de classes != 521")
for c, r in zip(cl, rows):
    if (c['index'], c['id'], c['nom']) != (int(r['index']), r['mid'], r['display_name']):
        errs.append(f"désalignement {r['index']} {r['display_name']}")
if len({c['nom_fr'] for c in cl}) != 521: errs.append("noms FR en double")
if y['classes'] != cl or y['groupes'] != cat['groupes']: errs.append("YAML et JSON différents")
names = {c['nom']: c for c in cl}
ids = {c['id']: c['nom'] for c in cl}
for c in cl:
    # hiérarchie recalculée indépendamment depuis l'ontologie
    direct = {ids[ch] for ch in onto[c['id']]['child_ids'] if ch in ids}
    if not direct <= set(c['descendants_yamnet']): errs.append(f"enfant direct manquant {c['nom']}")
    for a in c['ancetres_yamnet']:
        if c['nom'] not in names[a]['descendants_yamnet']: errs.append(f"asymétrie {a}->{c['nom']}")
    s = c['suggestions']
    if c['clip_interdit'] and s['conservation_clip_jours']: errs.append(f"clip interdit/rétention {c['nom']}")
    if c['interet'] in ('ignorer', 'contexte') and s['conservation_clip_jours']: errs.append(f"rétention non-alerte {c['nom']}")
    if c['interet'] == 'surveiller' and not s['conservation_clip_jours'] and not c['clip_interdit']: errs.append(f"surveiller sans clip {c['nom']}")
    if not 0 < s['seuil'] < 1: errs.append(f"seuil {c['nom']}")
    if c['categorie'] not in cat['categories']: errs.append(f"catégorie {c['nom']}")
    if c['vie_privee'] == 'confidentielle' and c['interet'] == 'surveiller': errs.append(f"confidentielle surveillée {c['nom']}")
    if c['role'] == 'generique' and c['interet'] == 'surveiller': errs.append(f"générique surveillée {c['nom']}")
    for x in c['contextes_inhibiteurs']:
        if x not in names: errs.append(f"contexte inconnu {x}")
gids = {g['id'] for g in cat['groupes']}
for c in cl:
    for g in c['groupes']:
        if g not in gids: errs.append(f"groupe inconnu {g}")
for g in cat['groupes']:
    for m in g['membres']:
        if m not in names: errs.append(f"membre inconnu {m}")
for r in cat['regles_combinaison']:
    for m in r['classes']:
        if m not in names: errs.append(f"règle {r['id']}: {m}")
# « surveiller » : jamais deux classes d'une même branche parent/enfant
sv = [c for c in cl if c['interet'] == 'surveiller']
for a in sv:
    for b in sv:
        if a['nom'] in b['ancetres_yamnet']: errs.append(f"surveiller parent/enfant {a['nom']}/{b['nom']}")
print("ERREURS :", errs if errs else "aucune")
print("intérêt :", dict(Counter(c['interet'] for c in cl)))
print("à surveiller :", [(c['nom_fr'], c['suggestions']['seuil'], c['suggestions']['duree_min_s'], c['suggestions']['conservation_clip_jours']) for c in sv])
sys.exit(1 if errs else 0)
