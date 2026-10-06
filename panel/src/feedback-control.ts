import { LitElement, css, html, nothing } from "lit";
import { property, state } from "lit/decorators.js";
import type { PanelApi } from "./api";
import type { T } from "./i18n";
import { applyAndSave } from "./patch";

export interface FeedbackTarget { id: string; source: string; mid: string; score: number; threshold?: number; feedback?: string | null }

/** "The detection is wrong" for one detection: marks it false, optionally raising that sound's threshold on that source. Used by Live and Clips. */
export class DetectionFeedback extends LitElement {
  @property({ attribute: false }) api!: PanelApi;
  @property({ attribute: false }) t!: T;
  @property({ attribute: false }) ev!: FeedbackTarget;
  @property({ attribute: false }) sourceName = "";
  @property({ attribute: false }) audioName: (mid: string) => string | undefined = () => undefined;
  @state() private open = false;
  @state() private error = "";

  private get proposal(): number {
    return Math.min(0.95, Math.round((Math.max(this.ev.score, this.ev.threshold ?? 0) + 0.03) * 100) / 100);
  }

  private changed(feedback: string | null): void {
    this.dispatchEvent(new CustomEvent("feedback-changed", { detail: { id: this.ev.id, feedback }, bubbles: true, composed: true }));
  }

  private async mark(raise: boolean): Promise<void> {
    this.error = "";
    try {
      if (raise) {
        const errs = await applyAndSave(this.api, { source: this.ev.source, class_patch: { [this.ev.mid]: { threshold: this.proposal } } }, (mid) => this.audioName(mid));
        if (errs.length) { this.error = errs.join("; "); return; }
      }
      await this.api.feedback(this.ev.id, true);
      this.open = false;
      this.changed("false");
    } catch (err) {
      this.error = (err as { message?: string }).message ?? String(err);
    }
  }

  private async unmark(): Promise<void> {
    try {
      await this.api.feedback(this.ev.id, false);
      this.changed(null);
    } catch (err) {
      this.error = (err as { message?: string }).message ?? String(err);
    }
  }

  protected render() {
    const t = this.t;
    if (this.ev.feedback === "false")
      return html`<span class="chip off" data-false-chip>${t("markedFalse")}</span><button class="link" data-action="unmark" @click=${() => void this.unmark()}>${t("undo")}</button>${this.error ? html`<span class="error">${this.error}</span>` : nothing}`;
    if (this.open)
      return html`<button data-action="mark-only" @click=${() => void this.mark(false)}>${t("markFalse")}</button>
        <button class="primary" data-action="mark-raise" @click=${() => void this.mark(true)}>${t("markFalseRaise", { v: this.proposal.toFixed(2), s: this.sourceName })}</button>
        <button class="link" data-action="mark-cancel" @click=${() => (this.open = false)}>${t("cancel")}</button>
        ${this.error ? html`<span class="error">${this.error}</span>` : nothing}`;
    return html`<button class="link" data-action="false" @click=${() => { this.error = ""; this.open = true; }}>${t("notRealSound")}</button>`;
  }

  static styles = css`
    :host { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
    button { font: inherit; cursor: pointer; padding: 6px 12px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); }
    button.primary { background: var(--primary-color); border-color: transparent; color: var(--text-primary-color, #fff); }
    button.link { border: 0; background: none; padding: 2px 0; color: var(--primary-color); text-decoration: underline; font-size: 0.85rem; }
    .chip { font-size: 0.8rem; padding: 2px 10px; border-radius: 999px; border: 1px solid var(--divider-color); color: var(--secondary-text-color); }
    .error { color: var(--error-color, #db4437); font-size: 0.85rem; }
  `;
}
if (!customElements.get("sr-detection-feedback")) customElements.define("sr-detection-feedback", DetectionFeedback);
