import { LitElement, css, html, nothing } from "lit";
import { property, state } from "lit/decorators.js";
import type { PanelApi } from "./api";
import { clone, getBlock, putBlock } from "./classes";
import type { Key, T } from "./i18n";
import { resolveClass, type ByKey } from "./resolve";
import { cellsToWindows, hoursPerWeek, windowsToCells } from "./schedule";
import type { Advice, Catalog, CatalogClass, ClassBlock, Resolved, ServiceConfig, SourceCfg } from "./types";
import "./schedule-grid";

type NumField = "threshold" | "min_duration_s" | "cooldown_s" | "pre_roll_s" | "post_roll_s" | "clip_retention_days" | "min_volume_dbfs";
const FIELDS: { key: NumField; min: number; max: number; step: number; unit: string }[] = [
  { key: "threshold", min: 0.05, max: 0.99, step: 0.01, unit: "" },
  { key: "min_duration_s", min: 0, max: 600, step: 0.5, unit: "s" },
  { key: "cooldown_s", min: 0, max: 86400, step: 1, unit: "s" },
  { key: "pre_roll_s", min: 0, max: 120, step: 0.5, unit: "s" },
  { key: "post_roll_s", min: 0, max: 120, step: 0.5, unit: "s" },
  { key: "clip_retention_days", min: 0, max: 3650, step: 1, unit: "d" },
  { key: "min_volume_dbfs", min: -90, max: 0, step: 1, unit: "dBFS" },
];
type EnabledChoice = "inherit" | "on" | "off";
type SchedChoice = "inherit" | "always" | "times";

/** Provenance code of the service -> translation key. `enabled` has its own meaning for "source". */
export function provKey(code: string, field: string): Key {
  if (field === "enabled" && code === "source") return "prov_source_off";
  return `prov_${code.replace("+source_offset", "_offset")}` as Key;
}

/** Settings of one sound in one scope (all sources, or one source). Works on a copy; `apply` returns the edited configuration. */
export class ClassDetail extends LitElement {
  @property({ attribute: false }) api!: PanelApi;
  @property({ attribute: false }) t!: T;
  @property({ attribute: false }) language = "en";
  @property({ attribute: false }) cls!: CatalogClass;
  @property({ attribute: false }) catalog!: Catalog;
  @property({ attribute: false }) cfg!: ServiceConfig;
  @property({ attribute: false }) byKey!: ByKey;
  @property() scope: string | null = null;
  @state() private values: Record<NumField, string> = {} as Record<NumField, string>;
  @state() private enabled: EnabledChoice = "inherit";
  @state() private sched: SchedChoice = "inherit";
  @state() private cells: boolean[] = new Array(336).fill(false);
  @state() private warnings: Advice[] = [];
  private timer?: number;
  private seq = 0;

  protected willUpdate(changed: Map<string, unknown>): void {
    if (changed.has("cls") || changed.has("scope")) this.loadForm();
  }

  private loadForm(): void {
    const b = getBlock(this.cfg, this.scope, this.cls, this.byKey);
    const values = {} as Record<NumField, string>;
    for (const f of FIELDS) values[f.key] = b[f.key] == null ? "" : String(b[f.key]);
    this.values = values;
    this.enabled = b.enabled === undefined ? "inherit" : b.enabled ? "on" : "off";
    this.sched = !b.schedule ? "inherit" : b.schedule.mode === "continuous" ? "always" : "times";
    this.cells = windowsToCells(b.schedule?.windows ?? []);
    this.queueWarnings();
  }

  // ------------------------------------------------------------------ candidate configuration
  private block(skip?: NumField | "schedule" | "enabled"): ClassBlock {
    const b: ClassBlock = { ...getBlock(this.cfg, this.scope, this.cls, this.byKey) };
    for (const f of FIELDS) {
      const raw = this.values[f.key]?.trim();
      const n = parseFloat(raw);
      if (f.key === skip || raw === "" || !Number.isFinite(n)) delete b[f.key]; else (b[f.key] as number) = n;
    }
    if (skip !== "enabled") {
      if (this.enabled === "inherit") delete b.enabled; else b.enabled = this.enabled === "on";
    } else delete b.enabled;
    if (skip === "schedule" || this.sched === "inherit") delete b.schedule;
    else if (this.sched === "always") b.schedule = { mode: "continuous" };
    else {
      const w = cellsToWindows(this.cells);
      if (w && w.length) b.schedule = { mode: "scheduled", windows: w }; else if (w === null) b.schedule = { mode: "continuous" }; else delete b.schedule;
    }
    return b;
  }

  private candidate(skip?: NumField | "schedule" | "enabled"): ServiceConfig {
    const c = clone(this.cfg);
    putBlock(c, this.scope, this.cls, this.byKey, this.block(skip));
    return c;
  }

  private get sources(): SourceCfg[] {
    return this.cfg.sources ?? [];
  }

  private resolveFor(cfg: ServiceConfig, src: SourceCfg): Resolved {
    return resolveClass(cfg, (cfg.sources ?? []).find((s) => s.id === src.id) ?? src, this.cls, this.byKey);
  }

  /** Value that would apply if this field were left empty (shown as placeholder). */
  private inherited(field: NumField): string {
    const src = this.scope ? this.sources.find((s) => s.id === this.scope) : this.sources[0];
    if (!src) return String(this.cls.suggestions[field as keyof typeof this.cls.suggestions] ?? "");
    const r = this.resolveFor(this.candidate(field), src);
    const v = r[field];
    // at "all sources" level the source offset is not part of the inherited value of the threshold
    if (!this.scope && field === "threshold") return String(this.cls.suggestions.threshold);
    return v == null ? "" : String(v);
  }

  // ------------------------------------------------------------------ advice from the service (dry run)
  private queueWarnings(): void {
    window.clearTimeout(this.timer);
    this.timer = window.setTimeout(() => void this.fetchWarnings(), 350);
  }

  private async fetchWarnings(): Promise<void> {
    const my = ++this.seq;
    try {
      const r = await this.api.validate(this.candidate());
      if (my !== this.seq) return;
      this.warnings = r.errors.length ? [] : r.warnings.filter((w) => w.classes.includes(this.cls.mid) && (this.scope === null || w.source === this.scope));
    } catch {
      /* advice is a courtesy; saving reports real problems */
    }
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    window.clearTimeout(this.timer);
  }

  private setValue(key: NumField, v: string): void {
    this.values = { ...this.values, [key]: v };
    this.queueWarnings();
  }

  private fire(name: string, detail?: unknown): void {
    this.dispatchEvent(new CustomEvent(name, { detail, bubbles: true, composed: true }));
  }

  // ------------------------------------------------------------------ rendering
  private fmt(f: NumField, v: number | null | undefined): string {
    if (v == null) return "—";
    return f === "min_volume_dbfs" ? `${v} dBFS` : f === "threshold" ? String(v) : `${v} ${FIELDS.find((x) => x.key === f)!.unit}`;
  }

  render() {
    const t = this.t;
    const c = this.cls;
    const cand = this.candidate();
    const fp = c.false_positives;
    const forbidden = c.clip_forbidden;
    const scopedSource = this.scope ? this.sources.find((s) => s.id === this.scope) : undefined;
    const applied = scopedSource ? this.resolveFor(cand, scopedSource) : undefined;
    return html`
      <div class="head">
        <button @click=${() => this.fire("close")}>← ${t("back")}</button>
        <h2>${c.name}</h2>
        <span class="dim">${this.catalog.categories[c.category] ?? c.category} · ${t(`interest_${c.interest}` as Key)}${c.privacy !== "normal" ? ` · ${t(`privacy_${c.privacy}` as Key)}` : ""}</span>
        <span class="dim">${scopedSource ? scopedSource.name ?? scopedSource.id : t("scopeAll")}</span>
      </div>
      ${c.note_text ? html`<p class="note">${c.note_text}</p>` : nothing}
      <p class="dim">${t("falsePositives", { level: t(`fp_${fp.level}` as Key), causes: fp.cause_labels.join(", ") || "—" })}</p>
      ${forbidden ? html`<p class="warn">${t("clipForbidden")}</p>` : nothing}

      <div class="form">
        <label>${t("enabledChoice")}
          <select name="enabled" .value=${this.enabled} @change=${(e: Event) => { this.enabled = (e.target as HTMLSelectElement).value as EnabledChoice; this.queueWarnings(); }}>
            <option value="inherit" ?selected=${this.enabled === "inherit"}>${t("choiceInherit")}</option>
            <option value="on" ?selected=${this.enabled === "on"}>${t("choiceOn")}</option>
            <option value="off" ?selected=${this.enabled === "off"}>${t("choiceOff")}</option>
          </select></label>
        ${FIELDS.map((f) => html`
          <label>${t(`f_${f.key}` as Key)}
            <input name=${f.key} type="number" min=${f.min} max=${f.max} step=${f.step} .value=${this.values[f.key] ?? ""} placeholder=${this.inherited(f.key)}
              @input=${(e: Event) => this.setValue(f.key, (e.target as HTMLInputElement).value)} />
            <small>${this.catalog.setting_help[f.key] ? this.catalog.setting_help[f.key] : ""}
              ${applied ? html`<span class="applied" data-applied=${f.key}>${t("applied")}: ${this.fmt(f.key, applied[f.key] as number | null)} — ${t(provKey(applied.provenance[f.key], f.key))}</span>` : nothing}</small>
          </label>`)}
      </div>
      <small class="dim">${t("emptyInherits")}. ${t("suggested")}: ${t("f_threshold")} ${c.suggestions.threshold} · ${c.suggestions.min_duration_s} s · ${c.suggestions.cooldown_s} s · ${c.suggestions.clip_retention_days} d</small>

      <fieldset>
        <legend>${t("scheduleChoice")}</legend>
        ${(["inherit", "always", "times"] as const).map((k) => html`<label class="inline"><input type="radio" name="sched" value=${k} .checked=${this.sched === k} @change=${() => { this.sched = k; this.queueWarnings(); }} />${t(k === "inherit" ? "schedInherit" : k === "always" ? "schedAlways" : "schedTimes")}</label>`)}
        ${this.sched === "times" ? html`
          <sr-schedule-grid .cells=${this.cells} .language=${this.language} @cells-changed=${(e: CustomEvent<boolean[]>) => { this.cells = e.detail; this.queueWarnings(); }}></sr-schedule-grid>
          <span class="dim">${t("hoursPerWeek", { h: hoursPerWeek(this.cells) })}</span>` : nothing}
      </fieldset>

      ${!scopedSource && this.sources.length ? html`
        <h3>${t("resultPerSource")}</h3>
        <table><thead><tr><th>${t("colSource")}</th><th>${t("colEnabled")}</th><th>${t("f_threshold")}</th><th>${t("f_min_volume_dbfs")}</th><th>${t("f_clip_retention_days")}</th></tr></thead>
        <tbody>${this.sources.map((s) => { const r = this.resolveFor(cand, s); return html`<tr data-row=${s.id}><td>${s.name ?? s.id}</td><td>${r.enabled ? t("yes") : t("no")}</td><td>${r.threshold}</td><td>${this.fmt("min_volume_dbfs", r.min_volume_dbfs)}</td><td>${r.clip_retention_days}</td></tr>`; })}</tbody></table>` : nothing}

      <h3>${t("advice")}</h3>
      ${this.warnings.length ? html`<ul class="advice">${this.warnings.map((w) => html`<li class=${w.level}>${w.message}</li>`)}</ul>` : html`<p class="dim">${t("noAdvice")}</p>`}

      <div class="buttons">
        <button @click=${() => this.fire("close")}>${t("cancel")}</button>
        <button class="primary" data-action="apply" @click=${() => this.fire("apply", this.candidate())}>${t("apply")}</button>
      </div>`;
  }

  static styles = css`
    :host { display: block; background: var(--card-background-color); border: 1px solid var(--divider-color); border-radius: 12px; padding: 16px; }
    .head { display: flex; flex-wrap: wrap; gap: 4px 12px; align-items: center; margin-bottom: 8px; }
    h2 { margin: 0; font-size: 1.15rem; font-weight: 500; flex: 1 1 auto; } h3 { font-size: 0.95rem; font-weight: 500; margin: 18px 0 8px; }
    .dim, small { color: var(--secondary-text-color); font-size: 0.85rem; }
    .note { margin: 6px 0; } .warn { background: color-mix(in srgb, var(--warning-color, #ffa600) 22%, var(--card-background-color)); padding: 8px 12px; border-radius: 8px; }
    .form { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 14px; margin: 14px 0 6px; }
    label { display: flex; flex-direction: column; gap: 4px; font-size: 0.9rem; } label.inline { flex-direction: row; align-items: center; gap: 8px; }
    input:not([type=radio]), select { font: inherit; padding: 9px 10px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--primary-background-color); color: var(--primary-text-color); min-width: 0; }
    .applied { display: block; color: var(--primary-color); }
    fieldset { border: 1px solid var(--divider-color); border-radius: 10px; margin: 14px 0; padding: 10px 14px 14px; display: flex; flex-direction: column; gap: 8px; min-width: 0; }
    table { border-collapse: collapse; width: 100%; font-size: 0.9rem; } th, td { text-align: left; padding: 6px 10px; border-bottom: 1px solid var(--divider-color); } th { color: var(--secondary-text-color); font-weight: 500; }
    .advice { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 6px; }
    .advice li { padding: 8px 12px; border-radius: 8px; background: var(--secondary-background-color); }
    .advice li.warning { background: color-mix(in srgb, var(--warning-color, #ffa600) 22%, var(--card-background-color)); }
    .advice li.danger { background: color-mix(in srgb, var(--error-color, #db4437) 20%, var(--card-background-color)); }
    button { font: inherit; cursor: pointer; padding: 8px 14px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); }
    button.primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: transparent; }
    .buttons { display: flex; justify-content: flex-end; gap: 10px; margin-top: 16px; }
  `;
}
if (!customElements.get("sr-class-detail")) customElements.define("sr-class-detail", ClassDetail);
