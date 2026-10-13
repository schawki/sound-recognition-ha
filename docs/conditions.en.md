# Conditions on Home Assistant states

A source or a sound can listen **only when a condition holds**: "only when nobody is home", "only while the alarm is disarmed", "not while guests are here". The condition adds to the [schedule](source-settings.en.md): a sound is heard when its schedule allows it **and** its condition holds.

## Setting one

- **For a whole source:** *Sources → Edit*, *Condition* box under the listening hours.
- **For a sound:** *Sounds → settings of the sound*, *Condition* box under the schedule. At *all sources* level it applies to every source that does not set its own; with a source chosen, it applies to that source only.

The most specific one wins, as for the schedule: sound on a source, then sound, then source, then the defaults. Nothing is set by default.

Tick **Only listen when a condition holds** and build the rules:

- **The state of an entity**: pick the entity and say that it **is** or **is not** a state (`home`, `on`, `disarmed`… the panel suggests the usual states of the entity).
- **Nobody is home** / **Someone is home**: a shortcut over all the `person` entities of Home Assistant. *Nobody is home* holds when no person is `home`.
- With several rules, choose whether **every** rule or **at least one** must hold.

## When a state is not known

A state is unknown while Home Assistant restarts, when an entity has been removed or renamed, or when the link between Home Assistant and the service is cut (the states are pushed with a short lifetime, so the service does not keep a stale answer). A person whose state is `unknown` or `unavailable` counts as unknown too, unless another person's state already settles the rule (somebody is `home`, so "nobody is home" is false).

For each condition you choose what happens then:

- **Listen anyway** (the default, recommended): a missed alarm is worse than an extra detection.
- **Stay paused**: for a condition that protects privacy more than safety.

The *Live* tab says when a sound is paused by its condition and when a state is unknown.

## Safety sounds

Fire, security and baby sounds can be given a condition, but they are then **not heard while it does not hold**. The panel warns you each time. To keep a smoke alarm active on a source whose condition pauses the others, open the settings of that sound and choose **No condition**: it is then heard whenever its schedule allows it (in the file: `condition: null` on the sound).

## How it works

The service does not read Home Assistant. The integration finds the entities the conditions use, pushes their states (immediately on a change, and every 30 seconds) and the service decides. With a service older than API level 12 the integration ignores the conditions and logs a warning once: update the service from Home Assistant.

In the configuration file:

```yaml
sources:
  - id: kitchen
    condition:
      match: all              # all | any
      if_unknown: listen      # listen | pause
      rules:
        - people: nobody_home                                  # nobody_home | someone_home
        - {entity: alarm_control_panel.home, op: is, value: disarmed}   # op: is | is_not
```
