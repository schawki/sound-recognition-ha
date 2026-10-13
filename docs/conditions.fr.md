# Conditions sur des états de Home Assistant

Une source ou un son peut **n'écouter que si une condition est vraie** : « seulement quand personne n'est à la maison », « seulement quand l'alarme est désarmée », « pas quand j'ai des invités ». La condition s'ajoute à l'[horaire](source-settings.fr.md) : un son est entendu quand son horaire l'autorise **et** que sa condition est vraie.

## La régler

- **Pour toute une source :** *Sources → Modifier*, encadré *Condition* sous les heures d'écoute.
- **Pour un son :** *Sons → réglages du son*, encadré *Condition* sous l'horaire. Au niveau *toutes les sources*, elle vaut pour chaque source qui n'a pas la sienne ; avec une source choisie, elle vaut pour cette source seulement.

La plus précise l'emporte, comme pour l'horaire : le son sur une source, puis le son, puis la source, puis les valeurs par défaut. Rien n'est réglé par défaut.

Cochez **N'écouter que si une condition est vraie** puis composez les règles :

- **L'état d'une entité** : choisissez l'entité et dites qu'elle **est** ou **n'est pas** dans un état (`home`, `on`, `disarmed`… le panneau propose les états usuels de l'entité).
- **Personne n'est à la maison** / **Quelqu'un est à la maison** : un raccourci sur toutes les entités `person` de Home Assistant. *Personne n'est à la maison* est vrai quand aucune personne n'est `home`.
- Avec plusieurs règles, choisissez si **toutes** les règles ou **au moins une** doivent être vraies.

## Quand un état n'est pas connu

Un état est inconnu pendant le redémarrage de Home Assistant, quand une entité a été supprimée ou renommée, ou quand la liaison entre Home Assistant et le service est coupée (les états sont envoyés avec une courte durée de vie : le service ne garde pas une réponse périmée). Une personne dont l'état est `unknown` ou `unavailable` compte aussi comme inconnue, sauf si l'état d'une autre personne tranche déjà (quelqu'un est `home` : « personne n'est à la maison » est faux).

Pour chaque condition, vous choisissez ce qui se passe alors :

- **Écouter quand même** (par défaut, recommandé) : une alarme manquée est pire qu'une détection de trop.
- **Rester en pause** : pour une condition qui protège la vie privée plus que la sécurité.

L'onglet *En direct* indique quand un son est en pause à cause de sa condition et quand un état est inconnu.

## Sons de sécurité

Les sons d'incendie, de sécurité et de bébé peuvent recevoir une condition, mais ils ne sont alors **pas entendus tant qu'elle n'est pas vraie**. Le panneau vous en avertit à chaque fois. Pour garder un détecteur de fumée actif sur une source dont la condition met les autres sons en pause, ouvrez les réglages de ce son et choisissez **Aucune condition** : il est alors entendu dès que son horaire l'autorise (dans le fichier : `condition: null` sur le son).

## Comment ça marche

Le service ne lit pas Home Assistant. L'intégration trouve les entités qu'utilisent les conditions, envoie leurs états (tout de suite à chaque changement, et toutes les 30 secondes) et le service décide. Avec un service plus ancien que le niveau d'API 12, l'intégration ignore les conditions et le signale une fois dans le journal : mettez le service à jour depuis Home Assistant.

Dans le fichier de configuration :

```yaml
sources:
  - id: kitchen
    condition:
      match: all              # all | any
      if_unknown: listen      # listen | pause
      rules:
        - people: nobody_home                                  # nobody_home | someone_home
        - {entity: alarm_control_panel.home, op: is, value: disarmed}   # op: is | is_not
```
