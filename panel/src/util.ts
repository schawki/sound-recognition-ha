import type { T } from "./i18n";

export function relativeTime(ts: number, language: string, t: T): string {
  const diff = Math.round(ts - Date.now() / 1000);
  if (diff > -10) return t("justNow");
  const rtf = new Intl.RelativeTimeFormat(language, { numeric: "auto" });
  const abs = Math.abs(diff);
  if (abs < 3600) return rtf.format(Math.round(diff / 60), "minute");
  if (abs < 86400) return rtf.format(Math.round(diff / 3600), "hour");
  return rtf.format(Math.round(diff / 86400), "day");
}

/** Size in the language's units ("1.5 MB", "1,5 Mo"). */
export function formatBytes(n: number, language: string, t: T): string {
  const units = t("byteUnits").split(",");
  let i = 0, v = n;
  while (v >= 1000 && i < units.length - 1) { v /= 1000; i++; }
  return `${new Intl.NumberFormat(language, { maximumFractionDigits: i === 0 ? 0 : 1 }).format(v)} ${units[i]}`;
}

const CLIP_REASONS = ["source_class", "class", "catalog", "cap", "source_clips_disallowed", "catalog_clip_forbidden", "expired", "deleted"];

/** Why a detection has no clip, in words: only causes the service actually recorded (unknown or missing: a neutral sentence). */
export function clipNote(t: T, reason: string | null | undefined, source: string, sound: string): string {
  const key = reason && CLIP_REASONS.includes(reason) ? (`clipWhy_${reason}` as const) : "clipWhy_unknown";
  return t(key as Parameters<T>[0], { source, sound });
}
