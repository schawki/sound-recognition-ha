# Service API

For developers. The service exposes a local HTTP/WebSocket API under `/api/v1`, protected by a bearer token (`Authorization: Bearer <token>`). The Home Assistant integration is its main client.

| Endpoint | Purpose |
|---|---|
| `health` | Status, version and API level |
| `languages`, `catalog?lang=` | Available languages and the class catalog |
| `config` (GET/PUT), `config/validate` | Read and write the configuration; dry run with warnings |
| `warnings`, `recommendations` | Advice computed from the configuration (see [the Advice tab](advice.en.md)) |
| `stats?hours=` | Counts for the overview |
| `sources`, `resolved` | Sources and the effective setting of each class, with its origin |
| `events`, `events/{id}/feedback` | Detections; POST `{"false": true}` marks one as a wrong detection, `{"good": true}` confirms it (`false` values clear the verdict); an event without clip carries `clip_reason` (why: `source_class`, `class`, `source_category`, `category`, `catalog`, `catalog_confidential`, `cap`, `source_clips_disallowed`, `expired`, `deleted`, `quota`, `disk_low`) |
| `events/delete_clipless` | POST `{"filter": {...}, "dry_run": true}`: deletes the detections that have no clip and no verdict (marked or confirmed ones stay); returns the count |
| `clips`, `clips/delete`, `clips/{path}` | List (filter by `source`, `mid`, `usage`, `since`, `until`, `feedback` = `false`, `good` or `unjudged`), delete (`ids` or `filter`, `dry_run`), download |
| `storage` | GET: folder, size, free space, growth per day, days left, and the two limits (`storage.clips_max_gb`, `storage.clips_min_free_gb`); a clip missing because of them carries `clip_reason` `quota` or `disk_low` |
| `token/rotate` | POST: makes a new API token and returns it; the old one works for one more minute |
| `ws` | Live events |

The settings and their resolution order are described in [source-settings.en.md](source-settings.en.md) and [context-and-adaptive.en.md](context-and-adaptive.en.md).

## Development

```
cd service && pip install -e '.[test]' && SOUNDREC_MODEL=/path/to/yamnet.tflite python -m pytest
SOUNDREC_CONFIG=config.yaml SOUNDREC_MODEL=... SOUNDREC_CATALOG=../catalog python -m soundrec
```

Panel (Lit + TypeScript in `panel/`; the bundle in `custom_components/sound_recognition/frontend/` is committed because HACS does not run builds):

```
cd panel && npm install && npm run build      # rebuilds the committed file
python3 test/run.py                            # headless Chromium checks against a stand-in for Home Assistant
python3 test/shots.py                          # regenerates docs/images (demo data)
```
