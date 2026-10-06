import { LitElement, css, html, nothing } from "lit";
import { property, state } from "lit/decorators.js";
import type { PanelApi } from "./api";
import type { T } from "./i18n";
import type { Catalog, ClipFilter, ClipRow, ClipsPage, Overview, RetentionCategory } from "./types";
import { RETENTION_CATEGORIES, RET_KEYS, retBlock, retForm } from "./retention";
import "./feedback-control";
import { formatBytes, relativeTime } from "./util";

const PAGE = 100;

interface Pending { ids?: string[]; filter?: ClipFilter; count: number; bytes: number; all: boolean; clipless?: boolean }

/** The clips kept: size of each, filters (source, sound, category, period) and deletion one by one, selected, matching the filters, or all. */
export class ClipsView extends LitElement {
  @property({ attribute: false }) api!: PanelApi;
  @property({ attribute: false }) t!: T;
  @property({ attribute: false }) language = "en";
  @state() private rows: ClipRow[] = [];
  @state() private page: ClipsPage | null = null;
  @state() private sources = new Map<string, string>();
  @state() private usages = new Map<string, string>();
  private audio = new Map<string, string>();
  @state() private source = "";
  @state() private mid = "";
  @state() private usage = "";
  @state() private from = "";
  @state() private to = "";
  @state() private verdict: "" | "false" | "good" | "unjudged" = "";
  @state() private clipless = 0;
  @state() private ret: Record<RetentionCategory, string> = retForm(undefined);
  @state() private retMsg = "";
  @state() private retErrors: string[] = [];
  @state() private picked = new Set<string>();
  @state() private pending: Pending | null = null;
  @state() private result = "";
  @state() private busy = false;
  @state() private ready = false;
  @state() private loadError = false;

  connectedCallback(): void {
    super.connectedCallback();
    void this.init();
  }

  private async init(): Promise<void> {
    try {
      const [cat, ov] = await Promise.all([this.api.catalog(), this.api.overview()]);
      this.usages = new Map(Object.entries((cat as Catalog).usages ?? {}));
      this.audio = new Map((cat as Catalog).classes.map((k) => [k.mid, k.audioset_name]));
      this.sources = new Map((ov as Overview).sources.map((s) => [s.id, s.name]));
    } catch { /* the list below reports the connection problem */ }
    try {
      this.ret = retForm((await this.api.config()).defaults?.clips?.retention_by_category);
    } catch { /* the settings block just stays empty */ }
    await this.load(false);
  }

  /** Saves the global retention by kind of sound (defaults.clips.retention_by_category) on a fresh copy of the configuration. */
  private async saveRetention(): Promise<void> {
    this.busy = true;
    this.retMsg = "";
    this.retErrors = [];
    try {
      const cfg = await this.api.config();
      const block = retBlock(this.ret);
      const defaults = { ...(cfg.defaults ?? {}) };
      const clips = { ...(defaults.clips ?? {}) };
      if (Object.keys(block).length) clips.retention_by_category = block; else delete clips.retention_by_category;
      defaults.clips = clips;
      const next = { ...cfg, defaults };
      const check = await this.api.validate(next);
      if (check.errors.length) { this.retErrors = check.errors; return; }
      await this.api.save(next);
      this.retMsg = this.t("retentionSaved");
    } catch (err) {
      this.retErrors = [(err as { message?: string }).message ?? String(err)];
    } finally {
      this.busy = false;
    }
  }

  private retentionCard() {
    const t = this.t;
    return html`<details class="retention" data-retention><summary>${t("retentionTitle")}</summary>
      <p class="dim">${t("retentionHelp")}</p>
      <div class="two">${RETENTION_CATEGORIES.map((k) => html`<label>${t(RET_KEYS[k])}<input name=${`ret_${k}`} type="number" min="0" max="3650" step="1" .value=${this.ret[k]}
        @input=${(e: Event) => { this.ret = { ...this.ret, [k]: (e.target as HTMLInputElement).value }; this.retMsg = ""; }} /></label>`)}</div>
      ${parseInt(this.ret.confidential, 10) > 0 ? html`<p class="note error" data-confidential-warning>${t("clipForbiddenOn")}</p>` : nothing}
      ${this.retErrors.map((e) => html`<p class="note error">${e}</p>`)}
      <div class="buttons"><button class="primary" data-action="save-retention" ?disabled=${this.busy} @click=${() => void this.saveRetention()}>${t("retentionSave")}</button>
        ${this.retMsg ? html`<span class="ok" role="status" data-retention-saved>${this.retMsg}</span>` : nothing}</div></details>`;
  }

  private get filter(): ClipFilter {
    const f: ClipFilter = {};
    if (this.source) f.source = this.source;
    if (this.mid) f.mid = this.mid;
    if (this.usage) f.usage = this.usage;
    if (this.from) f.since = new Date(`${this.from}T00:00:00`).getTime() / 1000;
    if (this.to) f.until = new Date(`${this.to}T23:59:59.999`).getTime() / 1000;
    if (this.verdict) f.feedback = this.verdict;
    return f;
  }

  private get filtered(): boolean {
    return Object.keys(this.filter).length > 0;
  }

  /** Loads the first page, or the next one when `more`. */
  private async load(more: boolean): Promise<void> {
    try {
      const page = await this.api.clips(this.filter, PAGE, more ? this.rows.length : 0);
      this.rows = more ? [...this.rows, ...page.clips] : page.clips;
      this.page = page;
      if (this.mid && !page.sounds.some((s) => s.mid === this.mid)) this.mid = "";
      if (!more) this.picked = new Set();
      if (!more) await this.countClipless();
      this.loadError = false;
    } catch {
      this.loadError = true;
    }
    this.ready = true;
  }

  /** The filters without the verdict one: detections without a clip have no verdict to filter on. */
  private get cliplessFilter(): ClipFilter {
    const { feedback: _ignored, ...rest } = this.filter;
    return rest;
  }

  /** How many detections have no clip and no verdict (they cannot be checked); an older service just has none to offer. */
  private async countClipless(): Promise<void> {
    try {
      this.clipless = (await this.api.deleteClipless(this.cliplessFilter, true)).count;
    } catch {
      this.clipless = 0;
    }
  }

  private async askClipless(): Promise<void> {
    this.result = "";
    this.busy = true;
    try {
      const filter = this.cliplessFilter;
      const r = await this.api.deleteClipless(filter, true);
      this.pending = { filter, count: r.count, bytes: 0, all: false, clipless: true };
    } catch {
      this.loadError = true;
    } finally {
      this.busy = false;
    }
  }

  private change(apply: () => void): void {
    apply();
    this.pending = null;
    this.result = "";
    void this.load(false);
  }

  private size(n: number): string {
    return formatBytes(n, this.language, this.t);
  }

  private pickedBytes(): number {
    return this.rows.filter((r) => this.picked.has(r.id)).reduce((s, r) => s + r.size, 0);
  }

  private toggle(id: string): void {
    const next = new Set(this.picked);
    if (!next.delete(id)) next.add(id);
    this.picked = next;
  }

  private askIds(rows: ClipRow[]): void {
    this.result = "";
    this.pending = { ids: rows.map((r) => r.id), count: rows.length, bytes: rows.reduce((s, r) => s + r.size, 0), all: false };
  }

  /** The confirmation shows what would go: the service counts it first (an empty filter also counts files no detection refers to). */
  private async askFilter(): Promise<void> {
    this.result = "";
    this.busy = true;
    try {
      const filter = this.filter;
      const r = await this.api.deleteClips({ filter }, true);
      this.pending = { filter, count: r.count, bytes: r.bytes, all: Object.keys(filter).length === 0 };
    } catch {
      this.loadError = true;
    } finally {
      this.busy = false;
    }
  }

  private async confirm(): Promise<void> {
    const p = this.pending;
    if (!p) return;
    this.busy = true;
    try {
      if (p.clipless) {
        const r = await this.api.deleteClipless(p.filter ?? {});
        this.result = this.t("cliplessDeleted", { n: r.count });
      } else {
        const r = await this.api.deleteClips(p.ids ? { ids: p.ids } : { filter: p.filter ?? {} });
        this.result = this.t("clipsDeleted", { n: r.count, size: this.size(r.bytes) });
      }
      this.pending = null;
      await this.load(false);
    } catch {
      this.loadError = true;
    } finally {
      this.busy = false;
    }
  }

  private confirmText(p: Pending): string {
    const t = this.t, size = this.size(p.bytes);
    if (p.clipless) return t("confirmClipless", { n: p.count });
    if (p.all) return t("confirmDeleteAll", { n: p.count, size });
    return p.count === 1 && p.ids ? t("confirmDeleteOne", { size }) : t("confirmDelete", { n: p.count, size });
  }

  render() {
    const t = this.t;
    if (this.loadError) return html`<p class="note error">${t("unreachable")}</p>`;
    if (!this.ready || !this.page) return html`<p class="note">${t("loading")}</p>`;
    const pg = this.page, date = new Intl.DateTimeFormat(this.language, { dateStyle: "medium", timeStyle: "short" });
    const allShown = this.rows.length > 0 && this.rows.every((r) => this.picked.has(r.id));
    return html`
      ${this.retentionCard()}
      <div class="filters">
        <select name="source" aria-label=${t("allSources")} @change=${(e: Event) => this.change(() => (this.source = (e.target as HTMLSelectElement).value))}>
          <option value="" ?selected=${this.source === ""}>${t("allSources")}</option>${[...this.sources].map(([id, n]) => html`<option value=${id} ?selected=${this.source === id}>${n}</option>`)}</select>
        <select name="usage" aria-label=${t("allUsages")} @change=${(e: Event) => this.change(() => { this.usage = (e.target as HTMLSelectElement).value; this.mid = ""; })}>
          <option value="" ?selected=${this.usage === ""}>${t("allUsages")}</option>${[...this.usages].map(([id, n]) => html`<option value=${id} ?selected=${this.usage === id}>${n}</option>`)}</select>
        <select name="sound" aria-label=${t("allSounds")} @change=${(e: Event) => this.change(() => (this.mid = (e.target as HTMLSelectElement).value))}>
          <option value="" ?selected=${this.mid === ""}>${t("allSounds")}</option>${pg.sounds.map((s) => html`<option value=${s.mid} ?selected=${this.mid === s.mid}>${s.name} (${s.count})</option>`)}</select>
        <select name="verdict" aria-label=${t("verdictAll")} @change=${(e: Event) => this.change(() => (this.verdict = (e.target as HTMLSelectElement).value as typeof this.verdict))}>
          ${(["", "unjudged", "good", "false"] as const).map((v) => html`<option value=${v} ?selected=${this.verdict === v}>${t(({ "": "verdictAll", unjudged: "verdictUnjudged", good: "verdictGood", false: "verdictFalse" } as const)[v])}</option>`)}</select>
        <label class="date">${t("dateFrom")} <input type="date" name="from" .value=${this.from} @change=${(e: Event) => this.change(() => (this.from = (e.target as HTMLInputElement).value))}></label>
        <label class="date">${t("dateTo")} <input type="date" name="to" .value=${this.to} @change=${(e: Event) => this.change(() => (this.to = (e.target as HTMLInputElement).value))}></label>
        <button data-action="refresh" @click=${() => { this.pending = null; void this.load(false); }}>${t("refresh")}</button>
      </div>
      <p class="dim" data-summary>${t("clipsSummary", { n: pg.total, size: this.size(pg.total_bytes) })}</p>
      <p class="dim" data-disk>${t("clipsDisk", { size: this.size(pg.disk.bytes), free: pg.disk.free_bytes == null ? "?" : this.size(pg.disk.free_bytes) })}</p>
      ${this.result ? html`<p class="ok" role="status" data-result>${this.result}</p>` : nothing}
      ${pg.disk.clips > 0 || pg.total > 0 ? html`<div class="bulk">
        <label class="check"><input type="checkbox" name="selectPage" .checked=${allShown} @change=${(e: Event) => { this.picked = (e.target as HTMLInputElement).checked ? new Set(this.rows.map((r) => r.id)) : new Set(); }}> ${t("selectPage")}</label>
        <button data-action="delete-selected" ?disabled=${this.busy || this.picked.size === 0} @click=${() => this.askIds(this.rows.filter((r) => this.picked.has(r.id)))}>${t("deleteSelected", { n: this.picked.size })}</button>
        ${this.filtered && pg.total > 0 ? html`<button data-action="delete-matching" ?disabled=${this.busy} @click=${() => void this.askFilter()}>${t("deleteMatching", { n: pg.total })}</button>` : nothing}
        ${!this.filtered ? html`<button data-action="delete-all" ?disabled=${this.busy} @click=${() => void this.askFilter()}>${t("deleteEverything", { n: pg.disk.clips })}</button>` : nothing}
        ${this.picked.size ? html`<span class="dim" data-picked>${t("clipsSelected", { n: this.picked.size, size: this.size(this.pickedBytes()) })}</span>` : nothing}
      </div>` : nothing}
      ${this.clipless > 0 && !this.verdict ? html`<div class="bulk"><button data-action="delete-clipless" ?disabled=${this.busy} @click=${() => void this.askClipless()}>${t("deleteClipless", { n: this.clipless })}</button><span class="dim">${t("cliplessHelp")}</span></div>` : nothing}
      ${this.pending ? html`<div class="confirm" role="alertdialog" aria-label=${t("confirmYes")} data-confirm><p>${this.confirmText(this.pending)}</p>
        <div class="buttons"><button class="danger" data-action="confirm" ?disabled=${this.busy} @click=${() => void this.confirm()}>${t("confirmYes")}</button>
          <button data-action="cancel" @click=${() => (this.pending = null)}>${t("cancel")}</button></div></div>` : nothing}
      ${this.rows.length === 0 ? html`<p class="note">${t("noClips")}</p>` : html`<ul class="list">${this.rows.map((e) => html`
        <li data-event=${e.id}>
          <input type="checkbox" name="pick" aria-label=${t("selectClip")} .checked=${this.picked.has(e.id)} @change=${() => this.toggle(e.id)}>
          <div class="what"><strong>${e.name}</strong>
            <span class="dim">${this.sources.get(e.source) ?? e.source} · ${date.format(new Date(e.ts * 1000))} (${relativeTime(e.ts, this.language, t)}) · ${Math.round(e.score * 100)}% · <span data-size>${this.size(e.size)}</span></span>
            ${e.clip_expires ? html`<span class="dim">${t("keptUntil", { d: date.format(new Date(e.clip_expires)) })}</span>` : nothing}</div>
          <audio controls preload="none" src=${e.clip_url} aria-label=${t("play")}></audio>
          <sr-detection-feedback class="fb" .api=${this.api} .t=${t} .ev=${e} .sourceName=${this.sources.get(e.source) ?? e.source} .audioName=${(mid: string) => this.audio.get(mid)}
            @feedback-changed=${(ev: CustomEvent<{ id: string; feedback: string | null }>) => { this.rows = this.rows.map((x) => (x.id === ev.detail.id ? { ...x, feedback: ev.detail.feedback } : x)); }}></sr-detection-feedback>
          <button data-action="delete-one" ?disabled=${this.busy} @click=${() => this.askIds([e])}>${t("deleteClip")}</button>
        </li>`)}</ul>
        ${this.rows.length < pg.total ? html`<div class="buttons"><button data-action="more" @click=${() => void this.load(true)}>${t("clipsMore")} (${this.rows.length}/${pg.total})</button></div>` : nothing}`}`;
  }

  static styles = css`
    :host { display: block; }
    .note { color: var(--secondary-text-color); } .note.error { color: var(--error-color, #db4437); } .ok { color: var(--success-color, #43a047); }
    .dim { color: var(--secondary-text-color); font-size: 0.85rem; } p.dim { margin: 2px 0; }
    .retention { border: 1px solid var(--divider-color); border-radius: 12px; padding: 8px 14px; margin-bottom: 14px; background: var(--card-background-color); }
    .retention summary { cursor: pointer; font-weight: 500; } .retention label { display: flex; flex-direction: column; gap: 4px; font-size: 0.9rem; }
    .retention input { font: inherit; padding: 9px 10px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--primary-background-color); color: var(--primary-text-color); min-width: 0; }
    .two { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin: 10px 0; }
    button.primary { background: var(--primary-color); border-color: transparent; color: var(--text-primary-color, #fff); }
    .filters { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 10px; align-items: center; }
    .date { display: flex; gap: 6px; align-items: center; color: var(--secondary-text-color); font-size: 0.9rem; }
    select, input[type=date] { font: inherit; padding: 9px 10px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--primary-background-color); color: var(--primary-text-color); min-width: 0; }
    button { font: inherit; cursor: pointer; padding: 8px 14px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); }
    button:disabled { opacity: .5; cursor: default; } button.danger { background: var(--error-color, #db4437); border-color: transparent; color: #fff; }
    .bulk { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin: 12px 0; }
    .check { display: flex; gap: 6px; align-items: center; }
    .confirm { border: 1px solid var(--error-color, #db4437); border-radius: 12px; padding: 4px 14px 12px; margin-bottom: 12px; background: var(--card-background-color); }
    .buttons { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 10px; }
    .list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px; }
    .list li { display: grid; grid-template-columns: auto minmax(0, 1fr) minmax(220px, 360px) auto auto; gap: 8px 14px; align-items: center; padding: 10px 14px; background: var(--card-background-color); border: 1px solid var(--divider-color); border-radius: 12px; }
    .what { display: flex; flex-direction: column; min-width: 0; } audio { width: 100%; height: 36px; }
    @media (max-width: 700px) { .list li { grid-template-columns: auto minmax(0, 1fr) auto; } .list li audio { grid-column: 1 / -1; } }
  `;
}
if (!customElements.get("sound-recognition-clips")) customElements.define("sound-recognition-clips", ClipsView);
