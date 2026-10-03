"""Compares src/advice.ts effectiveLevel with the service's advisor overrides on random configurations."""
import json, os, random, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "service"))
from soundrec import advisor, catalog as cm, settings as st

CAT = st.Catalog(cm.load_raw())
safety = [c["mid"] for c in CAT.raw["classes"] if st.is_safety(c)]
plain = [c["mid"] for c in CAT.raw["classes"] if not st.is_safety(c)][:20]
rnd = random.Random(5)
LEVELS = ["default", "info", "warning", "danger", "ignore"]


def setting():
    lvl = rnd.choice(LEVELS)
    return {"level": lvl, "confirm": rnd.random() < 0.5} if rnd.random() < 0.4 else lvl


cases = []
for _ in range(500):
    cfg = {"advice": {"r": setting()} if rnd.random() < 0.6 else {}, "sources": [{"id": "s", "advice": {"r": setting()} if rnd.random() < 0.5 else {}}]}
    w = {"rule": "r", "kind": "rule", "level": rnd.choice(["info", "warning", "danger"]), "source": "s", "classes": [rnd.choice(safety + plain)], "message": "m"}
    out = advisor._apply_overrides(cfg, CAT, [dict(w)])
    cases.append({"cfg": cfg, "w": {**w, "safety": any(st.is_safety(CAT.get(m)) for m in w["classes"])}, "expected": out[0]["level"] if out else None})

panel = os.path.join(HERE, "..")
json.dump(cases, open(os.path.join(tempfile.gettempdir(), "advice_cases.json"), "w"))
script = f"""
import {{ build }} from "esbuild"; import {{ readFileSync }} from "node:fs";
await build({{ entryPoints: ["src/advice.ts"], bundle: true, format: "esm", outfile: "{tempfile.gettempdir()}/advice.mjs", logLevel: "silent" }});
const {{ effectiveLevel }} = await import("{tempfile.gettempdir()}/advice.mjs");
const cases = JSON.parse(readFileSync("{tempfile.gettempdir()}/advice_cases.json", "utf8"));
let bad = 0;
for (const k of cases) if (effectiveLevel(k.w, k.cfg) !== k.expected) bad++;
console.log("cases", cases.length, "mismatches", bad); process.exit(bad ? 1 : 0);
"""
open(os.path.join(panel, ".crosscheck_advice.mjs"), "w").write(script)
try:
    sys.exit(subprocess.call(["node", ".crosscheck_advice.mjs"], cwd=panel))
finally:
    os.remove(os.path.join(panel, ".crosscheck_advice.mjs"))
