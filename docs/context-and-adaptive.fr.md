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

## Prévu

Ajuster la sensibilité à partir d'entités Home Assistant (TV allumée et son volume, enceinte, aspirateur, lave-linge) par source, avec les mêmes plafonds et la même transparence. Pas encore implémenté.
