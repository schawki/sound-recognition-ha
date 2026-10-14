import { LitElement, css, html, nothing } from "lit";
import { property, state } from "lit/decorators.js";
import type { PanelApi } from "./api";
import type { T } from "./i18n";
import type { NoiseSource } from "./types";

const CHART = { w: 288, h: 64, lo: -90, hi: -10 };

/** Under the "minimum volume" field of a source: what was measured on it and the value it suggests. Never changes anything by itself:
 *  "Use this value" only emits `gate-chosen`, the form puts it in the field and the user saves. Absent for a service without the noise route. */
export class NoiseAssistant extends LitElement {
  @property({ attribute: false }) api!: PanelApi;
  @property({ attribute: false }) t!: T;
  @property() sourceId = "";
  /** The value of the field, to draw the current line on the chart. */
  @property() value = "";
  @property() language = "en";
  /** Whether the minimum volume of the source follows the measurements (the form says so, saved or not). */
  @property({ type: Boolean }) autoOn = false;
  @state() private info: NoiseSource | null = null;
  @state() private recording = true;
  @state() private unavailable = false;
  @state() private used = false;

  connectedCallback(): void {
    super.connectedCallback();
    if (!this.sourceId) return;
    this.api.noise().then((n) => {
      this.recording = n.recording;
      this.step = n.step_db ?? 3;
      this.info = n.sources.find((s) => s.id === this.sourceId) ?? null;
    }, () => { this.unavailable = true; });
  }

  private y(level: number): number {
    const f = (Math.min(CHART.hi, Math.max(CHART.lo, level)) - CHART.lo) / (CHART.hi - CHART.lo);
    return Math.round((1 - f) * CHART.h * 10) / 10;
  }

  private chart(n: NoiseSource, gate: number) {
    const bw = CHART.w / 24;
    const cur = parseFloat(this.value);
    return html`<svg viewBox="0 0 ${CHART.w} ${CHART.h}" role="img" aria-label=${this.t("noiseChart")} data-chart>
      ${n.hourly.map((v, h) => v == null ? nothing : html`<rect x=${h * bw + 1} y=${this.y(v)} width=${bw - 2} height=${CHART.h - this.y(v)} class="bar"></rect>`)}
      <line x1="0" x2=${CHART.w} y1=${this.y(gate)} y2=${this.y(gate)} class="gate"></line>
      ${Number.isFinite(cur) ? html`<line x1="0" x2=${CHART.w} y1=${this.y(cur)} y2=${this.y(cur)} class="cur"></line>` : nothing}
    </svg><small class="dim">${this.t("noiseChart")}</small>`;
  }

  private when(ts: number | null): string {
    return ts == null ? "" : new Date(ts * 1000).toLocaleString(this.language, { dateStyle: "medium", timeStyle: "short" });
  }

  /** What the service does for a source set to automatic: the value in use, what is waited for, and the last changes. */
  private autoBlock(n: NoiseSource) {
    const t = this.t, sg = n.suggestion, a = n.auto;
    const hist = a?.history ?? [];
    return html`<div data-noise="auto">
      <p class="big" data-noise="auto-state">${a && a.gate != null ? t("noiseAutoInUse", { gate: a.gate, when: this.when(a.since) })
        : sg.status === "not_enough" ? t("noiseAutoWaiting", { have: Math.floor(sg.minutes / 60), need: Math.round((sg.needed ?? 360) / 60) })
        : t("noiseAutoNext", { gate: sg.gate ?? 0, step: this.step })}</p>
      <p class="dim">${t("noiseAutoHow", { step: this.step })}</p>
      ${hist.length ? html`<details data-noise="auto-history"><summary>${t("noiseAutoHistory")}</summary><ul>${hist.map((h) => html`<li>${this.when(h.ts)} : ${h.old == null ? "—" : h.old} → ${h.new} dBFS</li>`)}</ul></details>` : nothing}
      ${sg.status === "ready" ? html`${this.chart(n, sg.gate ?? 0)}` : nothing}
    </div>`;
  }

  private step = 3;

  protected render() {
    const t = this.t;
    if (this.unavailable) return nothing;
    if (!this.sourceId) return html`<p class="dim" data-noise="new">${t("noiseSaveFirst")}</p>`;
    const n = this.info;
    if (!n) return nothing;
    const sg = n.suggestion;
    return html`<div class="box" data-noise="assistant">
      <strong>${t("noiseTitle")}</strong>
      <p class="dim">${t("noiseIntro")}</p>
      ${!this.recording ? html`<p class="dim" data-noise="off">${t("noiseOff")}</p>` : this.autoOn ? this.autoBlock(n) : sg.status === "not_enough"
        ? html`<p data-noise="progress">${t("noiseProgress", { have: Math.floor(sg.minutes / 60), need: Math.round((sg.needed ?? 360) / 60) })}</p>`
        : html`<p class="big" data-noise="ready">${t("noiseReady", { gate: sg.gate ?? 0 })}</p>
          <p class="dim">${t("noiseWhy", { quiet: sg.quiet_dbfs ?? 0, typical: sg.typical_dbfs ?? 0, loud: sg.loud_dbfs ?? 0, margin: sg.margin_db ?? 0 })}</p>
          ${sg.capped ? html`<p class="warn" data-noise="capped">${t("noiseCapped")}</p>` : nothing}
          ${this.chart(n, sg.gate ?? 0)}
          <div class="row"><button type="button" data-action="use-gate" @click=${() => { this.used = true; this.dispatchEvent(new CustomEvent("gate-chosen", { detail: sg.gate, bubbles: true, composed: true })); }}>${t("noiseUse")}</button>
            ${this.used ? html`<span class="ok" role="status">${t("noiseUsed")}</span>` : nothing}</div>`}
      ${n.level_dbfs != null ? html`<p class="dim" data-noise="now">${t("noiseNow", { level: n.level_dbfs })}</p>` : nothing}
      <p class="dim">${this.autoOn ? t("noiseManualFromAuto") : t("noiseManual")}</p>
    </div>`;
  }

  static styles = css`
    :host { display: block; }
    .box { border: 1px solid var(--divider-color); border-radius: 10px; padding: 10px 14px; background: var(--secondary-background-color); }
    p { margin: 6px 0; } .dim, small { color: var(--secondary-text-color); font-size: 0.85rem; } .big { font-size: 1.05rem; font-weight: 500; }
    .warn { background: color-mix(in srgb, var(--warning-color, #ffa600) 22%, var(--card-background-color)); padding: 8px 12px; border-radius: 8px; }
    .ok { color: var(--success-color, #43a047); } .row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-top: 8px; }
    svg { width: 100%; max-width: 420px; height: auto; display: block; margin-top: 8px; }
    .bar { fill: var(--primary-color); opacity: 0.55; } .gate { stroke: var(--success-color, #43a047); stroke-width: 1.5; stroke-dasharray: 4 3; }
    .cur { stroke: var(--primary-text-color); stroke-width: 1.5; }
    button { font: inherit; cursor: pointer; padding: 6px 14px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); }
  `;
}
if (!customElements.get("sr-noise-assistant")) customElements.define("sr-noise-assistant", NoiseAssistant);
