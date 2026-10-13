import { LitElement, css, html, nothing } from "lit";
import { property } from "lit/decorators.js";
import type { PanelApi } from "./api";
import type { T } from "./i18n";
import type { Condition, ConditionRule } from "./types";

/** States worth suggesting for an entity, by domain (the list of a select is read from Home Assistant instead). Any state can be typed. */
const STATES: Record<string, string[]> = {
  person: ["home", "not_home"], device_tracker: ["home", "not_home"], zone: [], binary_sensor: ["on", "off"], input_boolean: ["on", "off"],
  switch: ["on", "off"], light: ["on", "off"], lock: ["locked", "unlocked"], cover: ["open", "closed"], sun: ["above_horizon", "below_horizon"],
  alarm_control_panel: ["disarmed", "armed_home", "armed_away", "armed_night", "armed_vacation", "armed_custom_bypass", "pending", "arming", "triggered"],
  media_player: ["off", "idle", "playing", "paused"], vacuum: ["docked", "cleaning", "returning", "paused", "idle", "error"],
};

export const suggestions = (api: PanelApi, entity: string): string[] => {
  const own = api.entityOptions(entity);
  return own.length ? own : STATES[entity.split(".")[0]] ?? [];
};

const isPeople = (r: ConditionRule): r is { people: "nobody_home" | "someone_home" } => "people" in r;

/** The condition of a source or of a sound: rules on the states of Home Assistant entities, and what to do when one is not known.
 *  Emits `condition-changed` with the new condition, or `null` when it is turned off. */
export class ConditionEditor extends LitElement {
  @property({ attribute: false }) api!: PanelApi;
  @property({ attribute: false }) t!: T;
  @property({ attribute: false }) value: Condition | null = null;
  /** "source" (every sound of the source), "safety" (a safety sound) or "sound": decides which warning is shown. */
  @property() scope: "source" | "safety" | "sound" = "sound";
  /** Without its own on/off box (the parent decides whether there is a condition). */
  @property({ type: Boolean }) bare = false;

  private emit(c: Condition | null): void {
    this.dispatchEvent(new CustomEvent("condition-changed", { detail: c, bubbles: true, composed: true }));
  }

  private patch(change: Partial<Condition>): void {
    this.emit({ ...(this.value as Condition), ...change });
  }

  private setRule(i: number, rule: ConditionRule): void {
    const rules = [...(this.value?.rules ?? [])];
    rules[i] = rule;
    this.patch({ rules });
  }

  private add(rule: ConditionRule): void {
    this.patch({ rules: [...(this.value?.rules ?? []), rule] });
  }

  private rule(r: ConditionRule, i: number) {
    const t = this.t;
    if (isPeople(r)) {
      return html`<div class="rule" data-rule=${i} data-kind="people">
        <select name=${`people_${i}`} .value=${r.people} @change=${(e: Event) => this.setRule(i, { people: (e.target as HTMLSelectElement).value as "nobody_home" | "someone_home" })}>
          <option value="nobody_home" ?selected=${r.people === "nobody_home"}>${t("condNobody")}</option>
          <option value="someone_home" ?selected=${r.people === "someone_home"}>${t("condSomeone")}</option>
        </select>
        <button type="button" class="x" data-action="remove-rule" title=${t("condRemove")} aria-label=${t("condRemove")} @click=${() => this.patch({ rules: this.value!.rules.filter((_, k) => k !== i) })}>×</button>
      </div>`;
    }
    const list = `states_${i}`;
    return html`<div class="rule" data-rule=${i} data-kind="state">
      <input name=${`entity_${i}`} list="entities" placeholder=${t("condEntity")} aria-label=${t("condEntity")} .value=${r.entity}
        @change=${(e: Event) => this.setRule(i, { ...r, entity: (e.target as HTMLInputElement).value.trim() })} />
      <select name=${`op_${i}`} .value=${r.op} @change=${(e: Event) => this.setRule(i, { ...r, op: (e.target as HTMLSelectElement).value as "is" | "is_not" })}>
        <option value="is" ?selected=${r.op === "is"}>${t("condOpIs")}</option>
        <option value="is_not" ?selected=${r.op === "is_not"}>${t("condOpIsNot")}</option>
      </select>
      <input name=${`value_${i}`} list=${list} placeholder=${t("condValue")} aria-label=${t("condValue")} .value=${r.value}
        @change=${(e: Event) => this.setRule(i, { ...r, value: (e.target as HTMLInputElement).value.trim() })} />
      <datalist id=${list}>${suggestions(this.api, r.entity).map((s) => html`<option value=${s}></option>`)}</datalist>
      <button type="button" class="x" data-action="remove-rule" title=${t("condRemove")} aria-label=${t("condRemove")} @click=${() => this.patch({ rules: this.value!.rules.filter((_, k) => k !== i) })}>×</button>
    </div>`;
  }

  protected render() {
    const t = this.t, c = this.value;
    const entities = this.api.entityIds();
    return html`
      ${this.bare ? nothing : html`<label class="inline"><input type="checkbox" name="condition" .checked=${!!c}
        @change=${(e: Event) => this.emit((e.target as HTMLInputElement).checked ? { rules: [{ people: "nobody_home" }] } : null)} />${t("condEnable")}</label>`}
      ${c ? html`
        <p class="dim">${t("condHelp")}</p>
        <datalist id="entities">${entities.map((id) => html`<option value=${id}></option>`)}</datalist>
        ${c.rules.length > 1 ? html`<select name="match" .value=${c.match ?? "all"} @change=${(e: Event) => this.patch({ match: (e.target as HTMLSelectElement).value as "all" | "any" })}>
          <option value="all" ?selected=${(c.match ?? "all") === "all"}>${t("condMatchAll")}</option>
          <option value="any" ?selected=${c.match === "any"}>${t("condMatchAny")}</option>
        </select>` : nothing}
        ${c.rules.map((r, i) => this.rule(r, i))}
        ${c.rules.length === 0 ? html`<p class="note error">${t("condNoRules")}</p>` : nothing}
        <div class="adders">
          <button type="button" data-action="add-state" @click=${() => this.add({ entity: "", op: "is", value: "" })}>${t("condAddEntity")}</button>
          <button type="button" data-action="add-nobody" @click=${() => this.add({ people: "nobody_home" })}>${t("condAddNobody")}</button>
          <button type="button" data-action="add-someone" @click=${() => this.add({ people: "someone_home" })}>${t("condAddSomeone")}</button>
        </div>
        ${c.rules.some(isPeople) ? html`<small class="dim">${t("condPersonsHelp")}</small>` : nothing}
        <label>${t("condIfUnknown")}
          <select name="if_unknown" .value=${c.if_unknown ?? "listen"} @change=${(e: Event) => this.patch({ if_unknown: (e.target as HTMLSelectElement).value as "listen" | "pause" })}>
            <option value="listen" ?selected=${(c.if_unknown ?? "listen") === "listen"}>${t("condListen")}</option>
            <option value="pause" ?selected=${c.if_unknown === "pause"}>${t("condPause")}</option>
          </select>
          <small class="dim">${t("condUnknownHelp")}</small>
        </label>
        ${this.scope === "source" ? html`<p class="note warn" data-safety>${t("condSafetyHere")}</p>` : this.scope === "safety" ? html`<p class="note warn" data-safety>${t("condSafetySound")}</p>` : nothing}` : nothing}`;
  }

  static styles = css`
    :host { display: flex; flex-direction: column; gap: 8px; min-width: 0; }
    .dim, small { color: var(--secondary-text-color); font-size: 0.85rem; margin: 0; }
    label { display: flex; flex-direction: column; gap: 4px; font-size: 0.9rem; } label.inline { flex-direction: row; align-items: center; gap: 8px; }
    .rule { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
    .rule input:not([type=checkbox]) { flex: 1 1 180px; }
    input:not([type=checkbox]), select { font: inherit; padding: 9px 10px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--primary-background-color); color: var(--primary-text-color); min-width: 0; }
    .adders { display: flex; flex-wrap: wrap; gap: 8px; }
    button { font: inherit; cursor: pointer; padding: 8px 12px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); }
    button.x { padding: 6px 10px; line-height: 1; }
    .note { margin: 0; } .warn { background: color-mix(in srgb, var(--warning-color, #ffa600) 22%, var(--card-background-color)); padding: 8px 12px; border-radius: 8px; }
    .error { color: var(--error-color, #db4437); }
  `;
}
if (!customElements.get("sr-condition-editor")) customElements.define("sr-condition-editor", ConditionEditor);
