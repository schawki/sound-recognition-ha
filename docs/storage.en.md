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

The folder is a setting of the service (`storage.clips_dir` in `/etc/soundrec/config.yaml`), so the clips can live on another disk, a NAS or any place the container can see. Home Assistant is not a good place: the service writes the clips at the moment of the detection and Home Assistant only reads them.

With the **Proxmox container** (unprivileged), the place must first be given to the container:

1. On the Proxmox host, mount the disk or the share (as for Frigate) and create a folder for the clips, for example `/mnt/storage/soundrec-clips`.
2. In the shell of the container, run `id soundrec` to know the number of the service's user (for example 999). On the Proxmox host, give the folder to user number `100000 + that number` (`chown -R 100999:100999 /mnt/storage/soundrec-clips`): an unprivileged container shifts its numbers by 100000.
3. In Proxmox: the container → *Resources* → *Add* → *Mount Point*, or `pct set <id> -mp0 /mnt/storage/soundrec-clips,mp=/mnt/clips`.
4. In `/etc/soundrec/config.yaml` of the container, set `storage: clips_dir: /mnt/clips`, move the existing clips (`mv /var/lib/soundrec/clips/* /mnt/clips/`) and restart the service (`systemctl restart soundrec`).

With **Docker**, bind the folder you want to the clips folder of the container (`-v /your/folder:/data/clips`).

A guided way to move the clips from the panel is planned for a later version.

## Changing the token

The *Settings* tab, *Connection* section, has a **Change the token** button. The token is the secret that Home Assistant and the service share. Change it if you think it leaked: the service makes a new one, Home Assistant stores it and reloads by itself. The old one still works for one minute so nothing is cut. The token is never shown in the panel.
