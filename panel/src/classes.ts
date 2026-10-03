// Edits of the class blocks of a configuration: global (`classes`) or per source (`sources[i].classes`).
import type { ByKey } from "./resolve";
import type { CatalogClass, ClassBlock, ClassBlocks, ServiceConfig, SourceCfg } from "./types";

export const clone = <T>(x: T): T => JSON.parse(JSON.stringify(x));

/** Scope: null = all sources, otherwise a source id. Returns the (possibly new) blocks mapping of the scope. */
export function scopeBlocks(cfg: ServiceConfig, sid: string | null, create = false): ClassBlocks | undefined {
  if (sid === null) {
    if (!cfg.classes && create) cfg.classes = {};
    return cfg.classes;
  }
  const src = (cfg.sources ?? []).find((s: SourceCfg) => s.id === sid);
  if (!src) return undefined;
  if (!src.classes && create) src.classes = {};
  return src.classes as ClassBlocks | undefined;
}

const keyFor = (blocks: ClassBlocks, c: CatalogClass, byKey: ByKey): string | undefined =>
  Object.keys(blocks).find((k) => byKey.get(k) === c.mid);

export function getBlock(cfg: ServiceConfig, sid: string | null, c: CatalogClass, byKey: ByKey): ClassBlock {
  const blocks = scopeBlocks(cfg, sid);
  const k = blocks && keyFor(blocks, c, byKey);
  return (k && blocks![k]) || {};
}

/** Replaces the block of a class in a scope; an empty block removes the entry (and an empty mapping removes the mapping). */
export function putBlock(cfg: ServiceConfig, sid: string | null, c: CatalogClass, byKey: ByKey, block: ClassBlock): void {
  const blocks = scopeBlocks(cfg, sid, true)!;
  const k = keyFor(blocks, c, byKey) ?? c.audioset_name;
  const clean = Object.fromEntries(Object.entries(block).filter(([, v]) => v !== undefined)) as ClassBlock;
  if (Object.keys(clean).length) blocks[k] = clean; else delete blocks[k];
  if (!Object.keys(blocks).length) {
    if (sid === null) delete cfg.classes;
    else delete (cfg.sources!.find((s) => s.id === sid) as SourceCfg).classes;
  }
}

/** value: true/false = explicit choice in this scope, null = inherit. */
export function setEnabled(cfg: ServiceConfig, sid: string | null, c: CatalogClass, byKey: ByKey, value: boolean | null): void {
  const b = { ...getBlock(cfg, sid, c, byKey) };
  if (value === null) delete b.enabled; else b.enabled = value;
  putBlock(cfg, sid, c, byKey, b);
}
