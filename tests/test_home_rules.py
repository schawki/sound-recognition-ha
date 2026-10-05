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
    return hr.compute(c, structure, lang, RULES, {TV: "Television", RADIO: "Radio", MUSIC: "Music", FIREWORKS: "Fireworks", FIRECRACKER: "Firecracker"})


def by(r):
    return {x["rule"]: x for x in r}


def test_the_place_is_deduced_from_the_type_of_the_room_unless_the_source_names_one():
    got = hr.places_for(cfg(("chambre", {}), ("salon", {}), ("sdb", {}), ("cave", {}), ("jardin", {}), ("bureau", {"environment": "kitchen"}), ("nowhere", {}), ("off", {"enabled": False})), HOME, RULES)
    assert {k: v[0] for k, v in got.items()} == {"chambre": "bedroom", "salon": "living_tv", "sdb": "bathroom", "cave": None, "jardin": None, "nowhere": None}   # a source that names one, or is off, is left out
    assert got["sdb"][1]["name"] == "SDB" and got["nowhere"][1] is None and got["cave"][1]["name"] == "Cave"   # the space is given when Home Structure knows the room
    zone = {**HOME, "spaces": HOME["spaces"] + [dict(space("area:terrasse", "Terrasse", kind="terrace"))]}
    assert hr.places_for(cfg(("terrasse", {})), zone, RULES)["terrasse"][0] == "outdoor"             # a zone that is a Home Assistant area has a place too
    for kind, place in (("master_bedroom", "bedroom"), ("child_bedroom", "bedroom"), ("guest_room", "bedroom"), ("nursery", "nursery"), ("game_room", "living_tv"),
                        ("home_cinema", "living_tv"), ("workshop", "garage"), ("gym", "gym"), ("staircase", "entrance"), ("cellar", "storage"), ("toilet", "bathroom"),
                        ("laundry", "laundry"), ("utility_room", "laundry"), ("dining_room", "dining_room"), ("dressing", "storage")):
        st = {**HOME, "spaces": [space("area:x", "X", room_type=kind)]}
        assert hr.places_for(cfg(("x", {})), st, RULES)["x"][0] == place, kind


HS_ROOM_TYPES = ["bedroom", "master_bedroom", "child_bedroom", "nursery", "guest_room", "living_room", "dining_room", "game_room", "home_cinema", "gym", "office", "workshop",
                 "bathroom", "toilet", "kitchen", "pantry", "laundry", "utility_room", "dressing", "storage", "cellar", "attic", "hallway", "entrance", "staircase"]
HS_ZONE_KINDS = ["garden", "balcony", "terrace", "courtyard", "garage", "hall", "stairwell", "common_area", "street", "neighbor", "other"]


def test_every_room_type_of_home_structure_has_a_place_that_exists_in_the_catalog():
    from soundrec import catalog as cm
    known = {e["id"] for e in cm.load_lang("en")["environments"]}
    assert [t for t in HS_ROOM_TYPES if t not in RULES["places"]] == []
    assert [k for k in HS_ZONE_KINDS if k not in RULES["places"]] == ["neighbor", "other"]            # the only kinds that have no place
    assert set(RULES["places"].values()) <= known


def test_the_room_without_a_type_is_asked_for_one():
    r = hr.set_room_type_rows(cfg(("cave", {}), ("sdb", {}), ("chambre", {}), ("nowhere", {})), HOME, "en", RULES)
    assert [x["source"] for x in r] == ["cave"] and "« Cave »" in r[0]["message"] and "Home Structure" in r[0]["message"]
    assert "choisissez-le" in hr.set_room_type_rows(cfg(("cave", {})), HOME, "fr", RULES)[0]["message"]


def test_every_label_exists_in_both_languages_for_every_type():
    en, fr = RULES["texts"]["en"], RULES["texts"]["fr"]
    assert set(en["room_types"]) == set(fr["room_types"]) == set(HS_ROOM_TYPES) and set(en["kinds"]) == set(fr["kinds"]) == set(HS_ZONE_KINDS)
    assert set(RULES["places"]) <= set(en["room_types"]) | set(en["kinds"])
    assert all(t in en["room_types"] for rule in RULES["rules"] for t in rule.get("in", []))


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
    assert "Rue (Rue)" in r["home_noise_from_outside"]["message"] and "communique avec" in r["home_noise_from_outside"]["message"]
    assert rows(cfg(("chambre", {"enabled": False}))) == [] and rows(cfg(("chambre", {})), structure=None) == []
    assert rows(cfg(("nowhere", {}))) == []                                             # a room Home Structure does not know


def test_a_sound_enabled_under_its_audioset_name_counts_as_done():
    """The panel writes an enabled flag under the key already used in the configuration, which can be the AudioSet name rather than the id."""
    keys = {FIREWORKS: {FIREWORKS, "Fireworks"}, FIRECRACKER: {FIRECRACKER, "Firecracker"}}
    c = cfg(("chambre", {"adaptive": {"enabled": True}, "classes": {"Fireworks": {"enabled": True}, "Firecracker": {"enabled": True}}}))
    names = {FIREWORKS: "Fireworks", FIRECRACKER: "Firecracker"}
    assert not any(k.startswith("home_fireworks") for k in by(hr.compute(c, HOME, "en", RULES, names, keys)))
    assert "home_fireworks_outside" in by(hr.compute(c, HOME, "en", RULES, names))       # without the names the old behaviour: the recommendation stays


def test_a_choice_of_the_source_wins_over_the_global_one_like_in_the_service():
    c = cfg(("chambre", {"adaptive": {"enabled": True}, "classes": {FIREWORKS: {"enabled": False}, FIRECRACKER: {"enabled": True}}}))
    c["classes"] = {FIREWORKS: {"enabled": True}}
    assert by(rows(c))["home_fireworks_outside"]["classes"] == [FIREWORKS]
