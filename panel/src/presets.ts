import type { Catalog, PresetDef, ServiceConfig } from "./types";
import type { T } from "./i18n";

/** All the presets the user can pick: the catalog's (rooms, then situations), then their own. */
export function allPresets(catalog: Pick<Catalog, "presets"> | null, cfg: ServiceConfig | null): { place: PresetDef[]; situation: PresetDef[]; mine: PresetDef[] } {
  const built = catalog?.presets ?? [];
  return { place: built.filter((p) => p.kind === "place"), situation: built.filter((p) => p.kind !== "place"), mine: cfg?.presets ?? [] };
}

export const findPreset = (id: string, catalog: Pick<Catalog, "presets"> | null, cfg: ServiceConfig | null): PresetDef | undefined => {
  const a = allPresets(catalog, cfg);
  return [...a.place, ...a.situation, ...a.mine].find((p) => p.id === id);
};

/** What a preset does, in a few short lines: the sounds it enables and the values it sets on the source. */
export function presetLines(p: PresetDef, names: (key: string) => string, t: T): string[] {
  const out: string[] = [];
  const sounds = Object.keys(p.sounds ?? {});
  if (sounds.length) out.push(t("presetSounds", { n: sounds.length, names: sounds.map(names).join(", ") }));
  if (p.source?.min_volume_dbfs != null) out.push(t("presetVolume", { v: p.source.min_volume_dbfs }));
  if (p.source?.clips_allowed === false) out.push(t("presetClipsOff"));
  if (p.source?.clips_allowed === true) out.push(t("presetClipsOn"));
  if (p.source?.adaptive === true) out.push(t("presetAdaptive"));
  return out;
}

/** Name of a sound (given by AudioSet name or mid) in the user's language. */
export const soundName = (catalog: Pick<Catalog, "classes"> | null) => {
  const m = new Map<string, string>();
  for (const c of catalog?.classes ?? []) { m.set(c.audioset_name, c.name); m.set(c.mid, c.name); }
  return (key: string): string => m.get(key) ?? key;
};
