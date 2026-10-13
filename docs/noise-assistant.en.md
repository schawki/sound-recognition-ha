# Noise assistant

The **minimum volume** of a source is the quietest sound taken into account: below it, the service does not even try to recognise anything. It depends on the gain of each microphone, so no value suits all of them. The noise assistant measures the room and suggests one. **You decide**: nothing changes until you type or accept a value and save the source.

## How it works

- The service keeps **one number per source and minute**: the ambient level in dBFS (the median of that minute). **No audio is kept** in these measures, and a minute where a detection happened is marked so that it is left out of the calculation. A source takes about 40 bytes per minute, so about 400 KB per week.
- Once there are **6 hours of calm minutes**, the assistant looks at the quiet half of them (the room at rest), takes its upper part (90th percentile) and adds **6 dB** so that the background noise stays below the minimum.
- The suggestion is **never above -50 dBFS** (and never below -90), so that a distant or muffled alarm is still heard. If the room is noisier than that, the assistant says so and suggests moving the microphone or lowering its gain.

## Using it

In *Sources → Edit*, under **Minimum volume**, the assistant shows what was measured (hours of quiet), the suggested value, a chart of the quiet level by hour of the day with the suggestion (dashed) and your current value (solid), and the level of the moment.

- **Use this value** puts the suggestion in the field; you can still change it, and it is kept only when you save the source.
- **Manual mode.** Type any value in the field instead: it always wins over the suggestion, and the assistant never touches it. The level of the moment and the chart help you choose.

The minimum volume can also be set for one sound in that sound's settings (the stricter of the two applies, see [Per-source settings](source-settings.en.md)).

## Measures kept, and deleting them

*Settings → Noise measurements* lists, for each source, the number of measures (minutes), since when, and the room they take, with **Delete** for one source and **Delete all the measurements** (both ask for a confirmation). After a deletion the service measures again, and the assistant waits for 6 hours of calm before suggesting.

**Days to keep the measurements** (`storage.noise_retention_days`, 7 by default, 0 to 90): older measures are deleted automatically; **0 measures nothing** and the assistant is then switched off.
