"""Recommendations drawn from Home Structure: place of a source from the type of its room, rules about the linked spaces."""
from custom_components.sound_recognition import home_rules as hr

RULES = hr.load_rules()
FIREWORKS, FIRECRACKER, TV, RADIO, MUSIC = "/m/0g6b5", "/g/122z_qxw", "/m/07c52", "/m/06bz3", "/m/04rlf"


def space(i, name, kind="room", room_type=None):
    return {"id": i, "name": name, "kind": kind, "room_type": room_type, "in_home": kind == "room"}


def conn(a, b, *types):
    return {"id": f"{a}-{b}", "a": a, "b": b, "separations": [{"id": str(n), "type": t} for n, t in enumerate(types)]}


HOME = {"spaces": [space("area:chambre", "Chambre", room_type="bedroom"), space("area:salon", "Salon", room_type="living_room"),
                   space("area:bureau", "Bureau", room_type="office"), space("area:sdb", "SDB", room_type="bathroom"),
                   space("area:cave", "Cave"),                                   # a room without type
                   space("zone:rue", "Rue", kind="street"), space("zone:jardin", "Jardin", kind="garden"), space("zone:garage", "Garage", kind="garage")],
        "connections": [conn("area:chambre", "area:salon", "door"), conn("area:chambre", "zone:rue", "window", "wall"),
                        conn("area:bureau", "zone:jardin", "wall"), conn("area:sdb", "zone:rue", "window"),
                        conn("area:cave", "zone:garage", "grille")]}


def cfg(*sources):
    return {"sources": [{"id": a, "name": a.title(), "area": a, **kw} for a, kw in sources]}


def rows(c, lang="en", structure=HOME):
    return hr.compute(c, structure, lang, RULES, {TV: "Television", RADIO: "Radio", MUSIC: "Music", FIREWORKS: "Fireworks", FIRECRACKER: "Firecracker"},
                      {"bedroom": "Bedroom", "living_tv": "Living room (TV, music)", "kitchen": "Kitchen", "office": "Office"})


def by(r):
    return {x["rule"]: x for x in r}


def test_place_is_proposed_from_the_type_of_the_room_only_when_there_is_none():
    r = by(rows(cfg(("chambre", {}))))
    assert r["propose_place"]["apply"] == {"source": "chambre", "source_patch": {"environment": "bedroom"}}
    assert "« Bedroom »" in r["propose_place"]["message"]
    assert "propose_place" not in by(rows(cfg(("chambre", {"environment": "kitchen"}))))        # the user chose: left alone
    assert "propose_place" not in by(rows(cfg(("sdb", {}), ("cave", {}))))                  # no place for a bathroom, none for an untyped room


def test_a_link_is_needed_and_walls_do_not_count():
    r = by(rows(cfg(("bureau", {}))))                                                   # the garden is only behind a wall
    assert "home_fireworks_outside" not in r and "home_noise_from_outside" not in r
    r = by(rows(cfg(("chambre", {}))))                                                  # the street through a window (the wall beside it is ignored)
    assert r["home_fireworks_outside"]["classes"] == [FIREWORKS, FIRECRACKER]
    assert "Rue (Street)" in r["home_noise_from_outside"]["message"] and r["home_noise_from_outside"]["apply"]["source_patch"] == {"adaptive": {"enabled": True}}
    assert r["home_fireworks_outside"]["apply"]["class_patch"] == {FIREWORKS: {"enabled": True}, FIRECRACKER: {"enabled": True}}
    assert "Fireworks, Firecracker" in r["home_fireworks_outside"]["message"]


def test_the_type_of_the_neighbour_decides_not_its_name():
    r = by(rows(cfg(("chambre", {}))))
    assert set(r["home_tv_next_door"]["classes"]) == {TV, RADIO, MUSIC} and "Salon (Living room)" in r["home_tv_next_door"]["message"]
    renamed = {**HOME, "spaces": [dict(s, name="Pièce X") if s["id"] == "area:salon" else s for s in HOME["spaces"]]}
    assert "home_tv_next_door" in by(rows(cfg(("chambre", {})), structure=renamed))
    untyped = {**HOME, "spaces": [dict(s, room_type=None) if s["id"] == "area:salon" else s for s in HOME["spaces"]]}
    assert "home_tv_next_door" not in by(rows(cfg(("chambre", {})), structure=untyped))
    assert "home_garage_next_door" not in by(rows(cfg(("chambre", {}))))
    r = by(rows(cfg(("cave", {}))))
    assert r["home_garage_next_door"]["apply"]["source_patch"] == {"adaptive": {"enabled": True}} and "propose_place" not in r   # untyped room: the link to the garage still counts


def test_nothing_is_proposed_twice_or_for_what_is_done():
    done = cfg(("chambre", {"adaptive": {"enabled": True}, "classes": {FIREWORKS: {"enabled": True}, FIRECRACKER: {"enabled": True}}}))
    done["classes"] = {TV: {"enabled": True}, RADIO: {"enabled": True}, MUSIC: {"enabled": True}}
    r = by(rows(done))
    assert not any(k.startswith("home_") for k in r)
    partly = cfg(("chambre", {"classes": {FIREWORKS: {"enabled": True}}}))
    assert by(rows(partly))["home_fireworks_outside"]["classes"] == [FIRECRACKER]


def test_french_and_disabled_sources_and_no_structure():
    r = by(rows(cfg(("chambre", {})), "fr"))
    assert "Rue (Rue)" in r["home_noise_from_outside"]["message"] and "communique avec" in r["home_noise_from_outside"]["message"] and "« Bedroom »" in r["propose_place"]["message"] and "type « Chambre »" in r["propose_place"]["message"]
    assert rows(cfg(("chambre", {"enabled": False}))) == [] and rows(cfg(("chambre", {})), structure=None) == []
    assert rows(cfg(("nowhere", {}))) == []                                             # a room Home Structure does not know
