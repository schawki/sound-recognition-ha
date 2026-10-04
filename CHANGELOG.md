# Changelog

Releases are tagged `vX.Y.Z`; the service updates itself from Home Assistant to the latest tag.

## 0.2.1

- Fix a Home Assistant deprecation warning: audio source devices are now linked to the service device with its registry id (`via_device_id`).

## 0.2.0

- Update the service from Home Assistant: an Update entity and a panel banner tell when a newer release exists, one click installs it, and a notification says when the service is back online (or why the update failed).
- The service reports its `api_level`; a repair asks for an update when the service is too old for the integration.
- Context-aware sensitivity driven by Home Assistant devices (TV, music, vacuum…) and rooms, with a shared context between connected rooms.
- Home Structure (separate integration) is used for rooms, separations and opening sensors when installed; the internal description stays as a fallback.
- Manual update remains possible: `git -C /opt/sound-recognition-ha pull && bash /opt/sound-recognition-ha/deploy/install.sh` (needed once to install the update helper).

## 0.1.0

- First release: YAMNet service, Home Assistant integration, sidebar panel.
