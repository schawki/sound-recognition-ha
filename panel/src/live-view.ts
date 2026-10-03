import { LitElement, css, html, nothing } from "lit";
import { property, state } from "lit/decorators.js";
import type { PanelApi } from "./api";
import type { T } from "./i18n";
import { relativeTime } from "./util";
import type { Advice, Catalog, LiveMessage, SoundEvent, SourceStatus } from "./types";

const MIN_DB = -90;

export class LiveView extends LitElement {
  @property({ attribute: false }) api!: PanelApi;
  @property({ attribute: false }) t!: T;
  @property({ attribute: false }) language = "en";
  @state() private sources: SourceStatus[] = [];
  @state() private events: SoundEvent[] = [];
  @state() private advice: Advice[] = [];
  @state() private names = new Map<string, string>();
  @state() private error: "unreachable" | "not_loaded" | null = null;
  @state() private ready = false;
  private unsub?: () => void;
  private timer?: number;
  private closed = false;

  connectedCallback(): void {
    super.connectedCallback();
    this.closed = false;
    void this.start();
    this.timer = window.setInterval(() => this.requestUpdate(), 15000); // relative times
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this.closed = true;
    this.unsub?.();
    window.clearInterval(this.timer);
  }

  private async start(): Promise<void> {
    try {
      const [ov, cat, events] = await Promise.all([this.api.overview(), this.api.catalog(), this.api.events(50)]);
      this.sources = ov.sources;
      this.advice = ov.warnings;
      this.names = new Map((cat as Catalog).classes.map((c) => [c.mid, c.name]));
      this.events = events;
      this.error = null;
      this.ready = true;
      const unsub = await this.api.subscribe((m) => this.onMessage(m));
      if (this.closed) unsub(); else this.unsub = unsub;
    } catch (err) {
      const code = (err as { code?: string }).code;
      this.error = code === "not_loaded" ? "not_loaded" : "unreachable";
      this.ready = true;
      if (this.error === "unreachable" && !this.closed) window.setTimeout(() => void this.start(), 10000);
    }
  }

  private onMessage(m: LiveMessage): void {
    switch (m.type) {
      case "hello":
      case "status":
        this.sources = m.sources;
        break;
      case "active":
        this.sources = this.sources.map((s) => (s.id === m.source ? { ...s, active_classes: m.active_classes } : s));
        break;
      case "source_state":
        this.sources = this.sources.map((s) => (s.id === m.source ? { ...s, connected: m.state === "connected", error: m.error ?? null } : s));
        break;
      case "detection":
        this.events = [{ id: m.id, ts: Date.parse(m.detected_at) / 1000, source: m.source, mid: m.mid, name: m.name, class: m.class, score: m.score, duration_s: m.duration_s }, ...this.events].slice(0, 100);
        break;
      case "clip_ready":
        this.events = this.events.map((e) => (e.id === m.id ? { ...e, clip: m.clip, clip_url: m.clip_url } : e));
        break;
    }
  }

  private classLabel(mid: string, fallback?: string): string {
    return this.names.get(mid) ?? fallback ?? mid;
  }

  private sourceName(id: string): string {
    return this.sources.find((s) => s.id === id)?.name ?? id;
  }

  private relative(ts: number): string {
    return relativeTime(ts, this.language, this.t);
  }

  private status(s: SourceStatus): { key: "connected" | "connecting" | "disconnected" | "disabled"; cls: string } {
    if (!s.enabled) return { key: "disabled", cls: "off" };
    if (s.connected) return { key: "connected", cls: "ok" };
    return s.error === "starting" ? { key: "connecting", cls: "wait" } : { key: "disconnected", cls: "bad" };
  }

  render() {
    const t = this.t;
    if (!this.ready) return html`<p class="note">${t("loading")}</p>`;
    if (this.error) return html`<p class="note error">${t(this.error === "not_loaded" ? "notLoaded" : "unreachable")}</p>`;
    const urgent = this.advice.filter((a) => a.level !== "info").length;
    return html`
      ${urgent ? html`<div class="banner">${urgent === 1 ? t("adviceBannerOne") : t("adviceBanner", { n: urgent })}</div>` : nothing}
      <h2>${t("sources")}</h2>
      ${this.sources.length === 0 ? html`<p class="note">${t("noSources")}</p>` : html`<div class="grid">${this.sources.map((s) => this.sourceCard(s))}</div>`}
      <h2>${t("recent")}</h2>
      ${this.events.length === 0 ? html`<p class="note">${t("noEvents")}</p>` : html`<ul class="events">${this.events.map((e) => this.eventRow(e))}</ul>`}
    `;
  }

  private sourceCard(s: SourceStatus) {
    const t = this.t;
    const st = this.status(s);
    const pct = s.level_dbfs == null ? 0 : Math.max(0, Math.min(100, ((s.level_dbfs - MIN_DB) / -MIN_DB) * 100));
    return html`
      <section class="card" data-source=${s.id}>
        <header>
          <strong>${s.name}</strong>
          <span class="chip ${st.cls}" title=${s.error && s.error !== "starting" ? s.error : ""}>${t(st.key)}</span>
        </header>
        <div class="level" role="meter" aria-label=${t("level")} aria-valuemin=${MIN_DB} aria-valuemax="0" aria-valuenow=${s.level_dbfs ?? MIN_DB}>
          <div class="bar ${s.below_gate ? "gated" : ""}" style="width:${pct}%"></div>
        </div>
        <div class="meta">
          <span>${s.level_dbfs == null ? "—" : `${s.level_dbfs.toFixed(0)} dBFS`}</span>
          ${s.below_gate ? html`<span class="dim">${t("belowGate")}</span>` : nothing}
        </div>
        <div class="active">
          ${s.active_classes.length
            ? html`<span class="dim">${t("activeNow")}</span> ${s.active_classes.map((m) => html`<span class="chip hot">${this.classLabel(m)}</span>`)}`
            : html`<span class="dim">${t("listening")}</span>`}
        </div>
      </section>`;
  }

  private eventRow(e: SoundEvent) {
    const t = this.t;
    return html`
      <li data-event=${e.id}>
        <div class="what"><strong>${e.name ?? this.classLabel(e.mid, e.class)}</strong><span class="dim">${this.sourceName(e.source)} · ${this.relative(e.ts)}</span></div>
        <span class="score" title=${t("score")}>${Math.round(e.score * 100)}%</span>
        ${e.clip_url ? html`<audio controls preload="none" src=${e.clip_url} aria-label=${t("play")}></audio>` : html`<span class="dim">${t("noClip")}</span>`}
      </li>`;
  }

  static styles = css`
    :host { display: block; }
    h2 { font-size: 1.05rem; font-weight: 500; margin: 24px 0 12px; color: var(--primary-text-color); }
    h2:first-child { margin-top: 0; }
    .note { color: var(--secondary-text-color); }
    .note.error { color: var(--error-color, #db4437); }
    .dim { color: var(--secondary-text-color); font-size: 0.85rem; }
    .banner { background: var(--warning-color, #ffa600); color: #000; padding: 10px 14px; border-radius: 10px; margin-bottom: 16px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
    .card { background: var(--card-background-color, #fff); border-radius: var(--ha-card-border-radius, 12px); box-shadow: var(--ha-card-box-shadow, none); border: 1px solid var(--divider-color); padding: 16px; display: flex; flex-direction: column; gap: 10px; }
    .card header { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
    .chip { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 0.8rem; background: var(--secondary-background-color); color: var(--primary-text-color); margin: 2px 4px 2px 0; }
    .chip.ok { background: color-mix(in srgb, var(--success-color, #43a047) 22%, transparent); }
    .chip.bad { background: color-mix(in srgb, var(--error-color, #db4437) 22%, transparent); }
    .chip.wait, .chip.off { background: var(--secondary-background-color); color: var(--secondary-text-color); }
    .chip.hot { background: var(--primary-color); color: var(--text-primary-color, #fff); }
    .level { height: 8px; border-radius: 4px; background: var(--secondary-background-color); overflow: hidden; }
    .bar { height: 100%; background: var(--primary-color); transition: width 0.4s ease; }
    .bar.gated { background: var(--disabled-text-color, #9e9e9e); }
    .meta { display: flex; justify-content: space-between; font-size: 0.85rem; }
    .events { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
    .events li { display: grid; grid-template-columns: 1fr auto; gap: 6px 12px; align-items: center; padding: 10px 14px; background: var(--card-background-color, #fff); border: 1px solid var(--divider-color); border-radius: 12px; }
    .what { display: flex; flex-direction: column; min-width: 0; }
    .score { font-variant-numeric: tabular-nums; color: var(--secondary-text-color); }
    audio { grid-column: 1 / -1; width: 100%; height: 34px; }
    @media (prefers-reduced-motion: reduce) { .bar { transition: none; } }
  `;
}
customElements.define("sound-recognition-live", LiveView);
