import copy
import datetime as dt
import numpy as np
import pytest

from soundrec import catalog as cm, config, settings as st
from soundrec.detector import SourcePipeline

CAT = st.Catalog(cm.load_raw())
IDX = lambda name: CAT.get(name)["yamnet_index"]
T0 = dt.datetime(2026, 10, 5, 12, 0, tzinfo=dt.timezone.utc)  # Monday noon


class Fake:
    """Scripted classifier: scores[name] = value or callable(window_number)."""
    def __init__(self, scores):
        self.scores, self.calls = scores, 0

    def predict(self, x):
        s = np.zeros(521, dtype=np.float32)
        for name, v in self.scores.items():
            s[IDX(name)] = v(self.calls) if callable(v) else v
        self.calls += 1
        return s


def make_cfg(classes, source=None, **top):
    cfg = config._merge(config.DEFAULTS, {"classes": classes, "sources": [dict({"id": "s1", "type": "file", "url": "x"}, **(source or {}))], **top})
    assert config.validate(cfg, CAT) == []
    return cfg


def loud(n):  # noise at roughly -20 dBFS
    return (np.random.default_rng(1).standard_normal(n) * 3000).clip(-32768, 32767).astype(np.int16)


def run(pipe, seconds, audio=loud, start=T0, chunk=4000):
    events, now, fed = [], start, 0
    total = int(seconds * 16000)
    while fed < total:
        n = min(chunk, total - fed)
        now += dt.timedelta(seconds=n / 16000)
        events += pipe.feed(audio(n), now)
        fed += n
    return events


def det(events):
    return [e for e in events if e["type"] == "detection"]


def test_sustained_detection_and_cooldown():
    cfg = make_cfg({"Smoke detector, smoke alarm": {"enabled": True}})
    p = SourcePipeline(cfg["sources"][0], cfg, CAT, Fake({"Smoke detector, smoke alarm": 0.9}))
    ev = det(run(p, 12))
    assert len(ev) == 1                       # cooldown 60 s: a single event
    assert ev[0]["duration_s"] >= 3.0         # catalog min_duration 3 s
    assert ev[0]["class"] == "Smoke detector, smoke alarm" and ev[0]["score"] == 0.9


def test_short_burst_is_not_reported():
    cfg = make_cfg({"Smoke detector, smoke alarm": {"enabled": True}})
    f = Fake({"Smoke detector, smoke alarm": lambda i: 0.9 if i < 3 else 0.0})   # ~1.9 s only
    assert det(run(SourcePipeline(cfg["sources"][0], cfg, CAT, f), 10)) == []


def test_one_missed_window_is_tolerated_two_are_not():
    cls = {"Smoke detector, smoke alarm": {"enabled": True, "min_duration_s": 3}}
    pat = lambda bad: (lambda i: 0.0 if i in bad else 0.9)
    cfg = make_cfg(cls)
    ev = det(run(SourcePipeline(cfg["sources"][0], cfg, CAT, Fake({"Smoke detector, smoke alarm": pat({2})})), 10))
    assert len(ev) == 1
    ev = det(run(SourcePipeline(cfg["sources"][0], cfg, CAT, Fake({"Smoke detector, smoke alarm": pat({2, 3, 8, 9})})), 8))
    assert ev == []                           # run restarted after two misses and never reaches 3 s


def test_volume_gate_skips_inference():
    cfg = make_cfg({"Bark": {"enabled": True}}, source={"min_volume_dbfs": -40})
    f = Fake({"Bark": 0.9})
    p = SourcePipeline(cfg["sources"][0], cfg, CAT, f)
    assert det(run(p, 6, audio=lambda n: np.zeros(n, dtype=np.int16))) == []
    assert f.calls == 0 and p.state["below_gate"] is True
    ev = det(run(p, 6, start=T0 + dt.timedelta(seconds=6)))     # loud audio: gate open
    assert len(ev) == 1 and f.calls > 0 and p.state["below_gate"] is False


def test_schedule_outside_window_is_silent():
    sched = {"mode": "scheduled", "windows": [{"days": ["mon"], "from": "20:00", "to": "22:00"}]}
    cfg = make_cfg({"Bark": {"enabled": True}}, source={"schedule": sched}, timezone="UTC")
    f = Fake({"Bark": 0.9})
    assert det(run(SourcePipeline(cfg["sources"][0], cfg, CAT, f, tz="UTC"), 6)) == [] and f.calls == 0
    cfg = make_cfg({"Bark": {"enabled": True}}, source={"schedule": {"mode": "continuous"}})
    assert len(det(run(SourcePipeline(cfg["sources"][0], cfg, CAT, Fake({"Bark": 0.9}), tz="UTC"), 6))) == 1


def test_context_raises_threshold():
    cls = {"Bark": {"enabled": True, "min_duration_s": 0}, "Television": {"enabled": True}}
    cfg = make_cfg(cls)
    only_bark = Fake({"Bark": 0.6})                                 # catalog threshold 0.5
    assert len(det(run(SourcePipeline(cfg["sources"][0], cfg, CAT, only_bark), 3))) == 1
    with_tv = Fake({"Bark": 0.6, "Television": 0.9})                # threshold becomes 0.65 -> silent
    assert det(run(SourcePipeline(cfg["sources"][0], cfg, CAT, with_tv), 3)) == []
    strong = Fake({"Bark": 0.9, "Television": 0.9})
    ev = det(run(SourcePipeline(cfg["sources"][0], cfg, CAT, strong), 3))
    assert len(ev) == 1 and ev[0]["threshold"] == 0.65 and ev[0]["offset"] == 0.15


def test_safety_sounds_are_only_raised_up_to_the_cap():
    cls = {"Screaming": {"enabled": True, "min_duration_s": 0}, "Television": {"enabled": True}}   # Screaming: threshold 0.6
    cfg = make_cfg(cls)
    p = SourcePipeline(cfg["sources"][0], cfg, CAT, Fake({"Screaming": 0.7, "Television": 0.9}))
    ev = det(run(p, 3))
    assert len(ev) == 1 and ev[0]["threshold"] == 0.65             # +0.05 (cap), not +0.15
    cfg = make_cfg(cls, analysis={"safety_boost_cap": 0.0})
    p = SourcePipeline(cfg["sources"][0], cfg, CAT, Fake({"Screaming": 0.61, "Television": 0.9}))
    assert det(run(p, 3))[0]["threshold"] == 0.6                   # 0 = never raised
    cfg = make_cfg(cls, analysis={"safety_boost_cap": 1.0})
    p = SourcePipeline(cfg["sources"][0], cfg, CAT, Fake({"Screaming": 0.7, "Television": 0.9}))
    assert det(run(p, 3)) == []                                    # cap 1 = same as any other class


def test_sounds_hidden_by_the_raised_threshold_are_counted_once():
    cls = {"Bark": {"enabled": True, "min_duration_s": 0, "cooldown_s": 30}, "Television": {"enabled": True}}
    cfg = make_cfg(cls)
    p = SourcePipeline(cfg["sources"][0], cfg, CAT, Fake({"Bark": 0.6, "Television": 0.9}))
    ev = run(p, 6)
    assert [e["class"] for e in det(ev)] == ["Television"]          # the context itself is reported; the bark is not
    masked = [e for e in ev if e["type"] == "masked"]
    assert len(masked) == 1                                        # cooldown: one per episode, like a detection
    m = masked[0]
    assert m["class"] == "Bark" and m["base_threshold"] == 0.5 and m["threshold"] == 0.65 and m["reasons"] == ["context"]
    cfg = make_cfg({"Bark": {"enabled": True, "min_duration_s": 0}})
    assert [e for e in run(SourcePipeline(cfg["sources"][0], cfg, CAT, Fake({"Bark": 0.3})), 4) if e["type"] == "masked"] == []   # below even the base threshold


def test_ambient_tracker_baseline_and_offset():
    from soundrec.ambient import AmbientTracker, WARMUP_MINUTES
    tr = AmbientTracker()
    for i in range(WARMUP_MINUTES * 60 - 30):                      # not enough history yet
        tr.add(float(i), -50.0)
    assert tr.baseline is None and tr.offset(0.15) == 0.0
    for i in range(WARMUP_MINUTES * 60, WARMUP_MINUTES * 60 + 120):
        tr.add(float(i), -50.0)
    assert tr.baseline == -50.0 and tr.offset(0.15) == 0.0         # quiet room: nothing
    t0 = WARMUP_MINUTES * 60 + 120
    for i in range(90):                                            # TV on: 20 dB louder for 90 s
        tr.add(float(t0 + i), -30.0)
    assert tr.ambient == -30.0
    assert tr.offset(0.15) == pytest.approx(0.15 * (20 - 6) / 30, abs=0.001)
    assert tr.offset(0.0) == 0.0


def test_adaptive_setting_raises_thresholds_only_when_enabled():
    cls = {"Bark": {"enabled": True, "min_duration_s": 0}}
    for enabled, expected in ((False, 1), (True, 0)):
        cfg = make_cfg(cls, source={"adaptive": {"enabled": enabled, "max_offset": 0.2}})
        p = SourcePipeline(cfg["sources"][0], cfg, CAT, Fake({"Bark": 0.6}))
        p.ambient._minutes.extend([-60.0] * 40)                    # a known quiet baseline of -60 dBFS
        ev = run(p, 3)                                             # loud() sits near -20 dBFS: 40 dB above the baseline
        assert len(det(ev)) == expected
        if enabled:
            assert p.state["adaptive_offset"] == 0.2 and [e["reasons"] for e in ev if e["type"] == "masked"] == [["ambient"]]


def test_clip_pre_and_post_roll_and_forbidden():
    cfg = make_cfg({"Shatter": {"enabled": True, "min_duration_s": 0}, "Speech": {"enabled": True, "min_duration_s": 0}})
    f = Fake({"Shatter": lambda i: 0.9 if i == 12 else 0.0, "Speech": 0.9})
    ev = run(SourcePipeline(cfg["sources"][0], cfg, CAT, f), 20)
    shatter = [e for e in det(ev) if e["class"] == "Shatter"][0]
    clips = [e for e in ev if e["type"] == "clip"]
    assert len(clips) == 1 and clips[0]["id"] == shatter["id"]                    # speech never produces a clip
    sug = CAT.get("Shatter")["suggestions"]
    secs = len(clips[0]["pcm"]) / 16000
    assert abs(secs - (sug["pre_roll_s"] + 0.975 + sug["post_roll_s"])) < 0.6
    speech = [e for e in det(ev) if e["class"] == "Speech"][0]
    assert speech["clip_retention_days"] == 0 and speech["clip_reason"] == "catalog_clip_forbidden"
    assert "clip_reason" not in shatter                                           # a clip is coming: nothing to explain


def test_inactive_classes_state_and_hold():
    cfg = make_cfg({"Bark": {"enabled": True, "min_duration_s": 0}})
    p = SourcePipeline(cfg["sources"][0], cfg, CAT, Fake({"Bark": lambda i: 0.9 if i < 6 else 0.0}))
    run(p, 3)
    assert CAT.get("Bark")["mid"] in p.state["active_classes"]
    run(p, 8, start=T0 + dt.timedelta(seconds=3))
    assert p.state["active_classes"] == []


@pytest.mark.asyncio
async def test_engine_publishes_active_changes(tmp_path, monkeypatch):
    import asyncio
    import yaml
    from soundrec import engine as engine_mod

    cfgp = tmp_path / "c.yaml"
    yaml.safe_dump({"storage": {"clips_dir": str(tmp_path / "clips"), "db_path": str(tmp_path / "e.sqlite")},
                    "classes": {"Bark": {"enabled": True, "min_duration_s": 0}},
                    "sources": [{"id": "s1", "type": "file", "url": "x"}]}, open(cfgp, "w"))

    async def fake_read(source, on_pcm, on_state, **kw):   # stands in for ffmpeg
        on_state("connected", None)
        for _ in range(60):
            on_pcm(loud(4000))
            await asyncio.sleep(0)

    monkeypatch.setattr(engine_mod, "read_source", fake_read)
    eng = engine_mod.Engine(str(cfgp), "unused", classifier=Fake({"Bark": lambda i: 0.9 if i < 4 else 0.0}))
    q = eng.subscribe()
    await eng.start()
    await asyncio.sleep(0.3)
    await eng.stop()
    msgs = [q.get_nowait() for _ in range(q.qsize())]
    bark = CAT.get("Bark")["mid"]
    active = [m["active_classes"] for m in msgs if m["type"] == "active"]
    assert [bark] in active and active[-1] == []              # turned on, then off again
    assert any(m["type"] == "detection" for m in msgs)


def test_external_offset_from_the_integration_expires_and_is_capped():
    cls = {"Bark": {"enabled": True, "min_duration_s": 0}, "Screaming": {"enabled": True, "min_duration_s": 0}}   # thresholds 0.5 and 0.6
    cfg = make_cfg(cls)
    p = SourcePipeline(cfg["sources"][0], cfg, CAT, Fake({"Bark": 0.6, "Screaming": 0.64}))
    p.set_external(0.2, ["device"], [{"label": "TV (salon)", "value": 0.2}], 60, T0)
    ev = run(p, 3)
    assert det(ev) == []                                                       # Bark 0.6 < 0.7; Screaming 0.64 < 0.65 (safety cap: +0.05 only)
    masked = {e["class"]: e for e in ev if e["type"] == "masked"}
    assert masked["Bark"]["threshold"] == 0.7 and masked["Screaming"]["threshold"] == 0.65 and masked["Bark"]["reasons"] == ["device"]
    assert p.state["external_offset"] == 0.2 and p.state["external_detail"][0]["label"] == "TV (salon)"
    ev = run(p, 3, start=T0 + dt.timedelta(seconds=120))                       # lapsed: the integration stopped talking
    assert {e["class"] for e in det(ev)} == {"Bark", "Screaming"}
    assert p.state["external_offset"] == 0.0 and p.state["external_detail"] == []
    p.set_external(0.9, ["shared"], [], 60, T0 + dt.timedelta(seconds=120))      # absurd value: the total cap (0.30) applies
    p.feed(loud(16000), T0 + dt.timedelta(seconds=124))
    assert p.state["external_offset"] == 0.9
    p2 = SourcePipeline(cfg["sources"][0], cfg, CAT, Fake({"Bark": 0.79}))
    p2.set_external(0.9, ["shared"], [], 60, T0)
    assert det(run(p2, 3)) == []                                                 # 0.5 + 0.30 = 0.80 > 0.79
    p3 = SourcePipeline(cfg["sources"][0], cfg, CAT, Fake({"Bark": 0.81}))
    p3.set_external(0.9, ["shared"], [], 60, T0)
    assert len(det(run(p3, 3))) == 1
