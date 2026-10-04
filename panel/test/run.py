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

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium", args=["--no-sandbox"])
    errors = []

    def new(query="", scheme="light", w=1200, h=800):
        pg = b.new_page(viewport={"width": w, "height": h}, color_scheme=scheme)
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.goto(base + query)
        return pg

    pg = new()
    pg.wait_for_function("document.querySelector('sound-recognition-panel')?.shadowRoot?.querySelector('sound-recognition-live')?.shadowRoot?.querySelector('.card')")
    cards = text(pg, ".card")
    ok(len(cards) == 4, "four source cards")
    ok(any("Kitchen" in c and "Connected" in c and "-38 dBFS" in c for c in cards), "kitchen shows connection and level")
    ok(any("Garden camera" in c and "Below the volume gate" in c for c in cards), "gated source flagged")
    ok(any("Nursery" in c and "Starting" in c for c in cards) and any("Old Pi" in c and "Disabled" in c for c in cards), "starting and disabled states")
    ok(any("1 advice item" in t for t in text(pg, ".banner")), "advice banner")
    ev = text(pg, ".events li")
    ok(len(ev) == 3 and "Bark" in ev[0] and "91%" in ev[0] and "2 minutes ago" in ev[0], "stored events with names, score, relative time")
    ok(pg.evaluate("document.querySelector('sound-recognition-panel').shadowRoot.querySelector('sound-recognition-live').shadowRoot.querySelectorAll('audio').length") == 2, "player only when a clip exists")
    # live messages
    pg.evaluate("window.__push({type:'active', source:'kitchen', active_classes:['/m/01y3hg']})")
    pg.evaluate("window.__push({type:'detection', id:'n1', source:'kitchen', mid:'/m/01y3hg', class:'Smoke', name:'Smoke detector', score:0.88, duration_s:2, detected_at:new Date().toISOString()})")
    pg.wait_for_timeout(200)
    ok(any("Active now" in c and "Smoke detector" in c for c in text(pg, ".card")), "live active class shown")
    ev = text(pg, ".events li")
    ok(len(ev) == 4 and "Smoke detector" in ev[0] and "just now" in ev[0], "live detection prepended")
    pg.evaluate("window.__push({type:'clip_ready', id:'n1', source:'kitchen', mid:'/m/01y3hg', clip:'k/n1.wav', clip_url:'/clip.wav', expires_at:'x'})")
    pg.wait_for_timeout(200)
    ok(pg.evaluate("document.querySelector('sound-recognition-panel').shadowRoot.querySelector('sound-recognition-live').shadowRoot.querySelectorAll('audio').length") == 3, "clip attached to its detection")
    pg.evaluate("window.__push({type:'source_state', source:'kitchen', state:'disconnected', error:'boom'})")
    pg.wait_for_timeout(200)
    ok(any("Kitchen" in c and "Disconnected" in c for c in text(pg, ".card")), "connection loss shown")
    pg.evaluate("window.__push({type:'source_state', source:'kitchen', state:'connected'})")
    pg.evaluate("window.__push({type:'active', source:'kitchen', active_classes:[]})")
    pg.screenshot(path=os.path.join(OUT, "live-light.png"))
    pg.close()

    pg = new("?lang=fr", "dark")
    pg.wait_for_function("document.querySelector('sound-recognition-panel')?.shadowRoot?.querySelector('sound-recognition-live')?.shadowRoot?.querySelector('.card')")
    ok(any("Connecté" in c for c in text(pg, ".card")) and any("Aboiement" in e and "il y a 2 minutes" in e for e in text(pg, ".events li")), "French texts and catalog language")
    pg.screenshot(path=os.path.join(OUT, "live-dark-fr.png"))
    pg.close()

    pg = new("?narrow=1", "light", 390, 800)
    pg.wait_for_function("document.querySelector('sound-recognition-panel')?.shadowRoot?.querySelector('sound-recognition-live')?.shadowRoot?.querySelector('.card')")
    ok(pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "no horizontal scroll at phone width")
    ok(len(text(pg, ".menu")) == 1, "menu button when narrow")
    pg.screenshot(path=os.path.join(OUT, "live-phone.png"), full_page=True)
    pg.close()

    # ------------------------------------------------------------------ sources tab
    def deep(page, sel):
        return page.locator(sel)

    pg = new("", "light", 1200, 900)
    pg.wait_for_selector("sound-recognition-live .card")
    pg.click("button[data-tab=sources]")
    pg.wait_for_selector("sound-recognition-sources li[data-source]")
    rows = text(pg, ".list li")
    ok(len(rows) == 2 and "Scheduled · 52.5 h per week" in rows[0] and "Clips up to 7 days" in rows[0], "source list with schedule and clips summary")
    ok("Listens continuously" in rows[1] and "Clips: default" in rows[1], "continuous source summary")
    # edit keeps hidden fields and untouched schedule windows byte for byte
    pg.click("li[data-source=kitchen] button[data-action=edit]")
    pg.wait_for_selector("sound-recognition-sources form")
    ok(pg.locator("sr-schedule-grid .cell.on").count() == 5 * 21, "grid shows 08:00-18:30 on weekdays (off-grid end widened)")
    pg.fill("input[name=name]", "Kitchen ESP32")
    pg.click("button[data-action=save]")
    pg.wait_for_selector("sound-recognition-sources .notice")
    saved = pg.evaluate("window.__state.saves.at(-1)")
    k = next(s for s in saved["sources"] if s["id"] == "kitchen")
    ok(k["name"] == "Kitchen ESP32" and k["classes"] == {"Smoke detector, smoke alarm": {"enabled": True}} and k["schedule"]["windows"] == [{"days": ["mon", "tue", "wed", "thu", "fri"], "from": "08:00", "to": "18:10"}], "edit keeps class settings and untouched windows")
    ok(saved["api"]["token"] == "***" and saved["classes"] == {"Bark": {"enabled": True}}, "rest of the configuration is sent back unchanged")
    ok("Advice for this source" not in text(pg, ".notice")[0], "no advice shown for another source")
    # add a source with a painted schedule
    pg.click("button[data-action=add]")
    ok(pg.locator("select[name=type]").input_value() == "go2rtc", "the form starts on go2rtc")
    pg.select_option("select[name=type]", "rtsp")
    pg.fill("input[name=row-name]", "Nursery ESP32")
    pg.fill("input[name=row-url]", "rtsp://x/n")
    pg.click("details.adv summary")
    pg.fill("input[name=offset]", "-0.1")
    pg.fill("input[name=minVolume]", "-50")
    pg.check("input[name=mode][value=scheduled]")
    pg.wait_for_selector("sr-schedule-grid .cell")
    ok(pg.locator("sr-schedule-grid .cell.on").count() == 0, "new schedule starts empty")
    pg.click("button[data-action=save]")
    ok(any("at least one time slot" in t for t in text(pg, ".errors")), "empty schedule is refused before saving")
    first = pg.locator("sr-schedule-grid .cell").nth(0).bounding_box()
    last = pg.locator("sr-schedule-grid .cell").nth(11).bounding_box()      # Monday 00:00-06:00 by dragging
    pg.mouse.move(first["x"] + 2, first["y"] + 2); pg.mouse.down(); pg.mouse.move(last["x"] + 2, last["y"] + 2, steps=8); pg.mouse.up()
    ok(pg.locator("sr-schedule-grid .cell.on").count() == 12, "dragging paints cells")
    pg.locator("sr-schedule-grid .day").nth(1).click()                      # whole Tuesday
    ok(pg.locator("sr-schedule-grid .cell.on").count() == 12 + 48, "clicking a day toggles it")
    pg.screenshot(path=os.path.join(OUT, "sources-form.png"), full_page=True)
    pg.click("button[data-action=save]")
    pg.wait_for_selector("sound-recognition-sources .notice")
    saved = pg.evaluate("window.__state.saves.at(-1)")
    n = saved["sources"][-1]
    ok(n["id"] == "nursery_esp32" and n["threshold_offset"] == -0.1 and n["min_volume_dbfs"] == -50 and n["schedule"]["mode"] == "scheduled", "new source saved with id, offset, gate")
    ok(n["schedule"]["windows"] == [{"days": ["mon"], "from": "00:00", "to": "06:00"}, {"days": ["tue"], "from": "00:00", "to": "00:00"}], "painted cells become service windows")
    ok(any("Gap in the schedule" in t for t in text(pg, ".notice")), "advice for the saved source is shown")
    pg.screenshot(path=os.path.join(OUT, "sources-list.png"), full_page=True)
    # go2rtc stream picker and adding several sources at once
    pg.click("button[data-action=add]")
    ok(pg.locator("select[name=type]").input_value() == "rtsp", "after an RTSP source the next form starts on RTSP")
    pg.select_option("select[name=type]", "go2rtc")
    pg.wait_for_selector("input[name=g2url]")
    ok(pg.locator("input[name=g2pick]").count() == 0 and pg.evaluate("window.__state.g2calls") == [None], "go2rtc asks for the remembered address first, none known yet")
    pg.fill("input[name=g2url]", "go2rtc-down")
    pg.click("button[data-action=g2-load]")
    pg.wait_for_selector("[data-g2-error]")
    ok("refused" in text(pg, "[data-g2-error]")[0] and pg.locator("input[name=g2pick]").count() == 0, "an unreachable go2rtc shows the reason and no list")
    pg.fill("input[name=g2url]", "192.168.1.5")
    pg.click("button[data-action=g2-load]")
    pg.wait_for_selector("input[name=g2pick]")
    ok(pg.evaluate("window.__state.g2calls.at(-1)") == "192.168.1.5" and pg.locator("input[name=g2url]").input_value() == "http://192.168.1.5:1984", "address is sent and replaced by the normalised one")
    ok(pg.locator("input[name=g2pick]").count() == 2 and pg.locator("[data-stream]").all_text_contents()[0].strip().startswith("salon"), "streams are offered as checkboxes")
    pg.locator("[data-stream=garage] input[name=g2pick]").check()
    ok(pg.locator("[data-stream=garage] input[name=g2name]").input_value() == "garage", "a checked stream proposes its own name")
    pg.fill("[data-stream=garage] input[name=g2name]", "Garage mic")
    pg.locator("[data-stream=salon] input[name=g2pick]").check()
    pg.click("button[data-action=row-add]")
    pg.locator("input[name=row-name]").nth(0).fill("Porch")
    pg.locator("input[name=row-url]").nth(0).fill("rtsp://10.0.0.7/porch")
    pg.locator("details.paste summary").click()
    pg.fill("textarea[name=paste]", "Cellar, rtsp://10.0.0.8:554/s1\n\nrtsp://10.0.0.9/attic\n")
    pg.click("button[data-action=paste-add]")
    ok(pg.locator("input[name=row-url]").count() == 3 and pg.locator("input[name=row-name]").nth(1).input_value() == "Cellar" and pg.locator("input[name=row-url]").nth(2).input_value() == "rtsp://10.0.0.9/attic", "a pasted list becomes rows (name, address; address alone)")
    pg.screenshot(path=os.path.join(OUT, "sources-go2rtc.png"), full_page=True)
    before = len(pg.evaluate("window.__state.saves"))
    pg.click("button[data-action=save]")
    pg.wait_for_function(f"window.__state.saves.length == {before + 1}")
    batch = pg.evaluate("window.__state.saves.at(-1).sources")[-5:]
    ok([(x["name"], x["url"], x["type"]) for x in batch] == [
        ("Garage mic", "rtsp://192.168.1.5:8554/garage", "go2rtc"), ("salon", "rtsp://192.168.1.5:8554/salon", "go2rtc"),
        ("Porch", "rtsp://10.0.0.7/porch", "go2rtc"), ("Cellar", "rtsp://10.0.0.8:554/s1", "go2rtc"), ("attic", "rtsp://10.0.0.9/attic", "go2rtc")],
       "five sources are added with one save (names from the stream, the row or the address)")
    ok(len({x["id"] for x in pg.evaluate("window.__state.saves.at(-1).sources")}) == len(pg.evaluate("window.__state.saves.at(-1).sources")), "ids stay unique")
    pg.click("button[data-action=add]")
    ok(pg.locator("select[name=type]").input_value() == "go2rtc", "the next form starts on the last type used")
    pg.wait_for_selector("input[name=g2pick]")
    ok(pg.locator("[data-stream=salon] input[name=g2pick]").is_disabled() and "already added" in pg.locator("[data-stream=salon]").inner_text(), "streams already added are greyed out")
    pg.click("button[data-action=cancel]")
    # nothing to add is refused on the page; a refusal by the service is shown and nothing is saved
    pg.click("button[data-action=add]")
    pg.click("button[data-action=save]")
    ok(any("at least one" in t for t in text(pg, ".errors")), "adding nothing is refused on the page")
    pg.click("button[data-action=cancel]")
    pg.click("li[data-source=kitchen] button[data-action=edit]")
    pg.fill("input[name=url]", " ")
    pg.evaluate("document.querySelector('sound-recognition-panel').shadowRoot.querySelector('sound-recognition-sources').shadowRoot.querySelector('input[name=url]').removeAttribute('required')")
    pg.click("button[data-action=save]")
    pg.wait_for_selector("sound-recognition-sources .errors")
    ok(any("url is required" in t for t in text(pg, ".errors")) and len(pg.evaluate("window.__state.saves")) == 3, "service refusal is shown and nothing is saved")
    pg.click("button[data-action=cancel]")
    # disable and remove
    pg.locator("li[data-source=garden] input[type=checkbox]").uncheck()
    pg.wait_for_function("window.__state.saves.length == 4")
    ok(pg.evaluate("window.__state.saves.at(-1).sources.find(s => s.id==='garden').enabled") is False, "toggle disables a source")
    pg.click("li[data-source=garden] button[data-action=remove]")
    ok(pg.evaluate("window.__state.saves.length") == 4, "removal asks for confirmation first")
    pg.click("li[data-source=garden] button[data-action=confirm-remove]")
    pg.wait_for_function("window.__state.saves.length == 5")
    ok(all(s["id"] != "garden" for s in pg.evaluate("window.__state.saves.at(-1).sources")), "source removed after confirmation")
    pg.close()

    # ------------------------------------------------------------------ sounds tab
    def sounds_root(page):
        return "document.querySelector('sound-recognition-panel').shadowRoot.querySelector('sound-recognition-sounds').shadowRoot"

    def rows(page):
        return page.evaluate(sounds_root(page) + ".querySelectorAll('li[data-mid]').length")

    pg = new("", "light", 1200, 900)
    pg.wait_for_selector("sound-recognition-live .card")
    pg.click("button[data-tab=sounds]")
    pg.wait_for_selector("sound-recognition-sounds li[data-mid]")
    ok(any("521 sounds" in t for t in text(pg, ".dim")), "all 521 classes listed")
    ok(rows(pg) == 60, "list is paged")
    first = text(pg, "li[data-mid] .name")
    ok(all("Recommended alert" in f for f in first[:8]), "recommended alerts come first")
    pg.click("button[data-action=more]")
    ok(rows(pg) == 120, "show more adds a page")
    pg.fill("input[name=search]", "bark")
    pg.wait_for_timeout(100)
    names = text(pg, "li[data-mid] .name strong")
    ok("Bark" in names and 1 <= len(names) < 20, "search narrows the list")
    ok(any("Bark" in c for c in names), "search finds Bark")
    ok(pg.locator("sound-recognition-sounds li[data-mid]").first.locator("button.chip").count() == 2, "one chip per configured source in the all-sources view")
    # enable globally, save
    pg.fill("input[name=search]", "Bark")
    bark_row = pg.locator("sound-recognition-sounds li[data-mid='/m/05tny_']")
    ok(bark_row.locator("input[name=global]").is_checked(), "Bark is enabled globally in the stand-in configuration")
    pg.fill("input[name=search]", "Whistle")
    wh = pg.locator("sound-recognition-sounds li[data-mid]").first
    wh.locator("input[name=global]").check()
    ok(pg.locator("sound-recognition-sounds .savebar").count() == 1, "unsaved changes bar appears")
    wh.locator("button.chip[data-source=garden]").click()                         # explicit off on one source
    pg.click(".savebar button[data-action=save]")
    pg.wait_for_selector("sound-recognition-sounds .notice")
    saved = pg.evaluate("window.__state.saves.at(-1)")
    wkey = [k for k in saved["classes"] if k not in ("Bark",)][0]
    g = next(x for x in saved["sources"] if x["id"] == "garden")
    ok(saved["classes"][wkey] == {"enabled": True} and g["classes"][wkey] == {"enabled": False}, "global enable and per-source exception saved")
    ok(pg.locator("sound-recognition-sounds .savebar").count() == 0, "bar disappears once saved")
    # per-source scope: toggling back to the inherited state removes the override
    pg.select_option("select[name=scope]", "garden")
    pg.fill("input[name=search]", "Whistle")
    row = pg.locator("sound-recognition-sounds li[data-mid]").first
    ok(not row.locator("input[name=scoped]").is_checked(), "scope shows the effective state of the source")
    row.locator("input[name=scoped]").check()
    n_saves = pg.evaluate("window.__state.saves.length")
    pg.click(".savebar button[data-action=save]")
    pg.wait_for_function(f"window.__state.saves.length > {n_saves}")
    g = next(x for x in pg.evaluate("window.__state.saves.at(-1)")["sources"] if x["id"] == "garden")
    ok(wkey not in (g.get("classes") or {}), "back to the inherited value drops the exception")
    # discard
    pg.locator("li[data-mid]").first.locator("input").first.click()
    ok(pg.locator("sound-recognition-sounds .savebar").count() == 1, "toggle marks unsaved")
    pg.click(".savebar button:not(.primary)")
    ok(pg.locator("sound-recognition-sounds .savebar").count() == 0, "discard restores the saved configuration")
    # recommended
    pg.select_option("select[name=scope]", "")
    pg.fill("input[name=search]", "")
    pg.click("button[data-action=recommended]")
    pg.check("input[name=onlyEnabled]")
    ok(rows(pg) >= 8, "recommended sounds are enabled")
    pg.click(".savebar button:not(.primary)")
    pg.uncheck("input[name=onlyEnabled]")

    # detail of a sound in one source: placeholders, applied values with reasons
    pg.select_option("select[name=scope]", "garden")
    pg.fill("input[name=search]", "Bark")
    pg.locator("li[data-mid='/m/05tny_'] button[data-action=settings]").click()
    pg.wait_for_selector("sound-recognition-sounds sr-class-detail input[name=threshold]")
    ph = pg.get_attribute("input[name=threshold]", "placeholder")
    ok(ph in ("0.6", "0.60"), f"inherited threshold placeholder is catalog 0.5 + source offset 0.1 (got {ph})")
    ok(any("0.6 — catalog suggestion + source offset" in t for t in text(pg, "[data-applied=threshold]")), "applied threshold explains its origin")
    pg.fill("input[name=threshold]", "0.8")
    ok(any("0.8 — this source's setting for this sound" in t for t in text(pg, "[data-applied=threshold]")), "explicit value overrides the offset")
    pg.fill("input[name=min_volume_dbfs]", "-30")
    ok(any("-30 dBFS" in t for t in text(pg, "[data-applied=min_volume_dbfs]")), "volume gate applied")
    pg.click("button[data-action=apply]")
    n_saves = pg.evaluate("window.__state.saves.length")
    pg.click(".savebar button[data-action=save]")
    pg.wait_for_function(f"window.__state.saves.length > {n_saves}")
    g = next(x for x in pg.evaluate("window.__state.saves.at(-1)")["sources"] if x["id"] == "garden")
    ok(list(g["classes"].values())[0] == {"threshold": 0.8, "min_volume_dbfs": -30}, "per-source settings saved")

    # detail at "all sources" level: result per source, clip-forbidden class, schedule choice, advice
    pg.select_option("select[name=scope]", "")
    pg.fill("input[name=search]", "Speech")
    pg.locator("li[data-mid='/m/09x0r'] button[data-action=settings]").click()
    pg.wait_for_selector("sound-recognition-sounds sr-class-detail")
    ok(any("Clips are never kept" in t for t in text(pg, ".warn")) and pg.locator("input[name=clip_retention_days]").count() == 0, "clip-forbidden class explained, no retention field")
    pg.click("button:has-text('Back to the list')")
    pg.fill("input[name=search]", "Bark")
    pg.locator("li[data-mid='/m/05tny_'] button[data-action=settings]").click()
    pg.wait_for_selector("sr-class-detail table")
    pg.fill("input[name=threshold]", "0.7")
    thr = text(pg, "tbody tr")
    ok(thr[0].startswith("KitchenYes0.7") and thr[1].startswith("Garden cameraYes0.8"), "result per source includes each source's offset and own settings")
    pg.check("input[name=sched][value=times]")
    pg.wait_for_selector("sr-class-detail sr-schedule-grid .cell")
    pg.screenshot(path=os.path.join(OUT, "sounds-detail.png"), full_page=True)
    pg.click("button[data-action=apply]")
    pg.fill("input[name=search]", "")
    pg.fill("input[name=search]", "Smoke detector")
    pg.locator("li[data-mid='/m/01y3hg'] input[name=global]").check()
    pg.locator("li[data-mid='/m/01y3hg'] button[data-action=settings]").click()
    pg.wait_for_selector("sr-class-detail .advice li.danger", timeout=3000)
    ok(any("Add the beeps class too" in t for t in text(pg, ".advice li")), "service advice for this sound shown")
    pg.click("button:has-text('Back to the list')")
    pg.fill("input[name=search]", "")
    pg.screenshot(path=os.path.join(OUT, "sounds-list.png"), full_page=True)
    pg.close()

    # ------------------------------------------------------------------ advice tab
    def advice_cards(page, section=None):
        return page.locator("sound-recognition-advice li.advice")

    pg = new("", "light", 1200, 900)
    pg.wait_for_selector("sound-recognition-live .card")
    pg.click("button[data-tab=advice]")
    pg.wait_for_selector("sound-recognition-advice li.advice")
    ok(advice_cards(pg).count() == 4, "all advice listed")
    ok("Danger" in text(pg, "li.advice .badge")[0], "most serious advice first")
    pg.locator("li.advice[data-rule=speech_target][data-source=kitchen] select[data-scope=all]").select_option("info")
    badges = [b for b in text(pg, "li.advice.info .badge")]
    ok(sum("Information" in b for b in badges) == 3, "global level applies to every source (preview before saving)")
    ok(pg.locator("sound-recognition-advice .savebar").count() == 1, "advice change marks unsaved")
    pg.locator("li.advice[data-rule=speech_target][data-source=kitchen] select[data-scope=kitchen]").select_option("ignore")
    ok(pg.locator("sound-recognition-advice li.advice.hidden").count() == 1, "hiding for one source moves it to the hidden section")
    n_saves = pg.evaluate("window.__state.saves.length")
    pg.click(".savebar button[data-action=save]")
    pg.wait_for_function(f"window.__state.saves.length > {n_saves}")
    cfg = pg.evaluate("window.__state.saves.at(-1)")
    k = next(x for x in cfg["sources"] if x["id"] == "kitchen")
    ok(cfg["advice"] == {"speech_target": "info"} and k["advice"] == {"speech_target": "ignore"}, "global and per-source advice levels saved")
    # a safety advice needs confirmation
    pg.locator("li.advice[data-rule=fire_only] select[data-scope=kitchen]").select_option("ignore")
    ok(pg.locator("sound-recognition-advice .confirm").count() == 1 and pg.locator("sound-recognition-advice .savebar").count() == 0, "hiding a safety advice asks first and changes nothing yet")
    pg.click("button[data-action=cancel-hide]")
    ok(pg.locator("sound-recognition-advice .confirm").count() == 0, "confirmation can be cancelled")
    ok(pg.locator("li.advice[data-rule=fire_only] select[data-scope=kitchen]").input_value() == "inherit", "menu shows the real setting after cancelling")
    pg.locator("li.advice[data-rule=fire_only] select[data-scope=kitchen]").select_option("ignore")
    pg.click("button[data-action=confirm-hide]")
    pg.click(".savebar button[data-action=save]")
    pg.wait_for_function(f"window.__state.saves.length > {n_saves + 1}")
    k = next(x for x in pg.evaluate("window.__state.saves.at(-1)")["sources"] if x["id"] == "kitchen")
    ok(k["advice"]["fire_only"] == {"level": "ignore", "confirm": True}, "confirmed safety advice saved with confirm: true")
    ok(pg.locator("sound-recognition-advice li.advice.hidden").count() == 2, "hidden advice stays listed so it can be restored")
    pg.locator("li.advice[data-rule=speech_target][data-source=kitchen] select[data-scope=kitchen]").select_option("inherit")
    ok(pg.locator("sound-recognition-advice li.advice.hidden").count() == 1, "restoring brings the advice back")
    ok(pg.locator("li.advice[data-rule=speech_target][data-source=kitchen] select[data-scope=kitchen]").input_value() == "inherit" and pg.locator("li.advice[data-rule=speech_target][data-source=garden] select[data-scope=garden]").input_value() == "inherit", "each menu shows its own advice's setting after moves between sections")
    pg.screenshot(path=os.path.join(OUT, "advice.png"), full_page=True)
    pg.close()

    # ------------------------------------------------------------------ clips tab
    pg = new("", "light", 1200, 800)
    pg.wait_for_selector("sound-recognition-live .card")
    pg.click("button[data-tab=clips]")
    pg.wait_for_selector("sound-recognition-clips li[data-event]")
    ok(pg.locator("sound-recognition-clips li[data-event]").count() == 2 and pg.locator("sound-recognition-clips audio").count() == 2, "clips listed with players (events without clip left out)")
    ok(any("Kept until" in t for t in text(pg, ".what")), "expiry shown")
    pg.select_option("select[name=source]", "garden")
    ok(pg.locator("sound-recognition-clips li[data-event]").count() == 1, "filter by source")
    pg.select_option("select[name=source]", "")
    pg.select_option("select[name=sound]", "/m/01y3hg")
    ok(pg.locator("sound-recognition-clips li[data-event]").count() == 1, "filter by sound")
    pg.screenshot(path=os.path.join(OUT, "clips.png"), full_page=True)
    pg.close()

    # ------------------------------------------------------------------ keyboard
    pg = new("", "light", 1200, 800)
    pg.wait_for_selector("sound-recognition-live .card")
    pg.focus("button[data-tab=live]")
    pg.keyboard.press("ArrowRight")
    pg.wait_for_selector("sound-recognition-sources")
    ok(pg.get_attribute("button[data-tab=sources]", "aria-selected") == "true", "tabs follow the arrow keys")
    pg.keyboard.press("End")
    pg.wait_for_selector("sound-recognition-clips")
    ok(pg.get_attribute("button[data-tab=clips]", "aria-selected") == "true", "End goes to the last tab")
    pg.click("button[data-tab=sources]")
    pg.wait_for_selector("sound-recognition-sources li[data-source]")
    pg.click("li[data-source=kitchen] button[data-action=edit]")
    pg.wait_for_selector("sr-schedule-grid .grid")
    before = pg.locator("sr-schedule-grid .cell.on").count()
    pg.focus("sr-schedule-grid .grid")
    pg.keyboard.press("Space"); pg.keyboard.press("ArrowRight"); pg.keyboard.press("Space")
    ok(pg.locator("sr-schedule-grid .cell.on").count() == before + 2, "the schedule grid works with the keyboard")
    ok("Mon 00:00" in (pg.get_attribute("sr-schedule-grid #c0", "aria-label") or "") or "Mon" in (pg.get_attribute("sr-schedule-grid #c0", "aria-label") or ""), "cells have readable labels")
    pg.close()

    pg = new("?lang=fr", "dark", 1200, 800)
    pg.wait_for_selector("sound-recognition-live .card")
    pg.click("button[data-tab=advice]")
    pg.wait_for_selector("sound-recognition-advice li.advice")
    ok("Danger" in text(pg, "li.advice .badge")[0] and any("Niveau du catalogue" in t for t in text(pg, "option")), "French advice tab")
    pg.screenshot(path=os.path.join(OUT, "advice-dark-fr.png"))
    pg.close()

    pg = new("?lang=fr&narrow=1", "dark", 390, 800)
    pg.wait_for_selector("sound-recognition-live .card")
    pg.click("button[data-tab=sounds]")
    pg.wait_for_selector("sound-recognition-sounds li[data-mid]")
    ok(any("521 sons" in t for t in text(pg, ".dim")) and any("Alerte recommandée" in t for t in text(pg, "li[data-mid] .name")), "French sounds tab")
    ok(pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "sounds list fits a phone")
    pg.screenshot(path=os.path.join(OUT, "sounds-phone-fr.png"), full_page=False)
    pg.close()

    pg = new("?narrow=1&lang=fr", "dark", 390, 800)
    pg.wait_for_selector("sound-recognition-live .card")
    pg.click("button[data-tab=sources]")
    pg.wait_for_selector("sound-recognition-sources li[data-source]")
    pg.click("li[data-source=kitchen] button[data-action=edit]")
    pg.wait_for_selector("sr-schedule-grid .cell")
    ok(pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "form fits a phone without page scroll")
    ok(any("Écoute" in t for t in text(pg, "legend")), "French form")
    pg.screenshot(path=os.path.join(OUT, "sources-phone-fr.png"), full_page=True)
    pg.close()

    for q, msg in (("?fail=unreachable", "cannot be reached"), ("?fail=not_loaded", "is not set up")):
        pg = new(q)
        pg.wait_for_timeout(500)
        ok(any(msg in t for t in text(pg, ".note")), f"error state: {msg}")
        pg.close()
    ok(not errors, "no console errors" + (": " + "; ".join(errors[:3]) if errors else ""))
    b.close()
sys.exit(1 if ok.failed else 0)
