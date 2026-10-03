# -*- coding: utf-8 -*-
"""Assemble le catalogue final (YAML + JSON) à partir de :
 - yamnet_class_map.csv  : les 521 classes officielles, avec leur index
 - ontology.json         : hiérarchie AudioSet (parents/enfants), source des avertissements « certains »
 - fr_names_*.txt        : noms français (jugement)
 - ann_a/ann_b/ann_c.py  : annotations de jugement, groupes proches, règles de combinaison
"""
import csv, json, sys
from collections import defaultdict

sys.path.insert(0, '.')
import ann_a, ann_b, ann_c

classes = list(csv.DictReader(open('yamnet_class_map.csv', encoding='utf-8')))
names = [c['display_name'] for c in classes]
name_set = set(names)
skeleton = {s['nom']: s for s in json.load(open('skeleton.json', encoding='utf-8'))}
onto = json.load(open('ontology.json', encoding='utf-8'))
by_id = {o['id']: o for o in onto}

# --- noms français
fr = {}
for f in ('fr_names_1.txt', 'fr_names_2.txt'):
    for line in open(f, encoding='utf-8'):
        line = line.rstrip('\n')
        if line:
            en, f_ = line.split('|', 1)
            fr[en] = f_
assert set(fr) == name_set, "noms français incomplets"

# --- hiérarchie complète, limitée aux classes YAMNet
children = {o['id']: list(o['child_ids']) for o in onto}
parents_of = defaultdict(list)
for pid, chs in children.items():
    for ch in chs:
        parents_of[ch].append(pid)
mid_to_name = {c['mid']: c['display_name'] for c in classes}

def closure(start, graph):
    seen, stack = set(), list(graph.get(start, []))
    while stack:
        x = stack.pop()
        if x not in seen:
            seen.add(x)
            stack.extend(graph.get(x, []))
    return seen

# --- catégories (index → catégorie, corrigées par rapport à l'ontologie brute)
CAT_OVERRIDE_RANGES = [(61, 66, 'foule'), (518, 520, 'reproduction')]
def categorie(idx, base):
    for a, b, c in CAT_OVERRIDE_RANGES:
        if a <= idx <= b:
            return c
    return base

CAT_DEF = dict(ann_a.CAT_DEF)
CAT_DEF.update(ann_b.CAT_DEF_B)

# --- overrides
OV = {}
for src in (ann_a.OV, ann_b.OV):
    for k, v in src.items():
        assert k in name_set, f"override pour une classe inconnue : {k}"
        assert k not in OV, f"override en double : {k}"
        OV[k] = v

# --- groupes
groupes_par_classe = defaultdict(list)
for gid, nom, membres, risque, conseil in ann_c.GROUPES:
    for m in membres:
        assert m in name_set, f"groupe {gid} : classe inconnue {m}"
        groupes_par_classe[m].append(gid)

for r in ann_c.REGLES:
    for m in r['classes']:
        assert m in name_set, f"règle {r['id']} : classe inconnue {m}"

out = []
for c in classes:
    nom, mid, idx = c['display_name'], c['mid'], int(c['index'])
    sk = skeleton[nom]
    cat = categorie(idx, sk['categorie'])
    d = dict(CAT_DEF[cat])
    ov = OV.get(nom, {})
    # l'override peut utiliser les noms courts de o() ; on les traduit
    mapping = {'interet': 'interet', 'role': 'role', 'type_son': 'type_son', 'fp_niveau': 'fp_niveau',
               'vie_privee': 'vie_privee', 'seuil': 'seuil', 'jours': 'jours'}
    for k, v in ov.items():
        if k in mapping:
            d[mapping[k]] = v
    fp_causes = ov.get('fp_causes', [])
    usages = ov.get('usages', [])
    note = ov.get('note')
    ctx = ov.get('ctx', [])
    for x in ctx:
        assert x in name_set, f"contexte inconnu {x} pour {nom}"

    # règles de cohérence
    jours = d['jours']
    if d['vie_privee'] == 'confidentielle' or d['interet'] in ('ignorer', 'contexte'):
        jours = 0
    clip_interdit = d['vie_privee'] == 'confidentielle'

    anc = sorted(mid_to_name[a] for a in closure(mid, parents_of) if a in mid_to_name)
    desc = sorted(mid_to_name[a] for a in closure(mid, children) if a in mid_to_name)
    tp = ann_c.TYPE_PARAMS[d['type_son']]

    entry = {
        'index': idx,
        'id': mid,
        'nom': nom,
        'nom_fr': fr[nom],
        'categorie': cat,
        'chemin_audioset': sk['chemin'],
        'parents': sk['parents'],
        'ancetres_yamnet': anc,
        'descendants_yamnet': desc,
        'role': d['role'],
        'interet': d['interet'],
        'type_son': d['type_son'],
        'faux_positifs': {'niveau': d['fp_niveau'], 'causes': fp_causes},
        'vie_privee': d['vie_privee'],
        'clip_interdit': clip_interdit,
        'suggestions': {
            'seuil': d['seuil'],
            'duree_min_s': tp['duree_min_s'],
            'rearmement_s': tp['rearmement_s'],
            'tampon_avant_s': tp['tampon_avant_s'],
            'tampon_apres_s': tp['tampon_apres_s'],
            'conservation_clip_jours': jours,
        },
        'contextes_inhibiteurs': ctx,
        'usages': usages,
        'groupes': groupes_par_classe.get(nom, []),
        'note': note,
    }
    out.append(entry)

META = {
    'catalogue': "Catalogue des classes de sons (YAMNet / AudioSet) pour l'intégration de reconnaissance de sons",
    'version_schema': 1,
    'modele': "YAMNet (521 classes)",
    'nb_classes': len(out),
    'avertissement': (
        "Les champs interet, faux_positifs, seuil, duree_min_s, rearmement_s, tampon_*, conservation_clip_jours, "
        "usages, groupes, role et note sont des SUGGESTIONS DE DÉPART issues d'un jugement général sur ces sons ; "
        "rien n'a été mesuré dans une maison réelle. Les scores de YAMNet ne sont pas des probabilités calibrées : "
        "ajustez les seuils sur vos propres enregistrements. "
        "Les champs parents, ancetres_yamnet et descendants_yamnet viennent directement de l'ontologie AudioSet et sont fiables."),
    'sources': [
        "https://github.com/tensorflow/models/tree/master/research/audioset/yamnet (yamnet_class_map.csv)",
        "https://github.com/audioset/ontology (ontology.json)",
    ],
    'legende': {
        'interet': {
            'surveiller': "classe recommandée comme alerte pour une maison",
            'optionnel': "classe utile selon votre situation ; à activer en connaissance de cause",
            'contexte': "ne sert pas d'alerte : sert à relever les seuils des autres classes (télévision, musique, parole…)",
            'ignorer': "peu utile ou trop peu fiable pour une maison ; désactivée par défaut",
        },
        'role': {
            'evenement': "un événement que l'on peut signaler",
            'contexte': "décrit l'ambiance (télévision, foule, vent…) plutôt qu'un événement",
            'diagnostic': "indique l'état du micro (ronflement du secteur, vent, distorsion…)",
            'generique': "classe parente large : choisir plutôt ses sous-classes",
        },
        'type_son': {
            'impulsif': "bref (verre qui casse, coup à la porte)",
            'repete': "se répète (pleurs, pas, bips)",
            'tonal': "ton soutenu (sirène, détecteur de fumée, sonnette)",
            'continu': "dure longtemps (eau qui coule, moteur, pluie)",
            'variable': "durée très variable",
        },
        'suggestions': {
            'seuil': "score minimum (0 à 1) à partir duquel la détection compte ; à ajuster, les scores de YAMNet ne sont pas calibrés",
            'duree_min_s': "durée minimale de détection soutenue avant de signaler",
            'rearmement_s': "délai avant de pouvoir signaler à nouveau le même son",
            'tampon_avant_s': "secondes d'audio conservées avant le déclenchement dans un clip",
            'tampon_apres_s': "secondes d'audio conservées après le déclenchement",
            'conservation_clip_jours': "durée de conservation des clips ; 0 = aucun clip",
        },
        'faux_positifs.niveau': {'faible': "rarement déclenchée à tort", 'moyen': "parfois", 'eleve': "souvent (télévision, voisinage…)"},
        'vie_privee': {
            'normale': "pas de souci particulier",
            'sensible': "peut révéler des informations personnelles ; clips à garder très courts",
            'confidentielle': "conversations : aucun clip ne doit être conservé (clip_interdit = true)",
        },
    },
}

catalogue = {
    'meta': META,
    'categories': ann_c.CATEGORIES_FR,
    'groupes': [dict(id=g[0], nom=g[1], membres=g[2], risque=g[3], conseil=g[4]) for g in ann_c.GROUPES],
    'regles_combinaison': ann_c.REGLES,
    'regles_automatiques': ann_c.REGLES_AUTOMATIQUES,
    'classes': out,
}

json.dump(catalogue, open('catalogue_sons.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

import yaml
class D(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True
yaml.dump(catalogue, open('catalogue_sons.yaml', 'w', encoding='utf-8'), Dumper=D,
          allow_unicode=True, sort_keys=False, width=110, default_flow_style=None)
print("ok :", len(out), "classes")
