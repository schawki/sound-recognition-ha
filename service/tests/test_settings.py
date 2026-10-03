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


