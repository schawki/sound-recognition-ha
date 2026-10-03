// Port of service/soundrec/settings.py `resolve`; test/crosscheck_resolve.py compares both on random configurations.
import type { CatalogClass, ClassBlock, ClassBlocks, Resolved, Schedule, ServiceConfig, SourceCfg } from "./types";

export type ByKey = Map<string, string>; // mid or AudioSet name -> mid

export const buildByKey = (classes: CatalogClass[]): ByKey => {
  const m: ByKey = new Map();
  for (const c of classes) { m.set(c.mid, c.mid); m.set(c.audioset_name, c.mid); }
  return m;
};

/** Block of a scope keyed by mid or AudioSet name -> keyed by mid. */
export function indexBlocks(blocks: ClassBlocks | undefined, byKey: ByKey): Record<string, ClassBlock> {
  const out: Record<string, ClassBlock> = {};
  for (const [k, v] of Object.entries(blocks ?? {})) { const mid = byKey.get(k); if (mid) out[mid] = v ?? {}; }
  return out;
}

const CONTINUOUS: Schedule = { mode: "continuous" };
const NUMERIC = ["min_duration_s", "cooldown_s", "pre_roll_s", "post_roll_s"] as const;

export function resolveClass(cfg: ServiceConfig, src: SourceCfg, c: CatalogClass, byKey: ByKey): Resolved {
  const dflt = cfg.defaults ?? {};
  const g: ClassBlock = indexBlocks(cfg.classes, byKey)[c.mid] ?? {};
  const sc: ClassBlock = indexBlocks(src.classes as ClassBlocks | undefined, byKey)[c.mid] ?? {};
  const sug = c.suggestions;
  const out: Record<string, unknown> = {};
  const why: Record<string, string> = {};

  if (src.enabled === false) { out.enabled = false; why.enabled = "source"; }
  else if ("enabled" in sc) { out.enabled = sc.enabled; why.enabled = "source_class"; }
  else if ("enabled" in g) { out.enabled = g.enabled; why.enabled = "class"; }
  else { out.enabled = false; why.enabled = "default"; }

  let v: number, w: string;
  if ("threshold" in sc) { v = sc.threshold!; w = "source_class"; }
  else {
    const [base, w0] = "threshold" in g ? [g.threshold!, "class"] : [sug.threshold, "catalog"];
    const off = src.threshold_offset ?? 0;
    v = base + off; w = off ? `${w0}+source_offset` : w0;
  }
  out.threshold = Math.round(Math.min(0.99, Math.max(0.05, v)) * 1000) / 1000; why.threshold = w;

  for (const f of NUMERIC) {
    if (f in sc) { out[f] = sc[f]; why[f] = "source_class"; }
    else if (f in g) { out[f] = g[f]; why[f] = "class"; }
    else { out[f] = sug[f]; why[f] = "catalog"; }
  }

  if ("min_volume_dbfs" in sc) { out.min_volume_dbfs = sc.min_volume_dbfs; why.min_volume_dbfs = "source_class"; }
  else {
    const cands: [number, string][] = [];
    const sv = "min_volume_dbfs" in src ? src.min_volume_dbfs : dflt.min_volume_dbfs;
    if (sv != null) cands.push([sv, "min_volume_dbfs" in src ? "source" : "defaults"]);
    if (g.min_volume_dbfs != null) cands.push([g.min_volume_dbfs, "class"]);
    if (cands.length) { const best = cands.reduce((a, b) => (b[0] > a[0] || (b[0] === a[0] && b[1] > a[1]) ? b : a)); out.min_volume_dbfs = best[0]; why.min_volume_dbfs = best[1]; }
    else { out.min_volume_dbfs = null; why.min_volume_dbfs = "none"; }
  }

  out.schedule = CONTINUOUS; why.schedule = "builtin";
  for (const [lvl, d] of [["source_class", sc], ["class", g], ["source", src], ["defaults", dflt]] as const) {
    if ((d as { schedule?: Schedule }).schedule) { out.schedule = (d as { schedule?: Schedule }).schedule; why.schedule = lvl; break; }
  }

  let r: number, rw: string;
  if ("clip_retention_days" in sc) { r = sc.clip_retention_days!; rw = "source_class"; }
  else if ("clip_retention_days" in g) { r = g.clip_retention_days!; rw = "class"; }
  else { r = sug.clip_retention_days; rw = "catalog"; }
  const clips = src.clips ?? {};
  const caps = [clips.max_retention_days, dflt.clips?.max_retention_days].filter((x): x is number => x != null);
  if (caps.length && r > Math.min(...caps)) { r = Math.min(...caps); rw = "cap"; }
  if (!(clips.allowed ?? dflt.clips?.allowed ?? true)) { r = 0; rw = "source_clips_disallowed"; }
  if (c.clip_forbidden) { r = 0; rw = "catalog_clip_forbidden"; }
  out.clip_retention_days = r; why.clip_retention_days = rw;
  out.provenance = why;
  return out as unknown as Resolved;
}
