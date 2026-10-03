# -*- coding: utf-8 -*-
"""Génère catalog.<lang>.md. Usage : python tools/make_doc.py <catalog_dir> <lang> <out.md>"""
import sys
from collections import defaultdict, Counter
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from merge import load

S = {
'en': dict(
 title="Sound class catalog (YAMNet)", h_sure="What is certain and what is a judgment",
 intro="This document is the readable version of `catalog.yaml`. It describes the 521 sound classes recognised by YAMNet, with a name, a ranking and suggested settings for each.",
 sure="- **Certain (official data)**: the list of the 521 classes, their number, their English names and the parent/child hierarchy (for example “Bark” is part of “Dog”). They come from YAMNet's `yamnet_class_map.csv` and the AudioSet ontology.",
 judg="- **Judgment (starting suggestions)**: interest for a home, false-alert risk, privacy sensitivity, thresholds, durations, clip retention, groups of close classes and warning rules. They rely on general knowledge of these sounds, **nothing has been measured in a real home**. YAMNet scores are not calibrated probabilities: tune thresholds with your own recordings.",
 h_brief="At a glance",
 brief="Out of 521 classes, **{m}** are recommended as alerts, **{o}** are optional depending on your situation, **{c}** serve as context or diagnostics, and **{i}** are ignored by default (including {mu} music, instrument and genre classes).",
 h_read="How to read the fields",
 read=["**Interest**: *Monitor* = recommended as an alert; *Optional* = depends on your situation; *Context* = not an alert but lets you raise the thresholds of other classes; *Ignore* = disabled by default.",
       "**False positives**: how often the class triggers by mistake (television, neighbours, appliances…).",
       "**Privacy**: *confidential* = conversations, no clip may be kept; *sensitive* = may reveal personal information.",
       "**Threshold, min. duration, cooldown**: score threshold (0 to 1), sustained detection time before reporting, delay before a new report.",
       "**Retention**: how long audio clips are kept (0 = no clip)."],
 h1="1. Classes to monitor first", p1="These are the most useful classes as alerts. Even these will produce false alerts: the “False positives” field says which ones and why.",
 cat_="Category", stype="sound type", fp="False positives", causes="causes", sugg="Suggestions", thr="threshold", dur="sustained detection of at least {x} s", cool="cooldown {x} s",
 clip="clip from {a} s before to {b} s after, kept {d} days", partof="Part of", contains="Contains", ctxraise="Contexts that should raise the threshold",
 h2="2. Optional classes, by usage", p2="Useful depending on your situation (animals, baby, kitchen, leaks…). They stay disabled until you enable them.",
 col_class="Class", col_fp="False positives", col_priv="Privacy", col_thr="Threshold", col_note="Note",
 h3="3. Context and diagnostic classes", p3="They are not alerts. **Context** classes (television, music, speech, rain…) let you raise the thresholds of classes prone to false alerts. **Diagnostic** classes indicate a microphone problem (mains hum, wind, distortion).",
 h3a="Context", h3b="Microphone diagnostics",
 h4="4. Groups of close classes", p4="Classes that sound alike or overlap. The integration shows these warnings when you select several classes of the same group.",
 classes_="Classes", risk="Risk", advice="Advice",
 h5="5. Warning rules", h5a="Rules on specific combinations", col_level="Level", col_classes="Classes concerned", col_msg="Warning", col_match="Applies when",
 h5b="Rules applied automatically", p5b="They are deduced from each class's fields, without a list to maintain.",
 h6="6. All classes by category", p6="Each line gives the YAMNet number, the exact model name, the display name, the interest, the false-positive risk and the privacy sensitivity.",
 col_n="No.", col_model="Class (model)", col_name="Name", col_int="Interest", col_fp2="False pos.", h_src="Sources",
 match={'all': "all selected", 'at_least_two': "at least two selected", 'any': "any one selected"},
 interest={'monitor': "Monitor", 'optional': "Optional", 'context': "Context", 'ignore': "Ignored"},
 fpl={'low': "low", 'medium': "medium", 'high': "high"}, priv={'normal': "normal", 'sensitive': "sensitive", 'confidential': "confidential"},
 stypes={'impulsive': "short", 'repeated': "repeated", 'tonal': "sustained tone", 'continuous': "continuous", 'variable': "variable"},
 level={'info': "info", 'warning': "warning", 'danger': "danger"}),
'fr': dict(
 title="Catalogue des classes de sons (YAMNet)", h_sure="Ce qui est sûr et ce qui est un jugement",
 intro="Ce document est la version lisible du fichier `catalog.yaml`. Il décrit les 521 classes de sons que reconnaît YAMNet, avec pour chacune un nom, un classement et des suggestions de réglage.",
 sure="- **Sûr (données officielles)** : la liste des 521 classes, leur numéro, leurs noms anglais et la hiérarchie parent/enfant (par exemple « Aboiement » fait partie de « Chien »). Elles viennent du fichier `yamnet_class_map.csv` de YAMNet et de l'ontologie AudioSet.",
 judg="- **Jugement (suggestions de départ)** : l'intérêt pour une maison, le risque de fausses alertes, la sensibilité pour la vie privée, les seuils, les durées, la conservation des clips, les groupes de classes proches et les règles d'avertissement. Ils reposent sur une connaissance générale de ces sons, **rien n'a été mesuré dans une maison réelle**. Les scores de YAMNet ne sont pas des probabilités calibrées : les seuils sont à ajuster avec vos propres enregistrements.",
 h_brief="En bref",
 brief="Sur 521 classes, **{m}** sont recommandées comme alertes, **{o}** sont optionnelles selon votre situation, **{c}** servent de contexte ou de diagnostic, et **{i}** sont ignorées par défaut (dont {mu} classes de musique, d'instruments et de genres).",
 h_read="Comment lire les champs",
 read=["**Intérêt** : *À surveiller* = recommandée comme alerte ; *Optionnelle* = selon votre situation ; *Contexte* = ne sert pas d'alerte mais permet de relever les seuils des autres classes ; *Ignorée* = désactivée par défaut.",
       "**Faux positifs** : fréquence à laquelle la classe se déclenche à tort (télévision, voisinage, appareils…).",
       "**Vie privée** : *confidentielle* = conversations, aucun clip ne doit être conservé ; *sensible* = peut révéler des informations personnelles.",
       "**Seuil, durée min., ré-armement** : seuil de score (0 à 1), durée de détection soutenue avant de signaler, délai avant un nouveau signalement.",
       "**Conservation** : durée de conservation des clips audio (0 = aucun clip)."],
 h1="1. Les classes à surveiller en priorité", p1="Ce sont les classes les plus utiles comme alertes. Même celles-ci produiront des fausses alertes : le champ « Faux positifs » dit lesquelles et pourquoi.",
 cat_="Catégorie", stype="type de son", fp="Faux positifs", causes="causes", sugg="Suggestions", thr="seuil", dur="détection soutenue d'au moins {x} s", cool="ré-armement {x} s",
 clip="clip de {a} s avant à {b} s après, conservé {d} jours", partof="Fait partie de", contains="Contient", ctxraise="Contextes qui devraient relever le seuil",
 h2="2. Classes optionnelles, par usage", p2="Utiles selon votre situation (animaux, bébé, cuisine, fuites…). Elles sont désactivées tant que vous ne les activez pas.",
 col_class="Classe", col_fp="Faux positifs", col_priv="Vie privée", col_thr="Seuil", col_note="Remarque",
 h3="3. Classes de contexte et de diagnostic", p3="Elles ne servent pas d'alerte. Les classes de **contexte** (télévision, musique, parole, pluie…) permettent de relever les seuils des classes sensibles aux fausses alertes. Les classes de **diagnostic** indiquent un problème de micro (ronflement du secteur, vent, distorsion).",
 h3a="Contexte", h3b="Diagnostic du micro",
 h4="4. Groupes de classes proches", p4="Des classes qui se ressemblent ou se recouvrent. L'intégration affichera ces avertissements quand vous en sélectionnerez plusieurs d'un même groupe.",
 classes_="Classes", risk="Risque", advice="Conseil",
 h5="5. Règles d'avertissement", h5a="Règles sur des combinaisons précises", col_level="Niveau", col_classes="Classes concernées", col_msg="Avertissement", col_match="S'applique si",
 h5b="Règles appliquées automatiquement", p5b="Elles se déduisent des champs de chaque classe, sans liste à maintenir.",
 h6="6. Toutes les classes par catégorie", p6="Chaque ligne donne le numéro YAMNet, le nom exact du modèle, le nom affiché, l'intérêt, le risque de faux positifs et la sensibilité pour la vie privée.",
 col_n="N°", col_model="Classe (modèle)", col_name="Nom", col_int="Intérêt", col_fp2="Faux pos.", h_src="Sources",
 match={'all': "toutes sélectionnées", 'at_least_two': "au moins deux sélectionnées", 'any': "une seule suffit"},
 interest={'monitor': "À surveiller", 'optional': "Optionnelle", 'context': "Contexte", 'ignore': "Ignorée"},
 fpl={'low': "faible", 'medium': "moyen", 'high': "élevé"}, priv={'normal': "normale", 'sensitive': "sensible", 'confidential': "confidentielle"},
 stypes={'impulsive': "bref", 'repeated': "répété", 'tonal': "ton soutenu", 'continuous': "continu", 'variable': "variable"},
 level={'info': "info", 'warning': "attention", 'danger': "danger"}),
}

def build(root, lang):
    s = S[lang]; d = load(root, lang); cl = d['classes']; by = {c['mid']: c for c in cl}
    esc = lambda t: (t or '').replace('|', '\\|').replace('\n', ' ')
    nm = lambda m: by[m]['name']
    full = lambda c: c['name'] if c['name'] == c['audioset_name'] else f"{c['name']} ({c['audioset_name']})"
    L = []; w = L.append
    w(f"# {s['title']}\n"); w(s['intro'] + "\n"); w(f"## {s['h_sure']}\n"); w(s['sure']); w(s['judg'] + "\n")
    n = Counter(c['interest'] for c in cl)
    mu = sum(1 for c in cl if c['category'] == 'music' and c['interest'] == 'ignore')
    w(f"## {s['h_brief']}\n"); w(s['brief'].format(m=n['monitor'], o=n['optional'], c=n['context'], i=n['ignore'], mu=mu) + "\n")
    w(f"### {s['h_read']}\n"); [w('- ' + x) for x in s['read']]; w("")
    w(f"## {s['h1']}\n"); w(s['p1'] + "\n")
    for c in sorted([c for c in cl if c['interest'] == 'monitor'], key=lambda x: (-x['suggestions']['clip_retention_days'], x['yamnet_index'])):
        g = c['suggestions']; fp = c['false_positives']
        w(f"### {c['name']} — `{c['audioset_name']}` ({s['col_n']} {c['yamnet_index']})\n")
        w(f"- {s['cat_']}: {d['categories'][c['category']]} · {s['stype']}: {s['stypes'][c['sound_type']]}")
        w(f"- {s['fp']}: **{s['fpl'][fp['level']]}**" + (f" ({s['causes']}: {', '.join(fp['cause_labels'])})" if fp['cause_labels'] else ""))
        w(f"- {s['sugg']}: {s['thr']} {g['threshold']}, " + s['dur'].format(x=g['min_duration_s']) + ", " + s['cool'].format(x=g['cooldown_s']) + ", "
          + s['clip'].format(a=g['pre_roll_s'], b=g['post_roll_s'], d=g['clip_retention_days']))
        if c['ancestors']: w(f"- {s['partof']}: {', '.join(nm(a) for a in c['ancestors'])}")
        if c['descendants']: w(f"- {s['contains']}: {', '.join(nm(a) for a in c['descendants'])}")
        if c['inhibiting_contexts']: w(f"- {s['ctxraise']}: {', '.join(nm(a) for a in c['inhibiting_contexts'])}")
        if c['note_text']: w(f"- {c['note_text']}")
        w("")
    w(f"## {s['h2']}\n"); w(s['p2'] + "\n")
    by_use = defaultdict(list)
    for c in cl:
        if c['interest'] == 'optional': by_use[c['usages'][0] if c['usages'] else 'other'].append(c)
    order = ['security', 'fire', 'door', 'baby', 'animals', 'leaks', 'kitchen', 'presence', 'voiceless_command', 'outdoor', 'weather', 'garage', 'pests', 'comfort']
    for u in order + [k for k in by_use if k not in order]:
        if u not in by_use: continue
        w(f"### {d['usages'][u]}\n"); w(f"| {s['col_class']} | {s['col_fp']} | {s['col_priv']} | {s['col_thr']} | {s['col_note']} |"); w("|---|---|---|---|---|")
        for c in sorted(by_use[u], key=lambda x: x['yamnet_index']):
            w(f"| {esc(full(c))} | {s['fpl'][c['false_positives']['level']]} | {s['priv'][c['privacy']]} | {c['suggestions']['threshold']} | {esc(c['note_text'])} |")
        w("")
    w(f"## {s['h3']}\n"); w(s['p3'] + "\n")
    for roles, title in ((('context', 'event', 'generic'), s['h3a']), (('diagnostic',), s['h3b'])):
        w(f"### {title}\n"); w(f"| {s['col_class']} | {s['col_priv']} | {s['col_note']} |"); w("|---|---|---|")
        for c in sorted([c for c in cl if c['interest'] == 'context' and c['role'] in roles], key=lambda x: x['yamnet_index']):
            w(f"| {esc(full(c))} | {s['priv'][c['privacy']]} | {esc(c['note_text'])} |")
        w("")
    w(f"## {s['h4']}\n"); w(s['p4'] + "\n")
    for g in d['groups']:
        w(f"### {g['name']}\n"); w(f"{s['classes_']}: " + ", ".join(nm(m) for m in g['members']) + "\n")
        w(f"- **{s['risk']}**: {g['risk']}"); w(f"- **{s['advice']}**: {g['advice']}\n")
    w(f"## {s['h5']}\n"); w(f"### {s['h5a']}\n"); w(f"| {s['col_level']} | {s['col_classes']} | {s['col_match']} | {s['col_msg']} |"); w("|---|---|---|---|")
    for r in d['rules']:
        w(f"| {s['level'][r['level']]} | {esc(', '.join(nm(m) for m in r['classes']))} | {s['match'][r['match']]} | {esc(r['message'])} |")
    w(""); w(f"### {s['h5b']}\n"); w(s['p5b'] + "\n")
    for r in d['auto_rules']:
        w(f"- **{s['level'][r['level']]}** — *{r['condition']}*: {r['message']}")
    w(""); w(f"## {s['h6']}\n"); w(s['p6'] + "\n")
    by_cat = defaultdict(list)
    for c in cl: by_cat[c['category']].append(c)
    for k, title in d['categories'].items():
        if k not in by_cat: continue
        w(f"### {title} ({len(by_cat[k])})\n"); w(f"| {s['col_n']} | {s['col_model']} | {s['col_name']} | {s['col_int']} | {s['col_fp2']} | {s['col_priv']} |"); w("|---|---|---|---|---|---|")
        for c in sorted(by_cat[k], key=lambda x: x['yamnet_index']):
            w(f"| {c['yamnet_index']} | {esc(c['audioset_name'])} | {esc(c['name'])} | {s['interest'][c['interest']]} | {s['fpl'][c['false_positives']['level']]} | {s['priv'][c['privacy']]} |")
        w("")
    w(f"## {s['h_src']}\n"); [w(f"- {x}") for x in d['meta']['sources']]
    return "\n".join(L) + "\n"

if __name__ == '__main__':
    root, lang, dest = sys.argv[1:4]
    open(dest, 'w', encoding='utf-8').write(build(root, lang)); print('ok', dest)
