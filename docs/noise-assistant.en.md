# Noise assistant

The **minimum volume** of a source is the quietest sound taken into account: below it, the service does not even try to recognise anything. It depends on the gain of each microphone, so no value suits all of them. The noise assistant measures the room and suggests one. **You decide**: by default nothing changes until you type or accept a value and save the source; if you prefer, a source can follow the measurements by itself (see *Automatic mode* below).

## How it works

- The service keeps **one number per source and minute**: the ambient level in dBFS (the median of that minute). **No audio is kept** in these measures, and a minute where a detection happened is marked so that it is left out of the calculation. A source takes about 40 bytes per minute, so about 400 KB per week.
- Once there are **6 hours of calm minutes**, the assistant looks at the quiet half of them (the room at rest), takes its upper part (90th percentile) and adds **6 dB** so that the background noise stays below the minimum.
- The suggestion is **never above -50 dBFS** (and never below -90), so that a distant or muffled alarm is still heard. If the room is noisier than that, the assistant says so and suggests moving the microphone or lowering its gain.

## Using it

In *Sources → Edit*, under **Minimum volume**, the assistant shows what was measured (hours of quiet), the suggested value, a chart of the quiet level by hour of the day with the suggestion (dashed) and your current value (solid), and the level of the moment.

- **Use this value** puts the suggestion in the field; you can still change it, and it is kept only when you save the source.
- **Manual mode.** With the setting on *Manual*, type any value in the field instead: it always wins over the suggestion, and the assistant never touches it. The level of the moment and the chart help you choose.

The minimum volume can also be set for one sound in that sound's settings (the stricter of the two applies, see [Per-source settings](source-settings.en.md)).

## Automatic mode

Each source has a setting, **Who sets the minimum volume**: *Follow the default*, *Automatic* or *Manual* (the default is manual, so nothing moves unless you ask). In **Settings → Default values**, *Adjust the minimum volume automatically on every source* turns it on for all the sources at once; a source can still choose *Manual* (or *Automatic*) in its own form, the usual order of settings.

In automatic mode the service looks at the measures **once a day** and applies the suggestion, with some care:

- nothing happens before **6 hours of calm** have been measured; until then the value of the field applies;
- the value only **moves when the new suggestion differs from the one in use by at least 3 dB**, so that it does not wobble;
- it stays between -90 and -50 dBFS, like the suggestion;
- **your configuration is not rewritten**: the automatic value is kept next to it by the service. The value typed in the field stays where it is and is used again if you go back to *Manual*;
- a minimum volume set for one sound on a source (that sound's settings) still applies;
- erasing the measures does not change the value in use; the service waits for new measures before moving it again.

The source form shows the value in use and since when, what is waited for, and the **last changes** (the 5 latest, from and to). In the list of the sources, each line says the minimum volume in use and who set it (*automatic*, *set by hand*, *from a preset*, *default*), and the per-sound table of a sound's settings shows the automatic value too.

## Measures kept, and deleting them

*Settings → Noise measurements* lists, for each source, the number of measures (minutes), since when, and the room they take, with **Delete** for one source and **Delete all the measurements** (both ask for a confirmation). After a deletion the service measures again, and the assistant waits for 6 hours of calm before suggesting.

**Days to keep the measurements** (`storage.noise_retention_days`, 7 by default, 0 to 90): older measures are deleted automatically; **0 measures nothing** and the assistant is then switched off.
