import { LitElement, css, html, nothing } from "lit";
import { property, state } from "lit/decorators.js";
import { repeat } from "lit/directives/repeat.js";
import type { PanelApi } from "./api";
import { adviceKey, effectiveLevel, entry } from "./advice";
import { clone } from "./classes";
import type { Key, T } from "./i18n";
import type { Advice, AdviceLevel, AdviceSetting, Catalog, ServiceConfig, SourceCfg } from "./types";

const LEVELS: AdviceLevel[] = ["default", "info", "warning", "danger", "ignore"];
const ORDER = { danger: 0, warning: 1, info: 2 } as const;
type Choice = AdviceLevel | "inherit";

export class AdviceView extends LitElement {
  @property({ attribute: false }) api!: PanelApi;
  @property({ attribute: false }) t!: T;
  @property({ attribute: false }) language = "en";
  @state() private raw: Advice[] = [];
  @state() private saved: ServiceConfig | null = null;
  @state() private draft: ServiceConfig | null = null;
  @state() private names = new Map<string, string>();
  @state() private pending: { rule: string; sid: string | null } | null = null;
  @state() private errors: string[] = [];
  @state() private notice = false;
  @state() private busy = false;
  @state() private loadError = false;

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
  }

  private async load(): Promise<void> {
    try {
      const [raw, cfg, cat] = await Promise.all([this.api.warnings(false), this.api.config(), this.api.catalog()]);
      this.raw = raw;
      this.saved = cfg;
      this.draft = clone(cfg);
      this.names = new Map((cat as Catalog).classes.map((c) => [c.mid, c.name]));
      this.loadError = false;
    } catch {
      this.loadError = true;
    }
  }

  private get dirty(): boolean {
    return JSON.stringify(this.draft) !== JSON.stringify(this.saved);
  }

  private source(id: string): SourceCfg | undefined {
    return this.draft?.sources?.find((s) => s.id === id);
  }

  // ------------------------------------------------------------------ editing
  private current(rule: string, sid: string | null): Choice {
    const block = sid === null ? this.draft!.advice : this.source(sid)?.advice;
    const e = block?.[rule];
    return e === undefined ? (sid === null ? "default" : "inherit") : (entry(e).level ?? "default");
  }

  private isSafetyRule(rule: string, sid: string | null): boolean {
    return this.raw.some((w) => w.rule === rule && w.safety && (sid === null || w.source === sid));
  }

  private choose(rule: string, sid: string | null, choice: Choice, select?: HTMLSelectElement): void {
    if (choice === "ignore" && this.isSafetyRule(rule, sid)) {
      this.pending = { rule, sid };      // hiding a safety advice needs an explicit confirmation
      if (select) select.value = this.current(rule, sid);   // the menu keeps showing the real setting until confirmed
      return;
    }
    this.write(rule, sid, choice, false);
  }

  private write(rule: string, sid: string | null, choice: Choice, confirm: boolean): void {
    const d = clone(this.draft!);
    const holder = sid === null ? d : d.sources!.find((s) => s.id === sid)!;
    const block: Record<string, AdviceSetting> = { ...(holder.advice ?? {}) };
    if (choice === "inherit" || (sid === null && choice === "default")) delete block[rule];
    else block[rule] = choice === "ignore" && confirm ? { level: "ignore", confirm: true } : choice;
    if (Object.keys(block).length) holder.advice = block; else delete holder.advice;
    this.draft = d;
    this.pending = null;
  }

  private async save(): Promise<void> {
    if (!this.draft) return;
    this.busy = true;
    this.errors = [];
    try {
      const check = await this.api.validate(this.draft);
      if (check.errors.length) { this.errors = check.errors; return; }
      await this.api.save(this.draft);
      this.saved = clone(this.draft);
      this.notice = true;
    } catch (err) {
      this.errors = [(err as { message?: string }).message ?? String(err)];
    } finally {
      this.busy = false;
    }
  }

  // ------------------------------------------------------------------ rendering
  private levelSelect(rule: string, sid: string | null) {
    const t = this.t;
    const value = this.current(rule, sid);
    const options: Choice[] = sid === null ? LEVELS : ["inherit", ...LEVELS];
    return html`<select data-rule=${rule} data-scope=${sid ?? "all"} aria-label=${t(sid === null ? "onAllSources" : "onThisSource")} @change=${(e: Event) => this.choose(rule, sid, (e.target as HTMLSelectElement).value as Choice, e.target as HTMLSelectElement)}>
      ${options.map((o) => html`<option value=${o} ?selected=${value === o}>${t(`level_${o}` as Key)}</option>`)}</select>`;
  }

  private card(w: Advice, level: Advice["level"] | null) {
    const t = this.t;
    const sname = this.source(w.source)?.name ?? w.source;
    const confirming = this.pending && this.pending.rule === w.rule && (this.pending.sid === null || this.pending.sid === w.source);
    return html`
      <li class="advice ${level ?? "hidden"}" data-rule=${w.rule} data-source=${w.source}>
        <div class="msg"><span class="badge ${level ?? "hidden"}">${level ? t(`level_${level}` as Key) : t("level_ignore")}</span> ${w.message}</div>
        <div class="dim">${sname}${w.classes.length ? ` · ${w.classes.map((m) => this.names.get(m) ?? m).join(", ")}` : ""}</div>
        <div class="controls">
          <label>${t("onThisSource")}${this.levelSelect(w.rule, w.source)}</label>
          <label>${t("onAllSources")}${this.levelSelect(w.rule, null)}</label>
        </div>
        ${confirming ? html`<div class="confirm" role="alert">${t("safetyConfirm")}
          <button class="danger" data-action="confirm-hide" @click=${() => this.write(this.pending!.rule, this.pending!.sid, "ignore", true)}>${t("hideAnyway")}</button>
          <button data-action="cancel-hide" @click=${() => (this.pending = null)}>${t("cancel")}</button></div>` : nothing}
      </li>`;
  }

  render() {
    const t = this.t;
    if (this.loadError) return html`<p class="note error">${t("unreachable")}</p>`;
    if (!this.draft) return html`<p class="note">${t("loading")}</p>`;
    const shown: { w: Advice; level: Advice["level"] }[] = [];
    const hidden: Advice[] = [];
    for (const w of this.raw) {
      const level = effectiveLevel(w, this.draft);
      if (level === null) hidden.push(w); else shown.push({ w, level });
    }
    shown.sort((a, b) => ORDER[a.level] - ORDER[b.level]);
    const seen = new Set<string>();
    const uniq = <T>(items: T[], key: (x: T) => string) => items.filter((x) => (seen.has(key(x)) ? false : (seen.add(key(x)), true)));
    return html`
      ${this.notice ? html`<div class="notice" role="status">${t("saved")} <button class="link" @click=${() => (this.notice = false)}>${t("dismiss")}</button></div>` : nothing}
      ${this.errors.length ? html`<div class="errors" role="alert"><strong>${t("errorsTitle")}</strong><ul>${this.errors.map((e) => html`<li>${e}</li>`)}</ul></div>` : nothing}
      <p class="dim">${t("adviceHint")}</p>
      ${shown.length === 0 && hidden.length === 0 ? html`<p class="note">${t("adviceNone")}</p>` : nothing}
      ${shown.length ? html`<ul class="list">${repeat(uniq(shown, (x) => adviceKey(x.w)), (x) => adviceKey(x.w), (x) => this.card(x.w, x.level))}</ul>` : nothing}
      ${hidden.length ? html`<h2>${t("hiddenAdvice")}</h2><ul class="list">${repeat(uniq(hidden, adviceKey), adviceKey, (w) => this.card(w, null))}</ul>` : nothing}
      ${this.dirty ? html`<div class="savebar"><span>${t("unsaved")}</span>
        <button @click=${() => { this.draft = clone(this.saved!); this.pending = null; this.errors = []; }}>${t("discard")}</button>
        <button class="primary" data-action="save" ?disabled=${this.busy} @click=${() => void this.save()}>${this.busy ? t("saving") : t("saveChanges")}</button></div>` : nothing}`;
  }

  static styles = css`
    :host { display: block; }
    h2 { font-size: 1.05rem; font-weight: 500; margin: 24px 0 12px; }
    .note { color: var(--secondary-text-color); } .note.error { color: var(--error-color, #db4437); }
    .dim { color: var(--secondary-text-color); font-size: 0.85rem; }
    .list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 10px; }
    .advice { padding: 12px 14px; background: var(--card-background-color); border: 1px solid var(--divider-color); border-left-width: 5px; border-radius: 10px; display: flex; flex-direction: column; gap: 6px; }
    .advice.danger { border-left-color: var(--error-color, #db4437); } .advice.warning { border-left-color: var(--warning-color, #ffa600); }
    .advice.info { border-left-color: var(--primary-color); } .advice.hidden { border-left-color: var(--disabled-text-color, #9e9e9e); opacity: 0.8; }
    .badge { display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: 0.75rem; margin-right: 6px; background: var(--secondary-background-color); }
    .badge.danger { background: color-mix(in srgb, var(--error-color, #db4437) 25%, transparent); } .badge.warning { background: color-mix(in srgb, var(--warning-color, #ffa600) 30%, transparent); }
    .controls { display: flex; gap: 14px; flex-wrap: wrap; margin-top: 4px; }
    .controls label { display: flex; flex-direction: column; gap: 3px; font-size: 0.8rem; color: var(--secondary-text-color); }
    select { font: inherit; padding: 7px 9px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--primary-background-color); color: var(--primary-text-color); }
    .confirm { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; background: color-mix(in srgb, var(--error-color, #db4437) 14%, var(--card-background-color)); padding: 8px 12px; border-radius: 8px; }
    button { font: inherit; cursor: pointer; padding: 7px 14px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); }
    button.primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: transparent; } button.danger { background: var(--error-color, #db4437); color: #fff; border-color: transparent; }
    button.link { border: 0; background: none; color: var(--primary-color); padding: 4px 0; } button:disabled { opacity: .6; cursor: default; }
    .notice { background: color-mix(in srgb, var(--success-color, #43a047) 18%, var(--card-background-color)); border-radius: 10px; padding: 10px 14px; margin-bottom: 12px; }
    .errors { background: color-mix(in srgb, var(--error-color, #db4437) 15%, var(--card-background-color)); border-radius: 10px; padding: 10px 14px; margin-bottom: 12px; } .errors ul { margin: 6px 0 6px 18px; padding: 0; }
    .savebar { position: sticky; bottom: 0; z-index: 5; margin: 16px -16px -16px; display: flex; gap: 10px; align-items: center; justify-content: flex-end; padding: 12px 16px; background: var(--card-background-color); border-top: 1px solid var(--divider-color); box-shadow: 0 -2px 8px rgba(0,0,0,.12); } .savebar span { flex: 1; }
  `;
}
if (!customElements.get("sound-recognition-advice")) customElements.define("sound-recognition-advice", AdviceView);
