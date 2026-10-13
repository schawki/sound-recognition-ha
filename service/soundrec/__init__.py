"""Sound recognition service: classifies audio streams with YAMNet and serves detections over a local API."""
__version__ = "0.18.0"

# Raised when the API gains something the Home Assistant integration depends on; the integration says the service is outdated below its own minimum.
# 1: before the thresholds pushed by Home Assistant. 2: thresholds pushed by Home Assistant (devices, neighbouring rooms), updates from Home Assistant.
# 3: clip management (sizes, filters, bulk deletion). 4: kind of place deduced from Home Structure (PUT /sources/{id}/place).
# 5: warnings and recommendations say whether their gesture is already in place (`applied`), and some warnings carry one (`apply`).
# 6: warnings between close sounds carry `choices` (one gesture per sound to keep).
# 7: sources of type `esphome` (ESP32 microphones) with a `password`, never returned by the API (shown as "***").
# 8: retention of clips by category (`clips.retention_by_category`), verdict `good` on detections, `POST /events/delete_clipless`, `feedback` clip filter.
# 9: `GET /storage` (size, growth, limits of the clips), `POST /token/rotate`, `storage.clips_max_gb` / `clips_min_free_gb`, clip reasons `quota` and `disk_low`.
# 10: presets (`catalog.presets`, `presets` in the configuration and on each source), `GET /config/effective` (the configuration with the presets folded in), provenance `preset`.
# 11: `POST /storage/move` (move the clips to another folder), `POST /storage/old/delete` (delete the clips left in the old folder), `GET /storage` carries `move` (state of the helper, old folders kept) and `moved_skipped`, clip reason `moving`.
# 12: conditions on Home Assistant states (`condition` next to `schedule`, at the same levels), `PUT /conditions` (the states they read),
#     `held_by_condition` and `condition_unknown` in the status of each source.
API_LEVEL = 12
