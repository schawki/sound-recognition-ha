"""Loads the built panel in headless Chromium against a stand-in for Home Assistant, checks behaviour and writes screenshots.
Usage: python3 test/run.py [output_dir]   (after `npm run build`)"""
import http.server, json, os, sys, threading
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "..", "..", "custom_components", "sound_recognition", "frontend", "sound-recognition-panel.js")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, os.path.join(HERE, "..", "..", "service"))
from soundrec import catalog as _cm
CATALOGS = {f"/catalog_{lang}.json": json.dumps(_cm.load_lang(lang)).encode() for lang in ("en", "fr")}   # the real 521-class catalog


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        files = {"/": ("harness.html", "text/html"), "/panel.js": (BUILD, "text/javascript"), "/clip.wav": (None, "audio/wav")}
        if path == "/favicon.ico":
            self.send_response(204); self.end_headers(); return
        if path in CATALOGS:
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(CATALOGS[path]); return
        if path not in files:
            self.send_response(404); self.end_headers(); return
        name, ctype = files[path]
        body = b"RIFF" if name is None else open(name if os.path.isabs(name) else os.path.join(HERE, name), "rb").read()
        self.send_response(200); self.send_header("Content-Type", ctype); self.end_headers(); self.wfile.write(body)

    def log_message(self, *a): pass


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_port}/"


def text(page, sel):
    return page.evaluate("""(sel) => { const walk = (r) => { const out = []; r.querySelectorAll('*').forEach(e => { if (e.shadowRoot) out.push(...walk(e.shadowRoot)); }); out.push(...r.querySelectorAll(sel)); return out; }; return walk(document).map(e => e.textContent.trim().replace(/\\s+/g, ' ')); }""", sel)


def ok(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        ok.failed = True
ok.failed = False


SHOTS = os.path.join(HERE, "..", "..", "docs", "images")
os.makedirs(SHOTS, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium", args=["--no-sandbox"])
    def shot(name, tab, query="", scheme="light", w=1100, h=760, lang="en", after=None, wait="", full=False):
        pg = b.new_page(viewport={"width": w, "height": h}, color_scheme=scheme)
        pg.add_init_script("window.__updatePollMs = 50")
        pg.goto(base + "?upd=none&lang=" + lang + query)
        pg.wait_for_selector("sound-recognition-live .card")
        if tab != "live":
            pg.click(f"button[data-tab={tab}]")
        if wait: pg.wait_for_selector(wait)
        pg.wait_for_timeout(400)
        if after: after(pg)
        pg.screenshot(path=os.path.join(SHOTS, name), full_page=full)
        pg.close()
    shot("live.png", "live", h=720)
    shot("overview.png", "insights", h=820)
    shot("advice.png", "advice", "&choices=1&fix=1", h=900, wait="sound-recognition-advice li.advice")
    shot("sounds.png", "sounds", h=800)
    b.close()
