import { LitElement, css, html, nothing } from "lit";
import { property, state } from "lit/decorators.js";
import type { PanelApi } from "./api";
import { clone, getBlock, setEnabled } from "./classes";
import type { Key, T } from "./i18n";
import { buildByKey, indexBlocks, resolveClass, type ByKey } from "./resolve";
import type { Advice, Catalog, CatalogClass, ServiceConfig, SourceCfg } from "./types";
import "./class-detail";

const PAGE = 60;
const INTEREST_ORDER = { monitor: 0, optional: 1, context: 2, ignore: 3 } as const;
const norm = (s: string): string => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");

export class SoundsView extends LitElement {
  @property({ attribute: false }) api!: PanelApi;
  @property({ attribute: false }) t!: T;
  @property({ attribute: false }) language = "en";
  @state() private catalog: Catalog | null = null;
  @state() private saved: ServiceConfig | null = null;
  @state() private draft: ServiceConfig | null = null;
  @state() private scope: string | null = null;
  @state() private query = "";
  @state() private category = "";
  @state() private interest = "";
  @state() private onlyEnabled = false;
  @state() private limit = PAGE;
  @state() private open: string | null = null;
  @state() private errors: string[] = [];
  @state() private notice: { advice: Advice[] } | null = null;
  @state() private busy = false;
  @state() private loadError = false;
  private byKey: ByKey = new Map();

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
  }

  private async load(): Promise<void> {
    try {
      const [cfg, cat] = await Promise.all([this.api.config(), this.api.catalog()]);
      this.catalog = cat;
      this.byKey = buildByKey(cat.classes);
      this.saved = cfg;
      this.draft = clone(cfg);
      this.loadError = false;
    } catch {
      this.loadError = true;
    }
  }

  private get sources(): SourceCfg[] {
    return this.draft?.sources ?? [];
  }

  private get dirty(): boolean {
    return JSON.stringify(this.draft) !== JSON.stringify(this.saved);
  }

  // ------------------------------------------------------------------ state of a class
  private globalOn(c: CatalogClass): boolean {
    return indexBlocks(this.draft!.classes, this.byKey)[c.mid]?.enabled === true;
  }

  /** Effective state of a class on a source (the source's own enabled flag is ignored: it is shown separately). */
  private sourceOn(c: CatalogClass, s: SourceCfg): boolean {
    return resolveClass(this.draft!, { ...s, enabled: true }, c, this.byKey).enabled;
  }

  private isOn(c: CatalogClass): boolean {
    if (this.scope === null) return this.globalOn(c) || this.sources.some((s) => this.sourceOn(c, s));
    const s = this.sources.find((x) => x.id === this.scope);
    return s ? this.sourceOn(c, s) : false;
  }

  private toggleGlobal(c: CatalogClass, on: boolean): void {
    const d = clone(this.draft!);
    setEnabled(d, null, c, this.byKey, on ? true : null);
    this.draft = d;
  }

  private toggleSource(c: CatalogClass, sid: string, on: boolean): void {
    const d = clone(this.draft!);
    const inheritedOn = indexBlocks(d.classes, this.byKey)[c.mid]?.enabled === true;
    setEnabled(d, sid, c, this.byKey, on === inheritedOn ? null : on);
    this.draft = d;
  }

  private enableRecommended(): void {
    const d = clone(this.draft!);
    for (const c of this.catalog!.classes.filter((x) => x.interest === "monitor")) {
      if (this.scope === null) setEnabled(d, null, c, this.byKey, true);
      else setEnabled(d, this.scope, c, this.byKey, indexBlocks(d.classes, this.byKey)[c.mid]?.enabled === true ? null : true);
    }
    this.draft = d;
  }

  // ------------------------------------------------------------------ save
  private async save(): Promise<void> {
    if (!this.draft) return;
    this.busy = true;
    this.errors = [];
    try {
      const check = await this.api.validate(this.draft);
      if (check.errors.length) { this.errors = check.errors; return; }
      await this.api.save(this.draft);
      this.saved = clone(this.draft);
      this.notice = { advice: check.warnings.filter((w) => w.level !== "info" && (this.scope === null || w.source === this.scope)) };
    } catch (err) {
      this.errors = [(err as { message?: string }).message ?? String(err)];
    } finally {
      this.busy = false;
    }
  }

  // ------------------------------------------------------------------ rendering
  private filtered(): CatalogClass[] {
    const q = norm(this.query.trim());
    const list = this.catalog!.classes.filter((c) =>
      !this.inhibitors().has(c.mid) &&
      (!this.category || c.category === this.category) && (!this.interest || c.interest === this.interest) &&
      (!q || norm(c.name).includes(q) || norm(c.audioset_name).includes(q) || norm(c.note_text ?? "").includes(q)) &&
      (!this.onlyEnabled || this.isOn(c)));
    return list.sort((a, b) => INTEREST_ORDER[a.interest] - INTEREST_ORDER[b.interest] || a.name.localeCompare(b.name, this.language));
  }

  /** The sounds that raise the thresholds of look-alike sounds while they are heard (television, radio, music…). */
  private inhibitors(): Set<string> {
    return new Set(this.catalog!.classes.flatMap((c) => c.inhibiting_contexts ?? []));
  }

  private contextClasses(): CatalogClass[] {
    const q = norm(this.query.trim());
    const inh = this.inhibitors();
    return this.catalog!.classes.filter((c) => inh.has(c.mid) && (!q || norm(c.name).includes(q) || norm(c.audioset_name).includes(q)) && (!this.onlyEnabled || this.isOn(c)))
      .sort((a, b) => a.name.localeCompare(b.name, this.language));
  }

  /** Context sounds gathered in one place, with what fits the kind of place of the chosen source. */
  private renderContext() {
    const t = this.t;
    const list = this.contextClasses();
    if (!list.length) return nothing;
    const src = this.scope === null ? undefined : this.sources.find((x) => x.id === this.scope);
    const env = this.catalog!.environments?.find((e) => e.id === src?.environment);
    const wanted = env ? this.catalog!.classes.filter((c) => env.contexts.includes(c.mid)) : [];
    const missing = src ? wanted.filter((c) => !this.sourceOn(c, src)) : [];
    return html`<section class="ctx" data-context-group>
      <h3>${t("contextTitle")}</h3>
      <p class="dim">${t("contextHelp")}</p>
      ${env && wanted.length ? html`<p class="rec" data-context-rec>${t("contextRecommended", { p: env.name, c: wanted.map((c) => c.name).join(", ") })}
        ${missing.length ? html`<button data-action="enable-contexts" @click=${() => missing.forEach((c) => this.toggleSource(c, src!.id, true))}>${t("contextEnable")}</button>` : nothing}</p>` : nothing}
      <ul class="list">${list.map((c) => this.row(c, true))}</ul>
    </section>`;
  }

  render() {
    const t = this.t;
    if (this.loadError) return html`<p class="note error">${t("unreachable")}</p>`;
    if (!this.catalog || !this.draft) return html`<p class="note">${t("loading")}</p>`;
    const cls = this.open ? this.catalog.classes.find((c) => c.mid === this.open) : undefined;
    return html`
      ${this.notice ? html`<div class="notice">${t("saved")}
        ${this.notice.advice.length ? html`<ul>${this.notice.advice.slice(0, 8).map((a) => html`<li>${a.message}</li>`)}</ul>` : nothing}
        <button class="link" @click=${() => (this.notice = null)}>${t("dismiss")}</button></div>` : nothing}
      ${this.errors.length ? html`<div class="errors" role="alert"><strong>${t("errorsTitle")}</strong><ul>${this.errors.map((e) => html`<li>${e}</li>`)}</ul></div>` : nothing}
      ${cls
        ? html`<sr-class-detail .api=${this.api} .t=${t} .language=${this.language} .cls=${cls} .catalog=${this.catalog} .cfg=${this.draft} .byKey=${this.byKey} .scope=${this.scope}
            @close=${() => (this.open = null)} @apply=${(e: CustomEvent<ServiceConfig>) => { this.draft = e.detail; this.open = null; }}></sr-class-detail>`
        : this.renderList()}
      ${this.dirty ? html`<div class="savebar"><span>${t("unsaved")}</span>
        <button @click=${() => { this.draft = clone(this.saved!); this.errors = []; }}>${t("discard")}</button>
        <button class="primary" data-action="save" ?disabled=${this.busy} @click=${() => void this.save()}>${this.busy ? t("saving") : t("saveChanges")}</button></div>` : nothing}`;
  }

  private renderList() {
    const t = this.t;
    const cat = this.catalog!;
    const all = this.filtered();
    const shown = all.slice(0, this.limit);
    return html`
      <div class="filters">
        <label>${t("scope")}
          <select name="scope" @change=${(e: Event) => { this.scope = (e.target as HTMLSelectElement).value || null; this.limit = PAGE; }}>
            <option value="" ?selected=${this.scope === null}>${t("scopeAll")}</option>
            ${this.sources.map((s) => html`<option value=${s.id} ?selected=${this.scope === s.id}>${s.name ?? s.id}</option>`)}</select></label>
        <input name="search" type="search" placeholder=${t("search")} aria-label=${t("search")} .value=${this.query} @input=${(e: Event) => { this.query = (e.target as HTMLInputElement).value; this.limit = PAGE; }} />
        <select name="category" aria-label=${t("allCategories")} @change=${(e: Event) => { this.category = (e.target as HTMLSelectElement).value; this.limit = PAGE; }}>
          <option value="">${t("allCategories")}</option>${Object.entries(cat.categories).map(([k, v]) => html`<option value=${k}>${v}</option>`)}</select>
        <select name="interest" aria-label=${t("allInterests")} @change=${(e: Event) => { this.interest = (e.target as HTMLSelectElement).value; this.limit = PAGE; }}>
          <option value="">${t("allInterests")}</option>${(["monitor", "optional", "context", "ignore"] as const).map((k) => html`<option value=${k}>${t(`interest_${k}` as Key)}</option>`)}</select>
        <label class="inline"><input type="checkbox" name="onlyEnabled" .checked=${this.onlyEnabled} @change=${(e: Event) => { this.onlyEnabled = (e.target as HTMLInputElement).checked; this.limit = PAGE; }} />${t("onlyEnabled")}</label>
        <button data-action="recommended" @click=${() => this.enableRecommended()}>${t("enableRecommended")}</button>
      </div>
      ${this.renderContext()}
      <p class="dim">${t("soundsCount", { n: all.length })}</p>
      ${shown.length === 0 ? html`<p class="note">${t("noMatch")}</p>` : html`<ul class="list">${shown.map((c) => this.row(c))}</ul>`}
      ${all.length > shown.length ? html`<div class="more"><button data-action="more" @click=${() => (this.limit += PAGE)}>${t("showMore")}</button></div>` : nothing}`;
  }

  private row(c: CatalogClass, inCtx = false) {
    const t = this.t;
    const on = this.isOn(c);
    const inheritedHint = this.scope !== null && !("enabled" in getBlock(this.draft!, this.scope, c, this.byKey)) && on;
    return html`
      <li data-mid=${c.mid} class="${on ? "on" : ""}${inCtx ? " inctx" : ""}">
        <label class="check">
          ${this.scope === null
            ? html`<input type="checkbox" name="global" .checked=${this.globalOn(c)} aria-label=${c.name} @change=${(e: Event) => this.toggleGlobal(c, (e.target as HTMLInputElement).checked)} />`
            : html`<input type="checkbox" name="scoped" .checked=${on} aria-label=${c.name} @change=${(e: Event) => this.toggleSource(c, this.scope!, (e.target as HTMLInputElement).checked)} />`}
          <span class="name"><strong>${c.name}</strong>
            <span class="dim">${this.catalog!.categories[c.category] ?? c.category} · ${t(`interest_${c.interest}` as Key)}${c.clip_forbidden ? " · 🔒" : ""}${inheritedHint ? ` · ${t("inherited")}` : ""}</span></span>
        </label>
        ${this.scope === null && this.sources.length ? html`<span class="chips">${this.sources.map((s) => {
          const sOn = this.sourceOn(c, s);
          return html`<button class="chip ${sOn ? "on" : ""}" data-source=${s.id} aria-pressed=${sOn} title=${s.name ?? s.id} @click=${() => this.toggleSource(c, s.id, !sOn)}>${s.name ?? s.id}</button>`;
        })}</span>` : nothing}
        <button data-action="settings" @click=${() => (this.open = c.mid)}>${t("settings")}</button>
      </li>`;
  }

  static styles = css`
    :host { display: block; }
    .note { color: var(--secondary-text-color); } .note.error { color: var(--error-color, #db4437); }
    .dim { color: var(--secondary-text-color); font-size: 0.85rem; }
    .filters { display: flex; flex-wrap: wrap; gap: 10px; align-items: end; margin-bottom: 8px; }
    .filters label { display: flex; flex-direction: column; gap: 4px; font-size: 0.85rem; } .filters label.inline { flex-direction: row; align-items: center; gap: 6px; }
    input[type=search], select { font: inherit; padding: 9px 10px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--primary-background-color); color: var(--primary-text-color); min-width: 0; }
    input[type=search] { flex: 1 1 200px; }
    button { font: inherit; cursor: pointer; padding: 8px 14px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); }
    button.primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: transparent; } button.link { border: 0; background: none; color: var(--primary-color); padding: 4px 0; }
    button:disabled { opacity: 0.6; cursor: default; }
    .list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 6px; }
    .list li { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; padding: 8px 12px; background: var(--card-background-color); border: 1px solid var(--divider-color); border-radius: 10px; }
    .list li.on { border-color: var(--primary-color); }
    .check { display: flex; gap: 10px; align-items: center; flex: 1 1 240px; min-width: 0; cursor: pointer; }
    .name { display: flex; flex-direction: column; min-width: 0; }
    .chips { display: flex; gap: 4px; flex-wrap: wrap; }
    .chip { padding: 3px 10px; border-radius: 999px; font-size: 0.8rem; background: var(--secondary-background-color); color: var(--secondary-text-color); }
    .chip.on { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: transparent; }
    .ctx { background: color-mix(in srgb, var(--primary-color) 8%, var(--card-background-color)); border: 1px solid var(--divider-color); border-radius: 12px; padding: 4px 14px 14px; margin: 8px 0 14px; }
    .ctx h3 { margin: 10px 0 4px; font-size: 1rem; font-weight: 500; } .ctx .rec { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin: 6px 0; }
    .more { display: flex; justify-content: center; margin: 14px 0; }
    .notice { background: color-mix(in srgb, var(--success-color, #43a047) 18%, var(--card-background-color)); border-radius: 10px; padding: 10px 14px; margin-bottom: 12px; }
    .errors { background: color-mix(in srgb, var(--error-color, #db4437) 15%, var(--card-background-color)); border-radius: 10px; padding: 10px 14px; margin-bottom: 12px; }
    .notice ul, .errors ul { margin: 6px 0 6px 18px; padding: 0; }
    .savebar { position: sticky; bottom: 0; z-index: 5; margin: 16px -16px -16px; display: flex; gap: 10px; align-items: center; justify-content: flex-end; padding: 12px 16px; background: var(--card-background-color); border-top: 1px solid var(--divider-color); box-shadow: 0 -2px 8px rgba(0,0,0,.12); }
    .savebar span { flex: 1; }
  `;
}
customElements.define("sound-recognition-sounds", SoundsView);
