import { LitElement, css, html, nothing } from "lit";
import { property, state } from "lit/decorators.js";
import type { PanelApi } from "./api";
import type { T } from "./i18n";
import { cellsToWindows, hoursPerWeek, windowsToCells } from "./schedule";
import type { Advice, ServiceConfig, SourceCfg } from "./types";
import "./schedule-grid";

const TYPES: [string, "typeRtsp" | "typeGo2rtc" | "typeAlsa" | "typeEsphome" | "typeFile"][] = [
  ["rtsp", "typeRtsp"], ["go2rtc", "typeGo2rtc"], ["alsa_rpi", "typeAlsa"], ["esphome", "typeEsphome"], ["file", "typeFile"],
];

interface Form {
  id: string; isNew: boolean; name: string; type: string; url: string; enabled: boolean;
  offset: string; minVolume: string; scheduled: boolean; cells: boolean[];
  clipsAllowed: boolean; clipsMaxDays: string;
}

const slug = (s: string): string => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 40) || "source";

export class SourcesView extends LitElement {
  @property({ attribute: false }) api!: PanelApi;
  @property({ attribute: false }) t!: T;
  @property({ attribute: false }) language = "en";
  @state() private config: ServiceConfig | null = null;
  @state() private form: Form | null = null;
  @state() private errors: string[] = [];
  @state() private notice: { text: string; advice: Advice[] } | null = null;
  @state() private confirming: string | null = null;
  @state() private busy = false;
  @state() private loadError = false;

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
  }

  private async load(): Promise<void> {
    try {
      this.config = await this.api.config();
      this.loadError = false;
    } catch {
      this.loadError = true;
    }
  }

  private get sources(): SourceCfg[] {
    return this.config?.sources ?? [];
  }

  // ------------------------------------------------------------------ form <-> source
  private toForm(s: SourceCfg): Form {
    const sched = s.schedule;
    return {
      id: s.id, isNew: false, name: s.name ?? s.id, type: s.type, url: s.url, enabled: s.enabled !== false,
      offset: s.threshold_offset == null ? "" : String(s.threshold_offset),
      minVolume: s.min_volume_dbfs == null ? "" : String(s.min_volume_dbfs),
      scheduled: sched?.mode === "scheduled", cells: windowsToCells(sched?.windows ?? []),
      clipsAllowed: s.clips?.allowed !== false, clipsMaxDays: s.clips?.max_retention_days == null ? "" : String(s.clips.max_retention_days),
    };
  }

  private blankForm(): Form {
    return { id: "", isNew: true, name: "", type: "rtsp", url: "", enabled: true, offset: "", minVolume: "", scheduled: false, cells: new Array(336).fill(false), clipsAllowed: true, clipsMaxDays: "" };
  }

  /** Applies the form on a copy of the stored source, so fields the form does not know (class settings, advice) are kept. */
  private fromForm(f: Form, existing?: SourceCfg): SourceCfg {
    const s: SourceCfg = { ...(existing ?? {}), id: f.id, name: f.name.trim(), type: f.type, url: f.url.trim() };
    if (f.enabled) delete s.enabled; else s.enabled = false;
    const off = parseFloat(f.offset);
    if (Number.isFinite(off) && off !== 0) s.threshold_offset = off; else delete s.threshold_offset;
    const vol = parseFloat(f.minVolume);
    if (f.minVolume.trim() !== "" && Number.isFinite(vol)) s.min_volume_dbfs = vol; else delete s.min_volume_dbfs;
    const windows = f.scheduled ? cellsToWindows(f.cells) : null;
    if (f.scheduled && windows && windows.length) {
      const untouched = existing?.schedule?.mode === "scheduled" && JSON.stringify(windowsToCells(existing.schedule.windows ?? [])) === JSON.stringify(f.cells);
      s.schedule = untouched ? existing!.schedule! : { mode: "scheduled", windows };
    } else {
      s.schedule = { mode: "continuous" };
    }
    const clips: NonNullable<SourceCfg["clips"]> = {};
    if (!f.clipsAllowed) clips.allowed = false;
    const days = parseInt(f.clipsMaxDays, 10);
    if (f.clipsMaxDays.trim() !== "" && Number.isFinite(days)) clips.max_retention_days = days;
    if (Object.keys(clips).length) s.clips = clips; else delete s.clips;
    return s;
  }

  private uniqueId(name: string): string {
    const taken = new Set(this.sources.map((s) => s.id));
    const base = slug(name);
    let id = base;
    for (let n = 2; taken.has(id); n++) id = `${base}_${n}`;
    return id;
  }

  // ------------------------------------------------------------------ actions
  private async commit(next: SourceCfg[], focusId?: string): Promise<boolean> {
    if (!this.config) return false;
    this.busy = true;
    this.errors = [];
    const candidate: ServiceConfig = { ...this.config, sources: next };
    try {
      const check = await this.api.validate(candidate);
      if (check.errors.length) {
        this.errors = check.errors;
        return false;
      }
      await this.api.save(candidate);
      this.config = candidate;
      this.notice = { text: this.t("saved"), advice: check.warnings.filter((w) => w.source === focusId) };
      return true;
    } catch (err) {
      this.errors = [(err as { message?: string }).message ?? String(err)];
      return false;
    } finally {
      this.busy = false;
    }
  }

  private async submit(e: Event): Promise<void> {
    e.preventDefault();
    const f = this.form;
    if (!f) return;
    if (f.scheduled && !f.cells.some(Boolean)) {
      this.errors = [this.t("pickSomething")];
      return;
    }
    const id = f.isNew ? this.uniqueId(f.name || "source") : f.id;
    const existing = this.sources.find((s) => s.id === f.id);
    const updated = this.fromForm({ ...f, id }, existing);
    const next = f.isNew ? [...this.sources, updated] : this.sources.map((s) => (s.id === f.id ? updated : s));
    if (await this.commit(next, id)) this.form = null;
  }

  private async toggleEnabled(s: SourceCfg): Promise<void> {
    const flipped = { ...s };
    if (s.enabled === false) delete flipped.enabled; else flipped.enabled = false;
    await this.commit(this.sources.map((x) => (x.id === s.id ? flipped : x)), s.id);
  }

  private async removeSource(id: string): Promise<void> {
    this.confirming = null;
    await this.commit(this.sources.filter((s) => s.id !== id));
  }

  private set<K extends keyof Form>(key: K, value: Form[K]): void {
    if (this.form) this.form = { ...this.form, [key]: value };
  }

  // ------------------------------------------------------------------ rendering
  private summary(s: SourceCfg): string {
    const t = this.t;
    const sched = s.schedule?.mode === "scheduled" ? t("scheduleSummaryWeek", { h: hoursPerWeek(windowsToCells(s.schedule.windows ?? [])) }) : t("scheduleSummaryContinuous");
    const clips = s.clips?.allowed === false ? t("clipsOff") : s.clips?.max_retention_days != null ? t("clipsOn", { d: s.clips.max_retention_days }) : t("clipsDefault");
    return `${sched} · ${clips}`;
  }

  render() {
    const t = this.t;
    if (this.loadError) return html`<p class="note error">${t("unreachable")}</p>`;
    if (!this.config) return html`<p class="note">${t("loading")}</p>`;
    return html`
      ${this.notice ? html`<div class="notice"><div>${this.notice.text}</div>
        ${this.notice.advice.length ? html`<strong>${t("adviceAfterSave")}</strong><ul>${this.notice.advice.map((a) => html`<li>${a.message}</li>`)}</ul>` : nothing}
        <button class="link" @click=${() => (this.notice = null)}>${t("dismiss")}</button></div>` : nothing}
      ${this.form ? this.renderForm(this.form) : this.renderList()}
    `;
  }

  private renderList() {
    const t = this.t;
    return html`
      <div class="toolbar"><button class="primary" data-action="add" @click=${() => { this.errors = []; this.form = this.blankForm(); }}>${t("addSource")}</button></div>
      ${this.errors.length ? this.renderErrors() : nothing}
      ${this.sources.length === 0 ? html`<p class="note">${t("noSources")}</p>` : html`<ul class="list">${this.sources.map((s) => html`
        <li data-source=${s.id}>
          <div class="info">
            <strong>${s.name ?? s.id}</strong>
            <span class="dim">${TYPES.find(([k]) => k === s.type) ? t(TYPES.find(([k]) => k === s.type)![1]) : s.type} · ${s.url}</span>
            <span class="dim">${this.summary(s)}</span>
          </div>
          <div class="actions">
            <label class="switch" title=${t("enabled")}><input type="checkbox" .checked=${s.enabled !== false} ?disabled=${this.busy} @change=${() => void this.toggleEnabled(s)} aria-label=${t("enabled")} /></label>
            <button data-action="edit" @click=${() => { this.errors = []; this.form = this.toForm(s); }}>${t("edit")}</button>
            ${this.confirming === s.id
              ? html`<button class="danger" data-action="confirm-remove" @click=${() => void this.removeSource(s.id)}>${t("confirmRemove")}</button><button @click=${() => (this.confirming = null)}>${t("cancel")}</button>`
              : html`<button data-action="remove" @click=${() => (this.confirming = s.id)}>${t("remove")}</button>`}
          </div>
        </li>`)}</ul>`}`;
  }

  private renderErrors() {
    return html`<div class="errors" role="alert"><strong>${this.t("errorsTitle")}</strong><ul>${this.errors.map((e) => html`<li>${e}</li>`)}</ul></div>`;
  }

  private renderForm(f: Form) {
    const t = this.t;
    return html`
      <form @submit=${(e: Event) => void this.submit(e)}>
        <h2>${f.isNew ? t("addSource") : f.name}</h2>
        ${this.errors.length ? this.renderErrors() : nothing}
        <label>${t("name")}<input name="name" required .value=${f.name} @input=${(e: Event) => this.set("name", (e.target as HTMLInputElement).value)} /></label>
        <label>${t("type")}<select name="type" .value=${f.type} @change=${(e: Event) => this.set("type", (e.target as HTMLSelectElement).value)}>
          ${TYPES.map(([k, key]) => html`<option value=${k} ?selected=${f.type === k}>${t(key)}</option>`)}</select></label>
        <label>${t("address")}<input name="url" required .value=${f.url} @input=${(e: Event) => this.set("url", (e.target as HTMLInputElement).value)} /><small>${t("addressHelp")}</small></label>
        <label class="inline"><input type="checkbox" name="enabled" .checked=${f.enabled} @change=${(e: Event) => this.set("enabled", (e.target as HTMLInputElement).checked)} />${t("enabled")}</label>
        <div class="two">
          <label>${t("thresholdOffset")}<input name="offset" type="number" step="0.01" min="-1" max="1" .value=${f.offset} @input=${(e: Event) => this.set("offset", (e.target as HTMLInputElement).value)} /><small>${t("thresholdOffsetHelp")}</small></label>
          <label>${t("minVolume")}<input name="minVolume" type="number" step="1" min="-90" max="0" .value=${f.minVolume} @input=${(e: Event) => this.set("minVolume", (e.target as HTMLInputElement).value)} /><small>${t("minVolumeHelp")}</small></label>
        </div>
        <fieldset>
          <legend>${t("listenMode")}</legend>
          <label class="inline"><input type="radio" name="mode" value="continuous" .checked=${!f.scheduled} @change=${() => this.set("scheduled", false)} />${t("continuous")}</label>
          <label class="inline"><input type="radio" name="mode" value="scheduled" .checked=${f.scheduled} @change=${() => this.set("scheduled", true)} />${t("scheduled")}</label>
          ${f.scheduled ? html`
            <p class="dim">${t("gridHelp")}</p>
            <sr-schedule-grid .cells=${f.cells} .language=${this.language} @cells-changed=${(e: CustomEvent<boolean[]>) => this.set("cells", e.detail)}></sr-schedule-grid>
            <div class="gridbar">
              <span class="dim">${t("hoursPerWeek", { h: hoursPerWeek(f.cells) })}</span>
              <button type="button" @click=${() => this.set("cells", new Array(336).fill(true))}>${t("all")}</button>
              <button type="button" @click=${() => this.set("cells", new Array(336).fill(false))}>${t("none")}</button>
            </div>
            ${f.cells.some(Boolean) ? nothing : html`<p class="note error">${t("pickSomething")}</p>`}` : nothing}
        </fieldset>
        <fieldset>
          <legend>${t("clipsAllowed")}</legend>
          <label class="inline"><input type="checkbox" name="clipsAllowed" .checked=${f.clipsAllowed} @change=${(e: Event) => this.set("clipsAllowed", (e.target as HTMLInputElement).checked)} />${t("clipsAllowed")}</label>
          ${f.clipsAllowed ? html`<label>${t("clipsMaxDays")}<input name="clipsMaxDays" type="number" min="0" max="3650" step="1" .value=${f.clipsMaxDays} @input=${(e: Event) => this.set("clipsMaxDays", (e.target as HTMLInputElement).value)} /></label>` : nothing}
        </fieldset>
        <div class="buttons">
          <button type="button" data-action="cancel" @click=${() => { this.form = null; this.errors = []; }}>${t("cancel")}</button>
          <button type="submit" class="primary" data-action="save" ?disabled=${this.busy}>${this.busy ? t("saving") : t("save")}</button>
        </div>
      </form>`;
  }

  static styles = css`
    :host { display: block; }
    h2 { font-size: 1.05rem; font-weight: 500; margin: 0 0 12px; }
    .note { color: var(--secondary-text-color); } .note.error { color: var(--error-color, #db4437); }
    .dim, small { color: var(--secondary-text-color); font-size: 0.85rem; }
    .toolbar { display: flex; justify-content: flex-end; margin-bottom: 12px; }
    button { font: inherit; cursor: pointer; padding: 8px 14px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); }
    button.primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: transparent; }
    button.danger { background: var(--error-color, #db4437); color: #fff; border-color: transparent; }
    button.link { border: 0; background: none; color: var(--primary-color); padding: 4px 0; }
    button:disabled { opacity: 0.6; cursor: default; }
    .list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 10px; }
    .list li { display: flex; gap: 12px; align-items: center; justify-content: space-between; flex-wrap: wrap; padding: 14px 16px; background: var(--card-background-color); border: 1px solid var(--divider-color); border-radius: 12px; }
    .info { display: flex; flex-direction: column; gap: 2px; min-width: 0; flex: 1 1 260px; }
    .info .dim { overflow-wrap: anywhere; }
    .actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
    .notice { background: color-mix(in srgb, var(--success-color, #43a047) 18%, var(--card-background-color)); border-radius: 10px; padding: 10px 14px; margin-bottom: 12px; }
    .notice ul, .errors ul { margin: 6px 0 6px 18px; padding: 0; }
    .errors { background: color-mix(in srgb, var(--error-color, #db4437) 15%, var(--card-background-color)); border-radius: 10px; padding: 10px 14px; margin-bottom: 12px; }
    form { display: flex; flex-direction: column; gap: 14px; max-width: 760px; background: var(--card-background-color); border: 1px solid var(--divider-color); border-radius: 12px; padding: 16px; }
    label { display: flex; flex-direction: column; gap: 4px; font-size: 0.9rem; }
    label.inline { flex-direction: row; align-items: center; gap: 8px; }
    input:not([type=checkbox]):not([type=radio]), select { font: inherit; padding: 9px 10px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--primary-background-color); color: var(--primary-text-color); min-width: 0; }
    .two { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; }
    fieldset { border: 1px solid var(--divider-color); border-radius: 10px; padding: 10px 14px 14px; display: flex; flex-direction: column; gap: 8px; min-width: 0; }
    legend { padding: 0 6px; font-size: 0.9rem; }
    .gridbar { display: flex; gap: 8px; align-items: center; } .gridbar .dim { flex: 1; }
    .buttons { display: flex; justify-content: flex-end; gap: 10px; }
  `;
}
customElements.define("sound-recognition-sources", SourcesView);
