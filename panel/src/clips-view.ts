import { LitElement, css, html } from "lit";
import { property, state } from "lit/decorators.js";
import type { PanelApi } from "./api";
import type { T } from "./i18n";
import type { Catalog, Overview, SoundEvent } from "./types";
import { relativeTime } from "./util";

export class ClipsView extends LitElement {
  @property({ attribute: false }) api!: PanelApi;
  @property({ attribute: false }) t!: T;
  @property({ attribute: false }) language = "en";
  @state() private events: SoundEvent[] = [];
  @state() private names = new Map<string, string>();
  @state() private sources = new Map<string, string>();
  @state() private source = "";
  @state() private mid = "";
  @state() private ready = false;
  @state() private loadError = false;

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
  }

  private async load(): Promise<void> {
    try {
      const [events, cat, ov] = await Promise.all([this.api.events(500), this.api.catalog(), this.api.overview()]);
      this.events = events.filter((e) => !!e.clip_url);
      this.names = new Map((cat as Catalog).classes.map((c) => [c.mid, c.name]));
      this.sources = new Map((ov as Overview).sources.map((s) => [s.id, s.name]));
      this.loadError = false;
    } catch {
      this.loadError = true;
    }
    this.ready = true;
  }

  private label(e: SoundEvent): string {
    return e.name ?? this.names.get(e.mid) ?? e.class ?? e.mid;
  }

  render() {
    const t = this.t;
    if (this.loadError) return html`<p class="note error">${t("unreachable")}</p>`;
    if (!this.ready) return html`<p class="note">${t("loading")}</p>`;
    const sounds = [...new Map(this.events.map((e) => [e.mid, this.label(e)])).entries()].sort((a, b) => a[1].localeCompare(b[1], this.language));
    const list = this.events.filter((e) => (!this.source || e.source === this.source) && (!this.mid || e.mid === this.mid));
    const date = new Intl.DateTimeFormat(this.language, { dateStyle: "medium", timeStyle: "short" });
    return html`
      <div class="filters">
        <select name="source" aria-label=${t("allSources")} @change=${(e: Event) => (this.source = (e.target as HTMLSelectElement).value)}>
          <option value="">${t("allSources")}</option>${[...this.sources].map(([id, n]) => html`<option value=${id}>${n}</option>`)}</select>
        <select name="sound" aria-label=${t("allSounds")} @change=${(e: Event) => (this.mid = (e.target as HTMLSelectElement).value)}>
          <option value="">${t("allSounds")}</option>${sounds.map(([m, n]) => html`<option value=${m}>${n}</option>`)}</select>
        <button data-action="refresh" @click=${() => void this.load()}>${t("refresh")}</button>
      </div>
      ${list.length === 0 ? html`<p class="note">${t("noClips")}</p>` : html`<ul class="list">${list.map((e) => html`
        <li data-event=${e.id}>
          <div class="what"><strong>${this.label(e)}</strong>
            <span class="dim">${this.sources.get(e.source) ?? e.source} · ${date.format(new Date(e.ts * 1000))} (${relativeTime(e.ts, this.language, t)}) · ${Math.round(e.score * 100)}%</span>
            ${e.clip_expires ? html`<span class="dim">${t("keptUntil", { d: date.format(new Date(e.clip_expires)) })}</span>` : ""}</div>
          <audio controls preload="none" src=${e.clip_url!} aria-label=${t("play")}></audio>
        </li>`)}</ul>`}`;
  }

  static styles = css`
    :host { display: block; }
    .note { color: var(--secondary-text-color); } .note.error { color: var(--error-color, #db4437); } .dim { color: var(--secondary-text-color); font-size: 0.85rem; }
    .filters { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 14px; }
    select { font: inherit; padding: 9px 10px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--primary-background-color); color: var(--primary-text-color); min-width: 0; }
    button { font: inherit; cursor: pointer; padding: 8px 14px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); }
    .list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px; }
    .list li { display: grid; grid-template-columns: minmax(0, 1fr) minmax(220px, 360px); gap: 8px 14px; align-items: center; padding: 10px 14px; background: var(--card-background-color); border: 1px solid var(--divider-color); border-radius: 12px; }
    .what { display: flex; flex-direction: column; min-width: 0; } audio { width: 100%; height: 36px; }
    @media (max-width: 600px) { .list li { grid-template-columns: 1fr; } }
  `;
}
customElements.define("sound-recognition-clips", ClipsView);
