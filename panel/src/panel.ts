import { LitElement, css, html } from "lit";
import { property, state } from "lit/decorators.js";
import { PanelApi } from "./api";
import { translator } from "./i18n";
import type { Hass } from "./types";
import "./live-view";
import "./insights-view";
import "./sources-view";
import "./sounds-view";
import "./advice-view";
import "./clips-view";
import "./update-banner";

type Tab = "live" | "insights" | "sources" | "sounds" | "advice" | "clips";
const TABS: [Tab, "live" | "insightsTab" | "sourcesTab" | "soundsTab" | "adviceTab" | "clipsTab"][] = [
  ["live", "live"], ["insights", "insightsTab"], ["sources", "sourcesTab"], ["sounds", "soundsTab"], ["advice", "adviceTab"], ["clips", "clipsTab"],
];

class SoundRecognitionPanel extends LitElement {
  @property({ attribute: false }) hass!: Hass;
  @property({ type: Boolean }) narrow = false;
  @state() private api?: PanelApi;
  @state() private tab: Tab = "live";
  private uiLang = "";

  protected willUpdate(): void {
    if (this.hass && this.hass.language !== this.uiLang) {
      this.uiLang = this.hass.language;
      this.api = new PanelApi(this.hass, this.uiLang);
    }
  }

  private toggleMenu(): void {
    this.dispatchEvent(new CustomEvent("hass-toggle-menu", { bubbles: true, composed: true }));
  }

  private tabKeys = (e: KeyboardEvent): void => {
    const i = TABS.findIndex(([k]) => k === this.tab);
    const next = e.key === "ArrowRight" ? i + 1 : e.key === "ArrowLeft" ? i - 1 : e.key === "Home" ? 0 : e.key === "End" ? TABS.length - 1 : -1;
    if (next < 0) return;
    e.preventDefault();
    this.tab = TABS[(next + TABS.length) % TABS.length][0];
    void this.updateComplete.then(() => (this.shadowRoot?.getElementById(`tab-${this.tab}`) as HTMLElement | null)?.focus());
  };

  private view(t: ReturnType<typeof translator>) {
    const common = { api: this.api, t, language: this.uiLang };
    switch (this.tab) {
      case "insights": return html`<sound-recognition-insights .api=${common.api} .t=${t} .language=${common.language} @open-tab=${(e: CustomEvent<Tab>) => (this.tab = e.detail)}></sound-recognition-insights>`;
      case "sources": return html`<sound-recognition-sources .api=${common.api} .t=${t} .language=${common.language}></sound-recognition-sources>`;
      case "sounds": return html`<sound-recognition-sounds .api=${common.api} .t=${t} .language=${common.language}></sound-recognition-sounds>`;
      case "advice": return html`<sound-recognition-advice .api=${common.api} .t=${t} .language=${common.language}></sound-recognition-advice>`;
      case "clips": return html`<sound-recognition-clips .api=${common.api} .t=${t} .language=${common.language}></sound-recognition-clips>`;
      default: return html`<sound-recognition-live .api=${common.api} .t=${t} .language=${common.language}></sound-recognition-live>`;
    }
  }

  render() {
    if (!this.api) return html``;
    const t = translator(this.uiLang);
    return html`
      <div class="bar">
        ${this.narrow ? html`<button class="menu" @click=${this.toggleMenu} aria-label="Menu">☰</button>` : ""}
        <h1>${t("title")}</h1>
      </div>
      <sound-recognition-update .api=${this.api} .t=${t}></sound-recognition-update>
      <nav role="tablist" @keydown=${this.tabKeys}>
        ${TABS.map(([k, label]) => html`<button role="tab" id=${`tab-${k}`} aria-selected=${this.tab === k} aria-controls="view" tabindex=${this.tab === k ? 0 : -1} class=${this.tab === k ? "on" : ""} data-tab=${k} @click=${() => (this.tab = k)}>${t(label)}</button>`)}
      </nav>
      <main id="view" role="tabpanel" aria-labelledby=${`tab-${this.tab}`}>${this.view(t)}</main>`;
  }

  static styles = css`
    :host { display: block; min-height: 100%; background: var(--primary-background-color); color: var(--primary-text-color); font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif); }
    .bar { display: flex; align-items: center; gap: 8px; height: 56px; padding: 0 16px; background: var(--app-header-background-color, var(--primary-color)); color: var(--app-header-text-color, var(--text-primary-color, #fff)); position: sticky; top: 0; z-index: 2; }
    h1 { font-size: 1.25rem; font-weight: 400; margin: 0; }
    .menu { background: none; border: 0; color: inherit; font-size: 1.4rem; cursor: pointer; padding: 8px; }
    nav { display: flex; gap: 4px; padding: 0 12px; background: var(--card-background-color); border-bottom: 1px solid var(--divider-color); overflow-x: auto; }
    nav button { background: none; border: 0; border-bottom: 3px solid transparent; color: var(--secondary-text-color); font: inherit; padding: 12px 14px; cursor: pointer; white-space: nowrap; }
    nav button.on { color: var(--primary-color); border-bottom-color: var(--primary-color); }
    main { max-width: 1100px; margin: 0 auto; padding: 16px; box-sizing: border-box; }
  `;
}
if (!customElements.get("sound-recognition-panel")) customElements.define("sound-recognition-panel", SoundRecognitionPanel);
