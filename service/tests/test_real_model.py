"""End-to-end check of the pipeline with the real YAMNet model (skipped when the model file is not available)."""
import datetime as dt
import os
import numpy as np
import pytest

from soundrec import catalog as cm, config, settings as st
from soundrec.detector import SourcePipeline

MODEL = os.environ.get("SOUNDREC_MODEL", "/opt/models/yamnet.tflite")
pytestmark = pytest.mark.skipif(not os.path.exists(MODEL), reason="YAMNet model not available")


def test_tone_is_detected_as_beep_and_silence_is_gated():
    from soundrec.classifier import YamnetClassifier
    cat = st.Catalog(cm.load_raw())
    cfg = config._merge(config.DEFAULTS, {"classes": {"Beep, bleep": {"enabled": True, "threshold": 0.5, "min_duration_s": 2}},
                                          "sources": [{"id": "s", "type": "file", "url": "x"}]})
    p = SourcePipeline(cfg["sources"][0], cfg, cat, YamnetClassifier(MODEL))
    t = np.arange(16000 * 6) / 16000
    audio = (0.5 * np.sin(2 * np.pi * 1000 * t) * 32767).astype(np.int16)
    now, ev = dt.datetime(2026, 10, 5, 12, tzinfo=dt.timezone.utc), []
    for i in range(0, len(audio), 4000):
        now += dt.timedelta(seconds=0.25)
        ev += p.feed(audio[i:i + 4000], now)
    assert [e["class"] for e in ev if e["type"] == "detection"] == ["Beep, bleep"]
    for _ in range(12):                      # flush: windows still overlap the end of the tone
        now += dt.timedelta(seconds=0.25)
        p.feed(np.zeros(4000, dtype=np.int16), now)
    n = p.state["inferences"]
    for _ in range(40):                      # digital silence: below the -60 dBFS gate, no inference at all
        now += dt.timedelta(seconds=0.25)
        p.feed(np.zeros(4000, dtype=np.int16), now)
    assert p.state["inferences"] == n and p.state["below_gate"] is True
