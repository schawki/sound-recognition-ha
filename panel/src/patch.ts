import type { ClassBlock, Patch, ServiceConfig, SourceCfg } from "./types";
import type { PanelApi } from "./api";

/** Applies a recommendation or a threshold change on a copy of the configuration. Class blocks of a source may be keyed by mid or by AudioSet name. */
export function applyPatch(cfg: ServiceConfig, patch: Patch, audioName: (mid: string) => string | undefined = () => undefined): ServiceConfig {
  const next: ServiceConfig = JSON.parse(JSON.stringify(cfg));
  const src = (next.sources ?? []).find((s: SourceCfg) => s.id === patch.source);
  if (!src) return next;
  for (const [k, v] of Object.entries(patch.source_patch ?? {})) {
    const cur = (src as Record<string, unknown>)[k];
    (src as Record<string, unknown>)[k] = v && typeof v === "object" && cur && typeof cur === "object" ? { ...(cur as object), ...(v as object) } : v;
  }
  const classes: Record<string, ClassBlock> = (src.classes as Record<string, ClassBlock> | undefined) ?? {};
  for (const [mid, block] of Object.entries(patch.class_patch ?? {})) {
    const name = audioName(mid);
    const key = Object.keys(classes).find((k) => k === mid || k === name) ?? mid;
    classes[key] = { ...(classes[key] ?? {}), ...block };
  }
  if (Object.keys(classes).length) src.classes = classes;
  return next;
}

/** Applies a patch to the stored configuration: check, then save. Resolves to the error messages (empty = saved). */
export async function applyAndSave(api: PanelApi, patch: Patch, audioName?: (mid: string) => string | undefined): Promise<string[]> {
  const next = applyPatch(await api.config(), patch, audioName);
  const check = await api.validate(next);
  if (check.errors.length) return check.errors;
  await api.save(next);
  return [];
}
