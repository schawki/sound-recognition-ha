import { LitElement, css, html, nothing } from "lit";
import { property, state } from "lit/decorators.js";
import { repeat } from "lit/directives/repeat.js";
import type { PanelApi } from "./api";
import { adviceKey, entry } from "./advice";
import { buildItems, type Item } from "./advice-items";
import { describeBase, describeChanges } from "./advice-text";
import { clone } from "./classes";
import { applyAndSave, applyPatch, removePatch, undoAndSave } from "./patch";
import type { Key, T } from "./i18n";
import type { Advice, AdviceLevel, AdviceSetting, Catalog, Recommendation, ServiceConfig, SourceCfg, Suggestions } from "./types";

const LEVELS: AdviceLevel[] = ["default", "info", "warning", "danger", "ignore"];
type Choice = AdviceLevel | "inherit";

export class AdviceView extends LitElement {
  @property({ attribute: false }) api!: PanelApi;
  @property({ attribute: false }) t!: T;
  @property({ attribute: false }) language = "en";
  @property({ attribute: false }) focusKey: string | null = null;      // key of the advice to bring into view
  @state() private flash: string | null = null;
  private focused: string | null = null;
  @state() private raw: Advice[] = [];
  @state() private recs: Recommendation[] = [];
  @state() private applying: string | null = null;
  @state() private undoing: string | null = null;
  @state() private sourceFilter = "";                              // "" = all sources
  @state() private undone: { rule: string; source: string } | null = null;
  private suggest = new Map<string, Suggestions>();
  private done = new Set<string>();                       // applied just now, shown as such until the reload confirms it
  private audio = new Map<string, string>();
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

  private async load(quiet = false, attempt = 0): Promise<void> {
    try {
      const [raw, cfg, cat, recs] = await Promise.all([this.api.warnings(false), this.api.config(), this.api.catalog(), this.api.recommendations()]);
      this.raw = raw;
      this.recs = recs;
      this.saved = cfg;
      this.draft = clone(cfg);
      this.names = new Map((cat as Catalog).classes.map((c) => [c.mid, c.name]));
      this.audio = new Map((cat as Catalog).classes.map((c) => [c.mid, c.audioset_name]));
      this.suggest = new Map((cat as Catalog).classes.map((c) => [c.mid, c.suggestions]));
      this.done.clear();
      this.loadError = false;
    } catch {
      // right after a change the integration reloads for a moment: keep what is shown and try again
      if (quiet && attempt < 4) window.setTimeout(() => void this.load(true, attempt + 1), 1500);
      else if (!quiet) this.loadError = true;
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

  protected updated(): void {
    if (!this.focusKey || this.focusKey === this.focused || !this.draft) return;
    const li = [...(this.shadowRoot?.querySelectorAll<HTMLElement>("li.advice[data-key]") ?? [])].find((e) => e.dataset.key === this.focusKey);
    if (!li) return;
    this.focused = this.focusKey;
    const group = li.closest<HTMLDetailsElement>("details.group");
    if (group) group.open = true;                         // the advice is among those already applied: unfold them
    this.flash = this.focusKey;
    li.scrollIntoView({ block: "center", behavior: "smooth" });
    window.setTimeout(() => { this.flash = null; }, 2600);
  }

  private async apply(it: Item): Promise<void> {
    if (!it.apply) return;
    this.applying = it.key;
    this.errors = [];
    this.undone = null;
    // the patch carries what the trace of the advice needs, so it can be shown and undone later
    const patch = { ...it.apply, rule: it.rule, message: it.message, level: it.level, classes: it.classes };
    try {
      const errs = await applyAndSave(this.api, patch, (mid) => this.audio.get(mid));
      if (errs.length) { this.errors = errs; return; }
      const edits = this.dirty ? this.draft : null;      // display changes not saved yet are kept
      this.done.add(it.key);
      if (this.saved) this.saved = applyPatch(this.saved, patch, (mid) => this.audio.get(mid));
      this.draft = edits ? applyPatch(edits, patch, (mid) => this.audio.get(mid)) : clone(this.saved!);
      void this.load(true);
    } catch (err) {
      this.errors = [(err as { message?: string }).message ?? String(err)];
    } finally {
      this.applying = null;
    }
  }

  /** Takes the settings of an applied advice off its source: the catalog (or the global setting) takes over again. */
  private async undo(it: Item): Promise<void> {
    if (!it.undo) return;
    this.undoing = it.key;
    this.errors = [];
    const patch = { ...it.undo, rule: it.rule };
    try {
      const errs = await undoAndSave(this.api, patch, (mid) => this.audio.get(mid));
      if (errs.length) { this.errors = errs; return; }
      const edits = this.dirty ? this.draft : null;
      if (this.saved) this.saved = removePatch(this.saved, patch, (mid) => this.audio.get(mid));
      this.draft = edits ? removePatch(edits, patch, (mid) => this.audio.get(mid)) : clone(this.saved!);
      this.done.delete(it.key);
      this.undone = { rule: it.rule, source: it.source };
      void this.load(true);
    } catch (err) {
      this.errors = [(err as { message?: string }).message ?? String(err)];
    } finally {
      this.undoing = null;
    }
  }

  /** Shows a hidden advice again on one source, even when a setting for all sources hides it. */
  private show(w: Advice): void {
    const global = entry(this.draft!.advice?.[w.rule]).level;
    this.write(w.rule, w.source, global === "ignore" ? "default" : "inherit", false);
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
        <div class="actions"><button data-action="show" @click=${() => this.show(w)}>${t("adviceShow")}</button></div>
        <div class="controls">
          <label>${t("onThisSource")}${this.levelSelect(w.rule, w.source)}</label>
          <label>${t("onAllSources")}${this.levelSelect(w.rule, null)}</label>
        </div>
        ${confirming ? html`<div class="confirm" role="alert">${t("safetyConfirm")}
          <button class="danger" data-action="confirm-hide" @click=${() => this.write(this.pending!.rule, this.pending!.sid, "ignore", true)}>${t("hideAnyway")}</button>
          <button data-action="cancel-hide" @click=${() => (this.pending = null)}>${t("cancel")}</button></div>` : nothing}
      </li>`;
  }

  private day(at: string): string {
    const d = new Date(at);
    return Number.isNaN(d.getTime()) ? at : d.toLocaleDateString(this.language, { day: "numeric", month: "short" });
  }

  private where(it: { source: string; classes: string[] }) {
    const sname = it.source ? this.source(it.source)?.name ?? it.source : "";
    return html`<span class="dim">${sname}${it.classes.length ? `${sname ? " · " : ""}${it.classes.map((m) => this.names.get(m) ?? m).join(", ")}` : ""}</span>`;
  }

  private itemCard(it: Item) {
    const t = this.t;
    const w = it.advice;
    const status = it.applied ? "applied" : it.apply ? "todo" : "info";
    const confirming = w && this.pending && this.pending.rule === w.rule && (this.pending.sid === null || this.pending.sid === w.source);
    const busy = this.applying !== null || this.undoing !== null;
    const changes = it.changes ? describeChanges(it.changes, this.names, t) : [];
    const base = it.applied && it.undo && this.draft ? describeBase(it.undo, this.names, this.suggest, this.draft, t) : [];
    return html`
      <li class="advice ${it.applied ? "done" : it.level} ${this.flash === it.key ? "flash" : ""}" data-key=${it.key} data-rule=${it.rule} data-source=${it.source} data-kind=${it.kind} data-status=${status}>
        <div class="meta">${it.applied ? nothing : html`<span class="badge ${it.level}">${t(`level_${it.level}` as Key)}</span>`}${this.where(it)}</div>
        <div class="why"><span class="label">${t("adviceWhy")}</span> ${it.message}</div>
        ${changes.length ? html`<div class="does" data-changes><span class="label">${t(it.applied ? "adviceDid" : "adviceDoes")}</span>
          <ul>${changes.map((c) => html`<li>${c}</li>`)}</ul></div>` : nothing}
        ${base.length ? html`<div class="does base" data-undo-puts><span class="label">${t("adviceUndoPuts")}</span>
          <ul>${base.map((c) => html`<li>${c}</li>`)}</ul></div>` : nothing}
        <div class="actions">
          ${it.applied
            ? html`<span class="state" data-state-label="applied">${it.at ? t("adviceAppliedOn", { d: this.day(it.at) }) : `✓ ${t("adviceApplied")}`}</span>
              ${it.undo ? html`<button data-action="undo" ?disabled=${busy} @click=${() => void this.undo(it)}>${this.undoing === it.key ? t("adviceUndoing") : t("adviceUndo")}</button>` : nothing}`
            : it.apply
              ? html`<button class="primary" data-action="apply" ?disabled=${busy} @click=${() => void this.apply(it)}>${this.applying === it.key ? t("applying") : t("apply")}</button>`
              : html`<span class="dim" data-nothing>${t("adviceNothing")}</span>`}
          ${w && !it.applied ? html`<button class="link" data-action="hide" @click=${() => this.choose(w.rule, w.source, "ignore")}>${t("adviceHide")}</button>` : nothing}
        </div>
        ${w ? html`<details class="display" data-display ?open=${!!confirming}><summary>${t("adviceDisplay")}</summary>
          <div class="controls">
            <label>${t("onThisSource")}${this.levelSelect(w.rule, w.source)}</label>
            <label>${t("onAllSources")}${this.levelSelect(w.rule, null)}</label>
          </div></details>` : nothing}
        ${confirming ? html`<div class="confirm" role="alert">${t("safetyConfirm")}
          <button class="danger" data-action="confirm-hide" @click=${() => this.write(this.pending!.rule, this.pending!.sid, "ignore", true)}>${t("hideAnyway")}</button>
          <button data-action="cancel-hide" @click=${() => (this.pending = null)}>${t("cancel")}</button></div>` : nothing}
      </li>`;
  }

  private section(id: string, title: string, items: Item[], opts: { fold?: "open" | "closed" } = {}) {
    if (!items.length) return nothing;
    const list = html`<ul class="list">${repeat(items, (x) => x.key, (x) => this.itemCard(x))}</ul>`;
    return opts.fold
      ? html`<details class="group" data-section=${id} ?open=${opts.fold === "open"}><summary>${title}</summary>${list}</details>`
      : html`<section data-section=${id}><h2>${title}</h2>${list}</section>`;
  }

  render() {
    const t = this.t;
    if (this.loadError) return html`<p class="note error">${t("unreachable")}</p>`;
    if (!this.draft) return html`<p class="note">${t("loading")}</p>`;
    const all = buildItems(this.raw, this.recs, this.draft, this.done, (mid) => this.audio.get(mid));
    const f = this.sourceFilter;
    const mine = (x: { source: string }) => !f || x.source === f;
    const todo = all.todo.filter(mine), info = all.info.filter(mine), applied = all.applied.filter(mine), hidden = all.hidden.filter(mine);
    const sources = this.draft.sources ?? [];
    const back = this.undone && todo.some((x) => x.rule === this.undone!.rule && x.source === this.undone!.source);
    return html`
      ${this.notice ? html`<div class="notice" role="status">${t("saved")} <button class="link" @click=${() => (this.notice = false)}>${t("dismiss")}</button></div>` : nothing}
      ${this.undone ? html`<div class="notice" role="status" data-undone>${t("adviceUndone")}
        ${back ? html`<button class="link" data-action="hide-undone" @click=${() => this.choose(this.undone!.rule, this.undone!.source, "ignore")}>${t("adviceUndoneHide")}</button>` : nothing}
        <button class="link" @click=${() => (this.undone = null)}>${t("dismiss")}</button></div>` : nothing}
      ${this.errors.length ? html`<div class="errors" role="alert"><strong>${t("errorsTitle")}</strong><ul>${this.errors.map((e) => html`<li>${e}</li>`)}</ul></div>` : nothing}
      <div class="top">
        <strong data-summary>${t("adviceSummary", { todo: todo.length, applied: applied.length, hidden: hidden.length })}</strong>
        ${sources.length > 1 ? html`<label class="filter">${t("adviceFilter")}
          <select data-filter aria-label=${t("adviceFilter")} @change=${(e: Event) => (this.sourceFilter = (e.target as HTMLSelectElement).value)}>
            <option value="" ?selected=${f === ""}>${t("allSources")}</option>
            ${sources.map((s) => html`<option value=${s.id} ?selected=${f === s.id}>${s.name ?? s.id}</option>`)}</select></label>` : nothing}
      </div>
      <p class="dim">${t("adviceHint")}</p>
      ${todo.length + info.length + applied.length + hidden.length === 0 ? html`<p class="note" data-none>${t(f ? "adviceNoneFiltered" : "adviceNone")}</p>` : nothing}
      ${this.section("todo", t("adviceSectionTodo", { n: todo.length }), todo)}
      ${this.section("info", t("adviceSectionInfo", { n: info.length }), info)}
      ${this.section("applied", t("adviceSectionApplied", { n: applied.length }), applied, { fold: "open" })}
      ${hidden.length ? html`<details class="group" data-section="hidden"><summary>${t("adviceSectionHidden", { n: hidden.length })}</summary>
        <ul class="list">${repeat(hidden, adviceKey, (w) => this.card(w, null))}</ul></details>` : nothing}
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
    .top { display: flex; gap: 14px; align-items: center; justify-content: space-between; flex-wrap: wrap; margin-bottom: 4px; }
    .filter { display: flex; gap: 8px; align-items: center; font-size: 0.85rem; color: var(--secondary-text-color); }
    .meta { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
    .label { display: inline-block; font-size: 0.72rem; text-transform: uppercase; letter-spacing: .04em; color: var(--secondary-text-color); margin-right: 6px; }
    .does { font-size: 0.9rem; } .does ul { margin: 4px 0 0 18px; padding: 0; } .does.base { color: var(--secondary-text-color); }
    .actions { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-top: 2px; }
    .state { color: var(--success-color, #43a047); font-size: 0.9rem; white-space: nowrap; }
    section[data-section] > h2 { margin: 22px 0 10px; }
    .advice.flash { outline: 2px solid var(--primary-color); outline-offset: 2px; animation: flash 2.6s ease-out; }
    @keyframes flash { 0% { background: color-mix(in srgb, var(--primary-color) 28%, var(--card-background-color)); } 100% { background: var(--card-background-color); } }
    .advice.done { border-left-color: var(--success-color, #43a047); opacity: 0.85; }
    details.display > summary, details.group > summary { cursor: pointer; color: var(--secondary-text-color); font-size: 0.85rem; }
    details.group { margin-top: 18px; } details.group > ul { margin-top: 10px; }
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
