"""Constants for the Sound Recognition integration."""
DOMAIN = "sound_recognition"
PLATFORMS = ["binary_sensor", "event", "sensor", "update"]

DEFAULT_PORT = 8765
UPDATE_INTERVAL_S = 30
SIGNAL_MESSAGE = f"{DOMAIN}_message_{{}}"  # formatted with the config entry id
CLIP_VIEW_URL = "/api/sound_recognition/clip/{entry_id}/{rel:.+}"
CLIP_URL_TEMPLATE = "/api/sound_recognition/clip/{entry_id}/{rel}"
CLIP_SIGN_HOURS = 24
SIGNAL_LIVE = f"{DOMAIN}_live_{{}}"  # every message of the service, for the panel (formatted with the entry id)
PANEL_URL_PATH = "sound-recognition"
PANEL_STATIC_URL = "/sound_recognition_panel"

SOURCE_TYPES = ["rtsp", "go2rtc", "alsa_rpi", "esphome", "file"]

REPO = "schawki/sound-recognition-ha"
MIN_API_LEVEL = 7                 # oldest service this integration works fully with (health.api_level; absent = 1)
RELEASE_CHECK_S = 6 * 3600        # how often GitHub is asked for the latest release
UPDATE_TIMEOUT_S = 10 * 60        # an update that does not finish in this time is reported as failed
MANUAL_UPDATE_COMMAND = "git -C /opt/sound-recognition-ha pull && bash /opt/sound-recognition-ha/deploy/install.sh"
