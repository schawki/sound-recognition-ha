import { LitElement, css, html, nothing } from "lit";
import { property, state } from "lit/decorators.js";
import type { PanelApi } from "./api";
import type { T } from "./i18n";
import type { MoveInfo, StorageInfo } from "./types";
import { formatBytes } from "./util";

const GUIDE = "https://github.com/schawki/sound-recognition-ha/blob/main/docs/storage";

/** Where the clips are, what they take and how fast they grow, the two limits the administrator may set, and the change of token. */
export class StorageCard extends LitElement {
  @property({ attribute: false }) api!: PanelApi;
  @property({ attribute: false }) t!: T;
  @property({ attribute: false }) language = "en";
  /** Shown in the Clips tab: figures only, with a link to the Settings tab where the limits are set. */
  @property({ type: Boolean }) readonly = false;
  @state() private info: StorageInfo | null = null;
  @state() private stopOn = false;
  @state() private stopGb = "";
  @state() private delOn = false;
  @state() private delGb = "";
  @state() private retentionDays = 30;
  @state() private errors: string[] = [];
  @state() private saved = false;
  @state() private busy = false;
  @state() private failed = false;
  @state() private moveTo = "";
  @state() private moveConfirm = false;
  @state() private moveErrors: string[] = [];
  @state() private oldConfirm = "";
  @state() private oldError = "";
  private poll = 0;

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    window.clearInterval(this.poll);
  }

  /** While a move is requested or running, the figures are read again every few seconds (the service restarts at the end: a failed read is ignored). */
  private watchMove(): void {
    const mv = this.info?.move;
    const going = mv && (["requested", "running"].includes(mv.state) || ["requested", "running"].includes(mv.clean?.state ?? "idle"));
    if (going && !this.poll) {
      this.poll = window.setInterval(() => void this.api.storage().then((i) => { this.info = i; this.watchMove(); }, () => undefined), 3000);
    } else if (!going && this.poll) {
      window.clearInterval(this.poll);
      this.poll = 0;
      void this.load();
    }
  }

  private async startMove(): Promise<void> {
    this.busy = true; this.moveErrors = [];
    try {
      const move = await this.api.storageMove(this.moveTo.trim());
      this.moveConfirm = false;
      if (this.info) this.info = { ...this.info, move };
      this.watchMove();
    } catch (err) {
      const e = err as { code?: string; message?: string };
      this.moveConfirm = false;
      this.moveErrors = e.code === "invalid_path"
        ? (e.message ?? "").split(",").map((c) => this.reason(c))
        : [this.t("moveErr_other", { message: e.message ?? String(err) })];
    } finally { this.busy = false; }
  }

  private async deleteOld(path: string): Promise<void> {
    this.busy = true; this.oldError = "";
    try {
      const move = await this.api.storageOldDelete(path);
      this.oldConfirm = "";
      if (this.info) this.info = { ...this.info, move: { ...(this.info.move as MoveInfo), ...move, old: this.info.move?.old } };
      this.watchMove();
    } catch (err) {
      this.oldConfirm = "";
      this.oldError = this.t("oldFailed", { message: (err as { message?: string }).message ?? String(err) });
    } finally { this.busy = false; }
  }

  /** The old folders kept after a move: what is left in them, a button to delete their clips, and for what the button cannot do, what to do by hand. */
  private oldSection(i: StorageInfo) {
    const t = this.t, m = i.move;
    const olds = m?.old ?? [], clean = m?.clean;
    if (!olds.length) return nothing;
    const busy = clean && ["requested", "running"].includes(clean.state);
    return html`<h3>${t("oldTitle")}</h3><p class="dim">${t("oldHelp")}</p>
      ${olds.map((o) => {
        const hand = o.notes.includes("not_writable") || o.notes.includes("no_helper");
        const cmd = `rm -r ${o.path}`;
        const mine = clean && clean.path === o.path;
        return html`<div class="old" data-old=${o.path}><div><strong>${o.path}</strong><br><span class="dim">${o.clips ? t("oldContent", { n: o.clips, size: this.size(o.bytes) }) : t("oldEmpty")}</span>
          ${o.notes.includes("mount_point") ? html`<p class="dim" data-old-note="mount_point">${t("oldNote_mount_point")}</p>` : nothing}
          ${o.notes.includes("other_files") ? html`<p class="dim" data-old-note="other_files">${t("oldNote_other_files", { n: o.other })}</p>` : nothing}
          ${o.notes.includes("not_writable") ? html`<p class="note error" data-old-note="not_writable">${t("oldNote_not_writable", { command: cmd })}</p>` : nothing}
          ${o.notes.includes("no_helper") && !o.notes.includes("not_writable") ? html`<p class="note error" data-old-note="no_helper">${t("oldNote_no_helper", { command: cmd })}</p>` : nothing}
          ${!o.clips && !o.notes.length ? html`<p class="dim" data-old-note="leftover">${t("oldNote_leftover", { command: cmd })}</p>` : nothing}
          ${mine && busy ? html`<p role="status" data-old-progress>${clean!.state === "requested" ? t("oldRequested") : t("oldRunning")}</p>` : nothing}
          ${mine && clean!.state === "failed" ? html`<p class="note error" data-old-failed>${t("oldFailed", { message: clean!.message })}</p>` : nothing}
          ${mine && clean!.state === "done" ? html`<p class="ok" data-old-done>${clean!.message}</p>` : nothing}</div>
          ${hand || !o.clips || busy ? nothing : this.oldConfirm === o.path
            ? html`<div class="confirm" role="alertdialog" data-old-confirm><p>${t("oldConfirm", { n: o.clips, size: this.size(o.bytes), path: o.path, now: i.clips })}</p>
                <div class="buttons"><button class="danger" data-action="old-yes" ?disabled=${this.busy} @click=${() => void this.deleteOld(o.path)}>${t("oldYes")}</button>
                  <button data-action="old-cancel" @click=${() => (this.oldConfirm = "")}>${t("cancel")}</button></div></div>`
            : html`<button data-action="old-delete" @click=${() => { this.oldConfirm = o.path; this.oldError = ""; }}>${t("oldDelete")}</button>`}</div>`;
      })}
      ${this.oldError ? html`<p class="note error" role="alert" data-old-error>${this.oldError}</p>` : nothing}`;
  }

  private reason(code: string): string {
    const key = `moveErr_${code}` as Parameters<T>[0];
    const known = ["not_absolute", "bad_characters", "not_found", "not_directory", "symlink", "same_folder", "nested", "outside_roots", "not_empty", "not_writable", "not_enough_space"];
    return known.includes(code) ? this.t(key, { roots: (this.info?.move?.roots ?? []).join(", ") }) : this.t("moveErr_other", { message: code });
  }

  private moveSection(i: StorageInfo) {
    const t = this.t, m = i.move, lang = this.language.startsWith("fr") ? "fr" : "en";
    const guide = html`<a href=${`${GUIDE}.${lang}.md#moving-the-clips`} target="_blank" rel="noreferrer noopener">${t("storageGuide")}</a>`;
    if (!m) return html`<h3>${t("moveTitle")}</h3><p class="dim" data-move-update>${t("moveNeedsUpdate")}</p>`;
    if (!m.capable) return html`<h3>${t("moveTitle")}</h3><p class="dim" data-move-disabled>${t("moveNotEnabled")} ${guide}</p>${this.oldSection(i)}`;
    const going = m.state === "requested" || m.state === "running";
    return html`<h3>${t("moveTitle")}</h3>
      <p class="dim">${t("moveHelp", { roots: m.roots.join(", ") })} ${guide}</p>
      ${going ? html`<p role="status" data-move-progress>${m.state === "requested" ? t("moveRequested") : m.message}</p>
          ${m.stalled ? html`<p class="note error" data-move-stalled>${t("moveStalled")}</p>` : nothing}`
        : html`${m.state === "done" ? html`<p class="ok" data-move-done>${t("moveDone", { message: m.message })}</p>` : nothing}
          ${m.state === "failed" ? html`<p class="note error" data-move-failed>${t("moveFailed", { message: m.message })}</p>` : nothing}
          <label class="row">${t("moveFolder")} <input type="text" name="move_to" class="wide" placeholder="/mnt/nas/clips" .value=${this.moveTo}
            @input=${(e: Event) => { this.moveTo = (e.target as HTMLInputElement).value; this.moveConfirm = false; this.moveErrors = []; }} /></label>
          ${this.moveErrors.map((e) => html`<p class="note error" role="alert" data-move-error>${e}</p>`)}
          ${this.moveConfirm ? html`<div class="confirm" role="alertdialog" data-move-confirm><p>${t("moveConfirm", { size: this.size(i.bytes), path: this.moveTo.trim() })}</p>
              <div class="buttons"><button class="primary" data-action="move-yes" ?disabled=${this.busy} @click=${() => void this.startMove()}>${t("moveYes")}</button>
                <button data-action="move-cancel" @click=${() => (this.moveConfirm = false)}>${t("cancel")}</button></div></div>`
            : html`<div class="buttons"><button data-action="move-start" ?disabled=${this.busy || !this.moveTo.trim()} @click=${() => { this.moveConfirm = true; this.moveErrors = []; }}>${t("moveButton")}</button></div>`}`}
      ${this.oldSection(i)}`;
  }

  private async load(): Promise<void> {
    try {
      const [info, cfg] = await Promise.all([this.api.storage(), this.api.config()]);
      this.info = info;
      this.stopOn = info.min_free_gb != null; this.stopGb = info.min_free_gb != null ? String(info.min_free_gb) : "";
      this.delOn = info.max_gb != null; this.delGb = info.max_gb != null ? String(info.max_gb) : "";
      this.retentionDays = Number((cfg.defaults?.clips as { max_retention_days?: number } | undefined)?.max_retention_days ?? 30);
      this.watchMove();
    } catch { this.failed = true; }
  }

  private size = (n: number | null | undefined): string => (n == null ? "?" : formatBytes(n, this.language, this.t));

  private async save(): Promise<void> {
    this.busy = true; this.errors = []; this.saved = false;
    try {
      const cfg = await this.api.config();
      const num = (on: boolean, v: string) => (on && v.trim() !== "" ? Number(v.replace(",", ".")) : null);
      cfg.storage = { ...(cfg.storage as Record<string, unknown> | undefined), clips_min_free_gb: num(this.stopOn, this.stopGb), clips_max_gb: num(this.delOn, this.delGb) };
      await this.api.save(cfg);
      this.saved = true;
      await this.load();
    } catch (err) {
      this.errors = [(err as { message?: string }).message ?? String(err)];
    } finally { this.busy = false; }
  }

  private limit(on: boolean, gb: string, set: (v: boolean) => void, setGb: (v: string) => void, label: "storageStopLow" | "storageAutoDelete", help: "storageStopLowHelp" | "storageAutoDeleteHelp", name: string) {
    const t = this.t;
    return html`<div class="limit"><label class="check"><input type="checkbox" name=${`${name}_on`} .checked=${on} @change=${(e: Event) => { set((e.target as HTMLInputElement).checked); this.saved = false; }}> ${t(label)}</label>
      <input type="number" name=${`${name}_gb`} min="0.01" step="0.5" aria-label=${t(label)} .value=${gb} ?disabled=${!on} @input=${(e: Event) => { setGb((e.target as HTMLInputElement).value); this.saved = false; }} /> ${t("storageGb")}
      <small class="dim">${t(help)}</small></div>`;
  }

  render() {
    const t = this.t, i = this.info;
    if (this.failed || !i) return nothing;
    const lang = this.language.startsWith("fr") ? "fr" : "en";
    const rate = i.per_day_bytes, left = i.days_left;
    const days = left != null && left < 365 ? t("storageRateDays", { n: Math.round(left) }) : "";
    return html`<details class="card" data-storage open><summary>${t("storageTitle")}</summary>
      <p class="dim" data-storage-folder>${t("storageFolder", { path: i.path })}</p>
      <p data-storage-used>${t("storageUsed", { size: this.size(i.bytes), free: this.size(i.free_bytes), total: this.size(i.total_bytes) })}</p>
      <p class="dim" data-storage-rate>${rate ? t("storageRate", { rate: this.size(rate), days }) : t("storageNoRate")}
        ${rate ? t("storageForecast", { days: this.retentionDays, size: this.size(rate * this.retentionDays) }) : nothing}</p>
      ${i.paused ? html`<p class="note error" role="status" data-storage-paused>${t("storagePaused")}</p>` : nothing}
      ${i.auto_deleted > 0 ? html`<p class="dim" data-storage-autodeleted>${t("storageAutoDeleted", { n: i.auto_deleted })}</p>` : nothing}
      ${i.skipped > 0 ? html`<p class="dim" data-storage-skipped>${t("storageSkipped", { n: i.skipped })}</p>` : nothing}
      <p class="dim"><a href=${`${GUIDE}.${lang}.md`} target="_blank" rel="noreferrer noopener">${t("storageGuide")}</a></p>
      ${this.readonly ? html`${i.min_free_gb != null ? html`<p class="dim" data-limit-stop>${t("storageLimitStop", { n: i.min_free_gb })}</p>` : nothing}
        ${i.max_gb != null ? html`<p class="dim" data-limit-delete>${t("storageLimitDelete", { n: i.max_gb })}</p>` : nothing}
        <div class="buttons"><button data-action="storage-settings" @click=${() => this.dispatchEvent(new CustomEvent("open-tab", { detail: { tab: "settings" }, bubbles: true, composed: true }))}>${t("storageEdit")}</button></div>`
      : html`${this.limit(this.stopOn, this.stopGb, (v) => (this.stopOn = v), (v) => (this.stopGb = v), "storageStopLow", "storageStopLowHelp", "stop")}
      ${this.limit(this.delOn, this.delGb, (v) => (this.delOn = v), (v) => (this.delGb = v), "storageAutoDelete", "storageAutoDeleteHelp", "del")}
      ${this.errors.map((e) => html`<p class="note error">${e}</p>`)}
      <div class="buttons"><button class="primary" data-action="save-storage" ?disabled=${this.busy} @click=${() => void this.save()}>${t("storageSave")}</button>
        ${this.saved ? html`<span class="ok" role="status" data-storage-saved>${t("storageSaved")}</span>` : nothing}</div>
      ${this.moveSection(i)}`}
    </details>`;
  }

  static styles = css`
    .card { border: 1px solid var(--divider-color); border-radius: 12px; padding: 8px 14px; margin-bottom: 14px; background: var(--card-background-color); }
    summary { cursor: pointer; font-weight: 500; } p { margin: 8px 0; } h3 { font-size: 1rem; font-weight: 500; margin: 4px 0; } hr { border: 0; border-top: 1px solid var(--divider-color); margin: 14px 0; }
    .dim { color: var(--secondary-text-color); } small { display: block; margin: 2px 0 0 26px; }
    .limit { margin: 12px 0; } .check { display: inline-flex; align-items: center; gap: 8px; }
    input[type=number] { font: inherit; width: 90px; padding: 6px 8px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--primary-background-color); color: var(--primary-text-color); }
    .buttons { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-top: 8px; }
    button { font: inherit; padding: 6px 14px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); cursor: pointer; }
    button.primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: transparent; }
    button.danger { background: var(--error-color, #db4437); color: #fff; border-color: transparent; }
    .ok { color: var(--success-color, #43a047); } .note.error { color: var(--error-color, #db4437); } a { color: var(--primary-color); }
    .row { display: flex; align-items: center; gap: 8px; margin: 10px 0 2px; flex-wrap: wrap; } .wide { width: min(420px, 100%); font: inherit; padding: 6px 8px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--primary-background-color); color: var(--primary-text-color); }
    .old { display: flex; justify-content: space-between; gap: 10px; flex-wrap: wrap; align-items: flex-start; padding: 6px 0; border-bottom: 1px solid var(--divider-color); } .old p { margin: 4px 0; max-width: 60ch; }
    .confirm { border: 1px solid var(--warning-color, #ffa600); border-radius: 8px; padding: 6px 12px; margin: 8px 0; }
  `;
}
if (!customElements.get("sound-recognition-storage")) customElements.define("sound-recognition-storage", StorageCard);
