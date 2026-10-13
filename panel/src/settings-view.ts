import { LitElement, css, html, nothing } from "lit";
import { property, state } from "lit/decorators.js";
import type { PanelApi } from "./api";
import type { T } from "./i18n";
import type { ConnectionInfo, EsphomeDevice, ServiceConfig, StructureInfo } from "./types";
import "./storage-card";

const DOCS = "https://github.com/schawki/sound-recognition-ha/blob/main/docs";

/** Everything that is set once and rarely changed, on one page: the connection to the service, the storage, the global defaults,
 *  the link with Home Structure and the ESP32 microphones that were put aside. Sources, sounds and advice keep their own tabs. */
export class SettingsView extends LitElement {
  @property({ attribute: false }) api!: PanelApi;
  @property({ attribute: false }) t!: T;
  @property({ attribute: false }) language = "en";
  @state() private conn: ConnectionInfo | null = null;
  @state() private confirmToken = false;
  @state() private tokenMsg = "";
  @state() private busy = false;
  @state() private structure: StructureInfo | null = null;
  @state() private ignored: EsphomeDevice[] = [];
  @state() private minVolume = "";
  @state() private clipsAllowed = true;
  @state() private maxDays = "";
  @state() private defaultsSaved = false;
  @state() private defaultsError = "";

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
  }

  private async load(): Promise<void> {
    const [conn, st, esp, cfg] = await Promise.allSettled([this.api.connection(), this.api.structure(), this.api.esphomeState(), this.api.config()]);
    if (conn.status === "fulfilled") this.conn = conn.value;
    if (st.status === "fulfilled") this.structure = st.value;
    if (esp.status === "fulfilled") this.ignored = esp.value.devices.filter((d) => d.ignored && !d.added);
    if (cfg.status === "fulfilled") {
      const d = cfg.value.defaults ?? {};
      this.minVolume = d.min_volume_dbfs == null ? "" : String(d.min_volume_dbfs);
      this.clipsAllowed = d.clips?.allowed !== false;
      this.maxDays = d.clips?.max_retention_days == null ? "" : String(d.clips.max_retention_days);
    }
  }

  private async changeToken(): Promise<void> {
    this.busy = true; this.tokenMsg = "";
    try {
      await this.api.rotateToken();
      this.tokenMsg = this.t("tokenDone");
    } catch (err) {
      this.tokenMsg = (err as { message?: string }).message ?? String(err);
    } finally { this.busy = false; this.confirmToken = false; }
  }

  private async saveDefaults(): Promise<void> {
    this.busy = true; this.defaultsError = ""; this.defaultsSaved = false;
    try {
      const cfg: ServiceConfig = await this.api.config();
      const defaults = { ...(cfg.defaults ?? {}) };
      const vol = Number(this.minVolume.replace(",", "."));
      defaults.min_volume_dbfs = this.minVolume.trim() === "" || !Number.isFinite(vol) ? null : vol;
      const clips = { ...(defaults.clips ?? {}), allowed: this.clipsAllowed };
      const days = Number(this.maxDays.replace(",", "."));
      if (this.maxDays.trim() !== "" && Number.isFinite(days)) clips.max_retention_days = days; else delete clips.max_retention_days;
      defaults.clips = clips;
      await this.api.save({ ...cfg, defaults });
      this.defaultsSaved = true;
    } catch (err) {
      this.defaultsError = (err as { message?: string }).message ?? String(err);
    } finally { this.busy = false; }
  }

  private async unignore(d: EsphomeDevice): Promise<void> {
    const state = await this.api.esphomeIgnore(d.id ?? d.device_id, false);
    this.ignored = state.devices.filter((x) => x.ignored && !x.added);
  }

  private connection() {
    const t = this.t, c = this.conn;
    return html`<section class="card" data-section="connection"><h2>${t("connTitle")}</h2>
      ${c ? html`<p data-conn-address>${t("connAddress", { host: c.host, port: c.port })}</p>
        <p class="dim" data-conn-state>${c.connected ? t("connOk", { version: c.version ?? "?" }) : t("connDown")}</p>` : nothing}
      <p class="dim">${t("connAddressHelp")}</p>
      <h3>${t("tokenTitle")}</h3>
      <p class="dim">${t("tokenHelp")}</p>
      ${this.confirmToken ? html`<div class="confirm" role="alertdialog" data-token-confirm><p>${t("tokenConfirm")}</p>
        <div class="buttons"><button class="danger" data-action="token-yes" ?disabled=${this.busy} @click=${() => void this.changeToken()}>${t("tokenYes")}</button>
          <button data-action="token-cancel" @click=${() => (this.confirmToken = false)}>${t("cancel")}</button></div></div>`
        : html`<button data-action="token-change" @click=${() => { this.confirmToken = true; this.tokenMsg = ""; }}>${t("tokenChange")}</button>`}
      ${this.tokenMsg ? html`<span class="ok" role="status" data-token-msg>${this.tokenMsg}</span>` : nothing}
    </section>`;
  }

  private defaults() {
    const t = this.t;
    return html`<section class="card" data-section="defaults"><h2>${t("defaultsTitle")}</h2>
      <p class="dim">${t("defaultsHelp")}</p>
      <label class="row">${t("defaultsVolume")} <input type="number" name="min_volume" min="-90" max="0" step="1" .value=${this.minVolume}
        @input=${(e: Event) => { this.minVolume = (e.target as HTMLInputElement).value; this.defaultsSaved = false; }} /> dBFS</label>
      <small class="dim">${t("defaultsVolumeHelp")}</small>
      <label class="row"><input type="checkbox" name="clips_allowed" .checked=${this.clipsAllowed}
        @change=${(e: Event) => { this.clipsAllowed = (e.target as HTMLInputElement).checked; this.defaultsSaved = false; }} /> ${t("defaultsClips")}</label>
      <label class="row">${t("defaultsMaxDays")} <input type="number" name="max_days" min="0" step="1" .value=${this.maxDays}
        @input=${(e: Event) => { this.maxDays = (e.target as HTMLInputElement).value; this.defaultsSaved = false; }} /> ${t("settingsDays")}</label>
      <small class="dim">${t("defaultsMaxDaysHelp")}</small>
      ${this.defaultsError ? html`<p class="note error">${this.defaultsError}</p>` : nothing}
      <div class="buttons"><button class="primary" data-action="save-defaults" ?disabled=${this.busy} @click=${() => void this.saveDefaults()}>${t("storageSave")}</button>
        ${this.defaultsSaved ? html`<span class="ok" role="status" data-defaults-saved>${t("storageSaved")}</span>` : nothing}</div>
    </section>`;
  }

  private home() {
    const t = this.t, st = this.structure;
    const lang = this.language.startsWith("fr") ? "fr" : "en";
    const ready = st?.origin === "home_structure";
    const msg = ready ? t("hsSettingsReady", { n: st!.links.length }) : st?.status === "not_installed" ? t("hsSettingsMissing") : st?.status === "not_configured" ? t("hsSettingsSetup") : t("hsSettingsEmpty");
    return html`<section class="card" data-section="home"><h2>${t("hsSettingsTitle")}</h2>
      <p class="dim">${t("hsSettingsWhy")}</p><p data-hs-status>${msg}</p>
      <div class="buttons">
        ${ready ? html`<a class="btn" data-action="hs-open" href="/config/integrations/integration/home_structure">${t("hsOpenConfig")}</a>`
          : st?.status === "not_installed" ? html`<a class="btn primary" data-action="hs-github" href=${st.url} target="_blank" rel="noopener">${t("hsInstallLink")}</a>`
          : html`<a class="btn primary" data-action="hs-add" href="/config/integrations/dashboard/add?domain=home_structure">${t("hsAdd")}</a>`}
        <a class="btn" href=${`${DOCS}/home-structure.${lang}.md`} target="_blank" rel="noreferrer noopener">${t("hsDoc")}</a></div></section>`;
  }

  private esp() {
    const t = this.t;
    return html`<section class="card" data-section="esp"><h2>${t("espSettingsTitle")}</h2>
      ${this.ignored.length === 0 ? html`<p class="dim" data-esp-none>${t("espSettingsNone")}</p>`
        : html`<p class="dim">${t("espSettingsHelp")}</p>${this.ignored.map((d) => html`<div class="espdev" data-esp-device=${d.url}>
          <span><strong>${d.name}</strong> <span class="dim">${d.url}</span></span>
          <button data-action="esp-unignore" @click=${() => void this.unignore(d)}>${t("espUnignore")}</button></div>`)}`}
    </section>`;
  }

  render() {
    const t = this.t;
    return html`<p class="dim intro">${t("settingsIntro")}</p>
      ${this.connection()}
      <section data-section="storage"><sound-recognition-storage .api=${this.api} .t=${t} .language=${this.language}></sound-recognition-storage></section>
      ${this.defaults()}${this.home()}${this.esp()}`;
  }

  static styles = css`
    .card { border: 1px solid var(--divider-color); border-radius: 12px; padding: 10px 14px; margin-bottom: 14px; background: var(--card-background-color); }
    h2 { font-size: 1.05rem; font-weight: 500; margin: 4px 0 8px; } h3 { font-size: 1rem; font-weight: 500; margin: 14px 0 4px; } p { margin: 8px 0; }
    .dim { color: var(--secondary-text-color); } small { display: block; margin: 0 0 8px; } .intro { margin-top: 0; }
    .row { display: flex; align-items: center; gap: 8px; margin: 10px 0 2px; flex-wrap: wrap; }
    input[type=number] { font: inherit; width: 90px; padding: 6px 8px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--primary-background-color); color: var(--primary-text-color); }
    .buttons { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-top: 8px; }
    button, .btn { font: inherit; padding: 6px 14px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); cursor: pointer; text-decoration: none; }
    .primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: transparent; }
    .danger { background: var(--error-color, #db4437); color: #fff; border-color: transparent; }
    .ok { color: var(--success-color, #43a047); } .note.error { color: var(--error-color, #db4437); }
    .confirm { border: 1px solid var(--warning-color, #ffa600); border-radius: 8px; padding: 6px 12px; margin: 8px 0; }
    .espdev { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; min-height: 34px; }
  `;
}
if (!customElements.get("sound-recognition-settings")) customElements.define("sound-recognition-settings", SettingsView);
