# Sons de contexte, pièces et sensibilité adaptative

Pourquoi une télévision ou de la musique déclenche des aboiements, des sonnettes ou des cris, et ce que fait le service.

## Sons de contexte

Télévision, Radio et Musique (et Feux d'artifice, Pétard pour les coups de feu) sont des *sons de contexte*. Tant que l'un est entendu sur une source, le seuil des sons qui lui ressemblent est relevé de `analysis.context_boost` (0,15 par défaut). Environ 24 sons du catalogue sont concernés : aboiements, sonnette, coups à la porte, cris, pleurs de bébé, sirènes, coups de feu, bris de verre…

- Un son de contexte n'agit que sur la source où il est activé. Activez-le là où une telle source existe (salon, cuisine avec radio…), pas partout : ailleurs, il baisse la sensibilité pour rien.
- Les **sons de sécurité** (usages incendie, sécurité et bébé que le catalogue recommande comme alertes) ne sont jamais relevés de plus de `analysis.safety_boost_cap` (0,05 par défaut). Mettez 0 pour ne jamais les relever, ou 1 pour les traiter comme les autres.
- Les autres sons de contexte (vent, pluie, circulation…) sont signalés mais ne changent aucun seuil.

## Type de pièce et recommandations

Chaque source peut recevoir un type de pièce (`environment`) : salon, cuisine, chambre, chambre de bébé, bureau, entrée, extérieur, garage. Le catalogue (`catalog/environments.yaml`) indique quels sons de contexte conviennent à chaque pièce et si la sensibilité adaptative vaut la peine. L'onglet **Aperçu** en tire des recommandations avec un bouton **Appliquer**, et l'onglet Sons regroupe les sons de contexte avec la recommandation pour la source choisie.

Les détections marquées fausses (bouton **Ce n'est pas un vrai son**) alimentent une seconde recommandation : quand le même son est marqué faux au moins deux fois en 14 jours sur la même source, le panneau propose un seuil juste au-dessus du plus haut score faux.

## Sensibilité adaptative (par source, désactivée par défaut)

`sources[].adaptive: {enabled: true, max_offset: 0.15}`. Le service compare le niveau ambiant (médiane de la dernière minute) au niveau calme habituel de la source (10e centile des niveaux ambiants par minute des dernières 24 heures, connu après 30 minutes d'écoute, oublié au redémarrage). Jusqu'à 6 dB au-dessus de l'habituel, rien ne change ; à 36 dB au-dessus, les seuils sont relevés de `max_offset`, linéairement entre les deux. Les sons de sécurité sont plafonnés comme ci-dessus.

Comme la référence demande de l'historique, le décalage est nul pendant les 30 premières minutes après un démarrage, et une très longue période bruyante finit par devenir « habituelle ».

## Rien ne disparaît en silence

Quand un seuil relevé empêche un son qui aurait été signalé, le service le compte comme une *détection masquée* (une fois par épisode, même délai qu'une détection) avec son score, le seuil qu'il fallait et la cause (son de contexte, bruit ambiant). Le panneau les montre en direct et dans les chiffres des 24 heures. Les détections indiquent maintenant le seuil réellement appliqué (`threshold`) et la hausse (`offset`).

## Pièces, appareils et pièces reliées (par source, désactivé par défaut)

Donnez à une source une pièce Home Assistant (`sources[].area`) : l'intégration trouve les appareils qui font du bruit dedans, c'est-à-dire les lecteurs multimédias (TV, enceintes, consoles) et les aspirateurs. D'autres entités (un interrupteur de hotte, un ventilateur…) s'ajoutent à la main (`devices.include`), et tout appareil trouvé peut être écarté (`devices.exclude`). Plusieurs entités d'un même appareil (une TV qui apparaît trois fois) comptent une seule fois.

Rien ne change tant que vous ne l'activez pas pour la source : `sources[].devices: {enabled: true, max_offset: 0.15, exclude: [], include: []}`. Ensuite, tant qu'un appareil joue, les seuils des sons qui lui ressemblent sont relevés, de la moitié à la totalité de `max_offset` selon le volume (60 % si l'appareil n'en indique pas) ; un appareil coupé ou éteint ne compte pas. Un aspirateur compte pour 80 %, un interrupteur ou un ventilateur pour 60 %. La cause la plus forte l'emporte, elles ne s'additionnent pas.

**Pièces reliées** (`area_links`, onglet Sources) : un salon et une entrée sans cloison forment un seul espace, et une porte de cuisine souvent ouverte laisse passer le son.

```yaml
area_links:
  - {a: salon, b: entree, type: open}                                  # 100 %
  - {a: entree, b: cuisine, type: door, sensor: binary_sensor.porte}   # ouverte environ 70 %, fermée environ 15 %
  - {a: entree, b: cuisine, type: door}                                # sans capteur : environ 42 %
```

Les appareils d'une pièce reliée comptent pour la source en proportion de ce qui passe (jusqu'à deux liaisons, les coefficients se multiplient). On les modifie avec `open_factor` et `closed_factor`. Un capteur de porte indisponible compte comme la moyenne. Un son entendu par *une autre* source d'une pièce reliée (une télévision détectée par le micro du salon) relève aussi cette source, de `context_boost` multiplié par cette part : c'est le même interrupteur, rien d'autre à activer. Le total ne dépasse jamais `analysis.total_boost_cap` (0,30), et les sons de sécurité restent plafonnés à `safety_boost_cap`.

L'intégration recalcule dans la seconde qui suit un changement et envoie le résultat au service avec une durée de vie de 60 secondes, renouvelée toutes les 20 secondes : si Home Assistant s'arrête, les seuils reviennent seuls à la normale. L'onglet Aperçu montre ce qui relève chaque source (par exemple « TV Salon · 100 % +0.08 »), et les sons masqués indiquent leur cause (appareils de la pièce, son entendu dans une pièce voisine).

Tous les coefficients (0,15, 70 %, 15 %, 60 %…) sont des estimations : surveillez les détections masquées quelques jours et ajustez `max_offset` par source.
