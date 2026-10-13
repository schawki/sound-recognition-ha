import { LitElement, css, html } from "lit";
import { property, state } from "lit/decorators.js";
import { PanelApi } from "./api";
import { translator } from "./i18n";
import type { Hass } from "./types";
import "./live-view";
import "./insights-view";
import type { OpenTab } from "./advice-items";
import "./sources-view";
import "./sounds-view";
import "./advice-view";
import "./clips-view";
import "./settings-view";
import "./update-banner";

type Tab = "live" | "insights" | "sources" | "sounds" | "advice" | "clips" | "settings";
const TABS: [Tab, "live" | "insightsTab" | "sourcesTab" | "soundsTab" | "adviceTab" | "clipsTab" | "settingsTab"][] = [
  ["live", "live"], ["insights", "insightsTab"], ["sources", "sourcesTab"], ["sounds", "soundsTab"], ["advice", "adviceTab"], ["clips", "clipsTab"], ["settings", "settingsTab"],
];

class SoundRecognitionPanel extends LitElement {
  @property({ attribute: false }) hass!: Hass;
  @property({ type: Boolean }) narrow = false;
  @state() private api?: PanelApi;
  @state() private tab: Tab = "live";
  @state() private focusKey: string | null = null;             // the advice to show when the Advice tab opens from a link
  @state() private espPending = 0;                              // ESP32 microphones that can be added (the Repairs badge counts the same)
  @state() private wantEsp = false;
  private uiLang = "";
  private espTimer?: number;

  connectedCallback(): void {
    super.connectedCallback();
    void this.pollEsp();
    this.espTimer = window.setInterval(() => void this.pollEsp(), 60_000);
  }

  disconnectedCallback(): void {
    window.clearInterval(this.espTimer);
    super.disconnectedCallback();
  }

  private async pollEsp(): Promise<void> {
    try {
      if (this.api) this.espPending = (await this.api.esphomeState()).pending;
    } catch { /* the integration is not reachable right now: the live view says so */ }
  }

  protected updated(changed: Map<string, unknown>): void {
    if ((changed.has("api") || changed.has("tab")) && this.api) void this.pollEsp();
  }


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

  private openTab = (e: CustomEvent<OpenTab>): void => {
    this.focusKey = e.detail.focus ?? null;
    this.tab = e.detail.tab;
  };

  private view(t: ReturnType<typeof translator>) {
    const common = { api: this.api, t, language: this.uiLang };
    switch (this.tab) {
      case "insights": return html`<sound-recognition-insights .api=${common.api} .t=${t} .language=${common.language} @open-tab=${this.openTab}></sound-recognition-insights>`;
      case "sources": return html`<sound-recognition-sources .api=${common.api} .t=${t} .language=${common.language} .wantEsp=${this.wantEsp} @esp-opened=${() => { this.wantEsp = false; }} @esp-pending=${(e: CustomEvent<number>) => { this.espPending = e.detail; }}></sound-recognition-sources>`;
      case "sounds": return html`<sound-recognition-sounds .api=${common.api} .t=${t} .language=${common.language}></sound-recognition-sounds>`;
      case "advice": return html`<sound-recognition-advice .api=${common.api} .t=${t} .language=${common.language} .focusKey=${this.focusKey}></sound-recognition-advice>`;
      case "clips": return html`<sound-recognition-clips .api=${common.api} .t=${t} .language=${common.language} @open-tab=${this.openTab}></sound-recognition-clips>`;
      case "settings": return html`<sound-recognition-settings .api=${common.api} .t=${t} .language=${common.language}></sound-recognition-settings>`;
      default: return html`<sound-recognition-live .api=${common.api} .t=${t} .language=${common.language} @open-tab=${this.openTab}></sound-recognition-live>`;
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
      ${this.espPending > 0 ? html`<button class="esp-banner" data-esp-banner @click=${() => { this.focusKey = null; this.wantEsp = true; this.tab = "sources"; }}>${t(this.espPending > 1 ? "espBannerMany" : "espBanner", { n: String(this.espPending) })}</button>` : ""}
      <nav role="tablist" @keydown=${this.tabKeys}>
        ${TABS.map(([k, label]) => html`<button role="tab" id=${`tab-${k}`} aria-selected=${this.tab === k} aria-controls="view" tabindex=${this.tab === k ? 0 : -1} class=${this.tab === k ? "on" : ""} data-tab=${k} @click=${() => { this.focusKey = null; this.tab = k; }}>${t(label)}${k === "sources" && this.espPending > 0 ? ` (${this.espPending})` : ""}</button>`)}
      </nav>
      <main id="view" role="tabpanel" aria-labelledby=${`tab-${this.tab}`}>${this.view(t)}</main>`;
  }

  static styles = css`
    :host { display: block; min-height: 100%; background: var(--primary-background-color); color: var(--primary-text-color); font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif); }
    .bar { display: flex; align-items: center; gap: 8px; height: 56px; padding: 0 16px; background: var(--app-header-background-color, var(--primary-color)); color: var(--app-header-text-color, var(--text-primary-color, #fff)); position: sticky; top: 0; z-index: 2; }
    h1 { font-size: 1.25rem; font-weight: 400; margin: 0; }
    .menu { background: none; border: 0; color: inherit; font-size: 1.4rem; cursor: pointer; padding: 8px; }
    .esp-banner { display: block; width: 100%; text-align: left; font: inherit; border: 0; border-bottom: 1px solid var(--divider-color); cursor: pointer; background: var(--warning-color, #ffa600); color: #000; padding: 10px 16px; }
    .esp-banner:hover, .esp-banner:focus-visible { filter: brightness(0.95); }
    nav { display: flex; gap: 4px; padding: 0 12px; background: var(--card-background-color); border-bottom: 1px solid var(--divider-color); overflow-x: auto; }
    nav button { background: none; border: 0; border-bottom: 3px solid transparent; color: var(--secondary-text-color); font: inherit; padding: 12px 14px; cursor: pointer; white-space: nowrap; }
    nav button.on { color: var(--primary-color); border-bottom-color: var(--primary-color); }
    main { max-width: 1100px; margin: 0 auto; padding: 16px; box-sizing: border-box; }
  `;
}
if (!customElements.get("sound-recognition-panel")) customElements.define("sound-recognition-panel", SoundRecognitionPanel);
