# Storage of the clips

## What is kept, and where

Sound Recognition keeps two things on the machine of the **service** (the container or the computer where you installed it, not Home Assistant):

- the **history of detections**: a small database, a few megabytes at most;
- the **clips**: the short audio recordings of detections, in the folder shown in the *Storage* card (*Clips* and *Settings* tabs) (by default `/var/lib/soundrec/clips` on a Proxmox or Debian installation, `/data/clips` with Docker).

Only the clips take real room. As an indication, a clip lasts a few seconds and weighs about 350 KB; on one real home about 70 clips took 25 MB in a week. A noisier home, longer clips or longer retention take more, so it is worth knowing how much room you give them.

## The Storage card

In the *Clips* tab the card shows the folder, what the clips take, the free space of that disk, how fast they grow per day and, at this rate, how long before the disk is full and how much your retention would take. An advice also appears in the *Advice* tab when less than 2 GB is left, or when the disk would be full in less than two weeks.

The limits are set in the *Settings* tab, *Storage* section (the *Change the limits* button of the card leads there). Both are **off by default**. You decide: nothing is limited unless you turn it on.

- **Stop keeping clips when the free space is under…** Detections are still recorded, without a clip (the history says "the disk was almost full"). Clips resume by themselves once the free space is 10 % above your limit.
- **Delete the oldest clips automatically to keep the clips under…** When the clips take more than the size you set, the oldest are deleted until they take 90 % of it. Clips you judged (marked as wrong or good detection) are deleted last, since they help you tune the thresholds. The detections stay in the history ("deleted automatically to stay under the space limit"), and the card tells how many clips were deleted this way.

The retention in days (same tab) works as before: it says how long a clip may stay, the size limit says how much room all clips may take; whichever comes first removes the clip.

## Keeping the clips on another disk or a NAS

<a id="moving-the-clips"></a>

The folder is a setting of the service (`storage.clips_dir`), so the clips can live on another disk, a NAS or any place the machine of the service can see. Home Assistant is not a good place: the service writes the clips at the moment of the detection and Home Assistant only reads them.

### From the start (Proxmox)

`create-lxc.sh` takes a folder of the Proxmox host: `CLIPS_HOST=/mnt/storage/soundrec-clips bash deploy/create-lxc.sh`. The folder must exist (mount the disk or the share first, as for Frigate). The script mounts it in the container as `/mnt/clips`, gives it to the service account (an unprivileged container shifts its user numbers by 100000, the script does the sum) and installs the service with the clips there. On another installation, `SOUNDREC_CLIPS=/your/folder bash deploy/install.sh` does the same on a first install.

### Later, from Home Assistant

*Settings* tab, *Storage* card, **Move the clips**:

1. Make the new place visible to the machine of the service (with the Proxmox container: mount it on the host, then add a mount point to the container, `pct set <id> -mp0 /mnt/storage/soundrec-clips,mp=/mnt/clips`, and give the folder to the service account as above). It must be an **empty** folder under `/mnt`, `/media` or `/srv` (the card lists the allowed places).
2. Type the folder in the card and press **Move the clips…**. The card asks you to confirm.
3. A small helper on the service machine copies the clips as the service account, checks that the copy matches, points the service at the new folder and restarts it. The card shows the progress.

What to know:

- **Nothing is deleted.** The old folder stays where it was, with all its clips. Check that the new place works, then delete the old folder yourself.
- During the copy the detections go on, but **no new clip is kept** (the history says "the clips were being moved") and no old clip is purged.
- The copy needs room: the new place must have the size of the clips plus 10 %. If the copy or the check fails, or the service does not restart on the new folder, the previous setting is restored and the card says why.
- The helper accepts only an existing, empty, real folder (no link) under the allowed places, and writes as the service account, so it can never write where the service itself could not. The allowed places can be extended at install time with `SOUNDREC_MOVE_ROOTS=/data:/backup`. It is on by default; `SOUNDREC_REMOTE_MOVE=0 bash deploy/install.sh` removes it.
- With **Docker**, the card cannot move the clips: bind the folder you want to the clips folder of the container (`-v /your/folder:/data/clips`) and copy the clips once by hand.

## Changing the token

The *Settings* tab, *Connection* section, has a **Change the token** button. The token is the secret that Home Assistant and the service share. Change it if you think it leaked: the service makes a new one, Home Assistant stores it and reloads by itself. The old one still works for one minute so nothing is cut. The token is never shown in the panel.
