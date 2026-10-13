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

Le dossier est un réglage du service (`storage.clips_dir` dans `/etc/soundrec/config.yaml`) : les clips peuvent donc se trouver sur un autre disque, un NAS ou tout endroit que le conteneur voit. Home Assistant n'est pas un bon endroit : le service écrit les clips au moment de la détection et Home Assistant ne fait que les lire.

Avec le **conteneur Proxmox** (non privilégié), il faut d'abord donner l'endroit au conteneur :

1. Sur l'hôte Proxmox, montez le disque ou le partage (comme pour Frigate) et créez un dossier pour les clips, par exemple `/mnt/stockage/soundrec-clips`.
2. Dans le terminal du conteneur, lancez `id soundrec` pour connaître le numéro de l'utilisateur du service (par exemple 999). Sur l'hôte Proxmox, donnez le dossier à l'utilisateur numéro `100000 + ce numéro` (`chown -R 100999:100999 /mnt/stockage/soundrec-clips`) : un conteneur non privilégié décale ses numéros de 100000.
3. Dans Proxmox : le conteneur → *Ressources* → *Ajouter* → *Point de montage*, ou `pct set <id> -mp0 /mnt/stockage/soundrec-clips,mp=/mnt/clips`.
4. Dans `/etc/soundrec/config.yaml` du conteneur, mettez `storage: clips_dir: /mnt/clips`, déplacez les clips existants (`mv /var/lib/soundrec/clips/* /mnt/clips/`) et redémarrez le service (`systemctl restart soundrec`).

Avec **Docker**, liez le dossier de votre choix au dossier des clips du conteneur (`-v /votre/dossier:/data/clips`).

Un moyen guidé de déplacer les clips depuis le panneau est prévu dans une version ultérieure.

## Changer le jeton

L'onglet *Réglages*, section *Connexion*, a un bouton **Changer le jeton**. Le jeton est le secret que Home Assistant et le service partagent. Changez-le si vous pensez qu'il a fuité : le service en fabrique un nouveau, Home Assistant l'enregistre et se recharge tout seul. L'ancien fonctionne encore une minute pour que rien ne soit coupé. Le jeton n'est jamais affiché dans le panneau.
