import datetime as dt
import os
import yaml

from soundrec import catalog as cm
from soundrec.settings import Catalog, resolve, is_active, covers_24_7, warnings

EX = os.path.join(os.path.dirname(__file__), "..", "..", "examples", "config.example.yaml")


def test_layered_settings_and_warnings():
    cat = Catalog(cm.load_raw())
    cfg = yaml.safe_load(open(EX, encoding='utf-8'))
    R = lambda src, cls: resolve(cfg, cat, src, cls)
    D = lambda s: dt.datetime.strptime(s, '%Y-%m-%d %H:%M')   # 2026-10-05 is a Monday; 2026-10-09 a Friday

    # --- threshold layers
    r = R('garden_cam', 'Bark');       assert r['threshold'] == 0.7 and r['provenance']['threshold'] == 'source_class'      # absolute, ignores offset
    r = R('kitchen_esp32', 'Bark');    assert r['threshold'] == 0.55 and r['provenance']['threshold'] == 'class+source_offset'   # class 0.5 + offset 0.05
    r = R('kitchen_esp32', 'Doorbell'); assert r['threshold'] == 0.55 and r['provenance']['threshold'] == 'catalog+source_offset'  # catalog 0.5 + offset 0.05
    r = R('garden_cam', 'Shatter');    assert r['threshold'] == 0.55 and r['provenance']['threshold'] == 'catalog+source_offset'
    # clamp
    cfg['sources'][0]['threshold_offset'] = 5; assert R(cfg['sources'][0]['id'], 'Bark')['threshold'] == 0.99; cfg['sources'][0]['threshold_offset'] = 0.05

    # --- enabled
    assert R('kitchen_esp32', 'Smoke detector, smoke alarm')['enabled'] is True
    assert R('kitchen_esp32', 'Screaming')['enabled'] is False        # disabled on this source
    assert R('garden_cam', 'Screaming')['enabled'] is True            # inherited from global classes
    assert R('old_pi', 'Bark')['enabled'] is False                    # disabled source

    # --- volume gate: stricter of class/source, explicit source x class wins
    assert R('kitchen_esp32', 'Knock')['min_volume_dbfs'] == -35 and R('kitchen_esp32', 'Knock')['provenance']['min_volume_dbfs'] == 'class'
    assert R('garden_cam', 'Bark')['min_volume_dbfs'] == -45 and R('garden_cam', 'Bark')['provenance']['min_volume_dbfs'] == 'source_class'
    assert R('kitchen_esp32', 'Doorbell')['min_volume_dbfs'] == -55          # source value

    # --- schedule: continuous option, class override, cross-midnight
    assert R('nursery_esp32', 'Baby cry, infant cry')['schedule'] == {'mode': 'continuous'}
    s = R('kitchen_esp32', 'Doorbell')['schedule']                           # scheduled: weekdays 07:00-23:00
    assert is_active(s, D('2026-10-05 08:00')) and not is_active(s, D('2026-10-05 23:30')) and not is_active(s, D('2026-10-10 12:00'))
    assert R('kitchen_esp32', 'Smoke detector, smoke alarm')['provenance']['schedule'] == 'class'
    n = {'mode': 'scheduled', 'windows': [{'days': ['fri'], 'from': '22:00', 'to': '06:00'}]}
    assert is_active(n, D('2026-10-09 23:00')) and not is_active(n, D('2026-10-09 05:59'))   # Fri 23:00 is inside, Fri 05:59 is not (window starts Fri 22:00)
    assert is_active(n, D('2026-10-10 05:59')) and not is_active(n, D('2026-10-10 06:00')) and not is_active(n, D('2026-10-10 12:00'))
    assert covers_24_7({'mode': 'scheduled', 'windows': [{'from': '00:00', 'to': '12:00'}, {'from': '12:00', 'to': '00:00'}]})
    assert not covers_24_7(s)

    # --- clips
    assert R('kitchen_esp32', 'Speech')['clip_retention_days'] == 0           # catalog forbids
    assert R('garden_cam', 'Shatter')['clip_retention_days'] == 14            # catalog 30 capped by source max 14
    assert R('nursery_esp32', 'Baby cry, infant cry')['clip_retention_days'] == 0   # clips disallowed on this source

    # --- warnings
    w = {(a, b, c) for a, b, c, _ in warnings(cfg, cat)}
    assert ('schedule_gap_safety', 'kitchen_esp32', 'Doorbell') not in w                       # Doorbell is not a safety class
    assert ('clip_source_disallowed', 'nursery_esp32', 'Baby cry, infant cry') in w
    assert ('volume_gate_safety', 'garden_cam', 'Shatter') in w                                # gate -30 > -40 on a safety class




def test_clip_retention_by_category():
    cat = Catalog(cm.load_raw())
    mk = lambda **clips: {"defaults": {"clips": {"allowed": True, "max_retention_days": 30, **clips.get("d", {})}},
                          "sources": [{"id": "a", "type": "rtsp", "url": "rtsp://x", "clips": clips.get("s", {})}], "classes": clips.get("c", {})}
    R = lambda cfg, cls: resolve(cfg, cat, "a", cls)
    MUSIC, SPEECH, BARK, SMOKE = "Music", "Speech", "Bark", "Smoke detector, smoke alarm"
    # nothing set: the catalog decides, conversations default to 0 and say why
    assert R(mk(), MUSIC)["clip_retention_days"] == 0 and R(mk(), MUSIC)["provenance"]["clip_retention_days"] == "catalog"
    assert R(mk(), SPEECH)["clip_retention_days"] == 0 and R(mk(), SPEECH)["provenance"]["clip_retention_days"] == "catalog_confidential"
    # global category value, then the source's own wins over it
    g = {"d": {"retention_by_category": {"context": 7, "confidential": 2}}}
    assert R(mk(**g), MUSIC)["clip_retention_days"] == 7 and R(mk(**g), MUSIC)["provenance"]["clip_retention_days"] == "category"
    assert R(mk(**g), SPEECH)["clip_retention_days"] == 2                      # the user may choose to keep conversations
    both = dict(g, s={"retention_by_category": {"context": 3}})
    assert R(mk(**both), MUSIC)["clip_retention_days"] == 3 and R(mk(**both), MUSIC)["provenance"]["clip_retention_days"] == "source_category"
    assert R(mk(**both), SPEECH)["clip_retention_days"] == 2                   # other categories fall back to the global value
    # a class setting beats a category; the caps and the source switch still apply
    assert R(mk(**dict(g, c={MUSIC: {"clip_retention_days": 1}})), MUSIC)["clip_retention_days"] == 1
    assert R(mk(d={"retention_by_category": {"normal": 90}}), BARK)["clip_retention_days"] == 30 and R(mk(d={"retention_by_category": {"normal": 90}}), BARK)["provenance"]["clip_retention_days"] == "cap"
    off = dict(g, s={"allowed": False})
    assert R(mk(**off), MUSIC)["clip_retention_days"] == 0 and R(mk(**off), MUSIC)["provenance"]["clip_retention_days"] == "source_clips_disallowed"
    # categories: privacy first, then context
    from soundrec.settings import retention_category
    assert [retention_category(cat.get(n)) for n in (SPEECH, MUSIC, BARK)] == ["confidential", "context", "normal"]


def test_retention_by_category_is_validated():
    from soundrec import config as cfgmod
    cat = Catalog(cm.load_raw())
    cfg = cfgmod.load_defaults() if hasattr(cfgmod, "load_defaults") else None
    if cfg is None:
        cfg = {"analysis": {"hop_s": 0.5, "context_boost": 0.1, "safety_boost_cap": 0.1, "total_boost_cap": 0.3}, "defaults": {}, "sources": []}
    ok = lambda c: cfgmod.validate({**cfg, "defaults": {"clips": c}}, cat)
    assert ok({"retention_by_category": {"normal": 7, "context": 0}}) == []
    assert any("unknown category" in e for e in ok({"retention_by_category": {"funny": 1}}))
    assert any("between 0 and 3650" in e for e in ok({"retention_by_category": {"normal": -1}}))
    assert any("unknown field" in e for e in ok({"keep_forever": True}))
