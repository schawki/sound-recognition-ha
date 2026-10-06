# Réglages par source : spécification

État : conception, validée par un résolveur de référence (`tools/resolve.py`) et ses tests (`tools/test_resolve.py`). Exemple : `examples/config.example.yaml`.

## 1. Principes

- Un seul fichier YAML fait foi ; l'interface de Home Assistant lit et écrit la même structure.
- Chaque paramètre se règle à quatre niveaux. Le niveau le plus précis l'emporte, et l'interface montre **d'où vient chaque valeur** (sa provenance).
- Rien n'est figé : seuil, volume minimum, plages horaires et conservation des clips se règlent par source, par classe, et par source × classe.
- **La surveillance continue est explicite et c'est le défaut** (`schedule: {mode: continuous}`). Un planning ne restreint l'écoute que si vous le demandez.

## 2. Ordre de résolution

Du plus fort au plus faible : **source × classe** > **classe (utilisateur)** > **source** > **valeurs par défaut** > **suggestion du catalogue**.

| Paramètre | Résolution |
|---|---|
| `enabled` | Une source désactivée désactive tout. Sinon source × classe, puis classe, puis désactivé. |
| `threshold` | La valeur source × classe est **absolue** (le décalage de la source est ignoré). Sinon valeur de la classe (ou suggestion du catalogue) **plus le `threshold_offset` de la source**, bornée entre 0,05 et 0,99. |
| `min_duration_s`, `cooldown_s`, `pre_roll_s`, `post_roll_s` | Source × classe, puis classe, puis suggestion du catalogue. |
| `min_volume_dbfs` | Une valeur explicite source × classe l'emporte. Sinon **la plus stricte (la plus haute)** entre le seuil de la classe et celui de la source ou des défauts. |
| `schedule` | Source × classe, puis classe, puis source, puis défauts, puis continu. |
| `clip_retention_days` | Source × classe, puis classe, puis `clips.retention_by_category` de la source, puis `defaults.clips.retention_by_category` global, puis catalogue (0 pour les conversations) ; **plafonnée** par `max_retention_days` de la source et global ; forcée à 0 si la source a `clips.allowed: false`. |

## 3. Seuil de volume minimum

- Mesuré comme le niveau RMS de la fenêtre d'analyse (0,96 s) en dBFS, avant le classifieur. Plage de −90 à 0 ; `null` désactive le seuil.
- Si la fenêtre est sous le seuil de **toutes** les classes activées sur la source, l'inférence est sautée (économie de CPU) et la source signale `below_gate`. Si au moins une classe activée a un seuil plus bas, l'inférence tourne et chaque classe est ensuite filtrée par son propre seuil.
- Le niveau dépend du gain du micro : le réglage au niveau de la source est donc l'endroit naturel pour calibrer. Un seuil de classe se combine avec lui selon « le plus strict gagne », sauf si vous fixez une valeur explicite source × classe.
- Aide prévue : mesurer le niveau ambiant d'une source pendant quelques heures et suggérer un seuil (par exemple le 90e centile des périodes calmes plus une marge).

## 4. Plages horaires et surveillance continue

```yaml
schedule: {mode: continuous}          # écoute 24 h/24 (défaut)
schedule:
  mode: scheduled
  windows:
    - {days: [mon, tue, wed, thu, fri], from: "07:00", to: "23:00"}
    - {days: [fri], from: "22:00", to: "06:00"}   # passe minuit : appartient au jour de départ
```

- Les heures suivent le fuseau horaire de Home Assistant. Plusieurs plages s'additionnent (union). `days` omis = tous les jours.
- Une classe peut avoir son propre planning. C'est ainsi qu'un détecteur de fumée reste **actif 24 h/24 sur une source par ailleurs planifiée**.
- Réservé pour plus tard : conditions sur des états de Home Assistant (par exemple « seulement quand la maison est vide »).

## 5. Clips par source

`clips.allowed: false` signifie qu'aucun son n'est jamais enregistré depuis cette source (par exemple une chambre d'enfant). `clips.max_retention_days` plafonne toutes les classes de la source. 
`clips.retention_by_category` (sur une source, ou dans `defaults.clips` pour toutes) fixe le nombre de jours de conservation des clips de chaque type de son : `normal`, `sensitive` (confidentialité « sensible » dans le catalogue), `context` (musique, télévision… les sons qui ne font que relever les seuils) et `confidential` (conversations). Un nombre de jours (0 = pas de clip), ou rien pour garder la suggestion du catalogue. La valeur de la source l'emporte sur la valeur globale, et un réglage sur un son précis l'emporte sur les deux. Garder les clips quelques jours (7, par exemple) permet de vérifier si les détections étaient bonnes : les fichiers s'effacent ensuite tout seuls, les détections restent dans l'historique.

**Conversations.** Le catalogue les met à 0 jour par défaut : rien n'est enregistré sans que vous le décidiez. Vous pouvez le décider, sur une source ou partout. Les clips de conversations peuvent contenir des paroles privées, et l'enregistrement de conversations peut être encadré par la loi et exiger l'accord des personnes enregistrées. Le panneau et les avertissements le rappellent à chaque fois ; gardez une durée courte et informez les personnes concernées.

## Juger les détections

Dans *En direct* et *Clips*, une détection qui a un clip peut être marquée **La détection est bonne** ou **La détection n'est pas bonne** (avec, si vous voulez, un seuil relevé pour ce son sur cette source). Sans clip, rien ne peut être vérifié : le contrôle n'est pas proposé. L'*Aperçu* montre les détections confirmées et la part de bonnes détections parmi celles que vous avez jugées. *Clips* peut filtrer sur l'avis, et peut effacer les détections qui n'ont ni clip ni avis (celles marquées ou confirmées restent).

## 6. Avertissements ajoutés pour ces réglages

Une *classe de sécurité* est une classe recommandée comme alerte (`interest: monitor`) dont l'usage principal est `fire`, `security` ou `baby`.

| Règle | Niveau | Déclencheur |
|---|---|---|
| `schedule_gap_safety` | attention | Le planning de la source a des trous et une classe de sécurité n'a pas de planning propre. |
| `volume_gate_safety` | attention | Le volume minimum effectif dépasse −40 dBFS sur une classe de sécurité. |
| `clip_source_disallowed` | info | Les clips sont désactivés sur la source alors que la classe en conserverait. |

Les textes sont dans `catalog/i18n/*.yaml` (`auto_rules`) ; l'interface regroupe les avertissements identiques entre classes.

## 7. À vérifier à l'implémentation

- Comment chaque type de source expose un audio continu (ESPHome n'a pas de flux standard ; go2rtc et RTSP sont simples).
- Si le seuil de volume doit utiliser le RMS ou une mesure de sonie à court terme sur de vrais micros.
- Si Home Assistant retraduit les noms d'entités dynamiques quand la langue de l'utilisateur change (sinon les noms suivent la langue du serveur et seul le panneau suit l'utilisateur).
