# Assistant de bruit

Le **volume minimum** d'une source est le son le plus faible pris en compte : en dessous, le service n'essaie même pas de reconnaître quoi que ce soit. Il dépend du gain de chaque micro, donc aucune valeur ne convient à tous. L'assistant de bruit mesure la pièce et en suggère une. **Vous décidez** : rien ne change tant que vous n'avez pas tapé ou accepté une valeur et enregistré la source.

## Comment ça marche

- Le service garde **un chiffre par source et par minute** : le niveau ambiant en dBFS (la médiane de la minute). **Aucun audio n'est conservé** dans ces mesures, et une minute où une détection a eu lieu est marquée pour être écartée du calcul. Une source prend environ 40 octets par minute, soit environ 400 Ko par semaine.
- Dès qu'il y a **6 heures de minutes calmes**, l'assistant prend la moitié la plus calme (la pièce au repos), en retient le haut (90e centile) et ajoute **6 dB** pour que le bruit de fond reste sous le minimum.
- La suggestion n'est **jamais au-dessus de -50 dBFS** (ni sous -90), pour qu'une alarme lointaine ou étouffée soit encore entendue. Si la pièce est plus bruyante, l'assistant le dit et suggère de déplacer le micro ou de baisser son gain.

## L'utiliser

Dans *Sources → Modifier*, sous **Volume minimum**, l'assistant montre ce qui a été mesuré (heures de calme), la valeur suggérée, un graphique du niveau calme selon l'heure de la journée avec la suggestion (pointillés) et votre valeur actuelle (trait plein), et le niveau du moment.

- **Utiliser cette valeur** met la suggestion dans le champ ; vous pouvez encore la changer, et elle n'est gardée que si vous enregistrez la source.
- **Mode manuel.** Tapez plutôt n'importe quelle valeur dans le champ : elle l'emporte toujours sur la suggestion, et l'assistant n'y touche jamais. Le niveau du moment et le graphique aident à choisir.

Le volume minimum peut aussi se régler pour un son dans les réglages de ce son (le plus strict des deux s'applique, voir [Réglages par source](source-settings.fr.md)).

## Mesures conservées, et les effacer

*Réglages → Mesures de bruit* liste, pour chaque source, le nombre de mesures (minutes), depuis quand, et la place qu'elles prennent, avec **Effacer** pour une source et **Effacer toutes les mesures** (les deux demandent une confirmation). Après un effacement, le service mesure de nouveau et l'assistant attend 6 heures de calme avant de suggérer.

**Jours de conservation des mesures** (`storage.noise_retention_days`, 7 par défaut, de 0 à 90) : les mesures plus anciennes sont effacées automatiquement ; **0 ne mesure rien** et l'assistant est alors désactivé.
