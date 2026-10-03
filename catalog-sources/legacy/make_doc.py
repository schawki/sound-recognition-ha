# -*- coding: utf-8 -*-
"""Génère catalogue_sons.md (document lisible) à partir de catalogue_sons.json."""
import json
from collections import defaultdict, Counter

cat = json.load(open('catalogue_sons.json', encoding='utf-8'))
cl = cat['classes']
names = {c['nom']: c for c in cl}
CATS = cat['categories']

INTERET = {'surveiller': "À surveiller", 'optionnel': "Optionnelle", 'contexte': "Contexte", 'ignorer': "Ignorée"}
FP = {'faible': "faible", 'moyen': "moyen", 'eleve': "élevé"}
VP = {'normale': "normale", 'sensible': "sensible", 'confidentielle': "confidentielle"}
TYPE = {'impulsif': "bref", 'repete': "répété", 'tonal': "ton soutenu", 'continu': "continu", 'variable': "variable"}
ROLE = {'evenement': "événement", 'contexte': "contexte", 'diagnostic': "diagnostic", 'generique': "classe parente"}
USAGES = {
    'securite': "Sécurité", 'incendie': "Incendie", 'porte': "Porte et visiteurs", 'bebe': "Bébé", 'animaux': "Animaux",
    'fuite': "Eau et fuites", 'cuisine': "Cuisine", 'presence': "Présence", 'commande': "Commande sans voix",
    'exterieur': "Extérieur", 'meteo': "Météo", 'garage': "Garage et voiture", 'nuisibles': "Nuisibles", 'confort': "Confort",
    'ambiance': "Ambiance", 'contexte': "Contexte", 'diagnostic': "Diagnostic du micro", 'autres': "Autres usages",
}

def fr(n):  # « Français (English) »
    c = names[n]
    return c['nom_fr'] if c['nom_fr'] == n else f"{c['nom_fr']} ({n})"

def esc(s):
    return (s or "").replace("|", "\\|").replace("\n", " ")

L = []
w = L.append

w("# Catalogue des classes de sons (YAMNet)\n")
w("Ce document est la version lisible du fichier `catalogue_sons.yaml`. Il décrit les 521 classes de sons que reconnaît YAMNet, "
  "avec pour chacune un nom français, un classement et des suggestions de réglage.\n")
w("## Ce qui est sûr et ce qui est un jugement\n")
w("- **Sûr (données officielles)** : la liste des 521 classes, leur numéro, leurs noms anglais et la hiérarchie parent/enfant "
  "(par exemple « Aboiement » fait partie de « Chien »). Elles viennent du fichier `yamnet_class_map.csv` de YAMNet et de l'ontologie AudioSet.")
w("- **Jugement (suggestions de départ)** : l'intérêt pour une maison, le risque de fausses alertes, la sensibilité pour la vie privée, "
  "les seuils, les durées, la conservation des clips, les groupes de classes proches et les règles d'avertissement. "
  "Ils reposent sur une connaissance générale de ces sons, **rien n'a été mesuré dans une maison réelle**. "
  "Les scores de YAMNet ne sont pas des probabilités calibrées : les seuils sont à ajuster avec vos propres enregistrements.\n")

n_int = Counter(c['interet'] for c in cl)
w("## En bref\n")
w(f"Sur 521 classes, **{n_int['surveiller']}** sont recommandées comme alertes, **{n_int['optionnel']}** sont optionnelles selon votre situation, "
  f"**{n_int['contexte']}** servent de contexte ou de diagnostic, et **{n_int['ignorer']}** sont ignorées par défaut "
  f"(dont {sum(1 for c in cl if c['categorie'] == 'musique' and c['interet'] == 'ignorer')} classes de musique, d'instruments et de genres).\n")

w("### Comment lire les champs\n")
w("- **Intérêt** : *À surveiller* = recommandée comme alerte ; *Optionnelle* = selon votre situation ; "
  "*Contexte* = ne sert pas d'alerte mais permet de relever les seuils des autres classes ; *Ignorée* = désactivée par défaut.")
w("- **Faux positifs** : fréquence à laquelle la classe se déclenche à tort (télévision, voisinage, appareils…).")
w("- **Vie privée** : *confidentielle* = conversations, aucun clip ne doit être conservé ; *sensible* = peut révéler des informations personnelles.")
w("- **Seuil, durée min., ré-armement** : seuil de score (0 à 1), durée de détection soutenue avant de signaler, délai avant un nouveau signalement.")
w("- **Conservation** : durée de conservation des clips audio (0 = aucun clip).\n")

# ------------------------------------------------------------------ 1. À surveiller
w("## 1. Les classes à surveiller en priorité\n")
w("Ce sont les classes les plus utiles comme alertes. Même celles-ci produiront des fausses alertes : le champ « Faux positifs » dit lesquelles et pourquoi.\n")
for c in sorted([c for c in cl if c['interet'] == 'surveiller'], key=lambda x: (-x['suggestions']['conservation_clip_jours'], x['index'])):
    s = c['suggestions']
    w(f"### {c['nom_fr']} — `{c['nom']}` (n° {c['index']})\n")
    w(f"- Catégorie : {CATS[c['categorie']]} · type de son : {TYPE[c['type_son']]}")
    w(f"- Faux positifs : **{FP[c['faux_positifs']['niveau']]}**" + (f" (causes : {', '.join(c['faux_positifs']['causes'])})" if c['faux_positifs']['causes'] else ""))
    w(f"- Suggestions : seuil {s['seuil']}, détection soutenue d'au moins {s['duree_min_s']} s, ré-armement {s['rearmement_s']} s, "
      f"clip de {s['tampon_avant_s']} s avant à {s['tampon_apres_s']} s après, conservé {s['conservation_clip_jours']} jours")
    if c['ancetres_yamnet']:
        w(f"- Fait partie de : {', '.join(names[a]['nom_fr'] for a in c['ancetres_yamnet'])}")
    if c['descendants_yamnet']:
        w(f"- Contient : {', '.join(names[d]['nom_fr'] for d in c['descendants_yamnet'])}")
    if c['contextes_inhibiteurs']:
        w(f"- Contextes qui devraient relever le seuil : {', '.join(names[x]['nom_fr'] for x in c['contextes_inhibiteurs'])}")
    if c['note']:
        w(f"- {c['note']}")
    w("")

# ------------------------------------------------------------------ 2. Optionnelles
w("## 2. Classes optionnelles, par usage\n")
w("Utiles selon votre situation (animaux, bébé, cuisine, fuites…). Elles sont désactivées tant que vous ne les activez pas.\n")
by_use = defaultdict(list)
for c in cl:
    if c['interet'] == 'optionnel':
        by_use[c['usages'][0] if c['usages'] else 'autres'].append(c)
order = ['securite', 'incendie', 'porte', 'bebe', 'animaux', 'fuite', 'cuisine', 'presence', 'commande', 'exterieur', 'meteo', 'garage', 'nuisibles', 'confort']
for u in order + [k for k in by_use if k not in order]:
    items = by_use.get(u)
    if not items:
        continue
    w(f"### {USAGES.get(u, u)}\n")
    w("| Classe | Faux positifs | Vie privée | Seuil | Remarque |")
    w("|---|---|---|---|---|")
    for c in sorted(items, key=lambda x: x['index']):
        w(f"| {esc(fr(c['nom']))} | {FP[c['faux_positifs']['niveau']]} | {VP[c['vie_privee']]} | {c['suggestions']['seuil']} | {esc(c['note'])} |")
    w("")

# ------------------------------------------------------------------ 3. Contexte et diagnostic
w("## 3. Classes de contexte et de diagnostic\n")
w("Elles ne servent pas d'alerte. Les classes de **contexte** (télévision, musique, parole, pluie…) permettent de relever les seuils des classes "
  "sensibles aux fausses alertes. Les classes de **diagnostic** indiquent un problème de micro (ronflement du secteur, vent, distorsion).\n")
for role, title in (('contexte', "Contexte"), ('diagnostic', "Diagnostic du micro")):
    items = [c for c in cl if c['interet'] == 'contexte' and c['role'] == role]
    if role == 'contexte':
        items = [c for c in cl if c['interet'] == 'contexte' and c['role'] in ('contexte', 'evenement', 'generique')]
    w(f"### {title}\n")
    w("| Classe | Vie privée | Remarque |")
    w("|---|---|---|")
    for c in sorted(items, key=lambda x: x['index']):
        w(f"| {esc(fr(c['nom']))} | {VP[c['vie_privee']]} | {esc(c['note'])} |")
    w("")

# ------------------------------------------------------------------ 4. Groupes proches
w("## 4. Groupes de classes proches\n")
w("Des classes qui se ressemblent ou se recouvrent. L'intégration affichera ces avertissements quand vous en sélectionnerez plusieurs d'un même groupe.\n")
for g in cat['groupes']:
    w(f"### {g['nom']}\n")
    w("Classes : " + ", ".join(names[m]['nom_fr'] for m in g['membres']) + "\n")
    w(f"- **Risque** : {g['risque']}")
    w(f"- **Conseil** : {g['conseil']}\n")

# ------------------------------------------------------------------ 5. Règles
w("## 5. Règles d'avertissement\n")
w("### Règles sur des combinaisons précises\n")
w("| Niveau | Classes concernées | Avertissement |")
w("|---|---|---|")
for r in cat['regles_combinaison']:
    w(f"| {r['niveau']} | {esc(', '.join(names[m]['nom_fr'] for m in r['classes']))} | {esc(r['message'])} |")
w("")
w("### Règles appliquées automatiquement\n")
w("Elles se déduisent des champs de chaque classe, sans liste à maintenir.\n")
for r in cat['regles_automatiques']:
    w(f"- **{r['niveau']}** — *{r['condition']}* : {r['message']}")
w("")

# ------------------------------------------------------------------ 6. Toutes les classes
w("## 6. Toutes les classes par catégorie\n")
w("Chaque ligne donne le numéro YAMNet, le nom anglais exact (celui du modèle), le nom français, l'intérêt, le risque de faux positifs et la sensibilité pour la vie privée.\n")
by_cat = defaultdict(list)
for c in cl:
    by_cat[c['categorie']].append(c)
for k, title in CATS.items():
    items = by_cat.get(k)
    if not items:
        continue
    w(f"### {title} ({len(items)})\n")
    w("| N° | Classe (modèle) | Français | Intérêt | Faux pos. | Vie privée |")
    w("|---|---|---|---|---|---|")
    for c in sorted(items, key=lambda x: x['index']):
        w(f"| {c['index']} | {esc(c['nom'])} | {esc(c['nom_fr'])} | {INTERET[c['interet']]} | {FP[c['faux_positifs']['niveau']]} | {VP[c['vie_privee']]} |")
    w("")

w("## Sources\n")
for s in cat['meta']['sources']:
    w(f"- {s}")

open('catalogue_sons.md', 'w', encoding='utf-8').write("\n".join(L) + "\n")
print("ok", len(L), "lignes")
