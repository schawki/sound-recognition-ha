# Changelog

Releases are tagged `vX.Y.Z`; the service updates itself from Home Assistant to the latest tag.

## 0.6.1

- Fix: opening a panel right after an update no longer logs a "custom element already defined" error in the browser.
- Fix: the device registry lookup deprecated in recent Home Assistant versions is replaced.

## 0.6.0

- The kind of place of a source now comes from Home Structure: the type of its room (or the kind of its space) gives it automatically and follows any change there. Choosing a place in the source still overrides it. A room without a type is asked to get one in Home Structure. Needs Home Structure 0.6.0, which adds room types (master bedroom, child's bedroom, baby's room, guest room, game room, home cinema, gym, workshop, pantry, cellar, attic, staircase) organised in groups.
- Five new kinds of place so that every Home Structure room type has one: dining room, bathroom (and toilet), laundry and utility room, gym, storage (cellar, attic, pantry, dressing room).
- The source form shows a summary of the devices that count (in the room, in connected rooms, with the share of sound reaching the source); the detailed list and its settings are folded into expert settings.
- Fix: the rooms reached from a source could go beyond two connections, offering devices of far rooms.
- Service API level 4 (`PUT /sources/{id}/place`): update the service from Home Assistant after updating the integration.

## 0.5.0

- Clips tab: the size of each clip, the total of the selection and what all clips take on the disk (with the free space). Filters by source, sound, category (animals, fire…) and period.
- Delete one clip, a selection, everything the filters show, or all clips, after a confirmation that shows the number of clips and the space freed. Detections stay in the history; only the audio goes.
- Service API level 3 (`GET /clips`, `POST /clips/delete`): update the service from Home Assistant after updating the integration.

## 0.4.0

- Sound Recognition no longer describes rooms: the built-in "connected rooms" editor is removed (nothing is transferred; describe the home in Home Structure). Without Home Structure a source only sees the devices of its own room. Needs Home Structure 0.5.0 for the new recommendations.
- Recommendations from the home: the place of a source is proposed from the type of its room, and rules based on the spaces linked to it (street, garden, living room, garage…) propose the adaptive setting or the sounds to enable. The rules are a readable data file, `home_rules.yaml`.
- The plan in the Sources tab shows the type of each room and the kind of each outside space.

## 0.3.0

- The Sources tab draws the plan of your home as laid out in Home Structure (read-only, with the live state of each separation) and links to its editor. Needs Home Structure 0.4.0.
- New separation type *security grille* (grille or mesh door: almost no sound reduction), and a shutter named on one particular window or door of Home Structure now lowers only that separation.
- The update banner shows the version number without a leading "v".

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
