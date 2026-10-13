# Installing the recognition service

The **service** is the part that listens: it reads your audio streams, runs the YAMNet model and sends what it hears to Home Assistant. It runs **outside** Home Assistant, in its own container or machine, so that analysing audio never slows Home Assistant down. The integration (installed with HACS) then connects to it.

## What you need

- A Linux machine or container that is always on: **2 CPU cores, 1 GB of RAM and 8 GB of disk** are enough (ten simultaneous sources used about 12 % of one core and 0.6 GB of RAM in our measurements). No GPU needed.
- Audio sources the service can read as a stream: a camera or go2rtc stream (RTSP), a Raspberry Pi with a microphone, or any URL ffmpeg can open. See [Adding an audio source](#adding-an-audio-source).
- Network access from Home Assistant to the service on port **8765**.
- Internet access during installation only (it downloads ffmpeg, Python packages and the YAMNet model, whose SHA-256 is verified).

## Option A: Proxmox container (recommended, one command)

On the Proxmox host, as root:

```bash
curl -fsSLO https://raw.githubusercontent.com/schawki/sound-recognition-ha/main/deploy/create-lxc.sh
bash create-lxc.sh
```

The script asks for confirmation, creates an unprivileged Debian 13 container, installs the service, starts it and prints the **address** and the **access token** at the end. Keep both for the Home Assistant step. Options (container number, storage, network, fixed IP) are listed in [deploy/DEPLOY.md](../deploy/DEPLOY.md).

## Option B: any Debian or Ubuntu machine

```bash
apt-get update && apt-get install -y git
git clone https://github.com/schawki/sound-recognition-ha /opt/sound-recognition-ha
bash /opt/sound-recognition-ha/deploy/install.sh
```

The installer sets up ffmpeg, a Python environment, the model and a systemd service named `soundrec`. Run it again later to update; your configuration (`/etc/soundrec/config.yaml`) and data (`/var/lib/soundrec/`) are kept. The access token is generated at the first start and written in the configuration file:

```bash
grep token /etc/soundrec/config.yaml
```

## Option C: Docker

A `Dockerfile` is provided (it downloads and verifies the model while building). **This path has not been tested yet**: please report any problem.

```bash
git clone https://github.com/schawki/sound-recognition-ha && cd sound-recognition-ha
docker build -f service/Dockerfile -t sound-recognition-ha .
docker run -d --name soundrec --restart unless-stopped -p 8765:8765 \
  -v soundrec-config:/config -v soundrec-data:/data sound-recognition-ha
docker exec soundrec grep token /config/config.yaml
```

With Docker, the service cannot be updated from Home Assistant: rebuild the image to update.

## Check that it runs

```bash
curl http://<service-address>:8765/api/v1/health     # {"status": "ok", ...}
journalctl -u soundrec -f                            # logs (options A and B)
```

## Connect Home Assistant

1. In HACS, three dots → *Custom repositories* → `https://github.com/schawki/sound-recognition-ha`, category *Integration*; install **Sound Recognition**, then restart Home Assistant.
2. *Settings → Devices & services → Add integration → Sound Recognition*. Enter the service address, port 8765 and the token.
3. A **Sound Recognition** entry appears in the sidebar (administrators only).

## Protect the service (recommended)

The service listens on port 8765 in plain HTTP, and the token is the only lock. It does not need to be reachable by anything but Home Assistant, so close it to the rest of your network:

1. **Only Home Assistant may reach port 8765.** On Proxmox: the container → *Firewall* → *Add*: direction `in`, action `ACCEPT`, protocol `tcp`, destination port `8765`, source = the address of your Home Assistant machine; then *Firewall → Options*: enable the firewall and set *Input policy* to `DROP`. Keep a rule that lets you reach the container for administration (SSH, port 22) from your own computer, or you will lock yourself out. Without Proxmox, the same with `ufw`: `ufw allow from <HA address> to any port 8765 proto tcp`, `ufw allow from <your computer> to any port 22 proto tcp`, then `ufw enable`.
2. **Never forward port 8765 on your router** or publish it with a reverse proxy: use Home Assistant, which relays what the panel needs.
3. **Keep the token secret**, and change it (`token:` in `/etc/soundrec/config.yaml`, then restart the service and enter the new one in the integration) if it ever leaked. The service accepts it only in the `Authorization` header, never in an address.
4. **Optional: limit what the service can reach.** It only needs your cameras or go2rtc, your ESP32 microphones and GitHub (for updates). A rule `out` on the container that allows only those, and drops the rest, stops it from being used to probe the rest of your network.
5. **Protect the GitHub account of the repository the service updates from** (two-factor authentication): an update installs the latest release with administrator rights on the container.

## Adding an audio source

In the panel, *Sources → Add*. A source is a stream URL:

| Source | URL looks like |
|---|---|
| Camera or go2rtc stream | `rtsp://<host>:8554/<stream>` |
| Raspberry Pi with a microphone | a go2rtc stream from the Pi, `rtsp://<pi>:8554/mic` |
| Test file | a path or URL ffmpeg can read |

ESP32 microphones (ESPHome): see [ESP32 microphone](esphome-microphone.en.md).

## Keeping it up to date

With options A and B, an **Update** entity and a banner in the panel announce new releases; pressing *Update* installs the latest tagged release and keeps your settings. The first time, run the manual update command once (see [deploy/DEPLOY.md](../deploy/DEPLOY.md#updating-from-home-assistant)).

## Problems

- *The integration cannot connect*: check the address, port 8765 and the token; test `/api/v1/health` from the Home Assistant machine.
- *Service does not start*: `journalctl -u soundrec`. More cases in [deploy/DEPLOY.md](../deploy/DEPLOY.md#troubleshooting).
- *A source stays "Starting" or "Disconnected"*: open its URL with `ffprobe <url>` from the service machine; if that fails, the stream is the problem, not the service.
