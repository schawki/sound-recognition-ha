# Test deployment (Proxmox LXC)

Short recipe to get the service running in its own unprivileged Debian 13 container. Step-by-step guide with the Docker and plain-Debian options: [docs/install-service.en.md](../docs/install-service.en.md).

## 1. On the Proxmox host

Download the script and run it as root (it clones the repository from GitHub inside the container):

```bash
curl -fsSLO https://raw.githubusercontent.com/schawki/sound-recognition-ha/main/deploy/create-lxc.sh
bash create-lxc.sh
```

It asks for confirmation, then creates the container (2 vCPU, 1 GB RAM, 8 GB disk, start at boot), installs git and ffmpeg, clones the project, installs the service and the YAMNet model, and starts it. Defaults can be changed with environment variables, for example:

```bash
CTID=210 STORAGE=local-zfs BRIDGE=vmbr0 IP=192.168.1.50/24 GATEWAY=192.168.1.1 bash create-lxc.sh
```

(see the header of the script for all of them, including `REPO_URL`/`REF` to install another branch or fork). Without GitHub access, copy the repository to the node and run `SOURCE=local bash deploy/create-lxc.sh` from it. At the end it prints the container address and the API token.

## 2. Check

```bash
curl http://<container-ip>:8765/api/v1/health      # {"status": "ok", ...}
pct exec <CTID> -- journalctl -u soundrec -f       # logs
```

## 3. Home Assistant

Install the integration either through HACS (three dots → *Custom repositories* → `https://github.com/schawki/sound-recognition-ha`, category *Integration*) or by copying `custom_components/sound_recognition` into `/config/custom_components/`, restart HA, then *Settings → Devices & services → Add integration → Sound recognition* with the container address (port 8765) and the token. A *Sound recognition* entry appears in the sidebar (admins only).

## Where things are in the container

| What | Where |
|---|---|
| Configuration (YAML, source of truth) | `/etc/soundrec/config.yaml` |
| Code, venv, catalog, model | `/opt/soundrec/` |
| Clips and event database | `/var/lib/soundrec/` |
| Service | `systemctl status soundrec` |

Update (the project is cloned in `/opt/sound-recognition-ha`; config and data are kept):

```bash
pct exec <CTID> -- bash -c 'git -C /opt/sound-recognition-ha pull && bash /opt/sound-recognition-ha/deploy/install.sh'
```


### Updating from Home Assistant

From version 0.2.0 the integration shows an **Update** entity for the service (*Settings → Devices & services → Sound Recognition*) and a banner in the panel when a newer release exists or when the service is too old for the integration. Press *Update* (entity or banner): the service restarts, the panel follows the progress and Home Assistant sends a notification when the service is back online (or when the update failed, with the end of the log).

How it works, and what it is allowed to do:

- The service itself stays unprivileged. It only drops a request file; a small root helper (`soundrec-update`, started by the systemd path unit `soundrec-update.path`) does the work. The helper reads only its own root-owned file `/etc/soundrec-updater.env`, never the content of the request, and writes its progress in `/var/lib/soundrec-update/`, a folder the service can read but not write.
- Only **tagged releases** (`vX.Y.Z`) are installed, never the tip of `main`. The helper fast-forwards the clone to the latest tag and runs `install.sh`; if that fails, the previous version is restored and the failure is reported.
- Config and data are kept. After an update the clone stays on `main`, fast-forwarded to the tag, so the manual `git pull` command above keeps working.
- It needs Debian/Ubuntu with systemd (the LXC of this guide, or any host installed with `install.sh`). With Docker, update by pulling a new image: the Update entity then only informs.
- Turn it off with `SOUNDREC_REMOTE_UPDATE=0 bash deploy/install.sh` (the helper is removed). It is on by default.

**One manual update is needed** to install the helper the first time (the old service does not have it): run the update command above once, then restart the integration (HACS update + restart Home Assistant). Afterwards, updates can be launched from Home Assistant. Until then the Update entity only informs and shows the command to run.

Restart after editing the YAML by hand: `systemctl restart soundrec`.

## Troubleshooting

- Service fails with `226/NAMESPACE`: the installer already falls back to a drop-in without sandboxing; check `journalctl -u soundrec`.
- No Debian 13 template: run `pveam update` on the host, or update Proxmox.
- A static IP needs `GATEWAY`.
