// Words for what an advice changes, and for what undoing it gives back (the base value of the catalog, or the global setting).
import type { ClassBlock, Patch, ServiceConfig, Suggestions } from "./types";
import type { T } from "./i18n";

type Part = { source_patch?: Record<string, unknown>; class_patch?: Record<string, ClassBlock> };
const isObj = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object" && !Array.isArray(v);

function field(t: T, k: string, v: unknown): string {
  switch (k) {
    case "enabled": return t(v ? "chOn" : "chOff");
    case "min_duration_s": return t("chDuration", { v: String(v) });
    case "threshold": return t("chThreshold", { v: String(v) });
    case "cooldown_s": return t("chCooldown", { v: String(v) });
    case "clip_retention_days": return t("chRetention", { v: String(v) });
    case "min_volume_dbfs": return t("chVolume", { v: String(v) });
    case "schedule": return isObj(v) && v.mode === "continuous" ? t("chScheduleContinuous") : t("chScheduleOwn");
    default: return t("chSetting", { k });
  }
}

/** One line per setting the patch sets: « Beep : switched off ». */
export function describeChanges(patch: Part, names: ReadonlyMap<string, string>, t: T): string[] {
  const lines = Object.entries(patch.class_patch ?? {}).map(([mid, block]) =>
    `${names.get(mid) ?? mid}: ${Object.entries(block).map(([k, v]) => field(t, k, v)).join(", ")}`);
  for (const [k, v] of Object.entries(patch.source_patch ?? {})) {
    if (k === "adaptive" && isObj(v) && v.enabled === true) lines.push(t("chAdaptive"));
    else if (k === "devices" && isObj(v) && v.enabled === true) lines.push(t("chDevices"));
    else lines.push(t("chSetting", { k }));
  }
  return lines;
}

/** What each setting becomes once it is taken off the source: the global setting of the sound if there is one, else the catalog suggestion. */
export function describeBase(patch: Part & { source?: string }, names: ReadonlyMap<string, string>, suggest: ReadonlyMap<string, Suggestions>, cfg: ServiceConfig, t: T): string[] {
  const global = (mid: string, audio?: string): ClassBlock => {
    const c = (cfg.classes ?? {}) as Record<string, ClassBlock>;
    return c[mid] ?? (audio ? c[audio] : undefined) ?? {};
  };
  const lines = Object.entries(patch.class_patch ?? {}).map(([mid, block]) => {
    const g = global(mid), sug = suggest.get(mid);
    const parts = Object.keys(block).map((k) => {
      if (k === "enabled") return field(t, k, g.enabled ?? false);
      if (k === "schedule") return t("chScheduleSource");
      if (k === "min_volume_dbfs") return t("chRemoved");
      const own = (g as Record<string, unknown>)[k];
      const base = own ?? (sug as unknown as Record<string, unknown> | undefined)?.[k];
      return base === undefined ? t("chRemoved") : field(t, k, base);
    });
    return `${names.get(mid) ?? mid}: ${parts.join(", ")}`;
  });
  for (const k of Object.keys(patch.source_patch ?? {})) lines.push(`${t("chSetting", { k })}: ${t("chRemoved")}`);
  return lines;
}
