# Sons de contexte, pièces et sensibilité adaptative

Pourquoi une télévision ou de la musique déclenche des aboiements, des sonnettes ou des cris, et ce que fait le service.

## Sons de contexte

Télévision, Radio et Musique (et Feux d'artifice, Pétard pour les coups de feu) sont des *sons de contexte*. Tant que l'un est entendu sur une source, le seuil des sons qui lui ressemblent est relevé de `analysis.context_boost` (0,15 par défaut). Environ 24 sons du catalogue sont concernés : aboiements, sonnette, coups à la porte, cris, pleurs de bébé, sirènes, coups de feu, bris de verre…

- Un son de contexte n'agit que sur la source où il est activé. Activez-le là où une telle source existe (salon, cuisine avec radio…), pas partout : ailleurs, il baisse la sensibilité pour rien.
- Les **sons de sécurité** (usages incendie, sécurité et bébé que le catalogue recommande comme alertes) ne sont jamais relevés de plus de `analysis.safety_boost_cap` (0,05 par défaut). Mettez 0 pour ne jamais les relever, ou 1 pour les traiter comme les autres.
- Les autres sons de contexte (vent, pluie, circulation…) sont signalés mais ne changent aucun seuil.

## Type de pièce et recommandations

Chaque source peut recevoir un type de pièce (`environment`) : salon, salle à manger, cuisine, chambre, chambre de bébé, bureau, entrée, salle de bains, buanderie et local technique, salle de sport, rangement (cave, grenier), extérieur, garage. Le catalogue (`catalog/environments.yaml`) indique quels sons de contexte conviennent à chaque pièce et si la sensibilité adaptative vaut la peine. L'onglet **Aperçu** en tire des recommandations avec un bouton **Appliquer**, et l'onglet Sons regroupe les sons de contexte avec la recommandation pour la source choisie.

Les détections marquées fausses (bouton **Ce n'est pas un vrai son**) alimentent une seconde recommandation : quand le même son est marqué faux au moins deux fois en 14 jours sur la même source, le panneau propose un seuil juste au-dessus du plus haut score faux.

**Une seule liste, avec un état.** Les recommandations et les avertissements du catalogue partagent l'onglet **Conseils**. Un conseil qui a un geste (activer ces sons, activer le réglage adaptatif, utiliser les appareils de la pièce, relever un seuil) affiche un bouton **Appliquer** ; une fois le geste en place, il indique **Déjà appliqué** et passe dans un groupe replié en bas, pour que vous puissiez vérifier que cela a pris effet. L'avertissement sur les feux d'artifice et les pétards en fait partie : on y répond en activant ces deux sons comme contextes. Un avertissement sans geste reste une information ; son niveau se change, ou on le masque, sous **Affichage** (un avertissement de sécurité demande une confirmation pour être masqué). L'Aperçu se contente de résumer ce qui demande de l'attention et ouvre l'onglet. Dans Home Assistant, les alertes de *Réparations* suivent la même règle : un conseil déjà appliqué n'en crée pas, et celui qui a un geste propose un bouton *Corriger* qui demande confirmation puis l'applique.

## Sensibilité adaptative (par source, désactivée par défaut)

`sources[].adaptive: {enabled: true, max_offset: 0.15}`. Le service compare le niveau ambiant (médiane de la dernière minute) au niveau calme habituel de la source (10e centile des niveaux ambiants par minute des dernières 24 heures, connu après 30 minutes d'écoute, oublié au redémarrage). Jusqu'à 6 dB au-dessus de l'habituel, rien ne change ; à 36 dB au-dessus, les seuils sont relevés de `max_offset`, linéairement entre les deux. Les sons de sécurité sont plafonnés comme ci-dessus.

Comme la référence demande de l'historique, le décalage est nul pendant les 30 premières minutes après un démarrage, et une très longue période bruyante finit par devenir « habituelle ».

## Rien ne disparaît en silence

Quand un seuil relevé empêche un son qui aurait été signalé, le service le compte comme une *détection masquée* (une fois par épisode, même délai qu'une détection) avec son score, le seuil qu'il fallait et la cause (son de contexte, bruit ambiant). Le panneau les montre en direct et dans les chiffres des 24 heures. Les détections indiquent maintenant le seuil réellement appliqué (`threshold`) et la hausse (`offset`).

## Pièces, appareils et pièces reliées (par source, désactivé par défaut)

Donnez à une source une pièce Home Assistant (`sources[].area`) : l'intégration trouve les appareils qui font du bruit dedans, c'est-à-dire les lecteurs multimédias (TV, enceintes, consoles) et les aspirateurs. D'autres entités (un interrupteur de hotte, un ventilateur…) s'ajoutent à la main (`devices.include`), et tout appareil trouvé peut être écarté (`devices.exclude`). Plusieurs entités d'un même appareil (une TV qui apparaît trois fois) comptent une seule fois.

Rien ne change tant que vous ne l'activez pas pour la source : `sources[].devices: {enabled: true, max_offset: 0.15, exclude: [], include: []}`. Ensuite, tant qu'un appareil joue, les seuils des sons qui lui ressemblent sont relevés, de la moitié à la totalité de `max_offset` selon le volume (60 % si l'appareil n'en indique pas) ; un appareil coupé ou éteint ne compte pas. Un aspirateur compte pour 80 %, un interrupteur ou un ventilateur pour 60 %. La cause la plus forte l'emporte, elles ne s'additionnent pas.

**Pièces reliées.** Un salon et une entrée sans cloison forment un seul espace, et une porte de cuisine souvent ouverte laisse passer le son. La description du logement (quelles pièces sont voisines, ce qui les sépare, quel capteur dit si c'est ouvert) appartient à une intégration à part, [Home Structure](https://github.com/schawki/ha-home-structure), pour que d'autres intégrations puissent s'en servir aussi. Sound Recognition la lit si elle est installée et décide seulement ce que chaque type de séparation change pour le son :

| Séparation | ouverte | fermée |
|---|---|---|
| espace ouvert | 100 % | – |
| ouverture sans porte | 90 % | – |
| porte | 70 % | 15 % |
| porte vitrée ou coulissante | 70 % | 25 % |
| grille de sécurité ou porte grillagée | 90 % | 85 % |
| fenêtre | 60 % | 10 % |
| volet roulant (seul) | 60 % | 10 % |
| mur plein | 5 % | 5 % |

Un état illisible (pas de capteur, indisponible) compte comme la moyenne entre ouvert et fermé, de même pour « partiellement ouvert ». Plusieurs séparations entre les deux mêmes pièces : la plus ouverte l'emporte ; un volet roulant devant une fenêtre ou une porte la multiplie (ouvert ×1, partiel ×0,75, fermé ×0,5). Quand Home Structure indique le volet d'une fenêtre ou d'une porte précise, seule cette séparation est multipliée ; un volet déclaré comme séparation à part s'applique toujours à la plus ouverte. Un mur plein ne laisse presque rien passer et n'est pas suivi. On suit jusqu'à deux liaisons depuis une pièce, les coefficients se multiplient.

Sound Recognition ne décrit aucune pièce lui-même. Sans Home Structure (ou tant qu'elle ne décrit rien), l'onglet Sources recommande de l'installer ou de la remplir, et une source ne voit que les appareils de sa propre pièce. Types de séparation : `open_space`, `opening`, `door`, `glass_door`, `grille`, `window`, `shutter`, `wall`.

**Recommandations issues du logement.** L'environnement d'une source est déduit de Home Structure : le type de sa pièce (chaque type en a un : les chambres → chambre, chambre de bébé → chambre de bébé, salon, salle de jeux, salle de cinéma → salon, salle à manger, salle de sport, salle de bains et toilettes → salle de bains, buanderie et local technique, cellier, dressing, rangement, cave et grenier → rangement, couloir, entrée et escalier → entrée, atelier → garage) ou le genre de son espace (jardin, terrasse, balcon, cour, rue → extérieur ; garage ; hall d'immeuble, cage d'escalier, partie commune → entrée). Il suit ce que dit Home Structure, sans rien à recopier ; choisir un environnement dans la source le remplace, et l'intégration communique celui qui est déduit au service (API niveau 4). Une pièce sans type reçoit une recommandation de choisir son type dans Home Structure. Des règles sur les espaces reliés à la pièce d'une source apparaissent aussi dans les recommandations : une rue, une cour ou une cage d'escalier reliée par une porte ou une fenêtre (pas un mur) suggère le réglage adaptatif, un jardin ou une rue suggère Feux d'artifice et Pétard, un salon relié à une chambre suggère Télévision, Radio et Musique, un garage suggère le réglage adaptatif. Rien n'est deviné à partir des noms, et une règle ne s'applique que si la liaison existe dans le plan. La correspondance et les règles forment un fichier lisible, `custom_components/sound_recognition/home_rules.yaml` (textes anglais et français inclus).

**Appareils de la pièce et des pièces reliées.** Le formulaire d'une source affiche un résumé (appareils dans la pièce, dans les pièces reliées, et la part du son qui atteint la source depuis chaque pièce reliée selon l'état de sa porte ou de sa fenêtre) ; seules les pièces qui laissent passer au moins 10 % sont comptées. La liste détaillée, les exclusions, les entités supplémentaires et la hausse maximale sont des réglages expert.

Les appareils d'une pièce reliée comptent pour la source en proportion de ce qui passe. Un son entendu par *une autre* source d'une pièce reliée (une télévision détectée par le micro du salon) relève aussi cette source, de `context_boost` multiplié par cette part : c'est le même interrupteur, rien d'autre à activer. Le total ne dépasse jamais `analysis.total_boost_cap` (0,30), et les sons de sécurité restent plafonnés à `safety_boost_cap`. Les hausses inférieures à 0,01 sont ignorées.

L'intégration recalcule dans la seconde qui suit un changement et envoie le résultat au service avec une durée de vie de 60 secondes, renouvelée toutes les 20 secondes : si Home Assistant s'arrête, les seuils reviennent seuls à la normale. L'onglet Aperçu montre ce qui relève chaque source (par exemple « TV Salon · 100 % +0.08 »), et les sons masqués indiquent leur cause (appareils de la pièce, son entendu dans une pièce voisine).

Tous les coefficients (0,15, 70 %, 15 %, 60 %…) sont des estimations : surveillez les détections masquées quelques jours et ajustez `max_offset` par source.
