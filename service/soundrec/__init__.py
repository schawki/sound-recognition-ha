"""Sound recognition service: classifies audio streams with YAMNet and serves detections over a local API."""
__version__ = "0.9.0"

# Raised when the API gains something the Home Assistant integration depends on; the integration says the service is outdated below its own minimum.
# 1: before the thresholds pushed by Home Assistant. 2: thresholds pushed by Home Assistant (devices, neighbouring rooms), updates from Home Assistant.
# 3: clip management (sizes, filters, bulk deletion). 4: kind of place deduced from Home Structure (PUT /sources/{id}/place).
# 5: warnings and recommendations say whether their gesture is already in place (`applied`), and some warnings carry one (`apply`).
# 6: warnings between close sounds carry `choices` (one gesture per sound to keep).
API_LEVEL = 6
