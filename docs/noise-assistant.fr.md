# Assistant de bruit

Le **volume minimum** d'une source est le son le plus faible pris en compte : en dessous, le service n'essaie même pas de reconnaître quoi que ce soit. Il dépend du gain de chaque micro, donc aucune valeur ne convient à tous. L'assistant de bruit mesure la pièce et en suggère une. **Vous décidez** : par défaut rien ne change tant que vous n'avez pas tapé ou accepté une valeur et enregistré la source ; si vous préférez, une source peut suivre les mesures toute seule (voir *Mode automatique* plus bas).

## Comment ça marche

- Le service garde **un chiffre par source et par minute** : le niveau ambiant en dBFS (la médiane de la minute). **Aucun audio n'est conservé** dans ces mesures, et une minute où une détection a eu lieu est marquée pour être écartée du calcul. Une source prend environ 40 octets par minute, soit environ 400 Ko par semaine.
- Dès qu'il y a **6 heures de minutes calmes**, l'assistant prend la moitié la plus calme (la pièce au repos), en retient le haut (90e centile) et ajoute **6 dB** pour que le bruit de fond reste sous le minimum.
- La suggestion n'est **jamais au-dessus de -50 dBFS** (ni sous -90), pour qu'une alarme lointaine ou étouffée soit encore entendue. Si la pièce est plus bruyante, l'assistant le dit et suggère de déplacer le micro ou de baisser son gain.

## L'utiliser

Dans *Sources → Modifier*, sous **Volume minimum**, l'assistant montre ce qui a été mesuré (heures de calme), la valeur suggérée, un graphique du niveau calme selon l'heure de la journée avec la suggestion (pointillés) et votre valeur actuelle (trait plein), et le niveau du moment.

- **Utiliser cette valeur** met la suggestion dans le champ ; vous pouvez encore la changer, et elle n'est gardée que si vous enregistrez la source.
- **Mode manuel.** Avec le réglage sur *Manuel*, tapez plutôt n'importe quelle valeur dans le champ : elle l'emporte toujours sur la suggestion, et l'assistant n'y touche jamais. Le niveau du moment et le graphique aident à choisir.

Le volume minimum peut aussi se régler pour un son dans les réglages de ce son (le plus strict des deux s'applique, voir [Réglages par source](source-settings.fr.md)).

## Mode automatique

Chaque source a un réglage, **Qui règle le volume minimum** : *Suivre la valeur par défaut*, *Automatique* ou *Manuel* (le défaut est manuel : rien ne bouge si vous ne le demandez pas). Dans **Réglages → Valeurs par défaut**, *Ajuster automatiquement le volume minimum sur chaque source* l'active pour toutes les sources d'un coup ; une source peut toujours choisir *Manuel* (ou *Automatique*) dans son propre formulaire, selon l'ordre habituel des réglages.

En mode automatique, le service regarde les mesures **une fois par jour** et applique la suggestion, avec quelques précautions :

- rien ne se passe avant **6 heures de calme** mesurées ; d'ici là, la valeur du champ s'applique ;
- la valeur ne **bouge que si la nouvelle suggestion diffère d'au moins 3 dB** de celle en cours, pour ne pas osciller ;
- elle reste entre -90 et -50 dBFS, comme la suggestion ;
- **votre configuration n'est pas réécrite** : le service garde la valeur automatique à côté. La valeur saisie dans le champ reste en place et sert de nouveau si vous revenez à *Manuel* ;
- un volume minimum réglé pour un son sur une source (réglages de ce son) s'applique toujours ;
- effacer les mesures ne change pas la valeur en cours ; le service attend de nouvelles mesures avant de la déplacer de nouveau.

Le formulaire de la source montre la valeur en cours et depuis quand, ce qui est attendu, et les **derniers changements** (les 5 plus récents, de et vers). Dans la liste des sources, chaque ligne indique le volume minimum en cours et qui l'a réglé (*automatique*, *réglé à la main*, *d'un préréglage*, *par défaut*), et le tableau par source des réglages d'un son montre aussi la valeur automatique.

## Mesures conservées, et les effacer

*Réglages → Mesures de bruit* liste, pour chaque source, le nombre de mesures (minutes), depuis quand, et la place qu'elles prennent, avec **Effacer** pour une source et **Effacer toutes les mesures** (les deux demandent une confirmation). Après un effacement, le service mesure de nouveau et l'assistant attend 6 heures de calme avant de suggérer.

**Jours de conservation des mesures** (`storage.noise_retention_days`, 7 par défaut, de 0 à 90) : les mesures plus anciennes sont effacées automatiquement ; **0 ne mesure rien** et l'assistant est alors désactivé.
