// Property check: windows -> cells -> windows -> cells is stable, and emitted windows are valid for the service.
import { build } from "esbuild";
import { strict as assert } from "node:assert";
import { test } from "node:test";
import { writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const dir = mkdtempSync(join(tmpdir(), "sched-"));
await build({ entryPoints: ["src/schedule.ts"], bundle: true, format: "esm", outfile: join(dir, "schedule.mjs"), logLevel: "silent" });
const { windowsToCells, cellsToWindows } = await import(join(dir, "schedule.mjs"));

const rnd = (seed) => () => (seed = (seed * 1664525 + 1013904223) % 4294967296) / 4294967296;

test("round trip on random grids", () => {
  const r = rnd(7);
  const cases = [];
  for (let k = 0; k < 400; k++) {
    const density = [0.05, 0.3, 0.7, 0.95][k % 4];
    const blocky = k % 2 === 0;
    const cells = new Array(336).fill(false);
    for (let i = 0; i < 336; i++) cells[i] = blocky ? (i > 0 && r() < 0.9 ? cells[i - 1] : r() < density) : r() < density;
    const w = cellsToWindows(cells);
    if (w === null) { assert.ok(cells.every(Boolean)); cases.push({ cells, windows: null }); continue; }
    for (const x of w) assert.match(x.from, /^([01]\d|2[0-3]):[0-5]\d$/), assert.match(x.to, /^([01]\d|2[0-3]):[0-5]\d$/);
    assert.deepEqual(windowsToCells(w), cells);
    cases.push({ cells, windows: w });
  }
  writeFileSync(process.env.SCHEDULE_CASES ?? join(dir, "cases.json"), JSON.stringify(cases));
});

test("typical schedules", () => {
  const night = cellsToWindows(windowsToCells([{ days: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"], from: "22:00", to: "06:00" }]));
  assert.deepEqual(night, [{ days: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"], from: "22:00", to: "06:00" }]);
  const office = cellsToWindows(windowsToCells([{ days: ["mon", "tue", "wed", "thu", "fri"], from: "08:00", to: "18:00" }]));
  assert.deepEqual(office, [{ days: ["mon", "tue", "wed", "thu", "fri"], from: "08:00", to: "18:00" }]);
  assert.equal(cellsToWindows(new Array(336).fill(true)), null);
  assert.deepEqual(cellsToWindows(new Array(336).fill(false)), []);
  const widened = windowsToCells([{ days: ["mon"], from: "08:10", to: "09:20" }]);
  assert.equal(widened.slice(0, 48).filter(Boolean).length, 3); // 08:00-09:30
});
