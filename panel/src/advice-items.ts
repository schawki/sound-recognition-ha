// One list of advice for the administrator: the warnings of the catalog and the recommendations drawn from the sources and the home.
// Each item says where it stands: to do (a gesture exists and is not in place), information (nothing to apply), or already applied.
import type { Advice, Choice, Patch, Recommendation, ServiceConfig } from "./types";
import { adviceKey, effectiveLevel } from "./advice";
import { adviceId, inPlace } from "./patch";

export type Level = Advice["level"];
export interface Item {
  key: string; kind: "advice" | "recommendation" | "trace"; rule: string; source: string; classes: string[]; level: Level;
  message: string; safety: boolean; apply: Patch | null; applied: boolean; advice: Advice | null;
  choices: Choice[];              // advice between close sounds: one button per sound to keep, instead of a single gesture
  changes: Patch | null;          // what the button does (or did): the settings it sets on the source
  undo: Patch | null;             // what undoing takes off the source: only when it is still there
  at: string | null;              // when it was applied with its button, if a trace says so
}
export interface Items { todo: Item[]; info: Item[]; applied: Item[]; hidden: Advice[] }

const ORDER = { danger: 0, warning: 1, info: 2 } as const;
const patched = (p: Patch | null | undefined): Set<string> => new Set(Object.keys(p?.class_patch ?? {}));

/** `warnings` are the raw ones (no override applied): the level shown comes from `cfg`. `done` holds items just applied, not yet confirmed by a reload. */
export function buildItems(warnings: Advice[], recs: Recommendation[], cfg: ServiceConfig, done: ReadonlySet<string> = new Set(),
  audioName: (mid: string) => string | undefined = () => undefined): Items {
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
    if (done.has(key) && w.choices?.length) continue;           // just chosen: its trace shows it, the warning goes away with the reload
    items.push({ key, kind: "advice", rule: w.rule, source: w.source, classes: w.classes, level, message: w.message, safety: !!w.safety,
      apply: w.apply ?? null, applied: !!w.applied || done.has(key), advice: w, choices: w.choices ?? [], changes: w.apply ?? null, undo: null, at: null });
  }
  recs.forEach((r) => {
    const key = `rec|${r.rule}|${r.source}|${[...r.classes].sort().join(",")}`;
    items.push({ key, kind: "recommendation", rule: r.rule, source: r.source, classes: r.classes, level: r.level, message: r.message, safety: false,
      apply: r.apply, applied: !!r.applied || done.has(key), advice: null, choices: [], changes: r.apply, undo: null, at: null });
  });
  // what the button changed: the trace of each source says when, and keeps the advice visible when its cause is gone from the list
  for (const it of items) if (it.applied && it.changes && inPlace(cfg, it.changes, audioName)) it.undo = it.changes;
  for (const s of cfg.sources ?? []) {
    for (const a of s.applied_advice ?? []) {
      const changes: Patch = { source: s.id, ...a.patch };
      if (!inPlace(cfg, changes, audioName)) continue;                       // nothing of it is left on the source: nothing to show or undo
      const id = adviceId(a.rule, a.patch);
      const same = items.find((x) => x.applied && x.source === s.id && x.changes && adviceId(x.rule, x.changes) === id);
      if (same) { same.at = a.at; same.undo = changes; continue; }
      items.push({ key: `trace|${s.id}|${id}`, kind: "trace", rule: a.rule, source: s.id, classes: a.classes, level: a.level, message: a.message, safety: false,
        apply: null, applied: true, advice: null, choices: [], changes, undo: changes, at: a.at });
    }
  }
  const byLevel = (a: Item, b: Item) => ORDER[a.level] - ORDER[b.level];
  return {
    todo: items.filter((x) => !x.applied && (x.apply || x.choices.length)).sort(byLevel),
    info: items.filter((x) => !x.applied && !x.apply && !x.choices.length).sort(byLevel),
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
