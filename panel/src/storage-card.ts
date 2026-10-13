import { LitElement, css, html, nothing } from "lit";
import { property, state } from "lit/decorators.js";
import type { PanelApi } from "./api";
import type { T } from "./i18n";
import type { StorageInfo } from "./types";
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

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
  }

  private async load(): Promise<void> {
    try {
      const [info, cfg] = await Promise.all([this.api.storage(), this.api.config()]);
      this.info = info;
      this.stopOn = info.min_free_gb != null; this.stopGb = info.min_free_gb != null ? String(info.min_free_gb) : "";
      this.delOn = info.max_gb != null; this.delGb = info.max_gb != null ? String(info.max_gb) : "";
      this.retentionDays = Number((cfg.defaults?.clips as { max_retention_days?: number } | undefined)?.max_retention_days ?? 30);
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
        ${this.saved ? html`<span class="ok" role="status" data-storage-saved>${t("storageSaved")}</span>` : nothing}</div>`}
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
    .confirm { border: 1px solid var(--warning-color, #ffa600); border-radius: 8px; padding: 6px 12px; margin: 8px 0; }
  `;
}
if (!customElements.get("sound-recognition-storage")) customElements.define("sound-recognition-storage", StorageCard);
