import { LitElement, css, html, nothing } from "lit";
import { property, state } from "lit/decorators.js";
import type { PanelApi } from "./api";
import type { T } from "./i18n";
import type { Catalog, ClassBlock, PresetDef, ServiceConfig } from "./types";
import { allPresets, presetLines, soundName } from "./presets";

type Tri = "keep" | "on" | "off";
interface Draft { id: string; isNew: boolean; name: string; why: string; sounds: Record<string, ClassBlock>; volume: string; clips: Tri; adaptive: Tri }

const tri = (v: boolean | undefined): Tri => (v === true ? "on" : v === false ? "off" : "keep");
const slug = (s: string): string => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 40) || "preset";

/** The presets library: the catalog's ready-made ones (read only) and the user's own, which can be created, duplicated, edited and deleted. */
export class PresetsCard extends LitElement {
  @property({ attribute: false }) api!: PanelApi;
  @property({ attribute: false }) t!: T;
  @state() private catalog: Catalog | null = null;
  @state() private cfg: ServiceConfig | null = null;
  @state() private draft: Draft | null = null;
  @state() private error = "";
  @state() private busy = false;
  @state() private confirmDelete = "";

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
  }

  private async load(): Promise<void> {
    const [cat, cfg] = await Promise.allSettled([this.api.catalog(), this.api.config()]);
    if (cat.status === "fulfilled") this.catalog = cat.value;
    if (cfg.status === "fulfilled") this.cfg = cfg.value;
  }

  private usedBy(id: string): string[] {
    return (this.cfg?.sources ?? []).filter((s) => s.presets?.includes(id)).map((s) => s.name || s.id);
  }

  private startNew(from?: PresetDef, duplicate = false): void {
    this.error = "";
    const name = from ? (duplicate ? this.t("presetCopyOf", { name: from.name }) : from.name) : "";
    this.draft = {
      id: from && !duplicate ? from.id : "", isNew: !from || duplicate, name, why: from?.why ?? "",
      sounds: JSON.parse(JSON.stringify(from?.sounds ?? {})), volume: from?.source?.min_volume_dbfs == null ? "" : String(from.source.min_volume_dbfs),
      clips: tri(from?.source?.clips_allowed), adaptive: tri(from?.source?.adaptive),
    };
  }

  private num(v: unknown): number | undefined {
    if (v === "" || v == null) return undefined;
    const n = Number(String(v).replace(",", "."));
    return Number.isFinite(n) ? n : undefined;
  }

  private async save(): Promise<void> {
    const d = this.draft;
    if (!d || !this.cfg) return;
    if (!d.name.trim()) { this.error = this.t("presetNeedName"); return; }
    this.busy = true; this.error = "";
    try {
      const cfg: ServiceConfig = await this.api.config();
      const list = [...(cfg.presets ?? [])];
      let id = d.id;
      if (d.isNew) {
        const taken = new Set([...list.map((p) => p.id), ...(this.catalog?.presets ?? []).map((p) => p.id)]);
        const base = `my_${slug(d.name)}`;
        id = base;
        for (let i = 2; taken.has(id); i++) id = `${base}_${i}`;
      }
      const source: PresetDef["source"] = {};
      const vol = this.num(d.volume);
      if (vol != null) source.min_volume_dbfs = vol;
      if (d.clips !== "keep") source.clips_allowed = d.clips === "on";
      if (d.adaptive !== "keep") source.adaptive = d.adaptive === "on";
      const next: PresetDef = { id, name: d.name.trim(), ...(d.why.trim() ? { why: d.why.trim() } : {}), sounds: d.sounds, source };
      const at = list.findIndex((p) => p.id === id);
      if (at >= 0) list[at] = next; else list.push(next);
      await this.api.save({ ...cfg, presets: list });
      this.draft = null;
      await this.load();
    } catch (err) {
      this.error = (err as { message?: string }).message ?? String(err);
    } finally { this.busy = false; }
  }

  private async removePreset(id: string): Promise<void> {
    this.busy = true; this.error = "";
    try {
      const cfg: ServiceConfig = await this.api.config();
      const sources = (cfg.sources ?? []).map((s) => {
        if (!s.presets?.includes(id)) return s;
        const left = s.presets.filter((x) => x !== id);
        const { presets: _drop, ...rest } = s;
        return left.length ? { ...rest, presets: left } : rest;
      });
      const presets = (cfg.presets ?? []).filter((p) => p.id !== id);
      const next: ServiceConfig = { ...cfg, sources, presets };
      if (!presets.length) delete next.presets;
      await this.api.save(next);
      this.confirmDelete = "";
      await this.load();
    } catch (err) {
      this.error = (err as { message?: string }).message ?? String(err);
    } finally { this.busy = false; }
  }

  private setSound(key: string, field: keyof ClassBlock, v: string): void {
    if (!this.draft) return;
    const sounds = { ...this.draft.sounds };
    const block = { ...(sounds[key] ?? {}) } as Record<string, unknown>;
    const n = this.num(v);
    if (n == null) delete block[field as string]; else block[field as string] = n;
    sounds[key] = block as ClassBlock;
    this.draft = { ...this.draft, sounds };
  }

  private editor() {
    const t = this.t, d = this.draft!;
    const name = soundName(this.catalog);
    const options = (this.catalog?.classes ?? []).filter((c) => !(c.audioset_name in d.sounds)).sort((a, b) => a.name.localeCompare(b.name));
    const triSel = (value: Tri, on: (v: Tri) => void, label: string, field: string) => html`<label class="row">${label}
      <select data-field=${field} @change=${(e: Event) => on((e.target as HTMLSelectElement).value as Tri)}>
        <option value="keep" ?selected=${value === "keep"}>${field === "clips" ? t("presetClipsKeep") : t("presetAdaptiveKeep")}</option>
        <option value="on" ?selected=${value === "on"}>${t("presetOn")}</option><option value="off" ?selected=${value === "off"}>${t("presetOff")}</option></select></label>`;
    return html`<div class="editor" data-preset-editor>
      <label class="row">${t("presetName")} <input type="text" class="wide" name="preset_name" .value=${d.name} @input=${(e: Event) => (this.draft = { ...d, name: (e.target as HTMLInputElement).value })} /></label>
      <label class="row">${t("presetWhy")} <input type="text" class="wide" name="preset_why" .value=${d.why} @input=${(e: Event) => (this.draft = { ...d, why: (e.target as HTMLInputElement).value })} /></label>
      <h4>${t("presetSoundsTitle")}</h4>
      ${Object.keys(d.sounds).map((k) => html`<div class="snd" data-preset-sound=${k}><strong>${name(k)}</strong>
        <label>${t("presetThreshold")} <input type="number" step="0.05" min="0" max="1" data-f="threshold" .value=${d.sounds[k].threshold == null ? "" : String(d.sounds[k].threshold)} @input=${(e: Event) => this.setSound(k, "threshold", (e.target as HTMLInputElement).value)} /></label>
        <label>${t("presetMinDuration")} <input type="number" step="0.5" min="0" data-f="min_duration_s" .value=${d.sounds[k].min_duration_s == null ? "" : String(d.sounds[k].min_duration_s)} @input=${(e: Event) => this.setSound(k, "min_duration_s", (e.target as HTMLInputElement).value)} /></label>
        <label>${t("presetCooldown")} <input type="number" step="1" min="0" data-f="cooldown_s" .value=${d.sounds[k].cooldown_s == null ? "" : String(d.sounds[k].cooldown_s)} @input=${(e: Event) => this.setSound(k, "cooldown_s", (e.target as HTMLInputElement).value)} /></label>
        <button data-action="preset-sound-remove" @click=${() => { const s = { ...d.sounds }; delete s[k]; this.draft = { ...d, sounds: s }; }}>${t("presetRemove")}</button></div>`)}
      <select data-action="preset-sound-add" @change=${(e: Event) => { const el = e.target as HTMLSelectElement; if (el.value) this.draft = { ...d, sounds: { ...d.sounds, [el.value]: { enabled: true } } }; el.value = ""; }}>
        <option value="">${t("presetAddSound")}</option>${options.map((c) => html`<option value=${c.audioset_name}>${c.name}</option>`)}</select>
      <h4>${t("presetSourceTitle")}</h4>
      <label class="row">${t("presetVolumeLabel")} <input type="number" name="preset_volume" min="-90" max="-50" step="1" .value=${d.volume} @input=${(e: Event) => (this.draft = { ...d, volume: (e.target as HTMLInputElement).value })} /></label>
      ${triSel(d.clips, (v) => (this.draft = { ...d, clips: v }), t("presetClipsLabel"), "clips")}
      ${triSel(d.adaptive, (v) => (this.draft = { ...d, adaptive: v }), t("presetAdaptiveLabel"), "adaptive")}
      <p class="dim">${t("presetSafetyNote")}</p>
      ${this.error ? html`<p class="note error" role="alert" data-preset-error>${this.error}</p>` : nothing}
      <div class="buttons"><button class="primary" data-action="preset-save" ?disabled=${this.busy} @click=${() => void this.save()}>${t("presetSave")}</button>
        <button data-action="preset-cancel" @click=${() => { this.draft = null; this.error = ""; }}>${t("presetCancel")}</button></div></div>`;
  }

  private item(p: PresetDef, mine: boolean) {
    const t = this.t, name = soundName(this.catalog);
    const used = this.usedBy(p.id);
    return html`<div class="preset" data-preset=${p.id}><div><strong>${p.name}</strong>${p.why ? html`<br><span class="dim">${p.why}</span>` : nothing}
        <br><span class="dim">${presetLines(p, name, t).join(" · ")}</span>
        ${used.length ? html`<br><span class="dim" data-preset-used>${t("presetUsedBy", { names: used.join(", ") })}</span>` : nothing}</div>
      <div class="buttons">
        <button data-action="preset-duplicate" @click=${() => this.startNew(p, true)}>${t("presetDuplicate")}</button>
        ${mine ? html`<button data-action="preset-edit" @click=${() => this.startNew(p)}>${t("presetEdit")}</button>
          ${this.confirmDelete === p.id ? html`<span class="confirm" role="alertdialog">${t("presetDeleteConfirm")}
            <button class="danger" data-action="preset-delete-yes" ?disabled=${this.busy} @click=${() => void this.removePreset(p.id)}>${t("presetDelete")}</button>
            <button @click=${() => (this.confirmDelete = "")}>${t("presetCancel")}</button></span>`
            : html`<button data-action="preset-delete" @click=${() => (this.confirmDelete = p.id)}>${t("presetDelete")}</button>`}` : nothing}</div></div>`;
  }

  render() {
    const t = this.t, a = allPresets(this.catalog, this.cfg);
    return html`<section class="card" data-section="presets"><h2>${t("presetLibTitle")}</h2><p class="dim">${t("presetLibHelp")}</p>
      ${this.draft ? this.editor() : html`<div class="buttons"><button class="primary" data-action="preset-new" @click=${() => this.startNew()}>${t("presetNew")}</button></div>
        ${a.mine.length ? html`<h3>${t("presetGroupMine")}</h3>${a.mine.map((p) => this.item(p, true))}` : nothing}
        ${this.error ? html`<p class="note error" role="alert">${this.error}</p>` : nothing}
        <details><summary>${t("presetGroupPlace")}</summary>${a.place.map((p) => this.item(p, false))}</details>
        <details><summary>${t("presetGroupSituation")}</summary>${a.situation.map((p) => this.item(p, false))}</details>`}
    </section>`;
  }

  static styles = css`
    .card { border: 1px solid var(--divider-color); border-radius: 12px; padding: 10px 14px; margin-bottom: 14px; background: var(--card-background-color); }
    h2 { font-size: 1.05rem; font-weight: 500; margin: 4px 0 8px; } h3 { font-size: 1rem; font-weight: 500; margin: 14px 0 4px; } h4 { margin: 12px 0 4px; font-weight: 500; }
    .dim { color: var(--secondary-text-color); } p { margin: 8px 0; } summary { cursor: pointer; margin: 10px 0 4px; }
    .preset { display: flex; justify-content: space-between; gap: 10px; flex-wrap: wrap; padding: 6px 0; border-bottom: 1px solid var(--divider-color); }
    .row { display: flex; align-items: center; gap: 8px; margin: 8px 0; flex-wrap: wrap; }
    .snd { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin: 6px 0; }
    .snd strong { min-width: 160px; }
    input, select { font: inherit; padding: 6px 8px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--primary-background-color); color: var(--primary-text-color); }
    input[type=number] { width: 90px; } .wide { width: min(420px, 100%); }
    .buttons { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-top: 6px; }
    button { font: inherit; padding: 6px 14px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); cursor: pointer; }
    .primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: transparent; }
    .danger { background: var(--error-color, #db4437); color: #fff; border-color: transparent; }
    .note.error { color: var(--error-color, #db4437); }
    .confirm { border: 1px solid var(--warning-color, #ffa600); border-radius: 8px; padding: 4px 10px; display: inline-flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  `;
}
if (!customElements.get("sound-recognition-presets")) customElements.define("sound-recognition-presets", PresetsCard);
