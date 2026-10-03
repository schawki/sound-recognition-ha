// Conversion between the service's schedule windows and a week grid of half-hour cells.
// Service semantics: a window {days, from, to} belongs to the day it starts on; to <= from means it crosses midnight.
import type { ScheduleWindow } from "./types";

export const DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"] as const;
export const SLOTS = 48; // half-hours per day
const N = 7 * SLOTS;

const toSlot = (hm: string, up: boolean): number => {
  const [h, m] = hm.split(":").map(Number);
  const mins = h * 60 + m;
  return up ? Math.ceil(mins / 30) : Math.floor(mins / 30);
};
const fmt = (slot: number): string => {
  const mins = (slot % SLOTS) * 30;
  return `${String(Math.floor(mins / 60)).padStart(2, "0")}:${String(mins % 60).padStart(2, "0")}`;
};

/** Cells active under the given windows (off-grid minutes are widened to whole half-hours). */
export function windowsToCells(windows: ScheduleWindow[]): boolean[] {
  const cells = new Array<boolean>(N).fill(false);
  for (const w of windows) {
    const days = w.days?.length ? w.days : [...DAYS];
    const from = toSlot(w.from, false);
    let to = toSlot(w.to, true);
    if (to <= from) to += SLOTS;
    for (const d of days) {
      const di = DAYS.indexOf(d as (typeof DAYS)[number]);
      if (di < 0) continue;
      for (let s = from; s < to; s++) cells[(di * SLOTS + s) % N] = true;
    }
  }
  return cells;
}

/** Compact windows covering exactly the active cells; null when every cell is active (= continuous listening). */
export function cellsToWindows(cells: boolean[]): ScheduleWindow[] | null {
  if (cells.every(Boolean)) return null;
  if (!cells.some(Boolean)) return [];
  // circular runs: start at a cell that is on and whose predecessor is off
  const runs: { start: number; len: number }[] = [];
  for (let i = 0; i < N; i++) {
    if (!cells[i] || cells[(i + N - 1) % N]) continue;
    let len = 0;
    while (cells[(i + len) % N]) len++;
    runs.push({ start: i, len });
  }
  const pieces: { day: number; from: number; to: number }[] = [];
  for (const r of runs) {
    if (r.len <= SLOTS) {
      pieces.push({ day: Math.floor(r.start / SLOTS), from: r.start % SLOTS, to: (r.start + r.len) % SLOTS || SLOTS });
      continue;
    }
    // longer than a day: split at midnights, one window per day
    let pos = r.start;
    let left = r.len;
    while (left > 0) {
      const inDay = Math.min(left, SLOTS - (pos % SLOTS));
      pieces.push({ day: Math.floor((pos % N) / SLOTS), from: pos % SLOTS, to: (pos % SLOTS) + inDay });
      pos += inDay;
      left -= inDay;
    }
  }
  // same hours on several days -> one window with a day list
  const byHours = new Map<string, { from: number; to: number; days: Set<number> }>();
  for (const p of pieces) {
    const key = `${p.from}-${p.to}`;
    const e = byHours.get(key) ?? { from: p.from, to: p.to, days: new Set<number>() };
    e.days.add(p.day);
    byHours.set(key, e);
  }
  return [...byHours.values()]
    .sort((a, b) => a.from - b.from || a.to - b.to)
    .map((e) => ({ days: [...e.days].sort((a, b) => a - b).map((d) => DAYS[d]), from: fmt(e.from), to: fmt(e.to) }));
}

export const hoursPerWeek = (cells: boolean[]): number => cells.filter(Boolean).length / 2;
