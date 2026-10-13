// Port of service/soundrec/settings.py `resolve`; test/crosscheck_resolve.py compares both on random configurations.
import type { CatalogClass, ClassBlock, ClassBlocks, PresetDef, Resolved, RetentionCategory, Schedule, ServiceConfig, SourceCfg } from "./types";

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

// ---------------------------------------------------------------------------------------------------------------- presets (port of settings.fold_source)
export const PRESET_SOUND_FIELDS = ["enabled", "threshold", "min_duration_s", "cooldown_s", "pre_roll_s", "post_roll_s", "clip_retention_days"] as const;
export const PRESET_MAX_VOLUME = -50;                       // a preset never sets a gate above this, so that safety sounds are still heard
const SAFETY_USAGES = new Set(["fire", "security", "baby"]);
export const isSafety = (c: CatalogClass): boolean => c.interest === "monitor" && c.usages.length > 0 && SAFETY_USAGES.has(c.usages[0]);

/** What the folding of presets needs: the presets by id, and the sounds by mid or AudioSet name. */
export interface PresetCtx { presets: Map<string, PresetDef>; byName: Map<string, CatalogClass> }

export const presetCtx = (builtin: PresetDef[] | undefined, user: PresetDef[] | undefined, classes: CatalogClass[]): PresetCtx => {
  const presets = new Map<string, PresetDef>();
  for (const p of builtin ?? []) presets.set(p.id, p);
  for (const p of user ?? []) if (!presets.has(p.id)) presets.set(p.id, p);
  const byName = new Map<string, CatalogClass>();
  for (const c of classes) { byName.set(c.mid, c); byName.set(c.audioset_name, c); }
  return { presets, byName };
};

let lastCtx: { catalog: unknown; user: unknown; ctx: PresetCtx } | null = null;
/** The same, memoised on the catalog and on the user's presets (it is asked for once per sound and source). */
export const presetCtxFor = (catalog: { classes: CatalogClass[]; presets?: PresetDef[] }, cfg: ServiceConfig): PresetCtx => {
  if (lastCtx && lastCtx.catalog === catalog && lastCtx.user === cfg.presets) return lastCtx.ctx;
  const ctx = presetCtx(catalog.presets, cfg.presets, catalog.classes);
  lastCtx = { catalog, user: cfg.presets, ctx };
  return ctx;
};

/** For a safety sound a preset may only make detection easier (or equal), never switch it off. */
const eases = (f: string, v: unknown, g: ClassBlock, c: CatalogClass): boolean => {
  if (f === "enabled") return v === true;
  if (f === "threshold" || f === "min_duration_s" || f === "cooldown_s") {
    const base = (g as Record<string, unknown>)[f] ?? (c.suggestions as unknown as Record<string, unknown>)[f];
    return base == null || (v as number) <= (base as number);
  }
  return true;
};

export interface PresetOrigin { sounds: Record<string, Record<string, string>>; fields: Record<string, string>; ids: string[] }

/** The source as it is in effect: the presets listed on it (in order, the last one wins) fill in what the source does not set itself. */
export function foldSource(cfg: ServiceConfig, src: SourceCfg, ctx: PresetCtx): SourceCfg {
  const ids = (src.presets ?? []).filter((i) => ctx.presets.has(i));
  if (!ids.length) return src;
  const byKey: ByKey = new Map([...ctx.byName.entries()].map(([k, c]) => [k, c.mid]));
  const gcls = indexBlocks(cfg.classes, byKey);
  const explicit = indexBlocks(src.classes as ClassBlocks | undefined, byKey);
  const fromPresets: Record<string, Record<string, unknown>> = {}, soundsOrigin: Record<string, Record<string, string>> = {};
  const fields: Record<string, [unknown, string]> = {};
  for (const pid of ids) {
    const p = ctx.presets.get(pid)!;
    for (const [key, blk] of Object.entries(p.sounds ?? {})) {
      const c = ctx.byName.get(key);
      if (!c) continue;
      for (const [f, v] of Object.entries(blk ?? {})) {
        if (!(PRESET_SOUND_FIELDS as readonly string[]).includes(f) || (isSafety(c) && !eases(f, v, gcls[c.mid] ?? {}, c))) continue;
        (fromPresets[c.mid] ??= {})[f] = v;
        (soundsOrigin[c.mid] ??= {})[f] = pid;
      }
    }
    const sp = p.source as Record<string, unknown> | undefined;
    for (const f of ["min_volume_dbfs", "clips_allowed", "adaptive"]) if (sp && f in sp) fields[f] = [sp[f], pid];
  }
  const e: SourceCfg = JSON.parse(JSON.stringify(src));
  const classes: Record<string, ClassBlock> = {};
  for (const [k, v] of Object.entries((src.classes as Record<string, ClassBlock> | undefined) ?? {})) { const mid = byKey.get(k); if (!mid || !(mid in fromPresets)) classes[k] = v; }
  for (const [mid, blk] of Object.entries(fromPresets)) {
    classes[mid] = { ...blk, ...(explicit[mid] ?? {}) } as ClassBlock;
    for (const f of Object.keys(explicit[mid] ?? {})) delete soundsOrigin[mid][f];
  }
  if (Object.keys(classes).length) e.classes = classes;
  const origin: PresetOrigin = { sounds: Object.fromEntries(Object.entries(soundsOrigin).filter(([, o]) => Object.keys(o).length)), fields: {}, ids };
  if ("min_volume_dbfs" in fields && !("min_volume_dbfs" in src)) { e.min_volume_dbfs = Math.min(fields.min_volume_dbfs[0] as number, PRESET_MAX_VOLUME); origin.fields.min_volume_dbfs = fields.min_volume_dbfs[1]; }
  if ("clips_allowed" in fields && !("allowed" in (src.clips ?? {}))) { e.clips = { ...(src.clips ?? {}), allowed: fields.clips_allowed[0] as boolean }; origin.fields.clips_allowed = fields.clips_allowed[1]; }
  if ("adaptive" in fields && !("enabled" in (src.adaptive ?? {}))) { e.adaptive = { ...(src.adaptive ?? {}), enabled: !!fields.adaptive[0] }; origin.fields.adaptive = fields.adaptive[1]; }
  (e as Record<string, unknown>)._origin = origin;
  return e;
}

export function resolveClass(cfg: ServiceConfig, srcIn: SourceCfg, c: CatalogClass, byKey: ByKey, ctx?: PresetCtx): Resolved {
  const src = ctx ? foldSource(cfg, srcIn, ctx) : srcIn;
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
  else if (retentionCategory(c) in (src.clips?.retention_by_category ?? {})) { r = src.clips!.retention_by_category![retentionCategory(c)]!; rw = "source_category"; }
  else if (retentionCategory(c) in (dflt.clips?.retention_by_category ?? {})) { r = dflt.clips!.retention_by_category![retentionCategory(c)]!; rw = "category"; }
  else if (c.clip_forbidden) { r = 0; rw = "catalog_confidential"; }
  else { r = sug.clip_retention_days; rw = "catalog"; }
  const clips = src.clips ?? {};
  const caps = [clips.max_retention_days, dflt.clips?.max_retention_days].filter((x): x is number => x != null);
  if (caps.length && r > Math.min(...caps)) { r = Math.min(...caps); rw = "cap"; }
  if (!(clips.allowed ?? dflt.clips?.allowed ?? true)) { r = 0; rw = "source_clips_disallowed"; }
  out.clip_retention_days = r; why.clip_retention_days = rw;
  const origin = (src as Record<string, unknown>)._origin as PresetOrigin | undefined;
  if (origin) {                                            // a value that came from a preset says so
    for (const f of Object.keys(origin.sounds[c.mid] ?? {})) if (why[f] === "source_class") why[f] = "preset";
    if ("min_volume_dbfs" in origin.fields && why.min_volume_dbfs === "source") why.min_volume_dbfs = "preset";
  }
  out.provenance = why;
  return out as unknown as Resolved;
}

/** Which clip-retention setting a class follows: its privacy level first, then whether it is a context sound. */
export function retentionCategory(c: { privacy: string; clip_forbidden: boolean; interest: string }): RetentionCategory {
  if (c.privacy === "confidential" || c.clip_forbidden) return "confidential";
  if (c.privacy === "sensitive") return "sensitive";
  return c.interest === "context" ? "context" : "normal";
}
