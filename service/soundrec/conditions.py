"""Conditions on Home Assistant states: "listen only when the house is empty".

A condition sits next to the schedule, at the same levels (source x sound, sound, source, defaults), and is combined with it: a sound is heard
when its schedule allows it AND its condition holds.

    condition:            # `condition: null` at a narrower level means "no condition here"
      match: all            # all | any            (default: all)
      if_unknown: listen    # listen | pause       (default: listen; what to do when a state is not known)
      rules:
        - {entity: alarm_control_panel.home, op: is, value: disarmed}       # op: is | is_not
        - {people: nobody_home}                                            # nobody_home | someone_home (person entities)

The service does not read Home Assistant: the integration pushes the states of the entities the conditions use (`PUT /conditions`). A state
that was not pushed, or not pushed for longer than its time to live, is *unknown*."""
import re
import time

MATCH = ("all", "any")
UNKNOWN_POLICY = ("listen", "pause")
OPS = ("is", "is_not")
PEOPLE = ("nobody_home", "someone_home")
UNREADABLE = ("unknown", "unavailable")
ENTITY = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")
MAX_RULES = 10
PERSON_DOMAIN = "person."


def validate(cond, where, errs):
    """Appends the problems of a `condition` block to errs. `condition: null` is allowed: it ends a condition set at a wider level (a sound that
    must always be heard on a source whose condition pauses the others)."""
    if cond is None:
        return
    if not isinstance(cond, dict):
        errs.append(f"{where}: must be a mapping")
        return
    for k in cond:
        if k not in ("match", "if_unknown", "rules"):
            errs.append(f"{where}: unknown field '{k}'")
    if cond.get("match", "all") not in MATCH:
        errs.append(f"{where}.match must be 'all' or 'any'")
    if cond.get("if_unknown", "listen") not in UNKNOWN_POLICY:
        errs.append(f"{where}.if_unknown must be 'listen' or 'pause'")
    rules = cond.get("rules")
    if not isinstance(rules, list) or not rules:
        errs.append(f"{where}.rules needs at least one rule")
        return
    if len(rules) > MAX_RULES:
        errs.append(f"{where}.rules: at most {MAX_RULES} rules")
    for i, r in enumerate(rules[:MAX_RULES]):
        w = f"{where}.rules[{i}]"
        if not isinstance(r, dict):
            errs.append(f"{w}: must be a mapping")
        elif "people" in r:
            if set(r) != {"people"} or r["people"] not in PEOPLE:
                errs.append(f"{w}: 'people' must be 'nobody_home' or 'someone_home' and stand alone")
        else:
            if set(r) - {"entity", "op", "value"} or not isinstance(r.get("entity"), str) or not ENTITY.match(r["entity"]):
                errs.append(f"{w}: needs an 'entity' (domain.name), an 'op' and a 'value'")
            if r.get("op", "is") not in OPS:
                errs.append(f"{w}.op must be 'is' or 'is_not'")
            if not isinstance(r.get("value"), str) or not r["value"] or len(r["value"]) > 255:
                errs.append(f"{w}.value must be a state (text)")


def entities(cond):
    """Entities a condition reads (person entities are read as a whole, see needs_people)."""
    return {r["entity"] for r in (cond or {}).get("rules", []) if isinstance(r, dict) and "entity" in r}


def needs_people(cond):
    return any(isinstance(r, dict) and "people" in r for r in (cond or {}).get("rules", []))


def _rule(rule, states):
    """True / False, or None when the state is not known."""
    if "people" in rule:
        people = {e: s for e, s in states.items() if e.startswith(PERSON_DOMAIN)}
        if not people:
            return None
        home = [s == "home" for s in people.values()]
        unreadable = any(s in UNREADABLE for s in people.values())
        if rule["people"] == "someone_home":
            return True if any(home) else (None if unreadable else False)
        return False if any(home) else (None if unreadable else True)
    state = states.get(rule["entity"])
    if state is None or (state in UNREADABLE and rule["value"] != state):
        return None
    same = state == rule["value"]
    return same if rule.get("op", "is") == "is" else not same


def evaluate(cond, states):
    """True (the condition holds), False, or None (not known). `states` is {entity_id: state} or None when nothing is known."""
    states = states or {}
    got = [_rule(r, states) for r in cond["rules"]]
    if cond.get("match", "all") == "any":
        return True if any(g is True for g in got) else (None if any(g is None for g in got) else False)
    return False if any(g is False for g in got) else (None if any(g is None for g in got) else True)


def holds(cond, states):
    """(listens, unknown): whether the sound may be heard, and whether the answer rests on a state that is not known."""
    if not cond:
        return True, False
    verdict = evaluate(cond, states)
    if verdict is None:
        return cond.get("if_unknown", "listen") == "listen", True
    return verdict, False


class Facts:
    """The states pushed by Home Assistant, forgotten after their time to live."""

    def __init__(self):
        self.states = {}
        self.expires = 0.0

    def set(self, states, ttl_s, now=None):
        self.states = dict(states)
        self.expires = (time.time() if now is None else now) + ttl_s

    def get(self, now=None):
        return self.states if (time.time() if now is None else now) < self.expires else {}
