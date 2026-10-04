# Context sounds, places and adaptive sensitivity

Why a television or music triggers barking, doorbells or shouts, and what the service does about it.

## Context sounds

Television, Radio and Music (and Fireworks, Firecracker for gunshots) are *context sounds*. While one is heard on a source, the threshold of the sounds that look like it is raised by `analysis.context_boost` (0.15 by default). About 24 catalog sounds are affected: barking, doorbell, knocks, shouts and screams, baby cry, sirens, gunshots, glass breaking…

- A context sound only acts on the source where it is enabled. Enable it where such a source exists (living room, kitchen with a radio…), not everywhere: elsewhere it only lowers sensitivity for nothing.
- **Safety sounds** (fire, security and baby usages that the catalog recommends as alerts) are never raised by more than `analysis.safety_boost_cap` (0.05 by default). Set it to 0 to never raise them, or to 1 to treat them like any other sound.
- Other context sounds (wind, rain, traffic…) are reported but do not change any threshold.

## Kind of place and recommendations

Each source can be given a kind of place (`environment`): living room, kitchen, bedroom, baby room, office, entrance, outdoors, garage. The catalog (`catalog/environments.yaml`) says which context sounds fit each place and whether adaptive sensitivity is worth enabling. The **Overview** tab turns that into recommendations with an **Apply** button, and the Sounds tab shows the context sounds grouped, with what is recommended for the chosen source.

Detections marked false (**Not a real sound** button) feed a second recommendation: when the same sound on the same source is marked false at least twice in 14 days, the panel proposes a threshold just above the highest false score.

## Adaptive sensitivity (per source, off by default)

`sources[].adaptive: {enabled: true, max_offset: 0.15}`. The service compares the ambient level (median of the last minute) with the usual quiet level of that source (10th percentile of the per-minute ambient levels of the last 24 hours, known after 30 minutes of listening, forgotten when the service restarts). Up to 6 dB above the usual level nothing changes; 36 dB above it, thresholds are raised by `max_offset`, linearly in between. Safety sounds are capped as above.

Because the baseline needs history, the offset is 0 for the first 30 minutes after a start, and a very long noisy period slowly becomes “usual”.

## Nothing disappears silently

When a raised threshold stops a sound that would have been reported, the service counts it as a *hidden detection* (once per episode, same cooldown as a detection) with its score, the threshold it needed and the cause (context sound, ambient noise). The panel shows them live and in the 24-hour figures. Detections now report the threshold actually applied (`threshold`) and the increase (`offset`).

## Rooms, devices and connected rooms (per source, off by default)

Give a source a Home Assistant room (`sources[].area`) and the integration finds the devices that make sound there: media players (TV, speakers, consoles) and vacuum cleaners. Other entities (a switch for a hood, a fan…) can be added by hand (`devices.include`), and any found device can be left out (`devices.exclude`). Several entities of one physical device (a TV that appears three times) count once.

Nothing is changed until you enable it for the source: `sources[].devices: {enabled: true, max_offset: 0.15, exclude: [], include: []}`. Then, while a device plays, the thresholds of the sounds that look like it are raised, between half and the full `max_offset` depending on the volume (60 % when the device does not report one); muted or off devices count for nothing. Vacuum cleaners count for 80 %, switches and fans for 60 %. The strongest cause wins, they do not add up.

**Connected rooms** (`area_links`, Sources tab): a living room and a hall with no wall are one space, and a kitchen door that is often open lets sound through.

```yaml
area_links:
  - {a: salon, b: entree, type: open}                                  # 100 %
  - {a: entree, b: cuisine, type: door, sensor: binary_sensor.porte}   # open about 70 %, closed about 15 %
  - {a: entree, b: cuisine, type: door}                                # no sensor: about 42 %
```

The devices of a connected room count for the source in proportion to what passes (up to two links, factors multiply). The factors can be changed with `open_factor` and `closed_factor`. A door sensor that is unavailable counts as the average. A sound heard by *another* source of a connected room (a television detected by the living-room microphone) also raises this source, by `context_boost` times that share: it is the same switch, there is nothing else to enable. The total never exceeds `analysis.total_boost_cap` (0.30), and safety sounds stay capped at `safety_boost_cap`.

The integration recomputes within a second of any change and sends the result to the service with a 60 second lifetime, renewed every 20 seconds: if Home Assistant stops, the thresholds go back to normal by themselves. The Overview tab shows what raises each source (for example “TV Salon · 100 % +0.08”), and hidden sounds name their cause (devices in the room, sound heard in a neighbouring room).

All the coefficients (0.15, 70 %, 15 %, 60 %…) are estimates: watch the hidden detections for a few days and adjust `max_offset` per source.
