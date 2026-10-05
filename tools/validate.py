# -*- coding: utf-8 -*-
"""Validation du catalogue neutre et des fichiers de langue. Usage : python tools/validate.py <catalog_dir>"""
import sys, re, json, yaml, glob, os
root = sys.argv[1] if len(sys.argv) > 1 else 'catalog'
cat = yaml.safe_load(open(f'{root}/catalog.yaml', encoding='utf-8'))
langs = {os.path.basename(p)[:-5]: yaml.safe_load(open(p, encoding='utf-8')) for p in glob.glob(f'{root}/i18n/*.yaml')}
errs = []
E = errs.append
enums = cat['enums']; mids = [c['mid'] for c in cat['classes']]; mset = set(mids)
note_ids = {c['note'] for c in cat['classes'] if c['note']}

# -------- structure neutre
assert len(cat['classes']) == cat['meta']['num_classes'] == 521
for c in cat['classes']:
    n = c['audioset_name']
    for f, e in (('interest', 'interest'), ('role', 'role'), ('sound_type', 'sound_type'), ('privacy', 'privacy')):
        if c[f] not in enums[e]: E(f'{n}: {f}={c[f]}')
    if c['false_positives']['level'] not in enums['false_positive_level']: E(f'{n}: fp level')
    if c['category'] not in cat['categories']: E(f'{n}: category')
    for u in c['usages']:
        if u not in cat['usages']: E(f'{n}: usage {u}')
    for g in c['groups']:
        if g not in {x['id'] for x in cat['groups']}: E(f'{n}: group {g}')
    for x in c['false_positives']['causes']:
        if x not in cat['causes']: E(f'{n}: cause {x}')
    for k in ('ancestors', 'descendants', 'inhibiting_contexts'):
        for m in c[k]:
            if m not in mset: E(f'{n}: {k} {m}')
    if c['clip_forbidden'] and c['suggestions']['clip_retention_days'] != 0: E(f'{n}: clip interdit mais rétention > 0')
    if c['privacy'] == 'confidential' and not c['clip_forbidden']: E(f'{n}: confidentielle sans clip_forbidden')
for g in cat['groups']:
    for m in g['members']:
        if m not in mset: E(f"group {g['id']}: {m}")
for r in cat['rules']:
    if r['match'] not in enums['rule_match'] or r['level'] not in enums['level']: E(f"rule {r['id']}")
    for m in r['classes']:
        if m not in mset: E(f"rule {r['id']}: {m}")
    fx = r.get('fix') or {}
    ch = r.get('choose')
    if ch is not None and (set(ch) - {'recommended'} or ch.get('recommended') not in r['classes']): E(f"rule {r['id']}: choose")
    if ch is not None and fx: E(f"rule {r['id']}: choose and fix are exclusive")
    for k in fx:
        if k not in ('enable', 'disable', 'set'): E(f"rule {r['id']}: fix key {k}")
    for m in list(fx.get('enable', [])) + list(fx.get('disable', [])) + list(fx.get('set', {})):
        if m not in mset: E(f"rule {r['id']}: fix {m}")
    for m, vals in (fx.get('set') or {}).items():
        for k in vals:
            if k not in ('min_duration_s', 'threshold', 'cooldown_s', 'clip_retention_days'): E(f"rule {r['id']}: fix field {k}")

# -------- langues
PH = re.compile(r'\{(\w+)\}')
ref = langs.get('en')
for code, L in langs.items():
    nm = L['classes']
    if set(nm) != mset: E(f'{code}: classes manquantes {len(mset ^ set(nm))}')
    if len(set(nm.values())) != len(nm): 
        dup = [v for v in set(nm.values()) if list(nm.values()).count(v) > 1]
        E(f'{code}: noms en double {dup}')
    for sec, ids in (('categories', cat['categories']), ('usages', cat['usages']), ('causes', cat['causes'])):
        pass
    for key, ids in (('categories', cat['categories']), ('usages', cat['usages']), ('causes', cat['causes'])):
        if set(L[key]) != set(ids): E(f'{code}.{key}: {set(L[key]) ^ set(ids)}')
    if set(L['notes']) != note_ids: E(f"{code}.notes: {set(L['notes']) ^ note_ids}")
    if set(L['groups']) != {g['id'] for g in cat['groups']}: E(f'{code}.groups')
    if set(L['rules']) != {r['id'] for r in cat['rules']}: E(f'{code}.rules')
    if set(L['auto_rules']) != {r['id'] for r in cat['auto_rules']}: E(f'{code}.auto_rules')
    for k, v in enums.items():
        if k in L['enum_help'] and set(L['enum_help'][k]) != set(v): E(f'{code}.enum_help.{k}')
    # placeholders identiques à la référence
    if ref is not code and ref:
        for sec in ('rules',):
            for k in L[sec]:
                if set(PH.findall(L[sec][k])) != set(PH.findall(ref[sec][k])): E(f'{code}.{sec}.{k} placeholders')
        for k in L['auto_rules']:
            if set(PH.findall(L['auto_rules'][k]['message'])) != set(PH.findall(ref['auto_rules'][k]['message'])): E(f'{code}.auto.{k} placeholders')
    # noms de classes cités = noms existants
    q = (r'“([^”]+)”') if code == 'en' else (r'«\s*([^»]+?)\s*»')
    ok = set(nm.values()) | {x.lower() for x in nm.values()}
    allowed = {g['name'] for g in L['groups'].values()} | {'someone is talking', "quelqu'un parle", 'music is playing', 'de la musique joue', 'quelqu’un parle'}
    def texts():
        for k, v in L['notes'].items(): yield f'notes.{k}', v
        for k, v in L['groups'].items(): yield f'groups.{k}.risk', v['risk']; yield f'groups.{k}.advice', v['advice']
        for k, v in L['rules'].items(): yield f'rules.{k}', v
    for where, t in texts():
        for name in re.findall(q, t):
            if name not in ok and name not in allowed and not PH.fullmatch(name):
                E(f'{code} {where}: nom cité inconnu « {name} »')
    # classes citées dans les placeholders du FR : exemple, parent...
print('Langues :', sorted(langs))
if errs:
    print('ERREURS :', len(errs)); [print(' -', e) for e in errs[:80]]; sys.exit(1)
print('ERREURS : aucune')
