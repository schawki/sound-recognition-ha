# L'onglet Conseils

Sound Recognition examine vos réglages et vous prévient quand quelque chose est risqué, redondant ou manquant : une alarme incendie coupée la nuit, deux sons qui se déclenchent ensemble, un son qui ressemble à un autre. Ce sont les **conseils**. Ils ne changent jamais rien tout seuls.

![Onglet Conseils](images/advice-fr-dark.png)

## Lire une carte

Chaque carte dit trois choses :

- **Pourquoi** : quel est le problème, en mots simples, pour quelle source et quels sons.
- **Ce que fait le bouton** : les réglages exacts qui seront modifiés.
- **Où on en est** : à faire, information, appliqué ou masqué.

La couleur et le badge donnent l'importance : *Information*, *Avertissement* ou *Danger*.

## Les quatre sections

| Section | Contenu |
|---|---|
| **À faire** | Les conseils avec un bouton qui les règle. |
| **Information** | Les conseils qui vous demandent d'agir (rien que le bouton puisse décider sans risque). |
| **Appliqués** | Ce que vous avez déjà appliqué, avec ce que cela a changé et quand. |
| **Masqués** | Les conseils que vous avez choisi de ne pas voir. Ils restent listés pour pouvoir les réafficher. |

Le filtre **Source** en haut affiche une source ou toutes.

## Les boutons

- **Appliquer** modifie les réglages indiqués. Vous pouvez aussi appliquer depuis la page *Réparations* de Home Assistant, qui montre la liste des changements avant confirmation.
- **Garder X seulement** : quand deux sons se recouvrent (par exemple *Chien* et *Aboiement*), vous choisissez lequel garder. Le recommandé est en premier.
- **Annuler** : remet un conseil appliqué à la **valeur de base du catalogue** (la valeur avant le conseil). Un son que le conseil avait désactivé n'est pas réactivé, car sa valeur de base est « désactivé » ; la carte le rappelle, et vous pouvez le réactiver dans l'onglet Sons.
- **Masquer / Réafficher** : cache un conseil que vous ne voulez pas voir. Les conseils sur les sons de sécurité (incendie, bébé, verre, cris) demandent d'abord une confirmation.
- **Importance** : change le niveau d'un type de conseil, pour une source ou pour toutes.

Appliquer un conseil ne boucle jamais : un conseil appliqué ne revient pas à cause de son propre changement (un test le vérifie sur toutes les règles).

## D'où viennent les conseils

Les conseils sont écrits dans le **catalogue** neutre en langue (`catalog/catalog.yaml`), pas dans le code, pour pouvoir être relus et traduits :

- Des *règles* sur les sons proches, les combinaisons risquées ou les sons qui demandent un contexte.
- Un `fix` qui dit ce que change le bouton (`enable`, `disable`, ou `set` d'un seuil, d'une durée minimale, d'un délai de repos ou d'une conservation des extraits), ou un `choose` pour les boutons « garder un seul ».
- Des contrôles automatiques de vos propres réglages : seuil bas sur un son à fausses alarmes, trou dans un horaire pour un son de sécurité, son de contexte manquant, extraits d'un son qui ne doit pas être conservé.

Les contributions sont bienvenues : voir le commentaire en tête de `catalog/catalog.yaml` pour la syntaxe, et lancez `python3 tools/validate.py` pour vérifier une modification.
