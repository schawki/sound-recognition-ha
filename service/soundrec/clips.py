"""Clip files (WAV, 16 kHz mono) with a JSON sidecar holding the expiry date; periodic purge."""
import datetime as dt
import json
import os
import wave

from .classifier import SAMPLE_RATE


class ClipStore:
    def __init__(self, root):
        self.root = root

    def write(self, clip_id, pcm, meta, retention_days, now):
        day = now.strftime("%Y-%m-%d")
        d = os.path.join(self.root, day)
        os.makedirs(d, exist_ok=True)
        wav = os.path.join(d, f"{clip_id}.wav")
        with wave.open(wav, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SAMPLE_RATE)
            w.writeframes(pcm.tobytes())
        expire = now + dt.timedelta(days=retention_days)
        with open(os.path.join(d, f"{clip_id}.json"), "w", encoding="utf-8") as f:
            json.dump(dict(meta, clip_id=clip_id, expires_at=expire.isoformat()), f)
        return f"{day}/{clip_id}.wav", expire

    def path(self, rel):
        p = os.path.abspath(os.path.join(self.root, rel))
        if not p.startswith(os.path.abspath(self.root) + os.sep) or not os.path.isfile(p):
            return None
        return p

    def purge(self, now):
        """Deletes expired clips and empty day folders; returns the list of removed relative paths."""
        removed = []
        if not os.path.isdir(self.root):
            return removed
        for day in sorted(os.listdir(self.root)):
            d = os.path.join(self.root, day)
            if not os.path.isdir(d):
                continue
            for f in os.listdir(d):
                if not f.endswith(".json"):
                    continue
                try:
                    meta = json.load(open(os.path.join(d, f), encoding="utf-8"))
                    expired = dt.datetime.fromisoformat(meta["expires_at"]) <= now
                except Exception:  # noqa: BLE001 - unreadable sidecar: keep, never guess
                    continue
                if expired:
                    for ext in (".wav", ".json"):
                        p = os.path.join(d, f[:-5] + ext)
                        if os.path.exists(p):
                            os.remove(p)
                    removed.append(f"{day}/{f[:-5]}.wav")
            if not os.listdir(d):
                os.rmdir(d)
        return removed
