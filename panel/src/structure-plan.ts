import { LitElement, css, html, nothing, svg } from "lit";
import { property } from "lit/decorators.js";
import type { Key, T } from "./i18n";
import type { PlanConnection, PlanSpace, StructurePlan } from "./types";

const W = 168, H = 58, PAD = 24;
const STATE_KEYS = { open: "stOpen", closed: "stClosed", partial: "stPartial", unknown: "stUnknown" } as const;
const clip = (text: string, n = 20): string => (text.length > n ? `${text.slice(0, n - 1)}…` : text);

/** The plan of the home as drawn in Home Structure, read-only: rooms where they were placed, a dot per separation coloured by its state. */
export class StructurePlanView extends LitElement {
  @property({ attribute: false }) plan!: StructurePlan;
  @property({ attribute: false }) t!: T;
  @property({ attribute: false }) sepLabel: (type: string) => string = (x) => x;   // full name, for the tooltips

  private short(type: string): string {
    return this.t(`plan${type.charAt(0).toUpperCase()}${type.slice(1)}` as Key);
  }

  private pills(c: PlanConnection, a: PlanSpace, b: PlanSpace) {
    const cx = (a.x + b.x) / 2 + W / 2, cy = (a.y + b.y) / 2 + H / 2;
    const n = c.separations.length;
    return c.separations.map((s, i) => {
      const label = this.short(s.type);
      const tip = `${this.sepLabel(s.type)}: ${this.t(STATE_KEYS[s.state])}${s.shutter_state ? ` · ${this.sepLabel("shutter")}: ${this.t(STATE_KEYS[s.shutter_state])}` : ""}`;
      const y = cy + (i - (n - 1) / 2) * 20;
      const w = label.length * 6.2 + (s.shutter_state ? 38 : 28);
      return svg`<g class="pill" data-sep-type=${s.type} data-state=${s.state}><title>${tip}</title>
        <rect x=${cx - w / 2} y=${y - 9} width=${w} height="18" rx="9"></rect>
        <circle class=${s.state} cx=${cx - w / 2 + 10} cy=${y} r="4"></circle>
        ${s.shutter_state ? svg`<rect class="sh ${s.shutter_state}" x=${cx - w / 2 + 17} y=${y - 3} width="6" height="6" rx="1"></rect>` : nothing}
        <text x=${cx - w / 2 + (s.shutter_state ? 28 : 19)} y=${y + 4}>${label}</text></g>`;
    });
  }

  render() {
    const sp = this.plan.spaces;
    const byId = new Map(sp.map((s) => [s.id, s]));
    const minX = Math.min(...sp.map((s) => s.x)) - PAD, minY = Math.min(...sp.map((s) => s.y)) - PAD;
    const width = Math.max(...sp.map((s) => s.x + W)) + PAD - minX, height = Math.max(...sp.map((s) => s.y + H)) + PAD - minY;
    const center = (s: PlanSpace) => ({ x: s.x + W / 2, y: s.y + H / 2 });
    const links = this.plan.connections.filter((c) => byId.has(c.a) && byId.has(c.b));
    return html`<div class="wrap" role="img" aria-label=${this.t("hsPlanLabel")} data-plan><svg viewBox="${minX} ${minY} ${width} ${height}" width=${width} height=${height} style="max-width:100%;height:auto">
      ${links.map((c) => { const a = center(byId.get(c.a)!), b = center(byId.get(c.b)!); return svg`<line class="wire" x1=${a.x} y1=${a.y} x2=${b.x} y2=${b.y}></line>`; })}
      ${sp.map((s) => svg`<g class="box ${s.in_home ? "" : "outside"}" data-space=${s.id}><title>${s.name}</title>
        <rect x=${s.x} y=${s.y} width=${W} height=${H} rx="10"></rect><text x=${s.x + 10} y=${s.y + H / 2 + 5}>${clip(s.name)}</text></g>`)}
      ${links.map((c) => this.pills(c, byId.get(c.a)!, byId.get(c.b)!))}
    </svg></div>`;
  }

  static styles = css`
    :host { display: block; }
    .wrap { overflow: auto; max-height: 460px; border: 1px solid var(--divider-color); border-radius: 10px; background: var(--card-background-color); }
    svg { display: block; font-family: inherit; }
    .wire { stroke: var(--secondary-text-color); stroke-width: 2; opacity: .5; }
    .box rect { fill: var(--card-background-color); stroke: var(--primary-color); stroke-width: 2; }
    .box.outside rect { stroke: var(--secondary-text-color); stroke-dasharray: 6 4; }
    .box text { fill: var(--primary-text-color); font-size: 14px; font-weight: 600; }
    .pill rect { fill: var(--card-background-color); stroke: var(--divider-color); }
    .pill text { fill: var(--primary-text-color); font-size: 11px; }
    .pill circle, .pill .sh { fill: var(--disabled-color, #9e9e9e); }
    .pill .open { fill: var(--success-color, #43a047); } .pill .closed { fill: var(--error-color, #db4437); } .pill .partial { fill: var(--warning-color, #ffa600); }
  `;
}
customElements.define("structure-plan", StructurePlanView);
