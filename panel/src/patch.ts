import type { AppliedAdvice, ClassBlock, Patch, ServiceConfig, SourceCfg } from "./types";
import type { PanelApi } from "./api";

type AudioName = (mid: string) => string | undefined;
type Plain = Record<string, unknown>;
const isObj = (v: unknown): v is Plain => !!v && typeof v === "object" && !Array.isArray(v);

/** Identity of an advice on a source: its rule and what it touches. Applying it again replaces the trace instead of adding one. */
export const adviceId = (rule: string, p: { source_patch?: Plain; class_patch?: Record<string, ClassBlock> }): string =>
  `${rule}|${Object.keys(p.class_patch ?? {}).sort().join(",")}|${Object.keys(p.source_patch ?? {}).sort().join(",")}`;

const sourceOf = (cfg: ServiceConfig, id: string): SourceCfg | undefined => (cfg.sources ?? []).find((s: SourceCfg) => s.id === id);
const blockKey = (classes: Record<string, ClassBlock>, mid: string, name?: string): string | undefined => Object.keys(classes).find((k) => k === mid || k === name);

/** Applies a recommendation or a threshold change on a copy of the configuration. Class blocks of a source may be keyed by mid or by AudioSet name.
 *  A patch that answers an advice (`rule`) also leaves a trace on the source, so the advice can be undone. */
export function applyPatch(cfg: ServiceConfig, patch: Patch, audioName: AudioName = () => undefined, now: string = new Date().toISOString()): ServiceConfig {
  const next: ServiceConfig = JSON.parse(JSON.stringify(cfg));
  const src = sourceOf(next, patch.source);
  if (!src) return next;
  for (const [k, v] of Object.entries(patch.source_patch ?? {})) {
    const cur = (src as Plain)[k];
    (src as Plain)[k] = isObj(v) && isObj(cur) ? { ...cur, ...v } : v;
  }
  const classes: Record<string, ClassBlock> = (src.classes as Record<string, ClassBlock> | undefined) ?? {};
  for (const [mid, block] of Object.entries(patch.class_patch ?? {})) {
    const key = blockKey(classes, mid, audioName(mid)) ?? mid;
    classes[key] = { ...(classes[key] ?? {}), ...block };
  }
  if (Object.keys(classes).length) src.classes = classes;
  if (patch.rule) {
    const changes = { ...(patch.source_patch ? { source_patch: patch.source_patch } : {}), ...(patch.class_patch ? { class_patch: patch.class_patch } : {}) };
    const trace: AppliedAdvice = { rule: patch.rule, classes: patch.classes ?? Object.keys(patch.class_patch ?? {}), at: now, level: patch.level ?? "info", message: patch.message ?? "", patch: changes };
    const id = adviceId(patch.rule, changes);
    src.applied_advice = [...(src.applied_advice ?? []).filter((a) => adviceId(a.rule, a.patch) !== id), trace];
  }
  return next;
}

/** True when at least one setting of the patch is still stored on the source. */
export function inPlace(cfg: ServiceConfig, patch: Pick<Patch, "source" | "source_patch" | "class_patch">, audioName: AudioName = () => undefined): boolean {
  const src = sourceOf(cfg, patch.source);
  if (!src) return false;
  const classes = (src.classes as Record<string, ClassBlock> | undefined) ?? {};
  for (const [mid, block] of Object.entries(patch.class_patch ?? {})) {
    const key = blockKey(classes, mid, audioName(mid));
    if (key !== undefined && Object.keys(block).some((f) => f in (classes[key] as object))) return true;
  }
  const has = (cur: unknown, p: Plain): boolean => isObj(cur) && Object.entries(p).some(([k, v]) => (isObj(v) ? has(cur[k], v) : k in cur));
  return has(src, patch.source_patch ?? {});
}

/** Takes the settings of a patch off the source: the catalog (or the global setting) takes over again. Its trace is removed too. */
export function removePatch(cfg: ServiceConfig, patch: Pick<Patch, "source" | "source_patch" | "class_patch"> & { rule?: string }, audioName: AudioName = () => undefined): ServiceConfig {
  const next: ServiceConfig = JSON.parse(JSON.stringify(cfg));
  const src = sourceOf(next, patch.source);
  if (!src) return next;
  const classes = (src.classes as Record<string, ClassBlock> | undefined) ?? {};
  for (const [mid, block] of Object.entries(patch.class_patch ?? {})) {
    const key = blockKey(classes, mid, audioName(mid));
    if (key === undefined) continue;
    for (const f of Object.keys(block)) delete (classes[key] as Plain)[f];
    if (!Object.keys(classes[key]).length) delete classes[key];
  }
  if (Object.keys(classes).length) src.classes = classes; else delete src.classes;
  const strip = (cur: Plain, p: Plain): void => {
    for (const [k, v] of Object.entries(p)) {
      if (isObj(v) && isObj(cur[k])) { strip(cur[k] as Plain, v); if (!Object.keys(cur[k] as Plain).length) delete cur[k]; }
      else delete cur[k];
    }
  };
  strip(src as Plain, patch.source_patch ?? {});
  if (patch.rule) {
    const id = adviceId(patch.rule, patch);
    const left = (src.applied_advice ?? []).filter((a) => adviceId(a.rule, a.patch) !== id);
    if (left.length) src.applied_advice = left; else delete src.applied_advice;
  }
  return next;
}

/** Applies a patch to the stored configuration: check, then save. Resolves to the error messages (empty = saved). */
export async function applyAndSave(api: PanelApi, patch: Patch, audioName?: AudioName): Promise<string[]> {
  return saveChecked(api, applyPatch(await api.config(), patch, audioName));
}

/** Undoes a patch on the stored configuration: check, then save. */
export async function undoAndSave(api: PanelApi, patch: Parameters<typeof removePatch>[1], audioName?: AudioName): Promise<string[]> {
  return saveChecked(api, removePatch(await api.config(), patch, audioName));
}

async function saveChecked(api: PanelApi, next: ServiceConfig): Promise<string[]> {
  const check = await api.validate(next);
  if (check.errors.length) return check.errors;
  await api.save(next);
  return [];
}
