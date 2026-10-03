import { LitElement, css, html } from "lit";
import { property, state } from "lit/decorators.js";
import { DAYS, SLOTS } from "./schedule";

const N = 7 * SLOTS;

/** Week grid of half-hour cells. `cells` has 7*48 booleans (Monday first); fires `cells-changed` with the new array. */
export class ScheduleGrid extends LitElement {
  @property({ attribute: false }) cells: boolean[] = [];
  @property() language = "en";
  @state() private cursor = 0;
  private painting: boolean | null = null;
  private draft: boolean[] | null = null;
  private lastIdx: number | null = null;

  private dayLabel(i: number): string {
    return new Intl.DateTimeFormat(this.language, { weekday: "short" }).format(new Date(2024, 0, 1 + i));
  }

  private emit(cells: boolean[]): void {
    this.dispatchEvent(new CustomEvent("cells-changed", { detail: cells, bubbles: true, composed: true }));
  }

  private cellAt(e: PointerEvent): number | null {
    const el = this.shadowRoot?.elementFromPoint(e.clientX, e.clientY) as HTMLElement | null;
    const idx = el?.dataset?.i;
    return idx === undefined ? null : Number(idx);
  }

  private down(e: PointerEvent): void {
    const i = this.cellAt(e);
    if (i === null) return;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    this.draft = [...this.cells];
    this.painting = !this.draft[i];
    this.lastIdx = i;
    this.draft[i] = this.painting;
    this.cells = this.draft;
  }

  private move(e: PointerEvent): void {
    if (this.painting === null || !this.draft) return;
    const i = this.cellAt(e);
    if (i === null) return;
    // a fast drag can skip cells: fill the stretch between the previous and the current cell when they share a day row
    const from = this.lastIdx !== null && Math.floor(this.lastIdx / SLOTS) === Math.floor(i / SLOTS) ? this.lastIdx : i;
    this.lastIdx = i;
    const next = [...this.draft];
    for (let k = Math.min(from, i); k <= Math.max(from, i); k++) next[k] = this.painting;
    this.draft = next;
    this.cells = next;
  }

  private up(): void {
    if (this.painting === null) return;
    this.painting = null;
    this.lastIdx = null;
    this.emit(this.cells);
  }

  private keys(e: KeyboardEvent): void {
    const step: Record<string, number> = { ArrowRight: 1, ArrowLeft: -1, ArrowDown: SLOTS, ArrowUp: -SLOTS };
    if (e.key in step) {
      e.preventDefault();
      this.cursor = Math.max(0, Math.min(N - 1, this.cursor + step[e.key]));
    } else if (e.key === "Home" || e.key === "End") {
      e.preventDefault();
      this.cursor = Math.floor(this.cursor / SLOTS) * SLOTS + (e.key === "Home" ? 0 : SLOTS - 1);
    } else if (e.key === " " || e.key === "Enter") {
      e.preventDefault();
      const next = [...this.cells];
      next[this.cursor] = !next[this.cursor];
      this.cells = next;
      this.emit(next);
    }
  }

  private cellLabel(i: number): string {
    const d = Math.floor(i / SLOTS), s = i % SLOTS;
    const hm = (n: number) => `${String(Math.floor(n / 2)).padStart(2, "0")}:${n % 2 ? "30" : "00"}`;
    return `${this.dayLabel(d)} ${hm(s)}–${hm(s + 1)}`;
  }

  private toggle(indices: number[]): void {
    const on = indices.every((i) => this.cells[i]);
    const next = [...this.cells];
    indices.forEach((i) => (next[i] = !on));
    this.cells = next;
    this.emit(next);
  }

  render() {
    const hours = Array.from({ length: 24 }, (_, h) => h);
    return html`
      <div class="wrap">
        <div class="grid" role="grid" tabindex="0" aria-label="Weekly schedule" aria-activedescendant=${`c${this.cursor}`} @keydown=${this.keys} @pointerdown=${this.down} @pointermove=${this.move} @pointerup=${this.up} @pointercancel=${this.up}>
          <span></span>
          ${hours.map((h) => html`<button class="hour" style="grid-column: span 2" @click=${() => this.toggle(DAYS.flatMap((_, d) => [d * SLOTS + h * 2, d * SLOTS + h * 2 + 1]))}>${h % 3 === 0 ? String(h).padStart(2, "0") : ""}</button>`)}
          ${DAYS.map(
            (_, d) => html`
              <button class="day" @click=${() => this.toggle(Array.from({ length: SLOTS }, (_, s) => d * SLOTS + s))}>${this.dayLabel(d)}</button>
              ${Array.from({ length: SLOTS }, (_, s) => {
                const i = d * SLOTS + s;
                return html`<span id=${`c${i}`} class="cell ${this.cells[i] ? "on" : ""} ${s % 2 === 1 && (s + 1) % 6 === 0 ? "sep" : ""} ${i === this.cursor ? "cursor" : ""}" data-i=${i} role="gridcell" aria-label=${this.cellLabel(i)} aria-selected=${this.cells[i] ? "true" : "false"}></span>`;
              })}`,
          )}
        </div>
      </div>`;
  }

  static styles = css`
    :host { display: block; }
    .wrap { overflow-x: auto; padding-bottom: 4px; }
    .grid { display: grid; grid-template-columns: 44px repeat(48, minmax(11px, 1fr)); min-width: 600px; gap: 2px 0; touch-action: pan-y; user-select: none; -webkit-user-select: none; }
    .cell { height: 24px; background: var(--secondary-background-color); cursor: pointer; border-radius: 2px; margin: 0 0.5px; }
    .cell.on { background: var(--primary-color); }
    .cell.sep { margin-right: 3px; }
    .grid:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 3px; border-radius: 4px; }
    .cell.cursor { outline: 2px solid transparent; }
    .grid:focus-visible .cell.cursor { outline-color: var(--primary-text-color); outline-offset: 1px; }
    .day, .hour { background: none; border: 0; color: var(--secondary-text-color); font: inherit; font-size: 0.78rem; padding: 0; cursor: pointer; text-align: left; }
    .hour { height: 18px; text-align: left; }
    .day { height: 24px; text-align: left; text-transform: capitalize; }
    .day:hover, .hour:hover { color: var(--primary-text-color); }
  `;
}
customElements.define("sr-schedule-grid", ScheduleGrid);
