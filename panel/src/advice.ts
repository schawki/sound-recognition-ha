// Mirrors service/soundrec/advisor.py `_apply_overrides` so the panel can preview a change before it is saved.
import type { Advice, AdviceLevel, AdviceSetting, ServiceConfig } from "./types";

export const entry = (v: AdviceSetting | undefined): { level: AdviceLevel | undefined; confirm: boolean } =>
  typeof v === "string" ? { level: v, confirm: false } : v ? { level: v.level, confirm: !!v.confirm } : { level: undefined, confirm: false };

/** Level shown for an advice under the configuration, or null when it is hidden. `w.level` is the catalog level. */
export function effectiveLevel(w: Advice, cfg: ServiceConfig): Advice["level"] | null {
  const src = (cfg.sources ?? []).find((s) => s.id === w.source);
  const own = src?.advice?.[w.rule];
  const { level, confirm } = entry(own !== undefined ? own : cfg.advice?.[w.rule]);
  if (level === undefined || level === "default") return w.level;
  if (level === "ignore") return w.safety && !confirm ? w.level : null;
  return level;
}

export const adviceKey = (w: Advice): string => `${w.rule}|${w.source}|${[...w.classes].sort().join(",")}`;
