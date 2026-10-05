import { LitElement, css, html, nothing } from "lit";
import { property, state } from "lit/decorators.js";
import type { PanelApi } from "./api";
import type { T } from "./i18n";
import { applyAndSave } from "./patch";
import type { Advice, Catalog, LiveMessage, Recommendation, ServiceConfig, SourceStatus, Stats } from "./types";

interface Entry { key: number; ts: number; kind: "detection" | "hidden" | "context"; text: string }

const TIMELINE_MAX = 40;
const REFRESH_MS = 30000;

/** One place for the administrator: what each source hears and how it reacts now, the numbers of the day, the advice and the recommendations. */
export class InsightsView extends LitElement {
  @property({ attribute: false }) api!: PanelApi;
  @property({ attribute: false }) t!: T;
  @property({ attribute: false }) language = "en";
  @state() private sources: SourceStatus[] = [];
  @state() private config: ServiceConfig = {};
  @state() private catalog: Catalog | null = null;
  @state() private stats: Stats | null = null;
  @state() private recs: Recommendation[] = [];
  @state() private advice: Advice[] = [];
  @state() private timeline: Entry[] = [];
  @state() private ready = false;
  @state() private error = false;
  @state() private applying: string | null = null;
  @state() private message = "";
  @state() private errors: string[] = [];
  private unsub?: () => void;
  private timer?: number;
  private soon?: number;
  private closed = false;
  private seq = 0;

  connectedCallback(): void {
    super.connectedCallback();
    this.closed = false;
    void this.start();
    this.timer = window.setInterval(() => void this.refresh(), REFRESH_MS);
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this.closed = true;
    this.unsub?.();
    window.clearInterval(this.timer);
    window.clearTimeout(this.soon);
  }

  private async start(): Promise<void> {
    try {
      this.catalog = await this.api.catalog();
      await this.refresh();
      const unsub = await this.api.subscribe((m) => this.onMessage(m));
      if (this.closed) unsub(); else this.unsub = unsub;
    } catch {
      this.error = true;
      this.ready = true;
      if (!this.closed) window.setTimeout(() => void this.start(), 10000);
    }
  }

  private async refresh(): Promise<void> {
    try {
      const [ov, stats, recs] = await Promise.all([this.api.overview(), this.api.stats(24), this.api.recommendations()]);
      this.sources = ov.sources;
      this.advice = ov.warnings;
      this.config = ov.config as ServiceConfig;
      this.stats = stats;
      this.recs = recs;
      this.error = false;
      this.ready = true;
    } catch {
      if (!this.ready) throw new Error("unreachable");
    }
  }

  private refreshSoon(): void {
    window.clearTimeout(this.soon);
    this.soon = window.setTimeout(() => void this.refresh(), 1500);
  }

  // ------------------------------------------------------------------ live
  private name(mid: string, fallback?: string): string {
    return this.catalog?.classes.find((c) => c.mid === mid)?.name ?? fallback ?? mid;
  }

  private sourceName(id: string): string {
    return this.sources.find((s) => s.id === id)?.name ?? id;
  }

  private push(kind: Entry["kind"], text: string, ts = Date.now() / 1000): void {
    this.timeline = [{ key: ++this.seq, ts, kind, text }, ...this.timeline].slice(0, TIMELINE_MAX);
  }

  private onMessage(m: LiveMessage): void {
    const t = this.t;
    switch (m.type) {
      case "hello":
      case "status":
        this.sources = m.sources;
        break;
      case "source_state":
        this.sources = this.sources.map((s) => (s.id === m.source ? { ...s, connected: m.state === "connected", error: m.error ?? null } : s));
        break;
      case "context": {
        const prev = this.sources.find((s) => s.id === m.source);
        const was = prev?.active_contexts ?? [], now = m.active_contexts;
        const s = this.sourceName(m.source);
        if (now.join() !== was.join()) {
          if (now.length) this.push("context", t("evContext", { s, c: now.map((x) => this.name(x)).join(", ") }));
          else if (was.length) this.push("context", t("evContextEnd", { s }));
        }
        if (m.adaptive_offset > 0 && !((prev?.adaptive_offset ?? 0) > 0)) this.push("context", t("evAmbient", { s, v: `+${m.adaptive_offset.toFixed(2)}` }));
        this.sources = this.sources.map((x) => (x.id === m.source ? { ...x, active_contexts: m.active_contexts, ambient_dbfs: m.ambient_dbfs, baseline_dbfs: m.baseline_dbfs, adaptive_enabled: m.adaptive_enabled, adaptive_offset: m.adaptive_offset, external_offset: m.external_offset, external_reasons: m.external_reasons, external_detail: m.external_detail } : x));
        break;
      }
      case "detection":
        this.push("detection", t("evDetected", { c: m.name ?? this.name(m.mid, m.class), s: this.sourceName(m.source) }), Date.parse(m.detected_at) / 1000);
        this.refreshSoon();
        break;
      case "masked":
        this.push("hidden", t("evHidden", {
          c: m.name ?? this.name(m.mid, m.class), s: this.sourceName(m.source), score: m.score.toFixed(2), thr: m.threshold.toFixed(2),
          why: [...new Set(m.reasons)].map((r) => this.reason(r)).join(" + "),
        }), Date.parse(m.detected_at) / 1000);
        this.refreshSoon();
        break;
    }
  }

  // ------------------------------------------------------------------ actions
  private async apply(rec: Recommendation, index: number): Promise<void> {
    if (!rec.apply) return;
    const id = `${rec.rule}:${rec.source}:${index}`;
    this.applying = id;
    this.errors = [];
    this.message = "";
    try {
      const names = new Map((this.catalog?.classes ?? []).map((c) => [c.mid, c.audioset_name]));
      const errs = await applyAndSave(this.api, rec.apply, (mid) => names.get(mid));
      if (errs.length) this.errors = errs; else this.message = this.t("applied");
      await this.refresh();
    } catch (err) {
      this.errors = [(err as { message?: string }).message ?? String(err)];
    } finally {
      this.applying = null;
    }
  }

  // ------------------------------------------------------------------ rendering
  private inhibitors(): Set<string> {
    return new Set((this.catalog?.classes ?? []).flatMap((c) => c.inhibiting_contexts ?? []));
  }

  private reason(r: string): string {
    return this.t(r === "ambient" ? "insReasonAmbient" : r === "device" ? "insReasonDevice" : r === "shared" ? "insReasonShared" : "insReasonContext");
  }

  private raisedBy(s: SourceStatus): { total: number; reasons: string[] } {
    const boost = (this.config.analysis as { context_boost?: number } | undefined)?.context_boost ?? 0.15;
    const inh = this.inhibitors();
    const ctx = (s.active_contexts ?? []).some((m) => inh.has(m)) ? boost : 0;
    const amb = s.adaptive_enabled ? s.adaptive_offset ?? 0 : 0;
    const ext = s.external_offset ?? 0;
    const reasons = [ctx ? this.t("insReasonContext") : "", amb ? this.t("insReasonAmbient") : "", ...(ext ? [...new Set(s.external_reasons?.length ? s.external_reasons : ["device"])].map((r) => this.reason(r)) : [])].filter(Boolean);
    return { total: ctx + amb + ext, reasons };
  }

  render() {
    const t = this.t;
    if (!this.ready) return html`<p class="note">${t("loading")}</p>`;
    if (this.error) return html`<p class="note error">${t("unreachable")}</p>`;
    const urgent = this.advice.filter((a) => a.level !== "info");
    return html`
      <h2>${t("insNow")}</h2>
      ${this.sources.length === 0 ? html`<p class="note">${t("noSources")}</p>` : html`<div class="grid">${this.sources.filter((s) => s.enabled).map((s) => this.card(s))}</div>`}
      <h2>${t("insRecs")}</h2>
      ${this.message ? html`<p class="ok" role="status">${this.message}</p>` : nothing}
      ${this.errors.length ? html`<div class="errors" role="alert"><ul>${this.errors.map((e) => html`<li>${e}</li>`)}</ul></div>` : nothing}
      ${this.recs.length === 0 ? html`<p class="note">${t("insNoRecs")}</p>` : html`<ul class="recs">${this.recs.map((r, i) => this.rec(r, i))}</ul>`}
      <h2>${t("insStats")}</h2>
      ${this.renderStats()}
      <h2>${t("insAdvice")}</h2>
      ${urgent.length === 0 ? html`<p class="note">${t("insAdviceNone")}</p>` : html`<div class="advice" data-advice>
        <p>${urgent.length === 1 ? t("insAdviceOne") : t("insAdviceMore", { n: urgent.length })}</p>
        <ul>${urgent.slice(0, 3).map((a) => html`<li class=${a.level}><strong>${this.sourceName(a.source)}</strong> — ${a.message}</li>`)}</ul></div>`}
      <h2>${t("insTimeline")}</h2>
      ${this.timeline.length === 0 ? html`<p class="note">${t("insNoTimeline")}</p>` : html`<ul class="timeline">${this.timeline.map((e) => html`<li class=${e.kind} data-kind=${e.kind}>
        <time>${new Date(e.ts * 1000).toLocaleTimeString(this.language)}</time><span>${e.text}</span></li>`)}</ul>`}`;
  }

  private card(s: SourceStatus) {
    const t = this.t;
    const cfg = (this.config.sources ?? []).find((x) => x.id === s.id);
    const env = this.catalog?.environments.find((e) => e.id === cfg?.environment);
    const raised = this.raisedBy(s);
    const d = this.stats?.detections.by_source[s.id] ?? 0, h = this.stats?.masked.by_source[s.id] ?? 0, f = this.stats?.false.by_source[s.id] ?? 0;
    const ambient = s.ambient_dbfs == null ? "" : s.baseline_dbfs == null
      ? t("insAmbientLearning", { a: s.ambient_dbfs.toFixed(0) }) : t("insAmbient", { a: s.ambient_dbfs.toFixed(0), b: s.baseline_dbfs.toFixed(0) });
    return html`<section class="card" data-source=${s.id}>
      <header><strong>${s.name}</strong><span class="chip">${env ? t("insPlace", { p: env.name }) : t("insNoPlace")}</span></header>
      <div class="line">${s.level_dbfs == null ? "—" : `${s.level_dbfs.toFixed(0)} dBFS`}${ambient ? html` · <span class="dim" data-ambient>${ambient}</span>` : nothing}</div>
      <div class="line" data-contexts>${(s.active_contexts ?? []).length
        ? html`<span class="dim">${t("insCtxHeard", { c: "" })}</span>${(s.active_contexts ?? []).map((m) => html`<span class="chip hot">${this.name(m)}</span>`)}`
        : html`<span class="dim">${t("insCtxNone")}</span>`}</div>
      <div class="line" data-thresholds>${raised.total > 0
        ? html`<strong>${t("insRaised", { v: `+${raised.total.toFixed(2)}` })}</strong> <span class="dim">(${raised.reasons.join(" + ")})</span>`
        : html`<span class="dim">${s.adaptive_enabled ? t("insNormal") : `${t("insNormal")} · ${t("insAdaptiveOff")}`}</span>`}</div>
      ${(s.external_detail ?? []).length ? html`<div class="line dim" data-devices>${t("insDevicesLine", { d: (s.external_detail ?? []).slice(0, 3).map((d) => `${d.label} +${d.value.toFixed(2)}`).join(" ; ") })}</div>` : nothing}
      <div class="counts" data-counts><span>${t("statDetected")} <strong>${d}</strong></span><span>${t("statHidden")} <strong>${h}</strong></span><span>${t("statFalse")} <strong>${f}</strong></span></div>
    </section>`;
  }

  private rec(r: Recommendation, i: number) {
    const t = this.t;
    const id = `${r.rule}:${r.source}:${i}`;
    return html`<li class=${r.level} data-rule=${r.rule} data-source=${r.source}>
      <span>${r.message}</span>
      ${r.apply ? html`<button class="primary" data-action="apply" ?disabled=${this.applying !== null} @click=${() => void this.apply(r, i)}>${this.applying === id ? t("applying") : t("apply")}</button>` : nothing}
    </li>`;
  }

  private renderStats() {
    const t = this.t, st = this.stats;
    if (!st) return nothing;
    const det = st.detections.hourly, mk = st.masked.hourly;
    const max = Math.max(1, ...det.map((v, i) => v + (mk[i] ?? 0)));
    const total = st.detections.total + st.masked.total;
    const top = st.detections.by_class.slice(0, 5);
    return html`<div class="stats">
      <div class="tiles"><div class="tile"><strong data-stat="detected">${st.detections.total}</strong><span>${t("statDetected")}</span></div>
        <div class="tile"><strong data-stat="hidden">${st.masked.total}</strong><span>${t("statHidden")}</span></div>
        <div class="tile"><strong data-stat="false">${st.false.total}</strong><span>${t("statFalse")}</span></div></div>
      ${total === 0 ? html`<p class="note">${t("insNoStats")}</p>` : html`
        <div class="chart" role="img" aria-label=${t("statHourly")} data-chart>${det.map((v, i) => html`<div class="col" title=${`${v} / ${mk[i] ?? 0}`}>
          <div class="seg hid" style=${`height:${((mk[i] ?? 0) / max) * 100}%`}></div><div class="seg det" style=${`height:${(v / max) * 100}%`}></div></div>`)}</div>
        <div class="axis dim"><span>${t("statAgo", { h: det.length })}</span><span>${t("statHourly")}</span><span>${t("statNow")}</span></div>
        ${top.length ? html`<h3>${t("statTop")}</h3><ul class="top">${top.map((c) => html`<li><span>${this.name(c.mid, c.class)} <span class="dim">· ${this.sourceName(c.source)}</span></span><strong>${c.count}</strong></li>`)}</ul>` : nothing}`}
    </div>`;
  }

  static styles = css`
    :host { display: block; }
    h2 { font-size: 1.05rem; font-weight: 500; margin: 24px 0 12px; } h2:first-child { margin-top: 0; }
    h3 { font-size: 0.95rem; font-weight: 500; margin: 14px 0 6px; }
    .note { color: var(--secondary-text-color); } .note.error { color: var(--error-color, #db4437); }
    .dim { color: var(--secondary-text-color); font-size: 0.85rem; }
    .ok { color: var(--success-color, #43a047); }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); gap: 16px; }
    .card { background: var(--card-background-color, #fff); border-radius: var(--ha-card-border-radius, 12px); border: 1px solid var(--divider-color); padding: 16px; display: flex; flex-direction: column; gap: 8px; }
    .card header { display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; }
    .chip { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 0.8rem; background: var(--secondary-background-color); color: var(--primary-text-color); margin: 2px 4px 2px 0; }
    .chip.hot { background: var(--primary-color); color: var(--text-primary-color, #fff); }
    .counts { display: flex; gap: 14px; flex-wrap: wrap; font-size: 0.85rem; color: var(--secondary-text-color); }
    .counts strong { color: var(--primary-text-color); }
    .recs, .timeline, .top { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
    .recs li { display: flex; gap: 12px; align-items: center; justify-content: space-between; flex-wrap: wrap; padding: 10px 14px; background: var(--card-background-color); border: 1px solid var(--divider-color); border-left: 4px solid var(--primary-color); border-radius: 10px; }
    .recs li.warning { border-left-color: var(--warning-color, #ffa600); } .recs li.danger { border-left-color: var(--error-color, #db4437); }
    .recs li span { flex: 1 1 320px; }
    button { font: inherit; cursor: pointer; padding: 8px 14px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); }
    button.primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: transparent; } button:disabled { opacity: 0.6; cursor: default; }
    .errors { background: color-mix(in srgb, var(--error-color, #db4437) 15%, var(--card-background-color)); border-radius: 10px; padding: 10px 14px; margin-bottom: 12px; } .errors ul { margin: 0 0 0 18px; padding: 0; }
    .tiles { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 14px; }
    .tile { flex: 1 1 140px; display: flex; flex-direction: column; padding: 12px 16px; background: var(--card-background-color); border: 1px solid var(--divider-color); border-radius: 12px; }
    .tile strong { font-size: 1.6rem; font-variant-numeric: tabular-nums; } .tile span { color: var(--secondary-text-color); font-size: 0.85rem; }
    .chart { display: flex; align-items: flex-end; gap: 3px; height: 110px; padding: 6px; background: var(--card-background-color); border: 1px solid var(--divider-color); border-radius: 10px; }
    .col { flex: 1; height: 100%; display: flex; flex-direction: column; justify-content: flex-end; min-width: 0; }
    .seg.det { background: var(--primary-color); } .seg.hid { background: repeating-linear-gradient(45deg, var(--warning-color, #ffa600), var(--warning-color, #ffa600) 3px, transparent 3px, transparent 6px); }
    .axis { display: flex; justify-content: space-between; margin-top: 4px; }
    .top li { display: flex; justify-content: space-between; padding: 6px 12px; background: var(--card-background-color); border: 1px solid var(--divider-color); border-radius: 8px; }
    .advice { padding: 10px 14px; background: var(--card-background-color); border: 1px solid var(--divider-color); border-radius: 10px; } .advice p { margin: 0 0 6px; } .advice ul { margin: 0 0 0 18px; padding: 0; }
    .timeline li { display: flex; gap: 12px; padding: 6px 12px; background: var(--card-background-color); border: 1px solid var(--divider-color); border-radius: 8px; font-size: 0.9rem; }
    .timeline li.hidden { border-left: 4px solid var(--warning-color, #ffa600); } .timeline li.detection { border-left: 4px solid var(--primary-color); } .timeline li.context { border-left: 4px solid var(--secondary-text-color); }
    .timeline time { color: var(--secondary-text-color); font-variant-numeric: tabular-nums; flex: none; }
  `;
}
if (!customElements.get("sound-recognition-insights")) customElements.define("sound-recognition-insights", InsightsView);
