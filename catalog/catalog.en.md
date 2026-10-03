# Sound class catalog (YAMNet)

This document is the readable version of `catalog.yaml`. It describes the 521 sound classes recognised by YAMNet, with a name, a ranking and suggested settings for each.

## What is certain and what is a judgment

- **Certain (official data)**: the list of the 521 classes, their number, their English names and the parent/child hierarchy (for example “Bark” is part of “Dog”). They come from YAMNet's `yamnet_class_map.csv` and the AudioSet ontology.
- **Judgment (starting suggestions)**: interest for a home, false-alert risk, privacy sensitivity, thresholds, durations, clip retention, groups of close classes and warning rules. They rely on general knowledge of these sounds, **nothing has been measured in a real home**. YAMNet scores are not calibrated probabilities: tune thresholds with your own recordings.

## At a glance

Out of 521 classes, **8** are recommended as alerts, **71** are optional depending on your situation, **35** serve as context or diagnostics, and **407** are ignored by default (including 143 music, instrument and genre classes).

### How to read the fields

- **Interest**: *Monitor* = recommended as an alert; *Optional* = depends on your situation; *Context* = not an alert but lets you raise the thresholds of other classes; *Ignore* = disabled by default.
- **False positives**: how often the class triggers by mistake (television, neighbours, appliances…).
- **Privacy**: *confidential* = conversations, no clip may be kept; *sensitive* = may reveal personal information.
- **Threshold, min. duration, cooldown**: score threshold (0 to 1), sustained detection time before reporting, delay before a new report.
- **Retention**: how long audio clips are kept (0 = no clip).

## 1. Classes to monitor first

These are the most useful classes as alerts. Even these will produce false alerts: the “False positives” field says which ones and why.

### Smoke detector — `Smoke detector, smoke alarm` (No. 393)

- Category: Alarms, bells and signals · sound type: sustained tone
- False positives: **medium** (causes: appliance beeps (microwave, oven, washing machine), alarms of other devices, television)
- Suggestions: threshold 0.4, sustained detection of at least 3 s, cooldown 60 s, clip from 5 s before to 10 s after, kept 90 days
- Part of: Alarm
- The most useful use case. Require sustained detection of at least 3 seconds: an isolated beep must not trigger. It is NOT a replacement for a real smoke detector: it is a redundancy that listens to an existing detector.

### Fire alarm — `Fire alarm` (No. 394)

- Category: Alarms, bells and signals · sound type: sustained tone
- False positives: **medium** (causes: appliance beeps (microwave, oven, washing machine), neighbouring building alarm or drill, television)
- Suggestions: threshold 0.4, sustained detection of at least 3 s, cooldown 60 s, clip from 5 s before to 10 s after, kept 90 days
- Part of: Alarm
- Fire alarm (building siren for example). Close to “Smoke detector”: choose only one as the main alert, the other as confirmation.

### Shattering glass — `Shatter` (No. 437)

- Category: Impacts, breaking and gunshots · sound type: short
- False positives: **medium** (causes: dropped dishes or bottle, television, construction work)
- Suggestions: threshold 0.5, sustained detection of at least 1 s, cooldown 15 s, clip from 5 s before to 5 s after, kept 30 days
- Part of: Glass
- Contexts that should raise the threshold: Television, Radio, Music
- Shattering glass: useful for security (broken window). Confirm with a window sensor or a camera: dropped dishes are frequent.

### Screaming — `Screaming` (No. 11)

- Category: Human voice · sound type: short
- False positives: **high** (causes: children playing, neighbours, radio, television)
- Suggestions: threshold 0.6, sustained detection of at least 1 s, cooldown 15 s, clip from 5 s before to 5 s after, kept 7 days
- Contexts that should raise the threshold: Television, Radio, Music
- Screams: the most useful class for security but also the most prone to false alerts (films, games, playing children). Confirm with a second signal (presence, door, camera) before any action.

### Bark — `Bark` (No. 70)

- Category: Pets · sound type: short
- False positives: **medium** (causes: neighbours' dogs, street, television)
- Suggestions: threshold 0.5, sustained detection of at least 1 s, cooldown 15 s, clip from 5 s before to 5 s after, kept 7 days
- Part of: Animal, Dog, Pets
- Contexts that should raise the threshold: Television, Radio, Music
- Bark: the most useful class for dogs. Prefer “Bark” alone rather than “Dog” + “Bark” (duplicate).

### Doorbell — `Doorbell` (No. 349)

- Category: Alarms, bells and signals · sound type: repeated
- False positives: **medium** (causes: chimes, neighbours' doorbells, phones, doorbells on television)
- Suggestions: threshold 0.5, sustained detection of at least 2 s, cooldown 30 s, clip from 5 s before to 10 s after, kept 7 days
- Part of: Alarm, Door
- Contains: Ding-dong
- Contexts that should raise the threshold: Television, Radio, Music
- Doorbell: useful to notify and to trigger a camera. Electronic melody doorbells are detected better than simple beeps.

### Knock — `Knock` (No. 353)

- Category: Household sounds · sound type: short
- False positives: **medium** (causes: furniture, television, construction work)
- Suggestions: threshold 0.5, sustained detection of at least 1 s, cooldown 15 s, clip from 5 s before to 5 s after, kept 7 days
- Part of: Door
- Contexts that should raise the threshold: Television, Radio, Music
- Knock: useful to notify a visit when the doorbell is missing or broken.

### Baby cry — `Baby cry, infant cry` (No. 20)

- Category: Human voice · sound type: repeated
- False positives: **medium** (causes: cat meows, children playing, television)
- Suggestions: threshold 0.5, sustained detection of at least 2 s, cooldown 30 s, clip from 5 s before to 10 s after, kept 3 days
- Part of: Crying
- Contexts that should raise the threshold: Television, Radio, Music
- Baby cry: a very common use case. Sometimes confused with cat meows (see “Cries and screams”). Requiring at least 2 seconds of continuous detection reduces false alerts.

## 2. Optional classes, by usage

Useful depending on your situation (animals, baby, kitchen, leaks…). They stay disabled until you enable them.

### Security

| Class | False positives | Privacy | Threshold | Note |
|---|---|---|---|---|
| Shout | high | sensitive | 0.6 | Shout: parent class of “Yell”, “Whoop”, “Bellow” and “Children shouting”. Choose “Screaming” as the main alert and keep “Shout” as an option only. |
| Yell | high | sensitive | 0.6 | Yell: sub-class of “Shout”. Duplicate if “Shout” is selected; very sensitive to television and children. |
| Wail or moan (Wail, moan) | high | sensitive | 0.6 | Wail or moan: interesting in theory for distress, but too unreliable to trigger an alert on its own. |
| Groan | high | sensitive | 0.6 | Groan. Do not use alone for fall or distress detection. |
| Explosion | high | normal | 0.6 | Explosion: broad parent class of detonations. Loud and not very specific. |
| Gunshot (Gunshot, gunfire) | high | normal | 0.6 | Gunshot: never trigger a heavy automatic action on this class alone. In regions where firecrackers or fireworks are common, expect many false alerts. |
| Thud (Thump, thud) | high | normal | 0.6 | Thud: a falling object or person, furniture, neighbours. Do not use alone for fall detection. |
| Smash or crash (Smash, crash) | high | normal | 0.55 |  |
| Breaking | high | normal | 0.55 | Breaking in general (not only glass): broader, therefore more false alerts. |
| Clatter | high | normal | 0.5 | Clatter of objects falling or knocking together. |

### Fire

| Class | False positives | Privacy | Threshold | Note |
|---|---|---|---|---|
| Fire | high | normal | 0.6 | Fire: do NOT use as a reliable fire alert (crackling is very close to frying or rain). Keep for context. |

### Door and visitors

| Class | False positives | Privacy | Threshold | Note |
|---|---|---|---|---|
| Door | medium | normal | 0.5 | Parent class of “Doorbell”, “Knock”, “Slam”: do not select together with its children. |
| Ding-dong | medium | normal | 0.5 | Sub-class of “Doorbell”: duplicate if it is already monitored. Useful as a complement for two-tone doorbells. |
| Sliding door | medium | normal | 0.5 |  |
| Slam | medium | normal | 0.55 | Door slam: confused with gunshots (firecrackers) and falling objects. |
| Keys jangling | medium | normal | 0.5 | Keys jangling: a hint of arrival at the door, but unreliable alone. |
| Buzzer | high | normal | 0.55 | Buzzer: intercom, building door release, timers. Very close to appliance beeps. |
| Ding | high | normal | 0.6 | Ding: confused with the doorbell and timers. |

### Baby

| Class | False positives | Privacy | Threshold | Note |
|---|---|---|---|---|
| Crying (Crying, sobbing) | medium | sensitive | 0.55 | Crying of a child or an adult. Redundant with “Baby cry” when watching an infant. |
| Whimper | high | sensitive | 0.6 | Whimper: close to weak crying and to “Dog whimper”. Very vague. |

### Animals

| Class | False positives | Privacy | Threshold | Note |
|---|---|---|---|---|
| Dog | medium | normal | 0.5 | Parent class: includes barking, howling, growling, etc. Choose the specific classes instead. |
| Yip | medium | normal | 0.5 | Sub-class of “Dog”: redundant if “Bark” is already monitored. |
| Howl | medium | normal | 0.5 | Sub-class of “Dog”: redundant if “Bark” is already monitored. |
| Bow-wow | medium | normal | 0.5 | Sub-class of “Dog”: redundant if “Bark” is already monitored. |
| Growling | medium | normal | 0.5 | Sub-class of “Dog”: redundant if “Bark” is already monitored. |
| Dog whimper (Whimper (dog)) | medium | normal | 0.5 | Sub-class of “Dog”: redundant if “Bark” is already monitored. |
| Cat | medium | normal | 0.5 | Parent class: includes meowing, purring, hissing. |
| Meow | medium | normal | 0.5 | Meow: sometimes confused with a baby cry. |
| Hiss | high | normal | 0.5 | Hiss: close to a jet of air or steam (“Steam”, “Spray”). |
| Caterwaul | medium | normal | 0.5 | Fighting cat cries: loud, close to screams or crying. |

### Water and leaks

| Class | False positives | Privacy | Threshold | Note |
|---|---|---|---|---|
| Water tap (Water tap, faucet) | medium | normal | 0.5 | Running water: link it to a duration (tap left open). Confused with the shower and white noise. |
| Sink (filling or washing) | medium | normal | 0.5 | Running water: link it to a duration (tap left open). Confused with the shower and white noise. |
| Bathtub (filling or washing) | medium | normal | 0.5 | Running water: link it to a duration (tap left open). Confused with the shower and white noise. |
| Toilet flush | medium | normal | 0.5 | Toilet flush: a flush that runs continuously can be detected with a duration. |
| Drip | medium | normal | 0.5 | Drip: can signal a tap or a leak, provided the microphone is close and the environment is quiet. |
| Trickle (Trickle, dribble) | medium | normal | 0.5 |  |
| Gush | medium | normal | 0.5 | Gush: possible hint of a major leak. Detects the noise, not the leak: pair it with a water sensor. |
| Fill (with liquid) | medium | normal | 0.5 | Filling: useful for a bathtub or a bucket being filled. Combine with a duration (for example more than 10 minutes). |

### Kitchen

| Class | False positives | Privacy | Threshold | Note |
|---|---|---|---|---|
| Microwave oven | medium | normal | 0.5 | Microwave oven (mostly its end-of-cycle beeps). Source of FALSE alerts on “Smoke detector”: see the combination rules. |
| Whistle | medium | normal | 0.5 | Whistle: can detect a whistling kettle, but is confused with mouth whistling. |
| Steam whistle | medium | normal | 0.5 | Steam whistle: kettle or pressure cooker. To be tested. |
| Boiling | medium | normal | 0.5 | Boiling: can signal a pot or a kettle boiling. Does not replace a stove safety device. |
| Beep (Beep, bleep) | high | normal | 0.6 | Appliance beeps (end of cycle). Very common, so group with “Microwave oven”; do not make it a fire alert. |
| Sizzle | medium | normal | 0.5 | Sizzle: pan cooking. Detects a cooking noise, not a danger. |

### Presence

| Class | False positives | Privacy | Threshold | Note |
|---|---|---|---|---|
| Children shouting | high | sensitive | 0.6 | Almost always a normal sound. Of little use for an alert. |
| Snoring | medium | sensitive | 0.5 | Snoring: indicates that someone is sleeping in the room; sensitive, do not keep clips. |
| Cough | medium | sensitive | 0.5 | Cough: potential health data, therefore sensitive. Do not keep clips. |
| Sneeze | medium | sensitive | 0.5 |  |
| Run | medium | normal | 0.5 | Footsteps: complement a presence sensor but do not replace it; depends heavily on the floor covering and the microphone. |
| Shuffle | medium | normal | 0.5 | Footsteps: complement a presence sensor but do not replace it; depends heavily on the floor covering and the microphone. |
| Footsteps (Walk, footsteps) | medium | normal | 0.5 | Footsteps: complement a presence sensor but do not replace it; depends heavily on the floor covering and the microphone. |
| Children playing | high | sensitive | 0.5 | Children playing: normal in most cases. Can be used to calm other classes (screams). |
| Telephone bell ringing | high | normal | 0.6 | Landline telephone ring. Confused with the doorbell. |
| Ringtone | high | normal | 0.6 | Mobile ringtone: interesting to find a phone or to know it is ringing alone, but very variable (melodies). |

### Voiceless commands

| Class | False positives | Privacy | Threshold | Note |
|---|---|---|---|---|
| Finger snapping | medium | normal | 0.55 | Can be used as a voiceless command (finger snap); to be tested. |
| Clapping | medium | normal | 0.55 | Hand claps: can be used as a voiceless command. Confused with applause and some sharp impacts. |

### Outdoor

| Class | False positives | Privacy | Threshold | Note |
|---|---|---|---|---|
| Car alarm | medium | normal | 0.5 | Car alarm: useful only if the vehicle is within earshot. Repeats in the street, hence many unimportant alerts. |
| Emergency vehicle | high | normal | 0.6 |  |
| Police car (siren) | high | normal | 0.6 |  |
| Ambulance (siren) | high | normal | 0.6 |  |
| Fire engine, fire truck (siren) | high | normal | 0.6 |  |
| Siren | high | normal | 0.6 | Siren in general: parent class of vehicle sirens. Mostly an indicator of what is happening in the street. |

### Weather

| Class | False positives | Privacy | Threshold | Note |
|---|---|---|---|---|
| Thunderstorm | medium | normal | 0.5 | Thunderstorm: can drive automations (close shutters, protect equipment). Confused with heavy construction work. |
| Thunder | medium | normal | 0.5 | Thunder: confused with muffled gunshots. |

### Garage and car

| Class | False positives | Privacy | Threshold | Note |
|---|---|---|---|---|
| Engine starting | medium | normal | 0.5 | Engine starting: possible for a garage or a nearby car (arrival, departure). |
| Idling | medium | normal | 0.5 | Idling engine: for example a car running in a closed garage. Detects the noise, not carbon monoxide. |

### Pests

| Class | False positives | Privacy | Threshold | Note |
|---|---|---|---|---|
| Rodents (Rodents, rats, mice) | high | normal | 0.5 |  |
| Mouse | high | normal | 0.5 | Mouse: possible in an attic or cellar, but very vague; test before building an alert on it. |
| Patter | high | normal | 0.5 | Patter: often confused with light rain or light footsteps. |

### Comfort

| Class | False positives | Privacy | Threshold | Note |
|---|---|---|---|---|
| Alarm clock | medium | normal | 0.5 | Alarm clock ringing: can be used to check that an alarm clock did ring; confused with other beeps. |

### Other uses

| Class | False positives | Privacy | Threshold | Note |
|---|---|---|---|---|
| Whistling | medium | normal | 0.5 | Whistling with the mouth. Close to a whistle (kettle, steam whistle): see “Whistles”. |

## 3. Context and diagnostic classes

They are not alerts. **Context** classes (television, music, speech, rain…) let you raise the thresholds of classes prone to false alerts. **Diagnostic** classes indicate a microphone problem (mains hum, wind, distortion).

### Context

| Class | Privacy | Note |
|---|---|---|
| Speech | confidential | Speech: no clip must be kept. Useful only as context (“someone is talking”) to raise the thresholds of other classes. |
| Child speech (Child speech, kid speaking) | confidential | Same precautions as “Speech”: no clip, context only. |
| Conversation | confidential | Same precautions as “Speech”: no clip, context only. |
| Narration or monologue (Narration, monologue) | confidential | Same precautions as “Speech”: no clip, context only. |
| Babbling | confidential | Same precautions as “Speech”: no clip, context only. |
| Speech synthesizer | normal | Synthetic voice (voice assistant, announcements). Can be used to ignore sounds produced by your own assistants. |
| Chatter | confidential |  |
| Crowd | confidential | Crowd: often the television or the street. Use only as context. |
| Crowd chatter (hubbub) (Hubbub, speech noise, speech babble) | confidential | Crowd chatter: several voices at once. Context only. |
| Bird | normal | Birds in general: acts as an indicator of outdoor ambience (microphone near an open window). |
| Bird song (Bird vocalization, bird call, bird song) | normal |  |
| Music | normal | The most useful class of the music group: a single “music is playing” signal to raise the thresholds of other classes. The 140+ other music classes (instruments, genres) are ignored by default. |
| Wind | normal | Wind: used to put other outdoor detections into perspective. |
| Rain | normal | Rain: useful as context (window left open, laundry outside) and to raise the thresholds of other classes. Confused with white noise and frying. |
| Raindrop | normal | Rain: useful as context (window left open, laundry outside) and to raise the thresholds of other classes. Confused with white noise and frying. |
| Rain on surface | normal | Rain: useful as context (window left open, laundry outside) and to raise the thresholds of other classes. Confused with white noise and frying. |
| Traffic noise (Traffic noise, roadway noise) | normal | Traffic: indicates the outdoor ambience; useful to raise thresholds near a window. |
| Vacuum cleaner | normal | Vacuum cleaner: very recognizable. Useful to ignore other detections during cleaning. |
| Fireworks | normal | Fireworks: use as context to raise the thresholds of “Gunshot”, “Explosion” and “Burst or pop” during festivities. |
| Firecracker | normal | Firecracker: same as “Fireworks”; frequently confused with a gunshot. |
| Inside, small room | normal | Describes the acoustics of the place (room, outdoors) rather than an event: useful only to understand the microphone's environment. |
| Inside, large room or hall | normal | Describes the acoustics of the place (room, outdoors) rather than an event: useful only to understand the microphone's environment. |
| Inside, public space | normal | Describes the acoustics of the place (room, outdoors) rather than an event: useful only to understand the microphone's environment. |
| Outside, urban or manmade | normal | Describes the acoustics of the place (room, outdoors) rather than an event: useful only to understand the microphone's environment. |
| Outside, rural or natural | normal | Describes the acoustics of the place (room, outdoors) rather than an event: useful only to understand the microphone's environment. |
| Television | normal | Television is the first cause of false alerts. As a CONTEXT class, it raises the thresholds of screams, gunshots, barks and doorbells while it is on. |
| Radio | normal | Same use as “Television”: signals that a sound comes from a loudspeaker, not from the room. |

### Microphone diagnostics

| Class | Privacy | Note |
|---|---|---|
| Wind noise (microphone) | normal | Wind in the microphone: indicates that the microphone is exposed to a draught (open window, ventilation). Use it to decide where to move the microphone. |
| Silence | normal | Silence: if this class is constant while there is activity, the microphone is probably muted or badly connected. |
| Static | normal | Microphone quality indicator: a constantly high value often signals a noisy or saturated microphone. |
| Mains hum | normal | Mains hum (50/60 Hz): if permanently high, the microphone picks up electrical noise (power supply, ground loop). Fix on the wiring side. |
| Distortion | normal | Microphone quality indicator: a constantly high value often signals a noisy or saturated microphone. |
| Sidetone | normal | Microphone quality indicator: a constantly high value often signals a noisy or saturated microphone. |
| White noise | normal | Microphone quality indicator: a constantly high value often signals a noisy or saturated microphone. |
| Pink noise | normal | Microphone quality indicator: a constantly high value often signals a noisy or saturated microphone. |

## 4. Groups of close classes

Classes that sound alike or overlap. The integration shows these warnings when you select several classes of the same group.

### Dogs

Classes: Dog, Bark, Yip, Howl, Bow-wow, Growling, Dog whimper, Canids (dogs, wolves)

- **Risk**: “Dog” contains “Bark”, “Yip”, “Bow-wow”, “Growling”, “Howl” and “Dog whimper”: a bark often activates “Dog” at the same time. “Canids (dogs, wolves)” contains only “Growling” and “Howl”.
- **Advice**: Monitor “Bark” alone. Add “Howl” only if howling interests you.

### Cats

Classes: Cat, Meow, Purr, Hiss, Caterwaul

- **Risk**: “Cat” includes the others. Shrill meows resemble a baby crying.
- **Advice**: Choose “Meow” alone; do not combine it with a baby-cry alert without a confirmation rule.

### Cries and screams

Classes: Baby cry, Crying, Whimper, Wail or moan, Meow, Caterwaul, Screaming, Squeal

- **Risk**: High-pitched, plaintive sounds that get confused with each other (baby, cat, human scream, squeal).
- **Advice**: If you watch a baby: “Baby cry” with at least 2 seconds of continuous detection; ignore the others.

### Shouts and calls

Classes: Shout, Yell, Screaming, Bellow, Whoop, Children shouting, Children playing, Cheering, Crowd

- **Risk**: Playing children, TV matches and films often trigger these classes.
- **Advice**: Keep “Screaming” (and possibly “Shout”) with a high threshold; use “Television” as context.

### Speech, voices and vocal context

Classes: Speech, Conversation, Child speech, Narration or monologue, Babbling, Whispering, Chatter, Crowd chatter (hubbub), Speech synthesizer, Television, Radio

- **Risk**: Privacy: these classes detect conversations. They get confused with television and radio.
- **Advice**: Never keep a clip. Use them as context (“someone is talking”) rather than as an alert.

### Sung voice, chant and broadcast prayer

Classes: Singing, Chant, Mantra, Choir, Vocal music, Middle Eastern music, Humming, Child singing, Synthetic singing, Speech

- **Risk**: A sung or chanted voice broadcast by a loudspeaker (call to prayer, announcements) activates several of these classes, as well as “Speech”.
- **Advice**: Do not make them alerts. If these sounds are frequent where you live, raise the thresholds of the other vocal classes at those times.

### Detonations and sharp impacts

Classes: Gunshot, Machine gun, Fusillade, Artillery fire, Cap gun, Fireworks, Firecracker, Explosion, Boom, Bang, Burst or pop, Slam, Thud, Thunk, Thunder

- **Risk**: Firecrackers, fireworks, slamming doors and thunder are easily mistaken for a gunshot.
- **Advice**: Never trigger a heavy action on these classes alone. Use “Fireworks” and “Firecracker” as inhibiting context.

### Glass and breaking

Classes: Glass, Shattering glass, Glass clink, Breaking, Smash or crash, Dishes, pots, and pans, Cutlery, silverware, Clatter

- **Risk**: Dropped or clinking dishes resemble breaking glass.
- **Advice**: Keep “Shattering glass” alone for security; “Breaking” and “Clatter” as options. Confirm with an opening sensor or a camera.

### Fire alarms and appliance beeps

Classes: Smoke detector, Fire alarm, Alarm, Buzzer, Beep, Microwave oven, Reversing beeps, Alarm clock

- **Risk**: An isolated beep from a microwave or washing machine can resemble a smoke detector.
- **Advice**: For the fire alert: “Smoke detector” and “Fire alarm” with at least 3 seconds of sustained detection. Do not add “Beep” as an alert.

### Doorbells, ringtones and bells

Classes: Doorbell, Ding-dong, Ding, Ping, Bell, Church bell, Chime, Wind chime, Jingle bell, Bicycle bell, Telephone bell ringing, Ringtone, Telephone, Jingle, Tuning fork

- **Risk**: Telephone rings, television rings and bells are close to a doorbell.
- **Advice**: For the door: “Doorbell” alone. Telephone rings and bells stay out of alerts.

### Sirens and horns

Classes: Siren, Police car (siren), Ambulance (siren), Fire engine, fire truck (siren), Emergency vehicle, Civil defense siren, Car alarm, Car horn, Toot, Air horn, Foghorn

- **Risk**: Very frequent street sounds, confused with each other and with television.
- **Advice**: Useful only as an outdoor indicator; do not trigger a home alert.

### Whistles

Classes: Whistle, Steam whistle, Whistling, Train whistle, Hiss, Steam

- **Risk**: A whistling kettle, mouth whistling and a steam leak are close.
- **Advice**: Test with your kitchen before building an automation.

### Doors, knocks and bangs

Classes: Knock, Door, Slam, Tap, Sliding door, Thud, Thunk, Bang, Cupboard open or close, Drawer open or close, Squeak

- **Risk**: Knocks, drawers and furniture get confused. “Door” includes several sounds.
- **Advice**: Choose “Knock” for a visit, “Slam” for slamming; avoid “Door” and “Tap”.

### Running water, leaks

Classes: Water tap, Sink (filling or washing), Bathtub (filling or washing), Pour, Trickle, Gush, Fill (with liquid), Drip, Splash, Stream, Toilet flush, Rain, Rain on surface, Raindrop, Boiling, White noise

- **Risk**: A tap, the shower, rain and white noise sound alike. None of these classes detects water: only its noise.
- **Advice**: Always pair with a duration and a real water sensor for leaks.

### Motors and continuous appliances

Classes: Vacuum cleaner, Hair dryer, Blender, Mechanical fan, Air conditioning, Engine, Light engine (high frequency), Medium engine (mid frequency), Heavy engine (low frequency), Idling, Lawn mower, Power tool, Drill, White noise, Pink noise, Noise, Environmental noise, Whir, Hum

- **Risk**: Continuous noises that get confused with each other and mask other sounds.
- **Advice**: Treat them as context: they mostly explain why other classes are less sensitive.

### Footsteps and presence

Classes: Footsteps, Run, Shuffle, Patter, Typing, Computer keyboard, Keys jangling, Finger snapping, Clapping

- **Risk**: A presence sensor does better. Footsteps depend on the floor, the microphone and the neighbours.
- **Advice**: Use as a complement to a presence sensor, not instead of it.

### Coughs, sneezes and breathing

Classes: Cough, Throat clearing, Sneeze, Sniff, Snort, Wheeze, Breathing, Snoring, Gasp, Pant, Sigh

- **Risk**: Sounds close to each other; they relate to health, therefore sensitive.
- **Advice**: Do not keep clips. Reserve for discreet presence uses.

### Insects and rodents

Classes: Insect, Mosquito, Housefly, Buzz, Bee or wasp, Cricket, Mouse, Rodents, Patter, Scratch

- **Risk**: Very faint and very close to appliance or plumbing noises.
- **Advice**: Unreliable; try only with a nearby microphone (attic, cellar).

### Birds

Classes: Bird, Bird song, Chirp, Squawk, Pigeon or dove, Coo, Crow, Caw, Owl, Hoot, Chicken or rooster, Rooster crow, Bird flight, flapping wings

- **Risk**: “Bird” includes almost all the other classes of this group.
- **Advice**: Useful only as an indicator of outdoor ambience.

### Vehicles in the street

Classes: Vehicle, Motor vehicle (road), Car, Car passing by, Truck, Bus, Motorcycle, Traffic noise, Engine, Engine starting, Idling, Accelerating, revving, vroom, Skidding, Tire squeal

- **Risk**: Omnipresent street sounds; a microphone near a window picks them up continuously.
- **Advice**: Use them as outdoor context; ignore their events.

### Fire, crackle and cooking

Classes: Fire, Crackle, Frying (food), Sizzle, Rustling leaves, Rain on surface, Static

- **Risk**: Fire, frying, rain and static sound very much alike.
- **Advice**: Do not use “Fire” as a fire alert. Rely on a real smoke detector.

### Microphone quality diagnostics

Classes: Mains hum, Static, White noise, Pink noise, Distortion, Silence, Wind noise (microphone), Sidetone, Reverberation

- **Risk**: These classes do not describe an event in the house but the state of the microphone and its wiring.
- **Advice**: Watch them during setup: a constant “Mains hum”, wind or distortion points to a hardware problem.

### Music

Classes: Music, Song, Background music, Theme music, Soundtrack music, Pop music, Singing, Television, Radio

- **Risk**: Background music activates many classes (voices, instruments, bells).
- **Advice**: Keep “Music” as context; ignore instruments and genres.

## 5. Warning rules

### Rules on specific combinations

| Level | Classes concerned | Applies when | Warning |
|---|---|---|---|
| info | Smoke detector, Fire alarm | all selected | “Smoke detector” and “Fire alarm” are very close: one event can trigger both. Use the same action for both and count a single alert (cooldown). |
| warning | Smoke detector, Beep | all selected | “Beep” also triggers on microwave ovens and washing machines: do not use it as a fire alert, and require sustained detection of at least 3 seconds for “Smoke detector”. |
| warning | Fire, Crackle | any one selected | “Fire” and “Crackle” get confused with frying and rain: do not use them as a fire alert. |
| warning | Gunshot, Explosion, Fireworks, Firecracker | any one selected | Fireworks and firecrackers get confused with gunshots. Use “Fireworks” and “Firecracker” as inhibiting context, not as events, and do not trigger a heavy action on “Gunshot” alone. |
| warning | Doorbell, Ding-dong, Ding, Bell, Chime | at least two selected | Several doorbell/bell classes trigger at the same time. Keep “Doorbell” as the main alert. |
| warning | Doorbell, Telephone bell ringing, Ringtone | at least two selected | Telephone rings can trigger “Doorbell”. Measure the confusions at home before automating. |
| warning | Baby cry, Meow, Caterwaul | at least two selected | Meows (especially cat cries) are sometimes classified as a baby cry: require sustained detection of at least 2 seconds and a suitable threshold. |
| info | Shout, Yell, Screaming, Children shouting | at least two selected | These classes are neighbours: choose one as the main alert (for example “Screaming”). The others will produce duplicate alerts. |
| info | Glass, Shattering glass, Breaking, Smash or crash | at least two selected | “Glass” is the parent of “Shattering glass”: choose “Shattering glass” alone, and “Breaking” or “Smash or crash” as an option with a higher threshold. |
| info | Dog, Bark, Canids (dogs, wolves) | at least two selected | “Dog” contains “Bark” (and “Yip”, “Bow-wow”, “Growling”, “Howl”): a bark triggers both. Keep “Bark”. “Canids (dogs, wolves)” is redundant and noisier. |
| warning | Speech, Conversation, Whispering, Child speech | any one selected | Speech classes: they detect conversations. No clip must be kept; use them only as context. |
| warning | Water tap, Gush, Drip, Fill (with liquid) | any one selected | These classes detect the noise of water, not water. For a leak, add a real water sensor and a minimum duration (for example 5 to 10 minutes). |
| info | Music, Song, Singing, Vocal music, Pop music, Background music | at least two selected | When music plays, many classes (voices, instruments, bells) activate. Monitor “Music” as context rather than its sub-classes. |
| info | Screaming, Gunshot, Bark, Doorbell, Shattering glass | any one selected | These classes are sensitive to television and radio. Add “Television” and “Radio” as context to raise the thresholds automatically. |

### Rules applied automatically

They are deduced from each class's fields, without a list to maintain.

- **info** — *a selected class is an ancestor (ancestors / descendants) of another selected class*: “{parent}” contains “{child}”: one sound will trigger both. Keep the more precise one, or the broader one, but not both with different rules (retention, threshold, action).
- **danger** — *clip_retention_days > 0 on a class whose clip_forbidden is true*: “{class}” detects conversations: no clip may be kept. Retention is forced to 0.
- **warning** — *threshold below the suggested threshold on a class whose false_positives.level is high*: “{class}” is often triggered by mistake; a threshold this low will multiply false alerts. Add an inhibiting context (television, radio, music).
- **info** — *role is generic*: “{class}” is a broad parent class: prefer its sub-classes ({examples}).
- **info** — *class with non-empty inhibiting_contexts and no context class selected*: “{class}” is sensitive to television, radio or music: select them as context classes to raise the thresholds automatically.
- **warning** — *the source has a schedule with gaps and a safety class has no schedule of its own*: “{class}” is a safety class, but the schedule of “{source}” leaves gaps: it will not be listened for during those hours. Give the class its own continuous schedule to keep it active at all times.
- **warning** — *effective minimum volume above -40 dBFS on a safety class*: The minimum volume of “{source}” ({gate} dBFS) is high for “{class}”: a distant or muffled alarm may fall below it and be missed. Lower the gate or set a lower one for this class.
- **info** — *clips disabled on the source while the class allows retention*: Clips are disabled on “{source}”: the retention of “{class}” is forced to 0 there.

## 6. All classes by category

Each line gives the YAMNet number, the exact model name, the display name, the interest, the false-positive risk and the privacy sensitivity.

### Human voice (36)

| No. | Class (model) | Name | Interest | False pos. | Privacy |
|---|---|---|---|---|---|
| 0 | Speech | Speech | Context | high | confidential |
| 1 | Child speech, kid speaking | Child speech | Context | high | confidential |
| 2 | Conversation | Conversation | Context | high | confidential |
| 3 | Narration, monologue | Narration or monologue | Context | high | confidential |
| 4 | Babbling | Babbling | Context | high | confidential |
| 5 | Speech synthesizer | Speech synthesizer | Context | medium | normal |
| 6 | Shout | Shout | Optional | high | sensitive |
| 7 | Bellow | Bellow | Ignored | high | sensitive |
| 8 | Whoop | Whoop | Ignored | high | sensitive |
| 9 | Yell | Yell | Optional | high | sensitive |
| 10 | Children shouting | Children shouting | Optional | high | sensitive |
| 11 | Screaming | Screaming | Monitor | high | sensitive |
| 12 | Whispering | Whispering | Ignored | high | confidential |
| 13 | Laughter | Laughter | Ignored | high | sensitive |
| 14 | Baby laughter | Baby laughter | Ignored | high | sensitive |
| 15 | Giggle | Giggle | Ignored | high | sensitive |
| 16 | Snicker | Snicker | Ignored | high | sensitive |
| 17 | Belly laugh | Belly laugh | Ignored | high | sensitive |
| 18 | Chuckle, chortle | Chuckle | Ignored | high | sensitive |
| 19 | Crying, sobbing | Crying | Optional | medium | sensitive |
| 20 | Baby cry, infant cry | Baby cry | Monitor | medium | sensitive |
| 21 | Whimper | Whimper | Optional | high | sensitive |
| 22 | Wail, moan | Wail or moan | Optional | high | sensitive |
| 23 | Sigh | Sigh | Ignored | high | sensitive |
| 24 | Singing | Singing | Ignored | high | sensitive |
| 25 | Choir | Choir | Ignored | high | sensitive |
| 26 | Yodeling | Yodeling | Ignored | high | sensitive |
| 27 | Chant | Chant | Ignored | high | sensitive |
| 28 | Mantra | Mantra | Ignored | high | sensitive |
| 29 | Child singing | Child singing | Ignored | high | sensitive |
| 30 | Synthetic singing | Synthetic singing | Ignored | high | sensitive |
| 31 | Rapping | Rapping | Ignored | high | sensitive |
| 32 | Humming | Humming | Ignored | high | sensitive |
| 33 | Groan | Groan | Optional | high | sensitive |
| 34 | Grunt | Grunt | Ignored | high | sensitive |
| 35 | Whistling | Whistling | Optional | medium | normal |

### Body and activities (25)

| No. | Class (model) | Name | Interest | False pos. | Privacy |
|---|---|---|---|---|---|
| 36 | Breathing | Breathing | Ignored | medium | sensitive |
| 37 | Wheeze | Wheeze | Ignored | medium | sensitive |
| 38 | Snoring | Snoring | Optional | medium | sensitive |
| 39 | Gasp | Gasp | Ignored | medium | sensitive |
| 40 | Pant | Pant | Ignored | medium | sensitive |
| 41 | Snort | Snort | Ignored | medium | sensitive |
| 42 | Cough | Cough | Optional | medium | sensitive |
| 43 | Throat clearing | Throat clearing | Ignored | medium | sensitive |
| 44 | Sneeze | Sneeze | Optional | medium | sensitive |
| 45 | Sniff | Sniff | Ignored | medium | sensitive |
| 46 | Run | Run | Optional | medium | normal |
| 47 | Shuffle | Shuffle | Optional | medium | normal |
| 48 | Walk, footsteps | Footsteps | Optional | medium | normal |
| 49 | Chewing, mastication | Chewing, mastication | Ignored | medium | sensitive |
| 50 | Biting | Biting | Ignored | medium | sensitive |
| 51 | Gargling | Gargling | Ignored | medium | sensitive |
| 52 | Stomach rumble | Stomach rumble | Ignored | medium | sensitive |
| 53 | Burping, eructation | Burping, eructation | Ignored | medium | sensitive |
| 54 | Hiccup | Hiccup | Ignored | medium | sensitive |
| 55 | Fart | Fart | Ignored | medium | sensitive |
| 56 | Hands | Hands | Ignored | medium | sensitive |
| 57 | Finger snapping | Finger snapping | Optional | medium | normal |
| 58 | Clapping | Clapping | Optional | medium | normal |
| 59 | Heart sounds, heartbeat | Heartbeat | Ignored | high | sensitive |
| 60 | Heart murmur | Heart murmur | Ignored | high | sensitive |

### Crowds and groups (6)

| No. | Class (model) | Name | Interest | False pos. | Privacy |
|---|---|---|---|---|---|
| 61 | Cheering | Cheering | Ignored | high | sensitive |
| 62 | Applause | Applause | Ignored | high | sensitive |
| 63 | Chatter | Chatter | Context | high | confidential |
| 64 | Crowd | Crowd | Context | high | confidential |
| 65 | Hubbub, speech noise, speech babble | Crowd chatter (hubbub) | Context | high | confidential |
| 66 | Children playing | Children playing | Optional | high | sensitive |

### Pets (13)

| No. | Class (model) | Name | Interest | False pos. | Privacy |
|---|---|---|---|---|---|
| 68 | Domestic animals, pets | Pets | Ignored | medium | normal |
| 69 | Dog | Dog | Optional | medium | normal |
| 70 | Bark | Bark | Monitor | medium | normal |
| 71 | Yip | Yip | Optional | medium | normal |
| 72 | Howl | Howl | Optional | medium | normal |
| 73 | Bow-wow | Bow-wow | Optional | medium | normal |
| 74 | Growling | Growling | Optional | medium | normal |
| 75 | Whimper (dog) | Dog whimper | Optional | medium | normal |
| 76 | Cat | Cat | Optional | medium | normal |
| 77 | Purr | Purr | Ignored | medium | normal |
| 78 | Meow | Meow | Optional | medium | normal |
| 79 | Hiss | Hiss | Optional | high | normal |
| 80 | Caterwaul | Caterwaul | Optional | medium | normal |

### Farm animals (22)

| No. | Class (model) | Name | Interest | False pos. | Privacy |
|---|---|---|---|---|---|
| 81 | Livestock, farm animals, working animals | Farm animals | Ignored | medium | normal |
| 82 | Horse | Horse | Ignored | medium | normal |
| 83 | Clip-clop | Clip-clop | Ignored | medium | normal |
| 84 | Neigh, whinny | Horse neigh | Ignored | medium | normal |
| 85 | Cattle, bovinae | Cattle | Ignored | medium | normal |
| 86 | Moo | Moo | Ignored | medium | normal |
| 87 | Cowbell | Cowbell | Ignored | medium | normal |
| 88 | Pig | Pig | Ignored | medium | normal |
| 89 | Oink | Oink | Ignored | medium | normal |
| 90 | Goat | Goat | Ignored | medium | normal |
| 91 | Bleat | Bleat | Ignored | medium | normal |
| 92 | Sheep | Sheep | Ignored | medium | normal |
| 93 | Fowl | Fowl | Ignored | medium | normal |
| 94 | Chicken, rooster | Chicken or rooster | Ignored | medium | normal |
| 95 | Cluck | Cluck | Ignored | medium | normal |
| 96 | Crowing, cock-a-doodle-doo | Rooster crow | Ignored | medium | normal |
| 97 | Turkey | Turkey | Ignored | medium | normal |
| 98 | Gobble | Gobble | Ignored | medium | normal |
| 99 | Duck | Duck | Ignored | medium | normal |
| 100 | Quack | Quack | Ignored | medium | normal |
| 101 | Goose | Goose | Ignored | medium | normal |
| 102 | Honk | Honk | Ignored | medium | normal |

### Wild animals, birds, insects (30)

| No. | Class (model) | Name | Interest | False pos. | Privacy |
|---|---|---|---|---|---|
| 67 | Animal | Animal | Ignored | medium | normal |
| 103 | Wild animals | Wild animals | Ignored | medium | normal |
| 104 | Roaring cats (lions, tigers) | Roaring cats (lions, tigers) | Ignored | high | normal |
| 105 | Roar | Roar | Ignored | high | normal |
| 106 | Bird | Bird | Context | medium | normal |
| 107 | Bird vocalization, bird call, bird song | Bird song | Context | medium | normal |
| 108 | Chirp, tweet | Chirp | Ignored | medium | normal |
| 109 | Squawk | Squawk | Ignored | medium | normal |
| 110 | Pigeon, dove | Pigeon or dove | Ignored | medium | normal |
| 111 | Coo | Coo | Ignored | medium | normal |
| 112 | Crow | Crow | Ignored | medium | normal |
| 113 | Caw | Caw | Ignored | medium | normal |
| 114 | Owl | Owl | Ignored | medium | normal |
| 115 | Hoot | Hoot | Ignored | medium | normal |
| 116 | Bird flight, flapping wings | Bird flight, flapping wings | Ignored | medium | normal |
| 117 | Canidae, dogs, wolves | Canids (dogs, wolves) | Ignored | medium | normal |
| 118 | Rodents, rats, mice | Rodents | Optional | high | normal |
| 119 | Mouse | Mouse | Optional | high | normal |
| 120 | Patter | Patter | Optional | high | normal |
| 121 | Insect | Insect | Ignored | high | normal |
| 122 | Cricket | Cricket | Ignored | high | normal |
| 123 | Mosquito | Mosquito | Ignored | high | normal |
| 124 | Fly, housefly | Housefly | Ignored | high | normal |
| 125 | Buzz | Buzz | Ignored | high | normal |
| 126 | Bee, wasp, etc. | Bee or wasp | Ignored | high | normal |
| 127 | Frog | Frog | Ignored | medium | normal |
| 128 | Croak | Croak | Ignored | medium | normal |
| 129 | Snake | Snake | Ignored | medium | normal |
| 130 | Rattle | Rattle | Ignored | medium | normal |
| 131 | Whale vocalization | Whale vocalization | Ignored | high | normal |

### Music (144)

| No. | Class (model) | Name | Interest | False pos. | Privacy |
|---|---|---|---|---|---|
| 132 | Music | Music | Context | high | normal |
| 133 | Musical instrument | Musical instrument | Ignored | high | normal |
| 134 | Plucked string instrument | Plucked string instrument | Ignored | high | normal |
| 135 | Guitar | Guitar | Ignored | high | normal |
| 136 | Electric guitar | Electric guitar | Ignored | high | normal |
| 137 | Bass guitar | Bass guitar | Ignored | high | normal |
| 138 | Acoustic guitar | Acoustic guitar | Ignored | high | normal |
| 139 | Steel guitar, slide guitar | Steel guitar, slide guitar | Ignored | high | normal |
| 140 | Tapping (guitar technique) | Tapping (guitar technique) | Ignored | high | normal |
| 141 | Strum | Strum | Ignored | high | normal |
| 142 | Banjo | Banjo | Ignored | high | normal |
| 143 | Sitar | Sitar | Ignored | high | normal |
| 144 | Mandolin | Mandolin | Ignored | high | normal |
| 145 | Zither | Zither | Ignored | high | normal |
| 146 | Ukulele | Ukulele | Ignored | high | normal |
| 147 | Keyboard (musical) | Keyboard (musical) | Ignored | high | normal |
| 148 | Piano | Piano | Ignored | high | normal |
| 149 | Electric piano | Electric piano | Ignored | high | normal |
| 150 | Organ | Organ | Ignored | high | normal |
| 151 | Electronic organ | Electronic organ | Ignored | high | normal |
| 152 | Hammond organ | Hammond organ | Ignored | high | normal |
| 153 | Synthesizer | Synthesizer | Ignored | high | normal |
| 154 | Sampler | Sampler | Ignored | high | normal |
| 155 | Harpsichord | Harpsichord | Ignored | high | normal |
| 156 | Percussion | Percussion | Ignored | high | normal |
| 157 | Drum kit | Drum kit | Ignored | high | normal |
| 158 | Drum machine | Drum machine | Ignored | high | normal |
| 159 | Drum | Drum | Ignored | high | normal |
| 160 | Snare drum | Snare drum | Ignored | high | normal |
| 161 | Rimshot | Rimshot | Ignored | high | normal |
| 162 | Drum roll | Drum roll | Ignored | high | normal |
| 163 | Bass drum | Bass drum | Ignored | high | normal |
| 164 | Timpani | Timpani | Ignored | high | normal |
| 165 | Tabla | Tabla | Ignored | high | normal |
| 166 | Cymbal | Cymbal | Ignored | high | normal |
| 167 | Hi-hat | Hi-hat | Ignored | high | normal |
| 168 | Wood block | Wood block | Ignored | high | normal |
| 169 | Tambourine | Tambourine | Ignored | high | normal |
| 170 | Rattle (instrument) | Rattle (instrument) | Ignored | high | normal |
| 171 | Maraca | Maraca | Ignored | high | normal |
| 172 | Gong | Gong | Ignored | high | normal |
| 173 | Tubular bells | Tubular bells | Ignored | high | normal |
| 174 | Mallet percussion | Mallet percussion | Ignored | high | normal |
| 175 | Marimba, xylophone | Marimba, xylophone | Ignored | high | normal |
| 176 | Glockenspiel | Glockenspiel | Ignored | high | normal |
| 177 | Vibraphone | Vibraphone | Ignored | high | normal |
| 178 | Steelpan | Steelpan | Ignored | high | normal |
| 179 | Orchestra | Orchestra | Ignored | high | normal |
| 180 | Brass instrument | Brass instrument | Ignored | high | normal |
| 181 | French horn | French horn | Ignored | high | normal |
| 182 | Trumpet | Trumpet | Ignored | high | normal |
| 183 | Trombone | Trombone | Ignored | high | normal |
| 184 | Bowed string instrument | Bowed string instrument | Ignored | high | normal |
| 185 | String section | String section | Ignored | high | normal |
| 186 | Violin, fiddle | Violin, fiddle | Ignored | high | normal |
| 187 | Pizzicato | Pizzicato | Ignored | high | normal |
| 188 | Cello | Cello | Ignored | high | normal |
| 189 | Double bass | Double bass | Ignored | high | normal |
| 190 | Wind instrument, woodwind instrument | Wind instrument, woodwind instrument | Ignored | high | normal |
| 191 | Flute | Flute | Ignored | high | normal |
| 192 | Saxophone | Saxophone | Ignored | high | normal |
| 193 | Clarinet | Clarinet | Ignored | high | normal |
| 194 | Harp | Harp | Ignored | high | normal |
| 195 | Bell | Bell | Ignored | medium | normal |
| 196 | Church bell | Church bell | Ignored | medium | normal |
| 197 | Jingle bell | Jingle bell | Ignored | medium | normal |
| 199 | Tuning fork | Tuning fork | Ignored | high | normal |
| 200 | Chime | Chime | Ignored | medium | normal |
| 201 | Wind chime | Wind chime | Ignored | medium | normal |
| 202 | Change ringing (campanology) | Change ringing (campanology) | Ignored | high | normal |
| 203 | Harmonica | Harmonica | Ignored | high | normal |
| 204 | Accordion | Accordion | Ignored | high | normal |
| 205 | Bagpipes | Bagpipes | Ignored | high | normal |
| 206 | Didgeridoo | Didgeridoo | Ignored | high | normal |
| 207 | Shofar | Shofar | Ignored | high | normal |
| 208 | Theremin | Theremin | Ignored | high | normal |
| 209 | Singing bowl | Singing bowl | Ignored | high | normal |
| 210 | Scratching (performance technique) | Scratching (performance technique) | Ignored | high | normal |
| 211 | Pop music | Pop music | Ignored | high | normal |
| 212 | Hip hop music | Hip hop music | Ignored | high | normal |
| 213 | Beatboxing | Beatboxing | Ignored | high | normal |
| 214 | Rock music | Rock music | Ignored | high | normal |
| 215 | Heavy metal | Heavy metal | Ignored | high | normal |
| 216 | Punk rock | Punk rock | Ignored | high | normal |
| 217 | Grunge | Grunge | Ignored | high | normal |
| 218 | Progressive rock | Progressive rock | Ignored | high | normal |
| 219 | Rock and roll | Rock and roll | Ignored | high | normal |
| 220 | Psychedelic rock | Psychedelic rock | Ignored | high | normal |
| 221 | Rhythm and blues | Rhythm and blues | Ignored | high | normal |
| 222 | Soul music | Soul music | Ignored | high | normal |
| 223 | Reggae | Reggae | Ignored | high | normal |
| 224 | Country | Country | Ignored | high | normal |
| 225 | Swing music | Swing music | Ignored | high | normal |
| 226 | Bluegrass | Bluegrass | Ignored | high | normal |
| 227 | Funk | Funk | Ignored | high | normal |
| 228 | Folk music | Folk music | Ignored | high | normal |
| 229 | Middle Eastern music | Middle Eastern music | Ignored | high | normal |
| 230 | Jazz | Jazz | Ignored | high | normal |
| 231 | Disco | Disco | Ignored | high | normal |
| 232 | Classical music | Classical music | Ignored | high | normal |
| 233 | Opera | Opera | Ignored | high | normal |
| 234 | Electronic music | Electronic music | Ignored | high | normal |
| 235 | House music | House music | Ignored | high | normal |
| 236 | Techno | Techno | Ignored | high | normal |
| 237 | Dubstep | Dubstep | Ignored | high | normal |
| 238 | Drum and bass | Drum and bass | Ignored | high | normal |
| 239 | Electronica | Electronica | Ignored | high | normal |
| 240 | Electronic dance music | Electronic dance music | Ignored | high | normal |
| 241 | Ambient music | Ambient music | Ignored | high | normal |
| 242 | Trance music | Trance music | Ignored | high | normal |
| 243 | Music of Latin America | Music of Latin America | Ignored | high | normal |
| 244 | Salsa music | Salsa music | Ignored | high | normal |
| 245 | Flamenco | Flamenco | Ignored | high | normal |
| 246 | Blues | Blues | Ignored | high | normal |
| 247 | Music for children | Music for children | Ignored | high | normal |
| 248 | New-age music | New-age music | Ignored | high | normal |
| 249 | Vocal music | Vocal music | Ignored | high | normal |
| 250 | A capella | A capella | Ignored | high | normal |
| 251 | Music of Africa | Music of Africa | Ignored | high | normal |
| 252 | Afrobeat | Afrobeat | Ignored | high | normal |
| 253 | Christian music | Christian music | Ignored | high | normal |
| 254 | Gospel music | Gospel music | Ignored | high | normal |
| 255 | Music of Asia | Music of Asia | Ignored | high | normal |
| 256 | Carnatic music | Carnatic music | Ignored | high | normal |
| 257 | Music of Bollywood | Music of Bollywood | Ignored | high | normal |
| 258 | Ska | Ska | Ignored | high | normal |
| 259 | Traditional music | Traditional music | Ignored | high | normal |
| 260 | Independent music | Independent music | Ignored | high | normal |
| 261 | Song | Song | Ignored | high | normal |
| 262 | Background music | Background music | Ignored | high | normal |
| 263 | Theme music | Theme music | Ignored | high | normal |
| 264 | Jingle (music) | Jingle (music) | Ignored | high | normal |
| 265 | Soundtrack music | Soundtrack music | Ignored | high | normal |
| 266 | Lullaby | Lullaby | Ignored | high | normal |
| 267 | Video game music | Video game music | Ignored | high | normal |
| 268 | Christmas music | Christmas music | Ignored | high | normal |
| 269 | Dance music | Dance music | Ignored | high | normal |
| 270 | Wedding music | Wedding music | Ignored | high | normal |
| 271 | Happy music | Happy music | Ignored | high | normal |
| 272 | Sad music | Sad music | Ignored | high | normal |
| 273 | Tender music | Tender music | Ignored | high | normal |
| 274 | Exciting music | Exciting music | Ignored | high | normal |
| 275 | Angry music | Angry music | Ignored | high | normal |
| 276 | Scary music | Scary music | Ignored | high | normal |

### Alarms, bells and signals (26)

| No. | Class (model) | Name | Interest | False pos. | Privacy |
|---|---|---|---|---|---|
| 198 | Bicycle bell | Bicycle bell | Ignored | medium | normal |
| 302 | Vehicle horn, car horn, honking | Car horn | Ignored | high | normal |
| 303 | Toot | Toot | Ignored | high | normal |
| 304 | Car alarm | Car alarm | Optional | medium | normal |
| 312 | Air horn, truck horn | Air horn | Ignored | high | normal |
| 317 | Police car (siren) | Police car (siren) | Optional | high | normal |
| 318 | Ambulance (siren) | Ambulance (siren) | Optional | high | normal |
| 319 | Fire engine, fire truck (siren) | Fire engine, fire truck (siren) | Optional | high | normal |
| 349 | Doorbell | Doorbell | Monitor | medium | normal |
| 350 | Ding-dong | Ding-dong | Optional | medium | normal |
| 382 | Alarm | Alarm | Ignored | high | normal |
| 383 | Telephone | Telephone | Ignored | high | normal |
| 384 | Telephone bell ringing | Telephone bell ringing | Optional | high | normal |
| 385 | Ringtone | Ringtone | Optional | high | normal |
| 386 | Telephone dialing, DTMF | Telephone dialing, DTMF | Ignored | medium | normal |
| 387 | Dial tone | Dial tone | Ignored | medium | normal |
| 388 | Busy signal | Busy signal | Ignored | medium | normal |
| 389 | Alarm clock | Alarm clock | Optional | medium | normal |
| 390 | Siren | Siren | Optional | high | normal |
| 391 | Civil defense siren | Civil defense siren | Ignored | high | normal |
| 392 | Buzzer | Buzzer | Optional | high | normal |
| 393 | Smoke detector, smoke alarm | Smoke detector | Monitor | medium | normal |
| 394 | Fire alarm | Fire alarm | Monitor | medium | normal |
| 395 | Foghorn | Foghorn | Ignored | medium | normal |
| 396 | Whistle | Whistle | Optional | medium | normal |
| 397 | Steam whistle | Steam whistle | Optional | medium | normal |

### Wind, storms and fire (7)

| No. | Class (model) | Name | Interest | False pos. | Privacy |
|---|---|---|---|---|---|
| 277 | Wind | Wind | Context | high | normal |
| 278 | Rustling leaves | Rustling leaves | Ignored | medium | normal |
| 279 | Wind noise (microphone) | Wind noise (microphone) | Context | high | normal |
| 280 | Thunderstorm | Thunderstorm | Optional | medium | normal |
| 281 | Thunder | Thunder | Optional | medium | normal |
| 292 | Fire | Fire | Optional | high | normal |
| 293 | Crackle | Crackle | Ignored | high | normal |

### Water and liquids (23)

| No. | Class (model) | Name | Interest | False pos. | Privacy |
|---|---|---|---|---|---|
| 282 | Water | Water | Ignored | medium | normal |
| 283 | Rain | Rain | Context | medium | normal |
| 284 | Raindrop | Raindrop | Context | medium | normal |
| 285 | Rain on surface | Rain on surface | Context | medium | normal |
| 286 | Stream | Stream | Ignored | medium | normal |
| 287 | Waterfall | Waterfall | Ignored | medium | normal |
| 288 | Ocean | Ocean | Ignored | medium | normal |
| 289 | Waves, surf | Waves | Ignored | medium | normal |
| 290 | Steam | Steam | Ignored | high | normal |
| 291 | Gurgling | Gurgling | Ignored | medium | normal |
| 438 | Liquid | Liquid | Ignored | medium | normal |
| 439 | Splash, splatter | Splash | Ignored | medium | normal |
| 440 | Slosh | Slosh | Ignored | medium | normal |
| 441 | Squish | Squish | Ignored | medium | normal |
| 442 | Drip | Drip | Optional | medium | normal |
| 443 | Pour | Pour | Ignored | medium | normal |
| 444 | Trickle, dribble | Trickle | Optional | medium | normal |
| 445 | Gush | Gush | Optional | medium | normal |
| 446 | Fill (with liquid) | Fill (with liquid) | Optional | medium | normal |
| 447 | Spray | Spray | Ignored | medium | normal |
| 448 | Pump (liquid) | Pump (liquid) | Ignored | medium | normal |
| 449 | Stir | Stir | Ignored | medium | normal |
| 450 | Boiling | Boiling | Optional | medium | normal |

### Vehicles and engines (47)

| No. | Class (model) | Name | Interest | False pos. | Privacy |
|---|---|---|---|---|---|
| 294 | Vehicle | Vehicle | Ignored | medium | normal |
| 295 | Boat, Water vehicle | Boat, Water vehicle | Ignored | medium | normal |
| 296 | Sailboat, sailing ship | Sailboat, sailing ship | Ignored | medium | normal |
| 297 | Rowboat, canoe, kayak | Rowboat, canoe, kayak | Ignored | medium | normal |
| 298 | Motorboat, speedboat | Motorboat, speedboat | Ignored | medium | normal |
| 299 | Ship | Ship | Ignored | medium | normal |
| 300 | Motor vehicle (road) | Motor vehicle (road) | Ignored | medium | normal |
| 301 | Car | Car | Ignored | medium | normal |
| 305 | Power windows, electric windows | Power windows, electric windows | Ignored | medium | normal |
| 306 | Skidding | Skidding | Ignored | medium | normal |
| 307 | Tire squeal | Tire squeal | Ignored | medium | normal |
| 308 | Car passing by | Car passing by | Ignored | medium | normal |
| 309 | Race car, auto racing | Race car, auto racing | Ignored | medium | normal |
| 310 | Truck | Truck | Ignored | medium | normal |
| 311 | Air brake | Air brake | Ignored | medium | normal |
| 313 | Reversing beeps | Reversing beeps | Ignored | high | normal |
| 314 | Ice cream truck, ice cream van | Ice cream truck, ice cream van | Ignored | medium | normal |
| 315 | Bus | Bus | Ignored | medium | normal |
| 316 | Emergency vehicle | Emergency vehicle | Optional | high | normal |
| 320 | Motorcycle | Motorcycle | Ignored | medium | normal |
| 321 | Traffic noise, roadway noise | Traffic noise | Context | medium | normal |
| 322 | Rail transport | Rail transport | Ignored | medium | normal |
| 323 | Train | Train | Ignored | medium | normal |
| 324 | Train whistle | Train whistle | Ignored | medium | normal |
| 325 | Train horn | Train horn | Ignored | medium | normal |
| 326 | Railroad car, train wagon | Railroad car, train wagon | Ignored | medium | normal |
| 327 | Train wheels squealing | Train wheels squealing | Ignored | medium | normal |
| 328 | Subway, metro, underground | Subway, metro, underground | Ignored | medium | normal |
| 329 | Aircraft | Aircraft | Ignored | medium | normal |
| 330 | Aircraft engine | Aircraft engine | Ignored | medium | normal |
| 331 | Jet engine | Jet engine | Ignored | medium | normal |
| 332 | Propeller, airscrew | Propeller, airscrew | Ignored | medium | normal |
| 333 | Helicopter | Helicopter | Ignored | medium | normal |
| 334 | Fixed-wing aircraft, airplane | Fixed-wing aircraft, airplane | Ignored | medium | normal |
| 335 | Bicycle | Bicycle | Ignored | medium | normal |
| 336 | Skateboard | Skateboard | Ignored | medium | normal |
| 337 | Engine | Engine | Ignored | medium | normal |
| 338 | Light engine (high frequency) | Light engine (high frequency) | Ignored | medium | normal |
| 339 | Dental drill, dentist's drill | Dental drill, dentist's drill | Ignored | medium | normal |
| 340 | Lawn mower | Lawn mower | Ignored | medium | normal |
| 341 | Chainsaw | Chainsaw | Ignored | medium | normal |
| 342 | Medium engine (mid frequency) | Medium engine (mid frequency) | Ignored | medium | normal |
| 343 | Heavy engine (low frequency) | Heavy engine (low frequency) | Ignored | medium | normal |
| 344 | Engine knocking | Engine knocking | Ignored | medium | normal |
| 345 | Engine starting | Engine starting | Optional | medium | normal |
| 346 | Idling | Idling | Optional | medium | normal |
| 347 | Accelerating, revving, vroom | Accelerating, revving, vroom | Ignored | medium | normal |

### Household sounds (32)

| No. | Class (model) | Name | Interest | False pos. | Privacy |
|---|---|---|---|---|---|
| 348 | Door | Door | Optional | medium | normal |
| 351 | Sliding door | Sliding door | Optional | medium | normal |
| 352 | Slam | Slam | Optional | medium | normal |
| 353 | Knock | Knock | Monitor | medium | normal |
| 354 | Tap | Tap | Ignored | high | normal |
| 355 | Squeak | Squeak | Ignored | medium | normal |
| 356 | Cupboard open or close | Cupboard open or close | Ignored | medium | normal |
| 357 | Drawer open or close | Drawer open or close | Ignored | medium | normal |
| 358 | Dishes, pots, and pans | Dishes, pots, and pans | Ignored | medium | normal |
| 359 | Cutlery, silverware | Cutlery, silverware | Ignored | medium | normal |
| 360 | Chopping (food) | Chopping (food) | Ignored | medium | normal |
| 361 | Frying (food) | Frying (food) | Ignored | medium | normal |
| 362 | Microwave oven | Microwave oven | Optional | medium | normal |
| 363 | Blender | Blender | Ignored | medium | normal |
| 364 | Water tap, faucet | Water tap | Optional | medium | normal |
| 365 | Sink (filling or washing) | Sink (filling or washing) | Optional | medium | normal |
| 366 | Bathtub (filling or washing) | Bathtub (filling or washing) | Optional | medium | normal |
| 367 | Hair dryer | Hair dryer | Ignored | medium | normal |
| 368 | Toilet flush | Toilet flush | Optional | medium | normal |
| 369 | Toothbrush | Toothbrush | Ignored | medium | normal |
| 370 | Electric toothbrush | Electric toothbrush | Ignored | medium | normal |
| 371 | Vacuum cleaner | Vacuum cleaner | Context | low | normal |
| 372 | Zipper (clothing) | Zipper (clothing) | Ignored | medium | normal |
| 373 | Keys jangling | Keys jangling | Optional | medium | normal |
| 374 | Coin (dropping) | Coin (dropping) | Ignored | medium | normal |
| 375 | Scissors | Scissors | Ignored | medium | normal |
| 376 | Electric shaver, electric razor | Electric shaver, electric razor | Ignored | medium | normal |
| 377 | Shuffling cards | Shuffling cards | Ignored | medium | normal |
| 378 | Typing | Typing | Ignored | medium | sensitive |
| 379 | Typewriter | Typewriter | Ignored | medium | normal |
| 380 | Computer keyboard | Computer keyboard | Ignored | medium | sensitive |
| 381 | Writing | Writing | Ignored | medium | normal |

### Tools and mechanisms (22)

| No. | Class (model) | Name | Interest | False pos. | Privacy |
|---|---|---|---|---|---|
| 398 | Mechanisms | Mechanisms | Ignored | medium | normal |
| 399 | Ratchet, pawl | Ratchet, pawl | Ignored | medium | normal |
| 400 | Clock | Clock | Ignored | medium | normal |
| 401 | Tick | Tick | Ignored | medium | normal |
| 402 | Tick-tock | Tick-tock | Ignored | medium | normal |
| 403 | Gears | Gears | Ignored | medium | normal |
| 404 | Pulleys | Pulleys | Ignored | medium | normal |
| 405 | Sewing machine | Sewing machine | Ignored | medium | normal |
| 406 | Mechanical fan | Mechanical fan | Ignored | medium | normal |
| 407 | Air conditioning | Air conditioning | Ignored | medium | normal |
| 408 | Cash register | Cash register | Ignored | medium | normal |
| 409 | Printer | Printer | Ignored | medium | normal |
| 410 | Camera | Camera | Ignored | medium | normal |
| 411 | Single-lens reflex camera | Single-lens reflex camera | Ignored | medium | normal |
| 412 | Tools | Tools | Ignored | medium | normal |
| 413 | Hammer | Hammer | Ignored | medium | normal |
| 414 | Jackhammer | Jackhammer | Ignored | medium | normal |
| 415 | Sawing | Sawing | Ignored | medium | normal |
| 416 | Filing (rasp) | Filing (rasp) | Ignored | medium | normal |
| 417 | Sanding | Sanding | Ignored | medium | normal |
| 418 | Power tool | Power tool | Ignored | medium | normal |
| 419 | Drill | Drill | Ignored | medium | normal |

### Impacts, breaking and gunshots (33)

| No. | Class (model) | Name | Interest | False pos. | Privacy |
|---|---|---|---|---|---|
| 420 | Explosion | Explosion | Optional | high | normal |
| 421 | Gunshot, gunfire | Gunshot | Optional | high | normal |
| 422 | Machine gun | Machine gun | Ignored | high | normal |
| 423 | Fusillade | Fusillade | Ignored | high | normal |
| 424 | Artillery fire | Artillery fire | Ignored | high | normal |
| 425 | Cap gun | Cap gun | Ignored | high | normal |
| 426 | Fireworks | Fireworks | Context | medium | normal |
| 427 | Firecracker | Firecracker | Context | medium | normal |
| 428 | Burst, pop | Burst or pop | Ignored | high | normal |
| 429 | Eruption | Eruption | Ignored | high | normal |
| 430 | Boom | Boom | Ignored | high | normal |
| 431 | Wood | Wood | Ignored | high | normal |
| 432 | Chop | Chop | Ignored | high | normal |
| 433 | Splinter | Splinter | Ignored | high | normal |
| 434 | Crack | Crack | Ignored | high | normal |
| 435 | Glass | Glass | Ignored | high | normal |
| 436 | Chink, clink | Glass clink | Ignored | high | normal |
| 437 | Shatter | Shattering glass | Monitor | medium | normal |
| 454 | Thump, thud | Thud | Optional | high | normal |
| 455 | Thunk | Thunk | Ignored | high | normal |
| 459 | Basketball bounce | Basketball bounce | Ignored | high | normal |
| 460 | Bang | Bang | Ignored | high | normal |
| 461 | Slap, smack | Slap | Ignored | high | normal |
| 462 | Whack, thwack | Whack | Ignored | high | normal |
| 463 | Smash, crash | Smash or crash | Optional | high | normal |
| 464 | Breaking | Breaking | Optional | high | normal |
| 465 | Bouncing | Bouncing | Ignored | high | normal |
| 466 | Whip | Whip | Ignored | high | normal |
| 467 | Flap | Flap | Ignored | high | normal |
| 468 | Scratch | Scratch | Ignored | high | normal |
| 469 | Scrape | Scrape | Ignored | high | normal |
| 470 | Rub | Rub | Ignored | high | normal |
| 471 | Roll | Roll | Ignored | high | normal |

### Generic sounds (onomatopoeia) (20)

| No. | Class (model) | Name | Interest | False pos. | Privacy |
|---|---|---|---|---|---|
| 453 | Whoosh, swoosh, swish | Whoosh | Ignored | high | normal |
| 475 | Beep, bleep | Beep | Optional | high | normal |
| 476 | Ping | Ping | Ignored | high | normal |
| 477 | Ding | Ding | Optional | high | normal |
| 478 | Clang | Clang | Ignored | high | normal |
| 479 | Squeal | Squeal | Ignored | high | normal |
| 480 | Creak | Creak | Ignored | high | normal |
| 481 | Rustle | Rustle | Ignored | high | normal |
| 482 | Whir | Whir | Ignored | high | normal |
| 483 | Clatter | Clatter | Optional | high | normal |
| 484 | Sizzle | Sizzle | Optional | medium | normal |
| 485 | Clicking | Clicking | Ignored | high | normal |
| 486 | Clickety-clack | Clickety-clack | Ignored | high | normal |
| 487 | Rumble | Rumble | Ignored | high | normal |
| 488 | Plop | Plop | Ignored | high | normal |
| 489 | Jingle, tinkle | Jingle | Ignored | high | normal |
| 490 | Hum | Hum | Ignored | high | normal |
| 491 | Zing | Zing | Ignored | high | normal |
| 492 | Boing | Boing | Ignored | high | normal |
| 493 | Crunch | Crunch | Ignored | high | normal |

### Noise, acoustics and microphone diagnostics (24)

| No. | Class (model) | Name | Interest | False pos. | Privacy |
|---|---|---|---|---|---|
| 494 | Silence | Silence | Context | low | normal |
| 495 | Sine wave | Sine wave | Ignored | high | normal |
| 496 | Harmonic | Harmonic | Ignored | high | normal |
| 497 | Chirp tone | Chirp tone | Ignored | high | normal |
| 498 | Sound effect | Sound effect | Ignored | high | normal |
| 499 | Pulse | Pulse | Ignored | high | normal |
| 500 | Inside, small room | Inside, small room | Context | medium | normal |
| 501 | Inside, large room or hall | Inside, large room or hall | Context | medium | normal |
| 502 | Inside, public space | Inside, public space | Context | medium | normal |
| 503 | Outside, urban or manmade | Outside, urban or manmade | Context | medium | normal |
| 504 | Outside, rural or natural | Outside, rural or natural | Context | medium | normal |
| 505 | Reverberation | Reverberation | Ignored | high | normal |
| 506 | Echo | Echo | Ignored | high | normal |
| 507 | Noise | Noise | Ignored | high | normal |
| 508 | Environmental noise | Environmental noise | Ignored | high | normal |
| 509 | Static | Static | Context | medium | normal |
| 510 | Mains hum | Mains hum | Context | low | normal |
| 511 | Distortion | Distortion | Context | medium | normal |
| 512 | Sidetone | Sidetone | Context | medium | normal |
| 513 | Cacophony | Cacophony | Ignored | high | normal |
| 514 | White noise | White noise | Context | medium | normal |
| 515 | Pink noise | Pink noise | Context | medium | normal |
| 516 | Throbbing | Throbbing | Ignored | high | normal |
| 517 | Vibration | Vibration | Ignored | high | normal |

### Reproduced sound (TV, radio) (3)

| No. | Class (model) | Name | Interest | False pos. | Privacy |
|---|---|---|---|---|---|
| 518 | Television | Television | Context | medium | normal |
| 519 | Radio | Radio | Context | medium | normal |
| 520 | Field recording | Field recording | Ignored | high | normal |

### Miscellaneous (8)

| No. | Class (model) | Name | Interest | False pos. | Privacy |
|---|---|---|---|---|---|
| 451 | Sonar | Sonar | Ignored | high | normal |
| 452 | Arrow | Arrow | Ignored | high | normal |
| 456 | Electronic tuner | Electronic tuner | Ignored | high | normal |
| 457 | Effects unit | Effects unit | Ignored | high | normal |
| 458 | Chorus effect | Chorus effect | Ignored | high | normal |
| 472 | Crushing | Crushing | Ignored | high | normal |
| 473 | Crumpling, crinkling | Crumpling | Ignored | high | normal |
| 474 | Tearing | Tearing | Ignored | high | normal |

## Sources

- https://github.com/tensorflow/models/tree/master/research/audioset/yamnet (yamnet_class_map.csv)
- https://github.com/audioset/ontology (ontology.json)
