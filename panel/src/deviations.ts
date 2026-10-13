import type { Environment, SourceCfg } from "./types";
import type { T } from "./i18n";

/** What a source sets for itself instead of following the defaults, in words; empty when it follows them all. */
export function deviations(s: SourceCfg, t: T, envs: Environment[]): string[] {
  const out: string[] = [];
  if (s.enabled === false) out.push(t("devDisabled"));
  if (s.threshold_offset) out.push(t("devSensitivity", { v: `${s.threshold_offset > 0 ? "+" : ""}${s.threshold_offset}` }));
  if (s.min_volume_dbfs != null) out.push(t("devVolume", { v: s.min_volume_dbfs }));
  if (s.schedule?.mode === "scheduled") out.push(t("devSchedule"));
  if (s.clips?.allowed === false) out.push(t("devClipsOff"));
  else if (s.clips?.max_retention_days != null) out.push(t("devClipsDays", { n: s.clips.max_retention_days }));
  if (s.clips?.retention_by_category && Object.keys(s.clips.retention_by_category).length) out.push(t("devRetention"));
  if (s.environment) out.push(t("devPlace", { name: envs.find((e) => e.id === s.environment)?.name ?? s.environment }));
  if (s.adaptive?.enabled) out.push(t("devAdaptive"));
  if (s.presets?.length) out.push(t("devPresets", { n: s.presets.length }));
  const sounds = Object.keys((s.classes as Record<string, unknown> | undefined) ?? {}).length;
  if (sounds) out.push(t("devSounds", { n: sounds }));
  const advice = Object.keys(s.advice ?? {}).length;
  if (advice) out.push(t("devAdvice", { n: advice }));
  return out;
}
