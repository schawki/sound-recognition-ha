"""Audio capture: ffmpeg subprocess per source (any URL ffmpeg can read), ring buffer, reconnection."""
import asyncio
import logging
import numpy as np

from .classifier import SAMPLE_RATE

log = logging.getLogger("soundrec.audio")


class RingBuffer:
    """Circular int16 buffer addressed by absolute sample index."""

    def __init__(self, seconds):
        self.size = int(seconds * SAMPLE_RATE)
        self.buf = np.zeros(self.size, dtype=np.int16)
        self.total = 0  # absolute index of the next sample to be written

    def write(self, pcm):
        n = len(pcm)
        if n >= self.size:
            raise ValueError("chunk larger than the ring buffer")
        start = self.total % self.size
        first = min(n, self.size - start)
        self.buf[start:start + first] = pcm[:first]
        if first < n:
            self.buf[:n - first] = pcm[first:]
        self.total += n

    def oldest(self):
        return max(0, self.total - self.size)

    def get(self, start, end):
        """Samples [start, end) clamped to what is still available; None if empty."""
        start = max(start, self.oldest())
        end = min(end, self.total)
        if end <= start:
            return None
        idx = np.arange(start, end) % self.size
        return self.buf[idx]


def ffmpeg_args(source):
    url, typ = source["url"], source["type"]
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-threads", "1"]
    if typ in ("rtsp", "go2rtc", "alsa_rpi") and url.startswith("rtsp"):
        args += ["-rtsp_transport", "tcp", "-allowed_media_types", "audio"]
    if typ == "file":
        args += ["-re", "-stream_loop", "-1"]
    args += ["-i", url, "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "s16le", "pipe:1"]
    return args


async def read_source(source, on_pcm, on_state, chunk_samples=SAMPLE_RATE // 4, stall_s=15.0):
    """Runs until cancelled. Calls on_pcm(int16 array) for each chunk and on_state('connected'|'reconnecting', error)."""
    if source["type"] == "esphome":
        on_state("unsupported", "esphome sources are not implemented yet")
        return
    backoff = 1.0
    while True:
        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(*ffmpeg_args(source), stdout=asyncio.subprocess.PIPE,
                                                        stderr=asyncio.subprocess.PIPE)
            nbytes = chunk_samples * 2
            got_any = False
            while True:
                data = await asyncio.wait_for(proc.stdout.readexactly(nbytes), timeout=stall_s)
                if not got_any:
                    got_any = True
                    backoff = 1.0
                    on_state("connected", None)
                on_pcm(np.frombuffer(data, dtype=np.int16))
        except asyncio.CancelledError:
            raise
        except asyncio.IncompleteReadError:
            err = "stream ended"
        except asyncio.TimeoutError:
            err = f"no audio for {stall_s:.0f} s"
        except Exception as e:  # noqa: BLE001
            err = str(e)
        finally:
            if proc and proc.returncode is None:
                proc.kill()
                await proc.wait()
        if proc is not None and proc.stderr:
            try:
                tail = (await proc.stderr.read())[-300:].decode(errors="replace").strip()
                if tail:
                    err = f"{err}: {tail}"
            except Exception:  # noqa: BLE001
                pass
        on_state("reconnecting", err)
        log.warning("source %s: %s; retry in %.0f s", source["id"], err, backoff)
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 30.0)
