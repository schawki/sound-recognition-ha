# Test deployment (Proxmox LXC)

Short recipe to get the service running in its own unprivileged Debian 13 container. A full user tutorial will come once the project is finished.

## 1. On the Proxmox host

Copy the repository (e.g. `sound-recognition-ha.zip`) to the node, unzip it, and run the script as root:

```bash
python3 -m zipfile -e sound-recognition-ha.zip /root/     # or: unzip sound-recognition-ha.zip -d /root
cd /root/sound-recognition-ha
bash deploy/create-lxc.sh
```

It asks for confirmation, then creates the container (2 vCPU, 1 GB RAM, 8 GB disk, start at boot), installs ffmpeg, the service and the YAMNet model, and starts it. Defaults can be changed with environment variables, for example:

```bash
CTID=210 STORAGE=local-zfs BRIDGE=vmbr0 IP=192.168.1.50/24 GATEWAY=192.168.1.1 bash deploy/create-lxc.sh
```

(see the header of `deploy/create-lxc.sh` for all of them). At the end it prints the container address and the API token.

## 2. Check

```bash
curl http://<container-ip>:8765/api/v1/health      # {"status": "ok", ...}
pct exec <CTID> -- journalctl -u soundrec -f       # logs
```

## 3. Home Assistant

Install the integration either through HACS (custom repository, category *Integration*) or by copying `custom_components/sound_recognition` into `/config/custom_components/`, restart HA, then *Settings → Devices & services → Add integration → Sound recognition* with the container address (port 8765) and the token. A *Sound recognition* entry appears in the sidebar (admins only).

## Where things are in the container

| What | Where |
|---|---|
| Configuration (YAML, source of truth) | `/etc/soundrec/config.yaml` |
| Code, venv, catalog, model | `/opt/soundrec/` |
| Clips and event database | `/var/lib/soundrec/` |
| Service | `systemctl status soundrec` |

Update: copy the new version into the container and run `bash deploy/install.sh` again (config and data are kept).
Restart after editing the YAML by hand: `systemctl restart soundrec`.

## Troubleshooting

- Service fails with `226/NAMESPACE`: the installer already falls back to a drop-in without sandboxing; check `journalctl -u soundrec`.
- No Debian 13 template: run `pveam update` on the host, or update Proxmox.
- A static IP needs `GATEWAY`.
