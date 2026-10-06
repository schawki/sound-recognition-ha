import datetime as dt

from soundrec.store import EventStore


def ev(i, **kw):
    now = dt.datetime.now(dt.timezone.utc)
    return dict({"id": i, "source": "s", "mid": "/m/x", "class": "X", "score": 0.8, "threshold": 0.5, "duration_s": 1, "level_dbfs": -30,
                 "started_at": now.isoformat(), "detected_at": now.isoformat()}, **kw)


def test_reason_is_stored_then_replaced_when_the_clip_goes(tmp_path):
    st = EventStore(str(tmp_path / "e.sqlite"))
    st.add(ev("a", clip_reason="class"))
    st.add(ev("b"))
    st.add(ev("c"))
    st.set_clip("b", "s/b.wav", "2999-01-01T00:00:00+00:00")
    st.set_clip("c", "s/c.wav", "2000-01-01T00:00:00+00:00")
    rows = {r["id"]: r for r in st.query()}
    assert rows["a"]["clip_reason"] == "class" and rows["b"]["clip_reason"] is None
    assert {r["id"] for r in st.clips()} == {"b", "c"} and all("threshold" in r and "feedback" in r for r in st.clips())
    st.purge(0, dt.datetime.now(dt.timezone.utc).isoformat())
    rows = {r["id"]: r for r in st.query()}
    assert rows["c"]["clip_reason"] == "expired" and rows["b"]["clip_reason"] is None
    st.forget_clips(["b"])
    assert {r["id"]: r for r in st.query()}["b"]["clip_reason"] == "deleted"
