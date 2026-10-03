import csv, json
classes = list(csv.DictReader(open('yamnet_class_map.csv')))
onto = json.load(open('ontology.json'))
by_id = {o['id']: o for o in onto}
parent = {}
for o in onto:
    for ch in o['child_ids']:
        parent.setdefault(ch, []).append(o['id'])

def ancestors(i):
    seen=set(); stack=list(parent.get(i,[]))
    while stack:
        x=stack.pop()
        if x in seen: continue
        seen.add(x); stack.extend(parent.get(x,[]))
    return seen

def first_chain(i):
    chain=[i]
    while parent.get(chain[-1]): chain.append(parent[chain[-1]][0])
    return [by_id[x]['name'] for x in reversed(chain)]

# ordre = priorité : le premier qui correspond gagne
RULES = [
 ('Alarm','alarmes'),
 ('Domestic animals, pets','animaux_domestiques'),
 ('Livestock, farm animals, working animals','animaux_ferme'),
 ('Wild animals','animaux_sauvages'),
 ('Animal','animaux_sauvages'),
 ('Human voice','voix'),
 ('Whistling','voix'),
 ('Respiratory sounds','corps'),
 ('Digestive','corps'),
 ('Heart sounds, heartbeat','corps'),
 ('Hands','corps'),
 ('Human locomotion','corps'),
 ('Human group actions','corps'),
 ('Human sounds','corps'),
 ('Domestic sounds, home sounds','maison'),
 ('Vehicle','vehicules'),
 ('Engine','vehicules'),
 ('Explosion','impacts_explosions'),
 ('Glass','impacts_explosions'),
 ('Generic impact sounds','impacts_explosions'),
 ('Specific impact sounds','impacts_explosions'),
 ('Wood','impacts_explosions'),
 ('Surface contact','impacts_explosions'),
 ('Tools','outils_mecanismes'),
 ('Mechanisms','outils_mecanismes'),
 ('Water','eau'),
 ('Liquid','eau'),
 ('Thunderstorm','nature'),
 ('Wind','nature'),
 ('Fire','nature'),
 ('Natural sounds','nature'),
 ('Music','musique'),
 ('Onomatopoeia','onomatopees'),
 ('Noise','bruit_ambiance'),
 ('Acoustic environment','bruit_ambiance'),
 ('Silence','bruit_ambiance'),
 ('Other sourceless','bruit_ambiance'),
 ('Channel, environment and background','bruit_ambiance'),
]
name2id = {o['name']:o['id'] for o in onto}
rules = [(name2id[n], cat) for n,cat in RULES]

def categorie(c):
    anc = ancestors(c['mid']) | {c['mid']}
    for rid, cat in rules:
        if rid in anc: return cat
    return 'divers'

out=[]
for c in classes:
    o = by_id[c['mid']]
    out.append({
        'index': int(c['index']),
        'id': c['mid'],
        'nom': c['display_name'],
        'categorie': categorie(c),
        'chemin': first_chain(c['mid']),
        'parents': [by_id[p]['name'] for p in parent.get(c['mid'],[])],
        'enfants': [by_id[ch]['name'] for ch in o['child_ids']],
        'enfants_yamnet': [],  # rempli ci-dessous
        'abstrait': 'abstract' in o.get('restrictions',[]),
        'description_en': o.get('description',''),
    })
yam_names = {x['nom'] for x in out}
for x in out:
    x['enfants_yamnet'] = [n for n in x['enfants'] if n in yam_names]
json.dump(out, open('skeleton.json','w'), ensure_ascii=False, indent=1)

from collections import defaultdict
g=defaultdict(list)
for x in out: g[x['categorie']].append(x)
for cat, items in g.items():
    print(f"\n## {cat} ({len(items)})")
    print("; ".join(f"{i['index']}:{i['nom']}" for i in items))
