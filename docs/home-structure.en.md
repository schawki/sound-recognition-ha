# Home Structure: why and how Sound Recognition uses it

[Home Structure](https://github.com/schawki/ha-home-structure) is a separate Home Assistant integration that describes the *shape* of your home: which rooms exist, which are next to each other, what separates them (wall, door, window, open space, shutter), which sensor says whether a door or window is open, and what each room is (kitchen, bedroom, garage…). It also knows the outside: a street, a garden, a stairwell, a neighbour.

Sound Recognition **needs none of it to work**. With it, Sound Recognition hears better and advises better.

## Why a separate integration

- **One description of the home, used by everyone.** Rooms and doors are not specific to sounds: lighting, climate, presence or security can use the same plan. Describing them once in Home Structure avoids a second, different copy inside Sound Recognition.
- **Nothing to guess.** Sound Recognition never deduces anything from the *names* of your rooms or devices. It only uses what you chose in Home Structure (a room type, a link between two rooms), so it works the same in every home and language.
- **Each integration stays small.** Home Structure knows the home; Sound Recognition only decides what a door, a window or a wall means *for sound*.

## What Sound Recognition takes from it

| It reads | It is used for |
|---|---|
| **Links between rooms** and what separates them, with the live state of each door or window (open, closed, partly open) | To estimate how much of a sound passes from one room to the next. A sound heard in the living room (a television) raises the thresholds of the kitchen microphone in proportion to what reaches it: a door that is open lets it through, a closed one muffles it. Table of values in [Contexts, rooms and adaptive sensitivity](context-and-adaptive.en.md). |
| **The type of each room** and the kind of outside spaces | To deduce the kind of place of a source (kitchen, bedroom, garage, outdoors…) without you choosing it a second time, which sets the sounds that fit the place. |
| **What is next to a source's room** | Advice in the *Advice* tab: a garden or street next to the room suggests Fireworks and Firecracker (so they are not taken for gunshots); a living room next door suggests Television, Radio and Music; a street, stairwell or hall suggests the adaptive setting. A rule only appears when the link exists in the plan. |
| **The plan** (position of the rooms) | Shown read-only in the source form. |
| **Roller shutters** in front of a window or door | A closed shutter reduces what passes through that window or door. |

The media players and vacuum cleaners of a room are found through Home Assistant's own areas, not through Home Structure; Home Structure tells which *other* rooms are connected, so that their devices count too, in proportion to what passes.

## How they talk

- Through one public service of Home Structure, `home_structure.get_structure`, and through the entities it creates. Nothing is imported from it, so each can be updated on its own.
- Home Structure fires the event `home_structure_changed` when you edit the plan (and when it starts). Sound Recognition then reads the plan again within seconds (several events in a row give one reading). It deduces nothing from the event itself. Without the event (older Home Structure), the plan is read again every 20 seconds anyway.
- If Home Structure is absent, not set up yet or failing, Sound Recognition does not fail: rooms are treated as separate, a source only sees the devices of its own room, and the Sources tab invites you to install or fill it in.

## What to do

1. Install Home Structure (HACS, same way as Sound Recognition) and describe your rooms: type of each room, and the separations between neighbouring rooms.
2. In Sound Recognition, give each source a Home Assistant room (*Sources → edit → Room*). Nothing else to set: the place, the recommendations and the passage of sound follow.
3. Turn on *devices* and *adaptive sensitivity* for the sources where you want thresholds to follow what plays in the room.

## Good to know

- Choosing a place by hand in a source overrides the one deduced from Home Structure.
- A plain wall lets almost nothing through and is not followed.
- Home Structure never sends anything to Sound Recognition by itself except the "something changed" event; Sound Recognition always asks for the full description.
