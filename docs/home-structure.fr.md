# Home Structure : pourquoi et comment Sound Recognition l'utilise

[Home Structure](https://github.com/schawki/ha-home-structure) est une intégration Home Assistant séparée qui décrit la *forme* de votre logement : quelles pièces existent, lesquelles se touchent, ce qui les sépare (mur, porte, fenêtre, espace ouvert, volet), quel capteur dit si une porte ou une fenêtre est ouverte, et ce qu'est chaque pièce (cuisine, chambre, garage…). Elle connaît aussi l'extérieur : une rue, un jardin, une cage d'escalier, un voisin.

Sound Recognition **n'en a pas besoin pour fonctionner**. Avec elle, il entend mieux et conseille mieux.

## Pourquoi une intégration séparée

- **Une seule description du logement, pour tout le monde.** Les pièces et les portes ne sont pas propres aux sons : l'éclairage, le chauffage, la présence ou la sécurité peuvent utiliser le même plan. La décrire une fois dans Home Structure évite une seconde copie, différente, dans Sound Recognition.
- **Rien n'est deviné.** Sound Recognition ne déduit jamais rien des *noms* de vos pièces ou de vos appareils. Il n'utilise que ce que vous avez choisi dans Home Structure (un type de pièce, un lien entre deux pièces), donc il fonctionne pareil dans tous les logements et dans toutes les langues.
- **Chaque intégration reste petite.** Home Structure connaît le logement ; Sound Recognition décide seulement ce qu'une porte, une fenêtre ou un mur signifie *pour le son*.

## Ce que Sound Recognition en tire

| Il lit | Cela sert à |
|---|---|
| **Les liens entre les pièces** et ce qui les sépare, avec l'état en direct de chaque porte ou fenêtre (ouverte, fermée, entrouverte) | Estimer la part d'un son qui passe d'une pièce à l'autre. Un son entendu dans le salon (une télévision) relève les seuils du micro de la cuisine en proportion de ce qui l'atteint : une porte ouverte le laisse passer, une porte fermée l'étouffe. Tableau des valeurs dans [Contextes, pièces et sensibilité adaptative](context-and-adaptive.fr.md). |
| **Le type de chaque pièce** et la nature des espaces extérieurs | Déduire le type de lieu d'une source (cuisine, chambre, garage, extérieur…) sans que vous le choisissiez une seconde fois, ce qui règle les sons adaptés au lieu. |
| **Ce qui touche la pièce d'une source** | Des conseils dans l'onglet *Conseils* : un jardin ou une rue à côté suggère Feux d'artifice et Pétard (pour qu'ils ne soient pas pris pour des coups de feu) ; un salon voisin suggère Télévision, Radio et Musique ; une rue, une cage d'escalier ou un hall suggère le réglage adaptatif. Une règle n'apparaît que si le lien existe dans le plan. |
| **Le plan** (position des pièces) | Affiché en lecture seule dans le formulaire d'une source. |
| **Les volets roulants** devant une fenêtre ou une porte | Un volet fermé réduit ce qui passe par cette fenêtre ou cette porte. |

Les lecteurs multimédias et les aspirateurs d'une pièce sont trouvés grâce aux pièces (zones) de Home Assistant, pas par Home Structure ; Home Structure dit quelles *autres* pièces sont reliées, pour que leurs appareils comptent aussi, en proportion de ce qui passe.

## Comment elles se parlent

- Par un service public de Home Structure, `home_structure.get_structure`, et par les entités qu'elle crée. Rien n'est importé de l'une dans l'autre : chacune se met à jour séparément.
- Home Structure émet l'évènement `home_structure_changed` quand vous modifiez le plan (et à son démarrage). Sound Recognition relit alors le plan en quelques secondes (plusieurs évènements de suite donnent une seule lecture). Il ne déduit rien de l'évènement lui-même. Sans l'évènement (Home Structure plus ancienne), le plan est de toute façon relu toutes les 20 secondes.
- Si Home Structure est absente, pas encore configurée ou en panne, Sound Recognition ne plante pas : les pièces sont traitées comme séparées, une source ne voit que les appareils de sa propre pièce, et l'onglet Sources vous invite à l'installer ou à la remplir.

## Ce qu'il faut faire

1. Installez Home Structure (HACS, comme Sound Recognition) et décrivez vos pièces : le type de chaque pièce et les séparations entre pièces voisines.
2. Dans Sound Recognition, donnez à chaque source une pièce de Home Assistant (*Sources → modifier → Pièce*). Rien d'autre à régler : le lieu, les conseils et le passage du son suivent.
3. Activez *appareils* et *sensibilité adaptative* pour les sources où vous voulez que les seuils suivent ce qui joue dans la pièce.

## Bon à savoir

- Choisir un lieu à la main dans une source l'emporte sur celui déduit de Home Structure.
- Un mur plein laisse passer très peu de son et n'est pas suivi.
- Home Structure n'envoie rien d'elle-même à Sound Recognition, à part l'évènement « quelque chose a changé » ; Sound Recognition redemande toujours la description complète.
