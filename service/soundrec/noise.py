"""Noise measurements of a source and the minimum volume they suggest.

The service keeps one number per source and minute (the ambient level in dBFS, the median of the minute's windows) and whether a detection
happened in it: never any audio. From the calm minutes it suggests a minimum volume (the quietest sound taken into account): the level of
the quiet periods plus a margin, never above PRESET_MAX_VOLUME so that a distant alarm is still heard. Nothing is ever applied by the service."""
import datetime as dt
import zoneinfo

from .settings import PRESET_MAX_VOLUME

MIN_MINUTES = 6 * 60          # calm minutes needed before a suggestion is made
MARGIN_DB = 6.0               # added to the level of the quiet periods
FLOOR_DB = -90                # the gate cannot go lower (valid range of min_volume_dbfs)
BYTES_PER_MINUTE = 40         # rough size of a measurement in the database, shown to give an idea of the weight
DEFAULT_DAYS = 7


def _pct(ordered, p):
    return ordered[int(p * (len(ordered) - 1))]


def summarize(rows, tz=None):
    """rows: [(epoch minute, level, event 0/1)] of one source. Returns the figures the panel shows, and the suggestion."""
    out = {"minutes": len(rows), "since": rows[0][0] * 60 if rows else None, "until": rows[-1][0] * 60 if rows else None}
    calm = [r for r in rows if not r[2]]
    out["calm_minutes"] = len(calm)
    out["bytes"] = len(rows) * BYTES_PER_MINUTE
    if len(calm) < MIN_MINUTES:
        out["suggestion"] = {"status": "not_enough", "minutes": len(calm), "needed": MIN_MINUTES}
        out["hourly"] = [None] * 24
        return out
    levels = sorted(r[1] for r in calm)
    quiet = levels[: max(1, len(levels) // 2)]                     # the quiet half of the calm minutes: the room at rest
    quiet_level = _pct(quiet, 0.9)
    raw = quiet_level + MARGIN_DB
    gate = int(round(max(FLOOR_DB, min(PRESET_MAX_VOLUME, raw))))
    out["suggestion"] = {"status": "ready", "gate": gate, "quiet_dbfs": round(quiet_level, 1), "typical_dbfs": round(_pct(levels, 0.5), 1),
                         "loud_dbfs": round(_pct(levels, 0.95), 1), "margin_db": MARGIN_DB, "capped": raw > PRESET_MAX_VOLUME, "minutes": len(calm)}
    zone = zoneinfo.ZoneInfo(tz) if tz else None
    sums, counts = [0.0] * 24, [0] * 24
    for minute, level, _ in calm:
        t = dt.datetime.fromtimestamp(minute * 60, zone) if zone else dt.datetime.fromtimestamp(minute * 60)
        sums[t.hour] += level
        counts[t.hour] += 1
    out["hourly"] = [round(sums[h] / counts[h], 1) if counts[h] else None for h in range(24)]
    return out
