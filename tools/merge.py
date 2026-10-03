# -*- coding: utf-8 -*-
"""Fusionne le catalogue neutre et un fichier de langue.
   load(root, lang) -> dict prêt à servir (API ?lang=fr|en). Repli : langue demandée -> en -> nom AudioSet officiel.
   CLI : python tools/merge.py <catalog_dir> <lang> <out.json>"""
import sys, json, yaml, os

def _y(p): return yaml.safe_load(open(p, encoding='utf-8'))

def load(root, lang):
    cat = _y(f'{root}/catalog.yaml')
    fb = _y(f'{root}/i18n/en.yaml')
    p = f'{root}/i18n/{lang}.yaml'
    L = _y(p) if os.path.exists(p) else {}
    def g(sec, key, default=None):
        return (L.get(sec) or {}).get(key) or (fb.get(sec) or {}).get(key) or default
    out = {'language': lang if L else 'en', 'meta': cat['meta'], 'enums': cat['enums']}
    out['categories'] = {k: g('categories', k, k) for k in cat['categories']}
    out['usages'] = {k: g('usages', k, k) for k in cat['usages']}
    out['causes'] = {k: g('causes', k, k) for k in cat['causes']}
    out['enum_help'] = {e: {v: ((L.get('enum_help') or fb['enum_help']).get(e, {}).get(v)) or fb['enum_help'][e][v] for v in vals}
                        for e, vals in cat['enums'].items() if e in fb['enum_help']}
    out['setting_help'] = {k: (L.get('setting_help') or {}).get(k) or v for k, v in fb['setting_help'].items()}
    by_mid = {c['mid']: c for c in cat['classes']}
    out['groups'] = [dict(id=x['id'], members=x['members'], **{k: g('groups', x['id'], {}).get(k) for k in ('name', 'risk', 'advice')}) for x in cat['groups']]
    out['rules'] = [dict(x, message=g('rules', x['id'])) for x in cat['rules']]
    out['auto_rules'] = [dict(x, **{k: g('auto_rules', x['id'], {}).get(k) for k in ('condition', 'message')}) for x in cat['auto_rules']]
    classes = []
    for c in cat['classes']:
        d = dict(c)
        d['name'] = g('classes', c['mid'], c['audioset_name'])
        d['note_text'] = g('notes', c['note']) if c['note'] else None
        d['false_positives'] = dict(c['false_positives'], cause_labels=[out['causes'][x] for x in c['false_positives']['causes']])
        classes.append(d)
    out['classes'] = classes
    return out

if __name__ == '__main__':
    root, lang, dest = sys.argv[1:4]
    json.dump(load(root, lang), open(dest, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', dest)
