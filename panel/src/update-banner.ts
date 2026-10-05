import { LitElement, css, html, nothing } from "lit";
import { property, state } from "lit/decorators.js";
import type { PanelApi } from "./api";
import type { T } from "./i18n";
import type { UpdateInfo } from "./types";

const IDLE_MS = 5 * 60 * 1000;
const BUSY_MS = 4000;
const busyMs = (): number => (window as unknown as { __updatePollMs?: number }).__updatePollMs ?? BUSY_MS;   // tests shorten it

/** Tells when the service should be updated, launches the update from Home Assistant when the installation allows it, and says when it is back. */
export class UpdateBanner extends LitElement {
  @property({ attribute: false }) api!: PanelApi;
  @property({ attribute: false }) t!: T;
  @state() private info: UpdateInfo | null = null;
  @state() private result: "done" | "failed" | null = null;
  @state() private error = "";
  private wasInstalling = false;
  private timer?: number;
  private closed = false;

  connectedCallback(): void {
    super.connectedCallback();
    this.closed = false;
    void this.poll();
  }

  disconnectedCallback(): void {
    this.closed = true;
    window.clearTimeout(this.timer);
    super.disconnectedCallback();
  }

  private async poll(): Promise<void> {
    try {
      const info = await this.api.update();
      if (this.closed) return;
      if (this.wasInstalling && !info.installing) this.result = info.status.state === "failed" ? "failed" : "done";
      this.wasInstalling = info.installing;
      this.info = info;
    } catch { /* the service or the integration is not reachable right now: the live view says so */ }
    if (!this.closed) this.timer = window.setTimeout(() => void this.poll(), this.info?.installing ? busyMs() : IDLE_MS);
  }

  private async install(): Promise<void> {
    this.error = "";
    this.result = null;
    try {
      this.info = await this.api.updateInstall();
      this.wasInstalling = true;
      window.clearTimeout(this.timer);
      this.timer = window.setTimeout(() => void this.poll(), busyMs());
    } catch (err) {
      this.error = String((err as { message?: string })?.message ?? err);
    }
  }

  private manual(info: UpdateInfo) {
    return html`<div class="manual">${this.t("updManual")}<code>${info.manual_command}</code></div>`;
  }

  render() {
    const { t, info } = this;
    if (!info) return nothing;
    const vars = { installed: info.installed ?? "?", latest: (info.latest ?? "?").replace(/^v/i, ""), message: info.status.message ?? "" };
    if (info.installing) return html`<div class="b run" data-update="installing" role="status">${t("updRunning", { ...vars, message: "" })}</div>`;
    if (this.result === "done") return html`<div class="b ok" data-update="done" role="status">${t("updDone", vars)}<button class="x" @click=${() => (this.result = null)}>${t("updDismiss")}</button></div>`;
    if (this.result === "failed") {
      return html`<div class="b bad" data-update="failed" role="alert">${t("updFailed", vars)}
        ${info.status.log ? html`<details><summary>${t("updLog")}</summary><pre>${info.status.log}</pre></details>` : nothing}
        <button class="x" @click=${() => (this.result = null)}>${t("updDismiss")}</button></div>`;
    }
    if (!info.available && !info.outdated) return nothing;
    return html`<div class="b warn" data-update=${info.outdated ? "outdated" : "available"} role="status">
      <span>${info.outdated ? t("updOutdated", vars) : t("updAvailable", vars)}
        ${info.latest ? html` <a href=${info.release_url} target="_blank" rel="noreferrer noopener">${t("updNotes")}</a>` : nothing}</span>
      ${info.capable ? html`<button class="go" @click=${this.install}>${t("updNow")}</button>` : this.manual(info)}
      ${this.error ? html`<div class="err">${this.error}</div>` : nothing}</div>`;
  }

  static styles = css`
    .b { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; padding: 10px 16px; font-size: .92rem; border-bottom: 1px solid var(--divider-color); }
    .warn { background: var(--warning-color, #ffa600); color: #000; }
    .run { background: var(--info-color, #039be5); color: #fff; }
    .ok { background: var(--success-color, #43a047); color: #fff; }
    .bad { background: var(--error-color, #db4437); color: #fff; }
    a { color: inherit; }
    button { font: inherit; border: 1px solid currentColor; background: transparent; color: inherit; border-radius: 6px; padding: 4px 12px; cursor: pointer; }
    .go { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: transparent; }
    .x { margin-left: auto; }
    .manual { flex-basis: 100%; } code, pre { display: block; margin-top: 4px; padding: 6px 8px; border-radius: 4px; background: rgba(0,0,0,.15); overflow-x: auto; white-space: pre-wrap; user-select: all; }
    details { flex-basis: 100%; }
    .err { flex-basis: 100%; }
  `;
}
customElements.define("sound-recognition-update", UpdateBanner);
