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
