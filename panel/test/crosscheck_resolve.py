"""Compares src/resolve.ts with the service's resolve() on random configurations. Usage: python3 test/crosscheck_resolve.py"""
import json, os, random, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "service"))
from soundrec import catalog as cm, settings as st

raw, merged = cm.load_raw(), cm.load_lang("en")
CAT = st.Catalog(raw)
classes = merged["classes"]
rnd = random.Random(11)
FIELDS = {"threshold": lambda: round(rnd.uniform(0.05, 0.95), 2), "min_duration_s": lambda: rnd.choice([0, 0.5, 2, 30]),
          "cooldown_s": lambda: rnd.choice([0, 5, 60]), "pre_roll_s": lambda: rnd.choice([0, 3]), "post_roll_s": lambda: rnd.choice([0, 8]),
          "clip_retention_days": lambda: rnd.choice([0, 1, 7, 90]), "min_volume_dbfs": lambda: rnd.choice([None, -80, -60, -45, -30]),
          "enabled": lambda: rnd.random() < 0.5,
          "schedule": lambda: rnd.choice([{"mode": "continuous"}, {"mode": "scheduled", "windows": [{"days": ["mon"], "from": "08:00", "to": "09:00"}]}])}


def block(sample):
    return {k: f() for k, f in FIELDS.items() if rnd.random() < sample}


def key(c):
    return rnd.choice([c["mid"], c["audioset_name"]])


cases = []
for _ in range(600):
    picks = rnd.sample(classes, 4)
    cfg = {"classes": {key(c): block(0.3) for c in picks if rnd.random() < 0.7}, "sources": []}
    if rnd.random() < 0.5:
        cfg["defaults"] = {k: v for k, v in {"min_volume_dbfs": rnd.choice([-60, -40]), "schedule": rnd.choice([None, {"mode": "continuous"}]),
                                              "clips": rnd.choice([None, {"allowed": True, "max_retention_days": 14}, {"allowed": False}])}.items() if v is not None}
    src = {"id": "s", "type": "rtsp", "url": "x", "classes": {key(c): block(0.3) for c in picks if rnd.random() < 0.7}}
    if rnd.random() < 0.4: src["threshold_offset"] = rnd.choice([-0.2, 0.1, 0.5])
    if rnd.random() < 0.4: src["min_volume_dbfs"] = rnd.choice([-70, -35])
    if rnd.random() < 0.3: src["enabled"] = False
    if rnd.random() < 0.3: src["clips"] = rnd.choice([{"allowed": False}, {"max_retention_days": 3}, {"allowed": True}])
    if rnd.random() < 0.3: src["schedule"] = {"mode": "scheduled", "windows": [{"days": ["tue"], "from": "01:00", "to": "02:00"}]}
    cfg["sources"] = [src]
    c = rnd.choice(picks)
    exp = st.resolve(cfg, CAT, "s", c["mid"])
    cases.append({"cfg": cfg, "mid": c["mid"], "expected": exp})

tmp = tempfile.mkdtemp()
json.dump({"classes": classes, "cases": cases}, open(os.path.join(tmp, "cases.json"), "w"))
script = f"""
import {{ build }} from "esbuild";
import {{ readFileSync }} from "node:fs";
await build({{ entryPoints: ["src/resolve.ts"], bundle: true, format: "esm", outfile: "{tmp}/resolve.mjs", logLevel: "silent" }});
const {{ resolveClass, buildByKey }} = await import("{tmp}/resolve.mjs");
const data = JSON.parse(readFileSync("{tmp}/cases.json", "utf8"));
const byKey = buildByKey(data.classes), byMid = new Map(data.classes.map((c) => [c.mid, c]));
let bad = 0;
for (const k of data.cases) {{
  const got = resolveClass(k.cfg, k.cfg.sources[0], byMid.get(k.mid), byKey);
  if (JSON.stringify(sortKeys(got)) !== JSON.stringify(sortKeys(k.expected))) {{ if (bad++ < 3) console.log("MISMATCH", JSON.stringify(k.cfg), k.mid, "\\n got", JSON.stringify(got), "\\n exp", JSON.stringify(k.expected)); }}
}}
function sortKeys(o) {{ return Array.isArray(o) || o === null || typeof o !== "object" ? o : Object.fromEntries(Object.keys(o).sort().map((x) => [x, sortKeys(o[x])])); }}
console.log("cases", data.cases.length, "mismatches", bad);
process.exit(bad ? 1 : 0);
"""
panel_dir = os.path.join(HERE, "..")
open(os.path.join(panel_dir, ".crosscheck.mjs"), "w").write(script)   # next to node_modules so esbuild resolves
try:
    sys.exit(subprocess.call(["node", ".crosscheck.mjs"], cwd=panel_dir))
finally:
    os.remove(os.path.join(panel_dir, ".crosscheck.mjs"))
