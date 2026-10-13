"""Conditions on Home Assistant states: evaluation, validation, resolution, and what the detector does with them."""
import datetime as dt

import pytest

from soundrec import conditions as cn, config
from test_detector import CAT, Fake, T0, det, make_cfg, run
from soundrec.detector import SourcePipeline

HOME = {"person.a": "home", "person.b": "not_home"}
EMPTY = {"person.a": "not_home", "person.b": "not_home"}
NOBODY = {"people": "nobody_home"}


def cond(*rules, **kw):
    return {"rules": list(rules), **kw}


def test_nobody_home():
    c = cond(NOBODY)
    assert cn.evaluate(c, EMPTY) is True
    assert cn.evaluate(c, HOME) is False
    assert cn.evaluate(c, {"person.a": "not_home", "person.b": "unavailable"}) is None       # one person unreadable and nobody known at home
    assert cn.evaluate(c, {"person.a": "home", "person.b": "unavailable"}) is False          # somebody is home whatever the other says
    assert cn.evaluate(c, {}) is None and cn.evaluate(c, None) is None


def test_someone_home():
    c = cond({"people": "someone_home"})
    assert cn.evaluate(c, HOME) is True and cn.evaluate(c, EMPTY) is False
    assert cn.evaluate(c, {"person.a": "not_home", "person.b": "unknown"}) is None
    assert cn.evaluate(c, {"sensor.x": "home"}) is None                                      # only persons count


def test_entity_rules():
    is_off = cond({"entity": "alarm_control_panel.home", "op": "is", "value": "disarmed"})
    assert cn.evaluate(is_off, {"alarm_control_panel.home": "disarmed"}) is True
    assert cn.evaluate(is_off, {"alarm_control_panel.home": "armed_away"}) is False
    assert cn.evaluate(is_off, {"alarm_control_panel.home": "unavailable"}) is None
    assert cn.evaluate(is_off, {}) is None
    not_on = cond({"entity": "input_boolean.guests", "op": "is_not", "value": "on"})
    assert cn.evaluate(not_on, {"input_boolean.guests": "off"}) is True
    assert cn.evaluate(not_on, {"input_boolean.guests": "on"}) is False
    assert cn.evaluate(not_on, {"input_boolean.guests": "unknown"}) is None
    lit = cond({"entity": "binary_sensor.door", "op": "is", "value": "unavailable"})          # asking for "unavailable" explicitly is allowed
    assert cn.evaluate(lit, {"binary_sensor.door": "unavailable"}) is True


def test_match_all_and_any():
    a, b = {"entity": "input_boolean.a", "value": "on"}, {"entity": "input_boolean.b", "value": "on"}
    both = {"input_boolean.a": "on", "input_boolean.b": "off"}
    assert cn.evaluate(cond(a, b), both) is False and cn.evaluate(cond(a, b, match="any"), both) is True
    assert cn.evaluate(cond(a, b), {"input_boolean.a": "on"}) is None                         # all: one unknown, nobody false
    assert cn.evaluate(cond(a, b), {"input_boolean.b": "off"}) is False                       # all: a known false is enough
    assert cn.evaluate(cond(a, b, match="any"), {"input_boolean.a": "off"}) is None
    assert cn.evaluate(cond(a, b, match="any"), {"input_boolean.a": "on"}) is True


def test_unknown_follows_if_unknown():
    assert cn.holds(None, {}) == (True, False)
    assert cn.holds(cond(NOBODY), {}) == (True, True)                                         # default: listen
    assert cn.holds(cond(NOBODY, if_unknown="listen"), {}) == (True, True)
    assert cn.holds(cond(NOBODY, if_unknown="pause"), {}) == (False, True)
    assert cn.holds(cond(NOBODY, if_unknown="pause"), HOME) == (False, False)
    assert cn.holds(cond(NOBODY, if_unknown="pause"), EMPTY) == (True, False)


def test_facts_expire():
    f = cn.Facts()
    assert f.get(100) == {}
    f.set(HOME, 120, now=100)
    assert f.get(150) == HOME and f.get(221) == {}


def test_validate():
    ok = []
    cn.validate(cond(NOBODY, {"entity": "input_boolean.x", "op": "is_not", "value": "on"}, match="any", if_unknown="pause"), "c", ok)
    assert ok == []
    for bad in ({}, {"rules": []}, {"rules": [{"people": "everybody"}]}, {"rules": [{"people": "nobody_home", "entity": "person.a"}]},
                {"rules": [{"entity": "no_domain", "value": "on"}]}, {"rules": [{"entity": "a.b", "op": "maybe", "value": "on"}]},
                {"rules": [{"entity": "a.b"}]}, {"rules": [NOBODY], "match": "some"}, {"rules": [NOBODY], "if_unknown": "stop"},
                {"rules": [NOBODY], "extra": 1}, "text"):
        errs = []
        cn.validate(bad, "c", errs)
        assert errs, bad


def test_config_accepts_conditions_at_every_level_and_rejects_bad_ones():
    c = cond(NOBODY)
    cfg = config._merge(config.DEFAULTS, {"defaults": {"condition": c}, "classes": {"Bark": {"enabled": True, "condition": c}},
                                          "sources": [{"id": "s1", "type": "file", "url": "x", "condition": c, "classes": {"Bark": {"condition": c}}}]})
    assert config.validate(cfg, CAT) == []
    for where in (lambda x: x["defaults"], lambda x: x["classes"]["Bark"], lambda x: x["sources"][0], lambda x: x["sources"][0]["classes"]["Bark"]):
        import copy
        bad = copy.deepcopy(cfg)
        where(bad)["condition"] = {"rules": [{"people": "nobody"}]}
        assert any("condition" in e for e in config.validate(bad, CAT))


def test_resolution_order_and_provenance():
    from soundrec import settings as st
    src_c, cls_c, sc_c, dft_c = (cond({"entity": f"input_boolean.{n}", "value": "on"}) for n in "abcd")
    cfg = config._merge(config.DEFAULTS, {"defaults": {"condition": dft_c}, "classes": {"Bark": {"enabled": True, "condition": cls_c}, "Doorbell": {"enabled": True}},
                                          "sources": [{"id": "s1", "type": "file", "url": "x", "condition": src_c, "classes": {"Bark": {"condition": sc_c}}},
                                                      {"id": "s2", "type": "file", "url": "y"}]})
    assert config.validate(cfg, CAT) == []
    R = lambda sid, name: st.resolve(cfg, CAT, sid, name)
    assert (R("s1", "Bark")["condition"], R("s1", "Bark")["provenance"]["condition"]) == (sc_c, "source_class")
    assert (R("s1", "Doorbell")["condition"], R("s1", "Doorbell")["provenance"]["condition"]) == (src_c, "source")
    assert (R("s2", "Bark")["condition"], R("s2", "Bark")["provenance"]["condition"]) == (cls_c, "class")
    assert (R("s2", "Doorbell")["condition"], R("s2", "Doorbell")["provenance"]["condition"]) == (dft_c, "class" if False else "defaults")
    # an explicit null ends a wider condition: the sound is heard whatever the source says
    cfg["sources"][0]["classes"]["Bark"]["condition"] = None
    assert config.validate(cfg, CAT) == []
    r = R("s1", "Bark")
    assert (r["condition"], r["provenance"]["condition"]) == (None, "source_class")
    plain = config._merge(config.DEFAULTS, {"classes": {"Bark": {"enabled": True}}, "sources": [{"id": "s1", "type": "file", "url": "x"}]})
    assert st.resolve(plain, CAT, "s1", "Bark")["condition"] is None


# ------------------------------------------------------------------------------------------------------ the detector
def pipe_with(condition, states, **kw):
    cfg = make_cfg({"Bark": {"enabled": True}}, source={"condition": condition} if condition else None, timezone="UTC")
    p = SourcePipeline(cfg["sources"][0], cfg, CAT, Fake({"Bark": 0.9}))
    if states is not None:
        p.facts.set(states, 10 ** 11, now=0)                                                   # never expires in the test
    return p


def test_detector_listens_when_the_condition_holds():
    p = pipe_with(cond(NOBODY), EMPTY)
    assert det(run(p, 12)) and p.state["held_by_condition"] == [] and p.state["condition_unknown"] is False


def test_detector_pauses_when_the_condition_fails():
    p = pipe_with(cond(NOBODY), HOME)
    assert det(run(p, 12)) == []
    assert len(p.state["held_by_condition"]) == 1 and p.state["condition_unknown"] is False
    assert p.state["active_classes"] == []


def test_detector_follows_the_state_as_it_changes():
    p = pipe_with(cond(NOBODY), HOME)
    assert det(run(p, 12)) == []
    p.facts.set(EMPTY, 10 ** 11, now=0)
    assert det(run(p, 12, start=T0 + dt.timedelta(seconds=12)))


def test_detector_unknown_state_listens_by_default_and_says_so():
    p = pipe_with(cond(NOBODY), None)                                                         # nothing was ever pushed
    assert det(run(p, 12)) and p.state["condition_unknown"] is True and p.state["held_by_condition"] == []


def test_detector_unknown_state_can_pause():
    p = pipe_with(cond(NOBODY, if_unknown="pause"), None)
    assert det(run(p, 12)) == [] and p.state["condition_unknown"] is True and len(p.state["held_by_condition"]) == 1


def test_detector_without_condition_is_unchanged():
    p = pipe_with(None, None)
    assert det(run(p, 12)) and p.state["held_by_condition"] == [] and p.state["condition_unknown"] is False


def test_pushed_states_lapse():
    p = pipe_with(cond(NOBODY), HOME)
    p.facts.set(HOME, 5, now=T0.timestamp())                                                  # a 5 s time to live
    run(p, 3)
    assert len(p.state["held_by_condition"]) == 1
    run(p, 12, start=T0 + dt.timedelta(seconds=3))                                            # 15 s later the states are forgotten: unknown -> listen
    assert p.state["held_by_condition"] == [] and p.state["condition_unknown"] is True


# ------------------------------------------------------------------------------------------------------ the API
from test_clips import H, client  # noqa: E402,F401  (fixture)


@pytest.mark.asyncio
async def test_api_takes_the_states_and_the_engine_keeps_them(client):
    r = await client.put("/api/v1/conditions", headers=H, json={"states": HOME, "ttl_s": 120})
    assert r.status == 200
    assert client.engine.facts.get() == HOME
    pipe = next(iter(client.engine.pipes.values()), None)
    if pipe:
        assert pipe.facts is client.engine.facts                              # every source reads the same states


@pytest.mark.asyncio
async def test_api_refuses_bad_bodies_and_needs_the_token(client):
    for body in ({}, {"states": []}, {"states": {}, "ttl_s": 1}, {"states": {}, "ttl_s": 100000}, {"states": {"a": 1}, "ttl_s": "x"}):
        assert (await client.put("/api/v1/conditions", headers=H, json=body)).status == 400, body
    assert (await client.put("/api/v1/conditions", json={"states": {}})).status in (401, 403)


@pytest.mark.asyncio
async def test_status_carries_the_state_of_the_conditions(client):
    s = (await (await client.get("/api/v1/sources", headers=H)).json())
    src = s["sources"][0] if isinstance(s, dict) else s[0]
    assert src["held_by_condition"] == [] and src["condition_unknown"] is False
