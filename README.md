# Sound recognition for Home Assistant

Recognises sounds (smoke alarm, baby cry, doorbell, breaking glass, barking…) from network microphones, cameras and Raspberry Pi, and reports them to Home Assistant. Think "Frigate's audio detection", but with any audio source and a configuration you can manage from Home Assistant.

**Status: early development (service and integration v0.1, tests passing, not yet run against real streams or a real Home Assistant).**

## How it fits together

- **`service/`**: the classifier. A small Python service (Docker image) meant to run in its own LXC/container. It reads audio streams with ffmpeg, runs YAMNet (TFLite), applies per-source settings, keeps short clips with a retention per class, and exposes a local HTTP/WebSocket API.
- **`custom_components/`**: the Home Assistant integration installed through HACS. It talks to the service over that API: sources, classes, thresholds, schedules, entities and advice, all from the Home Assistant UI.
- **`catalog/`**: the 521 YAMNet/AudioSet classes, language-neutral, with English and French texts (more languages can be added). Includes per-class suggestions and warnings about close classes and risky combinations.

## What the service does today

- Sources: any URL ffmpeg can read (RTSP from go2rtc or cameras, Raspberry Pi with go2rtc, files for tests). ESPHome sources: not yet.
- Settings per source, per class and per source × class: threshold, minimum volume (dBFS), schedules or continuous monitoring, minimum duration, cooldown, pre/post-roll, clip retention. See `docs/source-settings.en.md`.
- Context sounds (television, radio, music; fireworks and firecrackers for gunshots) raise the thresholds of look-alike sounds while they are heard. Safety sounds (smoke alarm, glass, screams, baby cry…) are raised by at most `analysis.safety_boost_cap` (0.05 by default; 0 = never). Each source can be given a kind of place (living room, kitchen, bedroom, outdoors…) to get recommendations, and an optional **adaptive sensitivity** that raises thresholds while the room is much noisier than usual. Sounds hidden this way are counted, never lost silently. Each source can also be given a Home Assistant room: the integration then finds its media players and vacuum cleaners and, if enabled, raises the thresholds while they play (rooms can be connected: the description of the home comes from the companion integration [Home Structure](https://github.com/schawki/ha-home-structure) when installed). See `docs/context-and-adaptive.en.md`.
- Clips of conversations are never kept: the catalog forbids it and the service enforces it.
- API (all under `/api/v1`, bearer token): `health`, `languages`, `catalog?lang=`, `config` (GET/PUT), `config/validate` (dry run with warnings), `warnings`, `recommendations`, `stats?hours=`, `sources`, `resolved`, `events`, `events/{id}/feedback` (POST `{"false": true}`), `clips` (list with size, filtered by `source`, `mid`, `usage`, `since`, `until`), `clips/delete` (POST `{"ids": [...]}` or `{"filter": {...}}`, `dry_run`), `clips/{path}`, `ws` (live events).

## Measured

On a 2-core test machine, ten simultaneous sources (continuous, 12 enabled classes) used about 12 % of one core and about 0.6 GB of RAM in total, including ffmpeg. One inference takes about 2 ms. Real RTSP streams add audio decoding; expect to re-measure on your hardware.

## Development

```
cd service && pip install -e '.[test]' && SOUNDREC_MODEL=/path/to/yamnet.tflite python -m pytest
SOUNDREC_CONFIG=config.yaml SOUNDREC_MODEL=... SOUNDREC_CATALOG=../catalog python -m soundrec
```

The Docker image downloads the model at build time and verifies its SHA-256 (`service/Dockerfile`; not yet built in CI). Example configuration: `examples/config.example.yaml`.

## Credits and licences

Code: MIT. YAMNet: Google, Apache-2.0 ([source](https://github.com/tensorflow/models/tree/master/research/audioset/yamnet)); AudioSet ontology: Google, CC BY-SA 4.0. The TFLite conversion of YAMNet used by default comes from a public fork; its checksum is pinned in the Dockerfile.

## Panel (sidebar)

The integration adds a **Sound Recognition** panel to the Home Assistant sidebar (administrators only). It has a live view (sources with level and connection state, sounds active right now, recent detections with clip playback and a “not a real sound” button that can raise the threshold for you), an **Overview** tab (what each source hears and how its thresholds react right now, the numbers of the last 24 hours with hidden and false detections, a summary of what needs your attention, and a live timeline), an **Advice** tab (one list of warnings and recommendations: what can be done in one click has an *Apply* button, what is already in place says *Already applied* and is kept in a folded group, the rest is information whose display you can change or hide), a Sources tab (add, edit, disable and remove sources, with a week grid to choose when each one listens) and a Sounds tab (search the 521 classes, enable them for all sources or per source, tune each one with the effective values and their origin shown, and see the advice before saving), an Advice tab (change the level of each advice globally or per source, or hide it; safety advice needs a confirmation to be hidden) and a Clips tab (find and play saved clips, with the size of each, filtered by source, sound, category such as animals, and period; delete one, a selection, everything the filters show, or all of them, after a confirmation that shows the count and the size). Everything works with the keyboard, in light and dark themes and on a phone.

The panel source is in `panel/` (Lit + TypeScript). The bundled file `custom_components/sound_recognition/frontend/sound-recognition-panel.js` is committed because HACS does not run builds. To change the panel:

```
cd panel && npm install && npm run build      # rebuilds the committed file
python3 test/run.py                            // headless Chromium checks against a stand-in for Home Assistant
python3 test/crosscheck_advice.py             // the advice levels shown by the panel match the service's
python3 test/crosscheck_resolve.py            // the panel's settings resolution matches the service's, on random configurations
node --test test/schedule.test.mjs             // schedule grid <-> service windows
```

## Deployment

Test deployment on Proxmox (unprivileged Debian 13 LXC, systemd service, no Docker): see [deploy/DEPLOY.md](deploy/DEPLOY.md) ([français](deploy/DEPLOY.fr.md)).

Updates: from version 0.2.0 the service can be updated from Home Assistant (Update entity and panel banner, tagged releases only); see [CHANGELOG.md](CHANGELOG.md) ([français](CHANGELOG.fr.md)).
