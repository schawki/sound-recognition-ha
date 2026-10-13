import { LitElement, css, html, nothing } from "lit";
import { property, state } from "lit/decorators.js";
import type { PanelApi } from "./api";
import type { T } from "./i18n";
import type { RetentionCategory } from "./types";
import { RETENTION_CATEGORIES, RET_KEYS, retBlock, retForm } from "./retention";

/** How long the clips of each kind of sound are kept (defaults.clips.retention_by_category). */
export class RetentionCard extends LitElement {
  @property({ attribute: false }) api!: PanelApi;
  @property({ attribute: false }) t!: T;
  @state() private ret: Record<RetentionCategory, string> = retForm(undefined);
  @state() private msg = "";
  @state() private errors: string[] = [];
  @state() private busy = false;

  connectedCallback(): void {
    super.connectedCallback();
    void this.api.config().then((c) => { this.ret = retForm(c.defaults?.clips?.retention_by_category); }, () => undefined);
  }

  /** Saves on a fresh copy of the configuration, so nothing else is overwritten. */
  private async save(): Promise<void> {
    this.busy = true; this.msg = ""; this.errors = [];
    try {
      const cfg = await this.api.config();
      const block = retBlock(this.ret);
      const defaults = { ...(cfg.defaults ?? {}) };
      const clips = { ...(defaults.clips ?? {}) };
      if (Object.keys(block).length) clips.retention_by_category = block; else delete clips.retention_by_category;
      defaults.clips = clips;
      const next = { ...cfg, defaults };
      const check = await this.api.validate(next);
      if (check.errors.length) { this.errors = check.errors; return; }
      await this.api.save(next);
      this.msg = this.t("retentionSaved");
    } catch (err) {
      this.errors = [(err as { message?: string }).message ?? String(err)];
    } finally { this.busy = false; }
  }

  render() {
    const t = this.t;
    return html`<details class="card" data-retention open><summary>${t("retentionTitle")}</summary>
      <p class="dim">${t("retentionHelp")}</p>
      <div class="two">${RETENTION_CATEGORIES.map((k) => html`<label>${t(RET_KEYS[k])}<input name=${`ret_${k}`} type="number" min="0" max="3650" step="1" .value=${this.ret[k]}
        @input=${(e: Event) => { this.ret = { ...this.ret, [k]: (e.target as HTMLInputElement).value }; this.msg = ""; }} /></label>`)}</div>
      ${parseInt(this.ret.confidential, 10) > 0 ? html`<p class="note error" data-confidential-warning>${t("clipForbiddenOn")}</p>` : nothing}
      ${this.errors.map((e) => html`<p class="note error">${e}</p>`)}
      <div class="buttons"><button class="primary" data-action="save-retention" ?disabled=${this.busy} @click=${() => void this.save()}>${t("retentionSave")}</button>
        ${this.msg ? html`<span class="ok" role="status" data-retention-saved>${this.msg}</span>` : nothing}</div></details>`;
  }

  static styles = css`
    .card { border: 1px solid var(--divider-color); border-radius: 12px; padding: 8px 14px; margin-bottom: 14px; background: var(--card-background-color); }
    summary { cursor: pointer; font-weight: 500; } label { display: flex; flex-direction: column; gap: 4px; font-size: 0.9rem; } p { margin: 8px 0; }
    input { font: inherit; padding: 9px 10px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--primary-background-color); color: var(--primary-text-color); min-width: 0; }
    .two { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin: 10px 0; }
    .dim { color: var(--secondary-text-color); } .note.error { color: var(--error-color, #db4437); } .ok { color: var(--success-color, #43a047); }
    .buttons { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
    button { font: inherit; padding: 6px 14px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); cursor: pointer; }
    button.primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: transparent; }
  `;
}
if (!customElements.get("sound-recognition-retention")) customElements.define("sound-recognition-retention", RetentionCard);
