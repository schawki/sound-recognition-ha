"""Ambient noise of a source: what the room sounds like right now compared with how quiet it usually is.
Pure (time comes from the caller). The ambient level is the median of the last minute of window levels; the baseline is
the 10th percentile of the per-minute ambient levels of the last 24 hours (the quiet hours), once 30 minutes are known."""
import collections
import statistics

AMBIENT_S = 60.0
BASELINE_MINUTES = 24 * 60
WARMUP_MINUTES = 30
QUIET_MARGIN_DB = 6.0       # no offset until the ambient level is this far above the baseline
FULL_SPAN_DB = 30.0         # the full offset is reached this much further up


class AmbientTracker:
    def __init__(self):
        self._recent = collections.deque()               # (ts, level)
        self._minutes = collections.deque(maxlen=BASELINE_MINUTES)
        self._minute_start = None
        self.ambient = None

    def add(self, ts, level):
        self._recent.append((ts, level))
        while self._recent and ts - self._recent[0][0] > AMBIENT_S:
            self._recent.popleft()
        self.ambient = statistics.median(v for _, v in self._recent)
        if self._minute_start is None:
            self._minute_start = ts
        elif ts - self._minute_start >= 60.0:
            self._minutes.append(self.ambient)
            self._minute_start = ts

    @property
    def baseline(self):
        if len(self._minutes) < WARMUP_MINUTES:
            return None
        ordered = sorted(self._minutes)
        return ordered[int(0.1 * (len(ordered) - 1))]

    def offset(self, max_offset):
        """Threshold offset (0 to max_offset) for the current ambient level; 0 while the baseline is unknown."""
        base = self.baseline
        if base is None or self.ambient is None:
            return 0.0
        frac = (self.ambient - base - QUIET_MARGIN_DB) / FULL_SPAN_DB
        return round(max_offset * min(1.0, max(0.0, frac)), 3)
