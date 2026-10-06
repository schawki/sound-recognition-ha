# Changelog

Releases are tagged `vX.Y.Z`; the service updates itself from Home Assistant to the latest tag.

## 0.11.0

- **How long to keep clips, by kind of sound.** Four settings (usual sounds, sensitive sounds, context sounds such as music and television, conversations), global (*Clips* tab) or per source (source form). A sound's own setting still wins, and the maximum and the "allow clips" switch of each source still apply. Nothing changes until you set them.
- **Conversations can be kept, knowingly.** The catalog's ban is now only the default (0 days). The panel and the advice warn about private speech and the law whenever clips of conversations are kept.
- **The detection is good.** A new button next to "The detection is wrong", on detections that have a clip (*Live* and *Clips*). The *Overview* shows the confirmed ones and the share of good detections among those you judged; *Clips* filters on the verdict.
- **No verdict without a clip.** Detections that have no clip cannot be checked, so the control is not offered; their "No clip" line says why.
- **Delete the detections without a clip** (*Clips*), following the filters. The ones you marked wrong or confirmed stay.
- Service API level 8: update the service from Home Assistant after updating the integration.

## 0.10.1

- **"No clip" now says why.** In *Live*, a detection without a clip explains the real cause: you turned clips off for this sound or this source, the sound is not recorded by default (a context sound), it is a private sound, the retention maximum is 0 days, or the clip was deleted or expired. Only causes the service really recorded are shown; an older detection gets a neutral sentence.
- **"The detection is wrong"** replaces "Not a real sound", and the same control is now on every clip in the *Clips* tab.

## 0.10.0

- **ESP32 microphones (ESPHome) as sources.** A small ESPHome component (`esphome/components/sound_recognition_stream`) streams the audio of an I2S microphone (INMP441...) over the network; the service connects to it, reads it and reconnects by itself if the Wi-Fi drops. Guide: `docs/esphome-microphone.en.md`.
- **A password protects the stream.** It is mandatory in the ESPHome configuration (8 characters or more, in `secrets.yaml`). The service proves it knows it without ever sending it, and the device sends no audio to anyone who cannot. The service never shows the password again (the API and the panel show `***`). The audio is **not encrypted** on the network: see the guide for a separate IoT network.
- **Found by themselves.** In *Sources → Add → ESP32 microphone*, the devices that run the component are listed (Home Assistant already knows their address and room) with a *Use* button. For a device not flashed yet, the form shows the ESPHome configuration to copy.
- Service API level 7: update the service from Home Assistant after updating the integration.
- The component is checked on a PC against the service client (audio, wrong password, takeover by a second client) and compiled for an ESP32 by the CI. It has not been tried on a real microphone yet.

## 0.9.2

- The *parent and child* advice no longer concerns a context at all (*Fireworks*, *Television*, *Music*...): a context only raises thresholds, so it has no alert rule that could conflict with its parent or child. 0.9.1 only covered two contexts together.
- A test now follows the gestures of the advice one after the other, from the sounds of every rule and every pair of rules, with the home recommendations that switch contexts on, and checks that it always ends: no advice undoes what another asks for. It found the loop of 0.9.1 before the fix, and none after.

## 0.9.1

- Fix: enabling *Fireworks* and *Firecracker* (what the fireworks advice and the advice drawn from a garden next door both do) raised a *parent and child* advice about those same two sounds, and choosing one of its buttons brought the first advice back. Two sounds that are only contexts, used to raise thresholds, are no longer treated as conflicting alerts.

## 0.9.0

- Advice between close sounds now offers a choice instead of plain text: one button per sound that is on, *Keep X only*, which switches the others off. The sound the catalog recommends comes first, as the main button. It covers close doorbell sounds, dog sounds (*Dog*, *Bark*, canids), glass sounds, shouts and screams, and any class that contains another one (parent and child, with no recommendation).
- *Music*: one button, keep *Music* as context and switch its sub-classes off. A broad class (such as *Dog*): one button that switches it off and switches on its sub-classes.
- After a choice the advice leaves *To do* and appears under *Applied* with its date and *Undo*. Sounds the choice switched off stay off after *Undo*, because their base value is off: the card says so before you click, and they come back from the Sounds tab.
- Service API level 6 (`choices` on warnings): update the service from Home Assistant after updating the integration. Without it the panel works but shows no choice buttons. In Repairs these advice stay plain alerts.
- Catalog rules say it once: `choose: {recommended: <sound>}` for a choice between the sounds of the rule, `fix` for a single gesture; `tools/validate.py` checks both.

## 0.8.1

- Fix for the Home Assistant validation (hassfest, red since 0.6.4): an issue in Repairs is either fixable or has a description, never both. The advice that has a *Fix* button now has its own entry whose confirmation shows the advice, then what will change. A test now guards this rule.

## 0.8.0

- The Advice tab is rebuilt around decisions. A summary at the top (*3 to do · 5 applied · 2 hidden*) and a filter by source, then four sections: *To do*, *Information*, *Applied*, *Hidden*.
- Every advice now says **why** (the problem), **what its button changes** (one line per setting, for example *Smoke detector: minimum duration 3 s*) and **where it stands**.
- **Undo** on every applied advice: it takes the settings of the advice off the source, so the base value of the catalog (or your global setting) applies again; the card says what will come back before you click. Afterwards the advice is back in *To do*, and you can hide it right away. For an advice that switched a sound off, the base value is *off*: undoing does not switch it back on (use the Sounds tab).
- An advice applied with its button leaves a small trace on its source (`applied_advice` in the configuration: rule, message, date, settings). That is what keeps an advice visible under *Applied* once its cause is gone from the list, with the date. The same trace is written by the *Fix* button of Home Assistant Repairs. Advice applied before this version has no date; it is shown while its warning is, and undone the same way.
- Hiding moved out of the folded settings: *Hide* on the card, *Show again* in the *Hidden* section. The level of each advice (information, warning, danger) is still adjustable, folded under *Importance*.
- No service API change: the service only checks the trace in the configuration.

## 0.7.0

- More advice now has an *Apply* button (and a *Fix* button in Home Assistant Repairs), when the warning says exactly what to do:
  - a threshold that is too low for a sound often triggered by mistake goes back to the suggested one;
  - a safety sound whose source schedule has gaps gets a continuous schedule of its own;
  - a sound sensitive to television, radio or music gets its inhibiting contexts switched on (*Television* and *Radio* for the sounds that react to them);
  - *Baby cry* asked to hold for 2 seconds when a cat is also listened to;
  - *Beep* switched off and 3 seconds required for *Smoke detector*; *Fire* and *Crackle* switched off as fire alerts;
  - a clip retention that the catalog forbids is removed from the source (when the global setting does not ask for it too).
- When the gesture switches something on or sets a duration the advice stays, marked *Already applied*. When it removes the cause (a sound switched off, a threshold corrected) the advice leaves the list.
- The confirmation of the Repairs fix now lists each change (*Beep: switched off*, *Smoke detector: minimum duration 3 s*...), not only the sounds switched on.
- Catalog rules can now carry a gesture made of `enable`, `disable` and `set` (duration, threshold, cooldown, retention); `tools/validate.py` checks it. The advice API format is unchanged, no service update is required beyond the version.

## 0.6.5

- The alert at the top of the Live view counts what the Advice tab shows first (advice to do and warnings), no longer the advice that is already applied: it used to announce an advice you could not find. A hidden advice is never counted.
- The alert is a link: a click opens the Advice tab on the first advice and highlights it. Each line of the summary in the Overview leads to its own advice in the same way.

## 0.6.4

- Repairs: an advice that is already applied no longer raises an alert in Home Assistant (the warning about fireworks and firecrackers kept coming back after the two sounds were enabled).
- Repairs: an advice that has a gesture is now fixable. The *Fix* button of the alert opens a confirmation that says what will be switched on, then saves it on the source, like the *Apply* button of the panel. Warnings without a gesture stay plain alerts.

## 0.6.3

- One list of advice: the recommendations of the Overview and the warnings of the Advice tab are now in the Advice tab. What can be done in one click has an *Apply* button; what is already in place says *Already applied* and is kept in a folded group at the bottom, so you can check it took effect. Warnings with nothing to apply stay information, with their display settings folded under *Display*. The Overview only summarises what needs attention and opens the tab.
- The warning about fireworks and firecrackers being mistaken for gunshots now has its gesture (enable those two sounds as contexts) and no longer contradicts the recommendation drawn from the home: it is one advice, shown once.
- Service API level 5 (`applied` and `apply` on warnings, `applied` on recommendations): update the service from Home Assistant after updating the integration.

## 0.6.2

- Fix: a recommendation drawn from the home (such as enabling the sounds of a TV next door) stayed in the list after being applied. The list now reads the saved configuration instead of a copy kept before the integration reloads, and recognises a sound switched on under its AudioSet name as well as under its id; a choice made on the source wins over the global one, as in the service.

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
