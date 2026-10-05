// One list of advice for the administrator: the warnings of the catalog and the recommendations drawn from the sources and the home.
// Each item says where it stands: to do (a gesture exists and is not in place), information (nothing to apply), or already applied.
import type { Advice, Patch, Recommendation, ServiceConfig } from "./types";
import { adviceKey, effectiveLevel } from "./advice";

export type Level = Advice["level"];
export interface Item {
  key: string; kind: "advice" | "recommendation"; rule: string; source: string; classes: string[]; level: Level;
  message: string; safety: boolean; apply: Patch | null; applied: boolean; advice: Advice | null;
}
export interface Items { todo: Item[]; info: Item[]; applied: Item[]; hidden: Advice[] }

const ORDER = { danger: 0, warning: 1, info: 2 } as const;
const patched = (p: Patch | null | undefined): Set<string> => new Set(Object.keys(p?.class_patch ?? {}));

/** `warnings` are the raw ones (no override applied): the level shown comes from `cfg`. `done` holds items just applied, not yet confirmed by a reload. */
export function buildItems(warnings: Advice[], recs: Recommendation[], cfg: ServiceConfig, done: ReadonlySet<string> = new Set()): Items {
  const seen = new Set<string>();
  const items: Item[] = [];
  const hidden: Advice[] = [];
  for (const w of warnings) {
    if (seen.has(adviceKey(w))) continue;
    seen.add(adviceKey(w));
    // a warning whose gesture a recommendation already offers for the same sounds is one advice, not two
    const mine = patched(w.apply);
    if (mine.size && recs.some((r) => r.source === w.source && r.apply && [...patched(r.apply)].some((m) => mine.has(m)))) continue;
    const level = effectiveLevel(w, cfg);
    if (level === null) { hidden.push(w); continue; }
    const key = `advice|${adviceKey(w)}`;
    items.push({ key, kind: "advice", rule: w.rule, source: w.source, classes: w.classes, level, message: w.message, safety: !!w.safety,
      apply: w.apply ?? null, applied: !!w.applied || done.has(key), advice: w });
  }
  recs.forEach((r) => {
    const key = `rec|${r.rule}|${r.source}|${[...r.classes].sort().join(",")}`;
    items.push({ key, kind: "recommendation", rule: r.rule, source: r.source, classes: r.classes, level: r.level, message: r.message, safety: false,
      apply: r.apply, applied: !!r.applied || done.has(key), advice: null });
  });
  const byLevel = (a: Item, b: Item) => ORDER[a.level] - ORDER[b.level];
  return {
    todo: items.filter((x) => !x.applied && x.apply).sort(byLevel),
    info: items.filter((x) => !x.applied && !x.apply).sort(byLevel),
    applied: items.filter((x) => x.applied).sort(byLevel),
    hidden,
  };
}

/** What deserves attention now: what can be applied, and the information that is more than a hint. */
export const attention = (i: Items): Item[] => [...i.todo, ...i.info.filter((x) => x.level !== "info")];

/** A request to open a tab of the panel, optionally on one advice (`focus` is the key of the item). */
export interface OpenTab { tab: "advice"; focus?: string }
export const openAdvice = (el: HTMLElement, focus?: string): void => {
  el.dispatchEvent(new CustomEvent<OpenTab>("open-tab", { detail: { tab: "advice", focus }, bubbles: true, composed: true }));
};
