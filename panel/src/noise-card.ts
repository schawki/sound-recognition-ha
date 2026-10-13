import { LitElement, css, html, nothing } from "lit";
import { property, state } from "lit/decorators.js";
import type { PanelApi } from "./api";
import type { T } from "./i18n";
import type { NoiseInfo } from "./types";
import { formatBytes } from "./util";

/** Settings: what the noise assistant keeps (one number per minute and source), how long, and the way to delete it. */
export class NoiseCard extends LitElement {
  @property({ attribute: false }) api!: PanelApi;
  @property({ attribute: false }) t!: T;
  @property({ attribute: false }) language = "en";
  @state() private info: NoiseInfo | null = null;
  @state() private days = "7";
  @state() private confirm = "";      // "" nothing to confirm, "*" all, otherwise a source id
  @state() private msg = "";
  @state() private errors: string[] = [];
  @state() private busy = false;
  @state() private unavailable = false;

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
  }

  private async load(): Promise<void> {
    try {
      this.info = await this.api.noise();
      this.days = String(this.info.retention_days);
    } catch { this.unavailable = true; }
  }

  private async forget(source?: string): Promise<void> {
    this.busy = true; this.errors = [];
    try {
      const r = await this.api.noiseDelete(source);
      this.msg = this.t("noiseDeleted", { n: r.deleted });
      this.confirm = "";
      await this.load();
    } catch (err) { this.errors = [(err as { message?: string }).message ?? String(err)]; } finally { this.busy = false; }
  }

  /** Saves the number of days on a fresh copy of the configuration, so nothing else is overwritten. */
  private async saveDays(): Promise<void> {
    this.busy = true; this.msg = ""; this.errors = [];
    try {
      const cfg = await this.api.config();
      const next = { ...cfg, storage: { ...((cfg.storage as Record<string, unknown> | undefined) ?? {}), noise_retention_days: parseInt(this.days, 10) } };
      const check = await this.api.validate(next);
      if (check.errors.length) { this.errors = check.errors; return; }
      await this.api.save(next);
      this.msg = this.t("noiseSaved");
    } catch (err) { this.errors = [(err as { message?: string }).message ?? String(err)]; } finally { this.busy = false; }
  }

  private since(ts: number | null): string {
    return ts == null ? "" : new Date(ts * 1000).toLocaleString(this.language, { dateStyle: "medium", timeStyle: "short" });
  }

  protected render() {
    const t = this.t;
    if (this.unavailable || !this.info) return nothing;
    const rows = this.info.sources;
    const total = rows.reduce((a, s) => a + s.minutes, 0);
    return html`<details class="card" data-noise-card><summary>${t("noiseCardTitle")}</summary>
      <p class="dim">${t("noiseCardHelp")}</p>
      <label>${t("noiseRetentionLabel")}<input name="noise_days" type="number" min="0" max="90" step="1" .value=${this.days}
        @input=${(e: Event) => { this.days = (e.target as HTMLInputElement).value; this.msg = ""; }} /></label>
      <div class="buttons"><button class="primary" data-action="save-noise-days" ?disabled=${this.busy} @click=${() => void this.saveDays()}>${t("noiseRetentionSave")}</button></div>
      ${total === 0 ? html`<p class="dim" data-noise-empty>${t("noiseNothing")}</p>` : html`
        <table><thead><tr><th>${t("noiseColSource")}</th><th>${t("noiseColCount")}</th><th>${t("noiseColSince")}</th><th>${t("noiseColSize")}</th><th></th></tr></thead>
        <tbody>${rows.map((s) => html`<tr data-noise-row=${s.id}><td>${s.name}</td><td data-count>${t("noiseMinutes", { n: s.minutes })}</td><td>${this.since(s.since)}</td>
          <td>${formatBytes(s.bytes, this.language, t)}</td>
          <td>${s.minutes === 0 ? nothing : this.confirm === s.id
            ? html`<button data-action="confirm-noise" ?disabled=${this.busy} @click=${() => void this.forget(s.id)}>${t("noiseConfirm", { n: s.minutes })}</button>`
            : html`<button data-action="delete-noise" @click=${() => { this.confirm = s.id; }}>${t("noiseDelete")}</button>`}</td></tr>`)}</tbody></table>
        <div class="buttons">${this.confirm === "*"
          ? html`<button data-action="confirm-noise-all" ?disabled=${this.busy} @click=${() => void this.forget()}>${t("noiseConfirm", { n: total })}</button>`
          : html`<button data-action="delete-noise-all" @click=${() => { this.confirm = "*"; }}>${t("noiseDeleteAll")}</button>`}</div>`}
      ${this.errors.map((e) => html`<p class="note error">${e}</p>`)}
      ${this.msg ? html`<p class="ok" role="status" data-noise-msg>${this.msg}</p>` : nothing}</details>`;
  }

  static styles = css`
    .card { border: 1px solid var(--divider-color); border-radius: 12px; padding: 8px 14px; margin-bottom: 14px; background: var(--card-background-color); }
    summary { cursor: pointer; font-weight: 500; } label { display: flex; flex-direction: column; gap: 4px; font-size: 0.9rem; max-width: 320px; } p { margin: 8px 0; }
    input { font: inherit; padding: 9px 10px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--primary-background-color); color: var(--primary-text-color); min-width: 0; }
    table { border-collapse: collapse; width: 100%; font-size: 0.9rem; margin: 10px 0; } th, td { text-align: left; padding: 6px 10px; border-bottom: 1px solid var(--divider-color); } th { color: var(--secondary-text-color); font-weight: 500; }
    .dim { color: var(--secondary-text-color); } .note.error { color: var(--error-color, #db4437); } .ok { color: var(--success-color, #43a047); }
    .buttons { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin: 8px 0; }
    button { font: inherit; padding: 6px 14px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); cursor: pointer; }
    button.primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: transparent; }
  `;
}
if (!customElements.get("sound-recognition-noise")) customElements.define("sound-recognition-noise", NoiseCard);
