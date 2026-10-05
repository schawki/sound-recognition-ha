"""Sound recognition service: classifies audio streams with YAMNet and serves detections over a local API."""
__version__ = "0.4.0"

# Raised when the API gains something the Home Assistant integration depends on; the integration says the service is outdated below its own minimum.
# 1: before the thresholds pushed by Home Assistant. 2: thresholds pushed by Home Assistant (devices, neighbouring rooms), updates from Home Assistant.
API_LEVEL = 2
