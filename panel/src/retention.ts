import type { RetentionCategory } from "./types";

export const RETENTION_CATEGORIES: RetentionCategory[] = ["normal", "sensitive", "context", "confidential"];
export const RET_KEYS = { normal: "retNormal", sensitive: "retSensitive", context: "retContext", confidential: "retConfidential" } as const;

/** Form values (strings, empty = not set) of a retention-by-category block. */
export const retForm = (b: Partial<Record<RetentionCategory, number>> | undefined): Record<RetentionCategory, string> =>
  Object.fromEntries(RETENTION_CATEGORIES.map((k) => [k, b?.[k] == null ? "" : String(b[k])])) as Record<RetentionCategory, string>;

/** Back from the form: only the categories that have a number. */
export function retBlock(v: Record<RetentionCategory, string>): Partial<Record<RetentionCategory, number>> {
  const out: Partial<Record<RetentionCategory, number>> = {};
  for (const k of RETENTION_CATEGORIES) { const n = parseInt(v[k], 10); if (v[k].trim() !== "" && Number.isFinite(n)) out[k] = n; }
  return out;
}
