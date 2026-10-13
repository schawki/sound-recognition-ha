# Presets

A preset is a ready-made bundle of settings for a source: which sounds to listen for, how quiet a sound may be, whether clips are kept, whether the adaptive setting is on. Instead of setting every sound of a kitchen or a baby's room by hand, you pick the preset and adjust what is specific.

## Choosing presets for a source

Open the source (*Sources → Edit*) and use **Add a preset…**. The menu has three groups:

- **By kind of room**: living room, dining room, kitchen, bedroom, baby's room, office, bathroom, laundry, gym, storage, entrance, outdoors, garage.
- **Situations**: TV nearby, outside noise, baby, pets, empty home.
- **My presets**: the ones you made.

Presets **add up**. A kitchen with a dog can have *Kitchen* and *Pets*. When two presets set the same value, the one **lower in the list wins**; use the arrows to reorder. What you set yourself on the source or on one of its sounds **always wins** over any preset, and the *Sounds* tab shows "a preset of this source" as the origin of a value.

The *Advice* tab suggests the preset that fits the kind of room of a source (from its Home Structure room type or the place you chose). Nothing is applied without your click, and *Undo* takes it off.

## Safety sounds

A preset can switch on a sound or make it **easier** to detect, never harder, for the sounds that protect you: smoke and fire alarms, break-in sounds, a baby's cry. The quietest sound a preset can set is -50 dBFS, so a preset never deafens a source.

## Your own presets

In *Settings → Presets*, **New preset** lets you name it, add **any detectable sound** (with its threshold, minimum duration and cooldown) and set the values for the source (quietest sound, clips, adaptive setting; "Leave as is" changes nothing). The catalog's presets are fixed, but **Duplicate** gives you a copy to change. A preset shows which sources use it; deleting it takes it off those sources.

## Good to know

- A source stores only the *names* of its presets. Changing one of your presets changes every source that uses it.
- Clips are off in the bedroom, baby's room and bathroom presets: these rooms are private. Turn clips back on in the source if you want them.
- Entities for the sounds a preset switches on are created after the integration reloads, which happens at each save.
