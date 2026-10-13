# Stockage des clips

## Ce qui est conservé, et où

Sound Recognition conserve deux choses sur la machine du **service** (le conteneur ou l'ordinateur où vous l'avez installé, pas Home Assistant) :

- l'**historique des détections** : une petite base de données, quelques mégaoctets au plus ;
- les **clips** : les courts enregistrements audio des détections, dans le dossier indiqué par la carte *Stockage* (onglets *Clips* et *Réglages*) (par défaut `/var/lib/soundrec/clips` sur une installation Proxmox ou Debian, `/data/clips` avec Docker).

Seuls les clips prennent vraiment de la place. À titre indicatif, un clip dure quelques secondes et pèse environ 350 Ko ; sur une vraie maison, environ 70 clips occupaient 25 Mo en une semaine. Une maison plus bruyante, des clips plus longs ou une rétention plus longue en prennent davantage : mieux vaut savoir combien de place vous leur donnez.

## La carte Stockage

Dans l'onglet *Clips*, la carte indique le dossier, ce que les clips occupent, l'espace libre du disque, leur croissance par jour et, à ce rythme, le temps avant que le disque soit plein et la place que prendrait votre rétention. Un conseil apparaît aussi dans l'onglet *Conseils* quand il reste moins de 2 Go, ou quand le disque serait plein dans moins de deux semaines.

Les limites se règlent dans l'onglet *Réglages*, section *Stockage* (le bouton *Modifier les limites* de la carte y mène). Toutes deux sont **désactivées par défaut**. C'est vous qui décidez : rien n'est limité tant que vous ne l'activez pas.

- **Ne plus garder de clips quand l'espace libre est inférieur à…** Les détections sont toujours enregistrées, sans clip (l'historique dit « le disque était presque plein »). Les clips reprennent d'eux-mêmes quand l'espace libre dépasse votre limite de 10 %.
- **Supprimer automatiquement les plus anciens clips pour garder les clips sous…** Quand les clips occupent plus que la taille choisie, les plus anciens sont supprimés jusqu'à n'occuper que 90 % de cette taille. Les clips que vous avez jugés (détection fausse ou bonne) sont supprimés en dernier, car ils servent à régler les seuils. Les détections restent dans l'historique (« supprimé automatiquement pour rester sous la limite d'espace »), et la carte indique combien de clips ont été supprimés ainsi.

La rétention en jours (même onglet) fonctionne comme avant : elle dit combien de temps un clip peut rester, la limite de taille dit combien de place tous les clips peuvent prendre ; le premier des deux qui s'applique supprime le clip.

## Garder les clips sur un autre disque ou un NAS

<a id="moving-the-clips"></a>

Le dossier est un réglage du service (`storage.clips_dir`) : les clips peuvent donc vivre sur un autre disque, un NAS ou tout endroit que la machine du service voit. Home Assistant n'est pas un bon endroit : le service écrit les clips au moment de la détection et Home Assistant ne fait que les lire.

### Dès le départ (Proxmox)

`create-lxc.sh` accepte un dossier de l'hôte Proxmox : `CLIPS_HOST=/mnt/storage/soundrec-clips bash deploy/create-lxc.sh`. Le dossier doit exister (montez d'abord le disque ou le partage, comme pour Frigate). Le script le monte dans le conteneur sous `/mnt/clips`, le donne au compte du service (un conteneur non privilégié décale ses numéros d'utilisateur de 100000, le script fait le calcul) et installe le service avec les clips à cet endroit. Sur une autre installation, `SOUNDREC_CLIPS=/votre/dossier bash deploy/install.sh` fait la même chose à la première installation.

### Plus tard, depuis Home Assistant

Onglet *Réglages*, carte *Stockage*, **Déplacer les clips** :

1. Rendez le nouvel endroit visible pour la machine du service (avec le conteneur Proxmox : montez-le sur l'hôte, puis ajoutez un point de montage au conteneur, `pct set <id> -mp0 /mnt/storage/soundrec-clips,mp=/mnt/clips`, et donnez le dossier au compte du service comme ci-dessus). Ce doit être un dossier **vide** sous `/mnt`, `/media` ou `/srv` (la carte liste les emplacements autorisés).
2. Saisissez le dossier dans la carte et appuyez sur **Déplacer les clips…**. La carte demande de confirmer.
3. Un petit assistant sur la machine du service copie les clips avec le compte du service, vérifie que la copie correspond, fait pointer le service sur le nouveau dossier et le redémarre. La carte montre l'avancement.

À savoir :

- **Rien n'est supprimé.** L'ancien dossier reste où il était, avec tous ses clips. Vérifiez que le nouvel endroit fonctionne, puis supprimez vous-même l'ancien dossier.
- Pendant la copie, les détections continuent, mais **aucun nouveau clip n'est gardé** (l'historique dit « les clips étaient en cours de déplacement ») et aucun ancien clip n'est purgé.
- La copie demande de la place : le nouvel endroit doit avoir la taille des clips plus 10 %. Si la copie ou la vérification échoue, ou si le service ne redémarre pas sur le nouveau dossier, le réglage précédent est rétabli et la carte dit pourquoi.
- L'assistant n'accepte qu'un dossier existant, vide et réel (pas un lien) sous les emplacements autorisés, et écrit avec le compte du service : il ne peut donc jamais écrire là où le service lui-même ne le pourrait pas. Les emplacements autorisés s'étendent à l'installation avec `SOUNDREC_MOVE_ROOTS=/data:/backup`. Il est activé par défaut ; `SOUNDREC_REMOTE_MOVE=0 bash deploy/install.sh` le retire.
- Avec **Docker**, la carte ne peut pas déplacer les clips : liez le dossier voulu au dossier des clips du conteneur (`-v /votre/dossier:/data/clips`) et copiez les clips une fois à la main.

## Changer le jeton

L'onglet *Réglages*, section *Connexion*, a un bouton **Changer le jeton**. Le jeton est le secret que Home Assistant et le service partagent. Changez-le si vous pensez qu'il a fuité : le service en fabrique un nouveau, Home Assistant l'enregistre et se recharge tout seul. L'ancien fonctionne encore une minute pour que rien ne soit coupé. Le jeton n'est jamais affiché dans le panneau.
