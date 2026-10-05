import { LitElement, css, html, nothing } from "lit";
import { property, state } from "lit/decorators.js";
import { repeat } from "lit/directives/repeat.js";
import type { PanelApi } from "./api";
import type { T } from "./i18n";
import { cellsToWindows, hoursPerWeek, windowsToCells } from "./schedule";
import { groupAdvice, type NoticeItem } from "./advice-group";
import type { Advice, HsPlace, SeparationType, StructureInfo, Catalog, Environment, Go2rtcStreams, HaArea, HaDevice, HaOpening, ServiceConfig, SourceCfg } from "./types";
import "./schedule-grid";
import "./structure-plan";

const TYPES: [string, "typeRtsp" | "typeGo2rtc" | "typeAlsa" | "typeEsphome" | "typeFile"][] = [
  ["rtsp", "typeRtsp"], ["go2rtc", "typeGo2rtc"], ["alsa_rpi", "typeAlsa"], ["esphome", "typeEsphome"], ["file", "typeFile"],
];

const MIN_WEIGHT = 0.1;   // a connected room whose sound reaches the source for less than this is ignored in the summary
const SEPARATIONS: [SeparationType, "sepOpenSpace" | "sepOpening" | "sepDoor" | "sepGlassDoor" | "sepGrille" | "sepWindow" | "sepShutter" | "sepWall"][] = [
  ["open_space", "sepOpenSpace"], ["opening", "sepOpening"], ["door", "sepDoor"], ["glass_door", "sepGlassDoor"], ["grille", "sepGrille"], ["window", "sepWindow"], ["shutter", "sepShutter"], ["wall", "sepWall"],
];
const STATE_KEYS = { open: "stOpen", closed: "stClosed", partial: "stPartial", unknown: "stUnknown" } as const;

interface Row { key: number; name: string; url: string }

interface Form {
  id: string; isNew: boolean; name: string; type: string; url: string; enabled: boolean;
  rows: Row[]; picked: Record<string, string>;
  offset: string; minVolume: string; scheduled: boolean; cells: boolean[];
  clipsAllowed: boolean; clipsMaxDays: string;
  environment: string; adaptive: boolean; adaptiveMax: string;
  area: string; devEnabled: boolean; devMax: string; devExclude: string[]; devInclude: string;
}

let rowKey = 0;
const newRow = (name = "", url = ""): Row => ({ key: ++rowKey, name, url });
let lastType = "go2rtc";   // the type of the last source added, so the next one starts on it (kept while the page stays open)

/** "name, rtsp://…" or just "rtsp://…" (one per line); blank lines are ignored. */
export function parseList(text: string): Row[] {
  return text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean).map((l) => {
    const m = l.match(/^(.*?)[,;\t]\s*([a-z][a-z0-9+.-]*:\/\/\S+)$/i);
    return m ? newRow(m[1].trim(), m[2]) : newRow("", l);
  });
}

const nameFromUrl = (u: string): string => {
  const last = u.replace(/[?#].*$/, "").split("/").filter(Boolean).pop() ?? "";
  return last.includes(":") ? "" : decodeURIComponent(last);
};

const slug = (s: string): string => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 40) || "source";

export class SourcesView extends LitElement {
  @property({ attribute: false }) api!: PanelApi;
  @property({ attribute: false }) t!: T;
  @property({ attribute: false }) language = "en";
  @state() private config: ServiceConfig | null = null;
  @state() private form: Form | null = null;
  @state() private errors: string[] = [];
  @state() private notice: { text: string; items: NoticeItem[]; sources: number } | null = null;
  private classNames: Map<string, string> | null = null;
  @state() private confirming: string | null = null;
  @state() private busy = false;
  @state() private loadError = false;
  @state() private environments: Environment[] = [];
  @state() private areas: HaArea[] = [];
  @state() private openings: HaOpening[] = [];
  @state() private devs: HaDevice[] = [];
  @state() private hsPlace: HsPlace | null = null;
  @state() private structure: StructureInfo | null = null;
  private devsFor = "";
  @state() private g2: { url: string; streams: Go2rtcStreams["streams"]; loading: boolean; error: string; tried: boolean } = { url: "", streams: [], loading: false, error: "", tried: false };

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
  }

  private async load(): Promise<void> {
    try {
      this.config = await this.api.config();
      this.loadError = false;
      void this.api.catalog().then((c) => { this.environments = c.environments ?? []; }, () => undefined);
      void this.api.areas().then((a) => { this.areas = a; }, () => undefined);
      void this.api.openings().then((o) => { this.openings = o; }, () => undefined);
      void this.api.structure().then((x) => { this.structure = x; }, () => undefined);
    } catch {
      this.loadError = true;
    }
  }

  protected willUpdate(): void {
    if (this.form?.type === "go2rtc" && !this.g2.tried && !this.g2.loading) void this.loadStreams();
  }

  /** Without `url`, reads the streams of the address Home Assistant remembers; with it, tries that address. */
  private async loadStreams(url?: string): Promise<void> {
    this.g2 = { ...this.g2, tried: true, loading: true, error: "" };
    try {
      const r = await this.api.go2rtcStreams(url);
      this.g2 = { url: r.url || this.g2.url, streams: r.streams, loading: false, error: "", tried: true };
    } catch (e) {
      const msg = (e as { message?: string })?.message ?? "";
      this.g2 = { ...this.g2, streams: [], loading: false, error: this.t("go2rtcFailed", { e: msg }), tried: true };
    }
  }

  private pickStream(rtsp: string): void {
    const stream = this.g2.streams.find((x) => x.url === rtsp);
    if (!stream || !this.form) return;
    this.form = { ...this.form, url: stream.url, name: this.form.name.trim() ? this.form.name : stream.name };
  }

  private get sources(): SourceCfg[] {
    return this.config?.sources ?? [];
  }

  // ------------------------------------------------------------------ form <-> source
  private toForm(s: SourceCfg): Form {
    const sched = s.schedule;
    return {
      id: s.id, isNew: false, name: s.name ?? s.id, type: s.type, url: s.url, enabled: s.enabled !== false, rows: [], picked: {},
      offset: s.threshold_offset == null ? "" : String(s.threshold_offset),
      minVolume: s.min_volume_dbfs == null ? "" : String(s.min_volume_dbfs),
      scheduled: sched?.mode === "scheduled", cells: windowsToCells(sched?.windows ?? []),
      clipsAllowed: s.clips?.allowed !== false, clipsMaxDays: s.clips?.max_retention_days == null ? "" : String(s.clips.max_retention_days),
      environment: s.environment ?? "", adaptive: s.adaptive?.enabled === true, adaptiveMax: s.adaptive?.max_offset == null ? "" : String(s.adaptive.max_offset),
      area: s.area ?? "", devEnabled: s.devices?.enabled === true, devMax: s.devices?.max_offset == null ? "" : String(s.devices.max_offset),
      devExclude: [...(s.devices?.exclude ?? [])], devInclude: (s.devices?.include ?? []).join("\n"),
    };
  }

  private blankForm(): Form {
    return { id: "", isNew: true, name: "", type: lastType, url: "", enabled: true, rows: [newRow()], picked: {}, offset: "", minVolume: "", scheduled: false, cells: new Array(336).fill(false), clipsAllowed: true, clipsMaxDays: "", environment: "", adaptive: false, adaptiveMax: "", area: "", devEnabled: false, devMax: "", devExclude: [], devInclude: "" };
  }

  /** Applies the form on a copy of the stored source, so fields the form does not know (class settings, advice) are kept. */
  private fromForm(f: Form, existing?: SourceCfg): SourceCfg {
    const s: SourceCfg = { ...(existing ?? {}), id: f.id, name: f.name.trim(), type: f.type, url: f.url.trim() };
    if (f.enabled) delete s.enabled; else s.enabled = false;
    const off = parseFloat(f.offset);
    if (Number.isFinite(off) && off !== 0) s.threshold_offset = off; else delete s.threshold_offset;
    const vol = parseFloat(f.minVolume);
    if (f.minVolume.trim() !== "" && Number.isFinite(vol)) s.min_volume_dbfs = vol; else delete s.min_volume_dbfs;
    const windows = f.scheduled ? cellsToWindows(f.cells) : null;
    if (f.scheduled && windows && windows.length) {
      const untouched = existing?.schedule?.mode === "scheduled" && JSON.stringify(windowsToCells(existing.schedule.windows ?? [])) === JSON.stringify(f.cells);
      s.schedule = untouched ? existing!.schedule! : { mode: "scheduled", windows };
    } else {
      s.schedule = { mode: "continuous" };
    }
    if (f.environment) s.environment = f.environment; else delete s.environment;
    const max = parseFloat(f.adaptiveMax);
    if (f.adaptive || (existing?.adaptive && Object.keys(existing.adaptive).length)) {
      s.adaptive = { ...(existing?.adaptive ?? {}), enabled: f.adaptive };
      if (f.adaptiveMax.trim() !== "" && Number.isFinite(max)) s.adaptive.max_offset = max; else delete s.adaptive.max_offset;
    }
    if (f.area) s.area = f.area; else delete s.area;
    const dmax = parseFloat(f.devMax), include = f.devInclude.split(/\r?\n|,/).map((x) => x.trim()).filter(Boolean);
    if (f.devEnabled || (existing?.devices && Object.keys(existing.devices).length) || include.length || f.devExclude.length) {
      const d: NonNullable<SourceCfg["devices"]> = { ...(existing?.devices ?? {}), enabled: f.devEnabled };
      if (f.devMax.trim() !== "" && Number.isFinite(dmax)) d.max_offset = dmax; else delete d.max_offset;
      if (f.devExclude.length) d.exclude = f.devExclude; else delete d.exclude;
      if (include.length) d.include = include; else delete d.include;
      s.devices = d;
    }
    const clips: NonNullable<SourceCfg["clips"]> = {};
    if (!f.clipsAllowed) clips.allowed = false;
    const days = parseInt(f.clipsMaxDays, 10);
    if (f.clipsMaxDays.trim() !== "" && Number.isFinite(days)) clips.max_retention_days = days;
    if (Object.keys(clips).length) s.clips = clips; else delete s.clips;
    return s;
  }

  private uniqueId(name: string, also: Iterable<string> = []): string {
    const taken = new Set([...this.sources.map((s) => s.id), ...also]);
    const base = slug(name);
    let id = base;
    for (let n = 2; taken.has(id); n++) id = `${base}_${n}`;
    return id;
  }

  // ------------------------------------------------------------------ actions
  private async commit(next: SourceCfg[], focus: string | string[] = [], extra: Partial<ServiceConfig> = {}): Promise<boolean> {
    if (!this.config) return false;
    this.busy = true;
    this.errors = [];
    const candidate: ServiceConfig = { ...this.config, sources: next, ...extra };
    try {
      const check = await this.api.validate(candidate);
      if (check.errors.length) {
        this.errors = check.errors;
        return false;
      }
      await this.api.save(candidate);
      this.config = candidate;
      const ids = new Set(Array.isArray(focus) ? focus : [focus]);
      const advice = check.warnings.filter((w: Advice) => ids.has(w.source));
      this.notice = { text: this.t("saved"), items: await this.noticeItems(advice, [...ids], next), sources: ids.size };
      return true;
    } catch (err) {
      this.errors = [(err as { message?: string }).message ?? String(err)];
      return false;
    } finally {
      this.busy = false;
    }
  }

  private async noticeItems(advice: Advice[], ids: string[], all: SourceCfg[]): Promise<NoticeItem[]> {
    if (!advice.length) return [];
    if (!this.classNames) {
      try {
        const cat: Catalog = await this.api.catalog();
        this.classNames = new Map(cat.classes.map((c) => [c.mid, c.name]));
      } catch {
        this.classNames = new Map();
      }
    }
    const names = this.classNames;
    const sname = (id: string) => all.find((x) => x.id === id)?.name ?? id;
    return groupAdvice(advice, sname, (mid) => names.get(mid) ?? mid, ids);
  }

  private async submit(e: Event): Promise<void> {
    e.preventDefault();
    const f = this.form;
    if (!f) return;
    if (f.scheduled && !f.cells.some(Boolean)) {
      this.errors = [this.t("pickSomething")];
      return;
    }
    if (!f.isNew) {
      const existing = this.sources.find((s) => s.id === f.id);
      const updated = this.fromForm({ ...f }, existing);
      if (await this.commit(this.sources.map((s) => (s.id === f.id ? updated : s)), [f.id])) this.form = null;
      return;
    }
    // new sources: the checked go2rtc streams, then the typed or pasted rows; one check and one save for all of them
    const wanted: { name: string; url: string }[] = [];
    if (f.type === "go2rtc") for (const [url, name] of Object.entries(f.picked)) wanted.push({ name, url });
    for (const r of f.rows) if (r.url.trim()) wanted.push({ name: r.name, url: r.url });
    if (wanted.length === 0) {
      this.errors = [this.t("pickAtLeastOne")];
      return;
    }
    const made: SourceCfg[] = [];
    for (const w of wanted) {
      const name = w.name.trim() || nameFromUrl(w.url) || this.t("sourceDefaultName");
      made.push(this.fromForm({ ...f, id: this.uniqueId(name, made.map((m) => m.id)), name, url: w.url }));
    }
    if (await this.commit([...this.sources, ...made], made.map((m) => m.id))) {
      lastType = f.type;
      this.form = null;
    }
  }

  private async toggleEnabled(s: SourceCfg): Promise<void> {
    const flipped = { ...s };
    if (s.enabled === false) delete flipped.enabled; else flipped.enabled = false;
    await this.commit(this.sources.map((x) => (x.id === s.id ? flipped : x)), [s.id]);
  }

  private async removeSource(id: string): Promise<void> {
    this.confirming = null;
    await this.commit(this.sources.filter((s) => s.id !== id));
  }

  private set<K extends keyof Form>(key: K, value: Form[K]): void {
    if (this.form) this.form = { ...this.form, [key]: value };
    if (key === "type" && this.form?.isNew) lastType = value as string;
    if (key === "area") void this.loadDevices(value as string);
  }

  private openForm(f: Form): void {
    this.errors = [];
    this.form = f;
    void this.loadDevices(f.area);
  }

  /** Devices of the room and of the rooms connected to it, as Home Assistant knows them. */
  private async loadDevices(area: string): Promise<void> {
    this.devsFor = area;
    if (!area) { this.devs = []; this.hsPlace = null; return; }
    try {
      const [rows, place] = await Promise.all([this.api.devices(area), this.api.place(area)]);
      if (this.devsFor === area) { this.devs = rows; this.hsPlace = place; }
    } catch {
      if (this.devsFor === area) { this.devs = []; this.hsPlace = null; }
    }
  }

  private areaName(id: string): string {
    return this.areas.find((a) => a.area_id === id)?.name ?? id;
  }

  // ------------------------------------------------------------------ rendering
  private summary(s: SourceCfg): string {
    const t = this.t;
    const sched = s.schedule?.mode === "scheduled" ? t("scheduleSummaryWeek", { h: hoursPerWeek(windowsToCells(s.schedule.windows ?? [])) }) : t("scheduleSummaryContinuous");
    const clips = s.clips?.allowed === false ? t("clipsOff") : s.clips?.max_retention_days != null ? t("clipsOn", { d: s.clips.max_retention_days }) : t("clipsDefault");
    return `${sched} · ${clips}`;
  }

  render() {
    const t = this.t;
    if (this.loadError) return html`<p class="note error">${t("unreachable")}</p>`;
    if (!this.config) return html`<p class="note">${t("loading")}</p>`;
    return html`
      ${this.notice ? this.renderNotice(this.notice) : nothing}
      ${this.form ? this.renderForm(this.form) : this.renderList()}
    `;
  }

  private renderNotice(n: NonNullable<typeof this.notice>) {
    const t = this.t;
    const line = (i: NoticeItem) => html`<li class=${i.level}>${i.message}
      ${i.sources.length ? html`<span class="dim"> — ${t("onlyOnSources", { s: i.sources.join(", ") })}</span>` : nothing}
      ${i.also.length ? html`<div class="dim">${t("sameAdviceFor", { c: i.also.join(", ") })}</div>` : nothing}</li>`;
    const urgent = n.items.filter((i) => i.level !== "info"), minor = n.items.filter((i) => i.level === "info");
    return html`<div class="notice"><div>${n.text}</div>
      ${urgent.length ? html`<strong>${t("adviceAfterSave")}</strong><ul data-advice=urgent>${urgent.map(line)}</ul>` : nothing}
      ${minor.length && !urgent.length ? html`<strong>${t("adviceAfterSave")}</strong><ul data-advice=minor>${minor.map(line)}</ul>` : nothing}
      ${minor.length && urgent.length ? html`<details><summary>${t("moreAdvice", { n: minor.length })}</summary><ul data-advice=minor>${minor.map(line)}</ul></details>` : nothing}
      <button class="link" @click=${() => (this.notice = null)}>${t("dismiss")}</button></div>`;
  }

  private renderList() {
    const t = this.t;
    return html`
      <div class="toolbar"><button class="primary" data-action="add" @click=${() => { this.errors = []; this.openForm(this.blankForm()); }}>${t("addSources")}</button></div>
      ${this.errors.length ? this.renderErrors() : nothing}
      ${this.sources.length === 0 ? html`<p class="note">${t("noSources")}</p>` : html`<ul class="list">${this.sources.map((s) => html`
        <li data-source=${s.id}>
          <div class="info">
            <strong>${s.name ?? s.id}</strong>
            <span class="dim">${TYPES.find(([k]) => k === s.type) ? t(TYPES.find(([k]) => k === s.type)![1]) : s.type} · ${s.url}</span>
            <span class="dim">${this.summary(s)}</span>
          </div>
          <div class="actions">
            <label class="switch" title=${t("enabled")}><input type="checkbox" .checked=${s.enabled !== false} ?disabled=${this.busy} @change=${() => void this.toggleEnabled(s)} aria-label=${t("enabled")} /></label>
            <button data-action="edit" @click=${() => this.openForm(this.toForm(s))}>${t("edit")}</button>
            ${this.confirming === s.id
              ? html`<button class="danger" data-action="confirm-remove" @click=${() => void this.removeSource(s.id)}>${t("confirmRemove")}</button><button @click=${() => (this.confirming = null)}>${t("cancel")}</button>`
              : html`<button data-action="remove" @click=${() => (this.confirming = s.id)}>${t("remove")}</button>`}
          </div>
        </li>`)}</ul>`}
      ${this.areas.length ? this.renderLinks() : nothing}`;
  }

  private sepLabel(type: string): string {
    const key = SEPARATIONS.find(([k]) => k === (type === "open" ? "open_space" : type))?.[1];
    return key ? this.t(key) : type;
  }

  /** The rooms and their connections come from Home Structure; nothing is described here. */
  private renderLinks() {
    const t = this.t, st = this.structure;
    return html`<section class="links" data-links><h2>${t("linksTitle")}</h2>
      ${st?.origin === "home_structure" ? this.renderManaged(st) : this.renderHsStatus(st)}</section>`;
  }

  private renderManaged(st: StructureInfo) {
    const t = this.t;
    return html`<div class="hs" data-hs="managed"><p class="dim">${t("hsManaged")}</p>
      ${st.plan ? html`<structure-plan .plan=${st.plan} .t=${t} .sepLabel=${(x: string) => this.sepLabel(x)}></structure-plan>` : st.links.length ? html`<p class="dim" data-plan="old">${t("hsPlanOld")}</p>` : nothing}
      <details data-plan-list><summary>${t("hsPlanDetails")}</summary><ul class="list">${st.links.map((l, i) => html`<li data-hs-link=${i}><div class="info"><strong>${l.a_name} ↔ ${l.b_name}</strong>
        <span class="dim">${this.sepLabel(l.type)} · ${t(STATE_KEYS[l.state])}${l.shutter_state ? ` · ${this.sepLabel("shutter")} ${t(STATE_KEYS[l.shutter_state])}` : ""}</span></div></li>`)}</ul></details>
      <div class="buttons"><a class="btn primary" data-action="hs-edit" href="/home-structure">${t("hsEditPlan")}</a><a class="btn" data-action="hs-open" href="/config/integrations/integration/home_structure">${t("hsOpenConfig")}</a></div></div>`;
  }

  private renderHsStatus(st: StructureInfo | null) {
    const t = this.t;
    if (!st) return nothing;
    if (st.status === "not_installed") {
      return html`<div class="hs recommend" data-hs="install"><strong>${t("hsInstallTitle")}</strong><p>${t("hsInstallWhy")}</p>
        <div class="buttons"><a class="btn primary" data-action="hs-github" href=${st.url} target="_blank" rel="noopener">${t("hsInstallLink")}</a></div></div>`;
    }
    if (st.status === "not_configured") {
      return html`<div class="hs recommend" data-hs="setup"><strong>${t("hsSetupTitle")}</strong><p>${t("hsSetupText")}</p>
        <div class="buttons"><a class="btn primary" data-action="hs-add" href="/config/integrations/dashboard/add?domain=home_structure">${t("hsAdd")}</a></div></div>`;
    }
    return html`<div class="hs recommend" data-hs="empty"><p>${t("hsEmpty")}</p>
      <div class="buttons"><a class="btn primary" data-action="hs-open" href="/config/integrations/integration/home_structure">${t("hsOpenConfig")}</a></div></div>`;
  }

  /** Devices that count for the source: those of its room, and those of the rooms connected to it that let enough sound through. */
  private counted(f: Form): HaDevice[] {
    return this.devs.filter((d) => !d.duplicate_of && d.available && !f.devExclude.includes(d.entity_id) && d.weight >= MIN_WEIGHT);
  }

  /** Room of the source and the devices around it that raise the thresholds: an automatic summary, the details being an expert setting. */
  private renderRoom(f: Form) {
    const t = this.t;
    const counted = this.counted(f), own = counted.filter((d) => d.area_id === f.area).length;
    const neighbours = [...new Map(this.devs.filter((d) => d.area_id !== f.area && d.weight >= MIN_WEIGHT).map((d) => [d.area_id, d])).values()];
    const custom = f.devMax !== "" || f.devExclude.length > 0 || f.devInclude.trim() !== "";
    return html`<fieldset class="room"><legend>${t("areaLabel")}</legend>
      <label>${t("areaLabel")}<select name="area" aria-label=${t("areaLabel")} @change=${(e: Event) => this.set("area", (e.target as HTMLSelectElement).value)}>
        <option value="" ?selected=${f.area === ""}>${t("areaNone")}</option>
        ${this.areas.map((a) => html`<option value=${a.area_id} ?selected=${f.area === a.area_id}>${a.name}</option>`)}</select>
        <small>${t("areaHelp")}</small></label>
      <label class="inline"><input type="checkbox" name="devEnabled" .checked=${f.devEnabled} @change=${(e: Event) => this.set("devEnabled", (e.target as HTMLInputElement).checked)} />${t("devicesLabel")}</label>
      <small>${t("devicesHelp")}</small>
      ${!f.area ? html`<p class="dim">${t("devicesPickRoom")}</p>` : html`<div class="devsum" data-devsummary>
        <p>${counted.length === 0 ? t("devicesNone") : t("devicesSummary", { own, near: counted.length - own })}</p>
        ${neighbours.length ? html`<p class="dim" data-neighbours>${t("devicesNeighbours")} ${neighbours.map((d) => `${d.area} (${Math.round(d.weight * 100)} %)`).join(" · ")}</p>` : nothing}</div>
        <details class="expert" data-expert ?open=${custom}><summary>${t("expertTitle")}</summary>
          ${f.devEnabled ? html`<label>${t("devicesMax")}<input name="devMax" type="number" step="0.05" min="0" max="0.4" placeholder="0.15" .value=${f.devMax} @input=${(e: Event) => this.set("devMax", (e.target as HTMLInputElement).value)} /></label>` : nothing}
          <div class="devs" data-devices role="group" aria-label=${t("devicesFound")}>
            <span class="dim">${t("devicesFound")}</span>
            ${this.devs.length === 0 ? html`<p class="note">${t("devicesNone")}</p>` : this.devs.map((d) => d.duplicate_of
              ? html`<div class="dev dim" data-device=${d.entity_id}>${d.name} <span>(${t("devicesFolded", { e: d.duplicate_of })})</span></div>`
              : html`<label class="inline dev" data-device=${d.entity_id}><input type="checkbox" name="devpick" .checked=${!f.devExclude.includes(d.entity_id)}
                @change=${(e: Event) => this.set("devExclude", (e.target as HTMLInputElement).checked ? f.devExclude.filter((x) => x !== d.entity_id) : [...f.devExclude, d.entity_id])} />
                ${d.name}${d.area_id !== f.area ? html` <span class="dim">· ${d.area} · ${Math.round(d.weight * 100)} %</span>` : nothing}
                <span class="dim">${d.available ? d.state : t("devicesUnavailable")}</span></label>`)}</div>
          <label>${t("devicesInclude")}<textarea name="devInclude" rows="2" placeholder="switch.hood" .value=${f.devInclude} @input=${(e: Event) => this.set("devInclude", (e.target as HTMLTextAreaElement).value)}></textarea><small>${t("devicesIncludeHelp")}</small></label>
        </details>`}
    </fieldset>`;
  }

  private renderErrors() {
    return html`<div class="errors" role="alert"><strong>${this.t("errorsTitle")}</strong><ul>${this.errors.map((e) => html`<li>${e}</li>`)}</ul></div>`;
  }

  private renderGo2rtc(f: Form) {
    const t = this.t, g = this.g2;
    const used = new Set(this.sources.filter((x) => x.id !== f.id).map((x) => x.url));
    return html`<fieldset class="g2"><legend>${t("go2rtcServer")}</legend>
      <label>${t("go2rtcAddress")}
        <span class="row"><input name="g2url" placeholder="192.168.1.5" .value=${g.url} @input=${(e: Event) => (this.g2 = { ...this.g2, url: (e.target as HTMLInputElement).value })}
          @keydown=${(e: KeyboardEvent) => { if (e.key === "Enter") { e.preventDefault(); void this.loadStreams(this.g2.url); } }} />
        <button type="button" data-action="g2-load" ?disabled=${g.loading || !g.url.trim()} @click=${() => void this.loadStreams(this.g2.url)}>${t("go2rtcLoad")}</button></span>
        <small>${t("go2rtcAddressHelp")}</small></label>
      ${g.error ? html`<p class="note error" data-g2-error>${g.error}</p>` : nothing}
      ${g.streams.length && f.isNew ? this.renderStreamChecklist(f, used) : g.streams.length ? html`<label>${t("go2rtcStream")}
        <select name="g2stream" @change=${(e: Event) => { this.pickStream((e.target as HTMLSelectElement).value); (e.target as HTMLSelectElement).value = ""; }}>
          <option value="" selected>${t("go2rtcPick")}</option>
          ${g.streams.map((x) => html`<option value=${x.url}>${x.name}${used.has(x.url) ? ` (${t("alreadyAdded")})` : ""}</option>`)}</select></label>` : g.tried && !g.loading && !g.error && g.url ? html`<p class="note">${t("go2rtcNone")}</p>` : nothing}
    </fieldset>`;
  }

  private renderStreamChecklist(f: Form, used: Set<string>) {
    const t = this.t;
    return html`<div class="streams" role="group" aria-label=${t("go2rtcStream")}>
      <div class="gridbar"><span class="dim">${t("go2rtcStream")}</span>
        <button type="button" data-action="g2-all" @click=${() => this.set("picked", Object.fromEntries(this.g2.streams.filter((x) => !used.has(x.url)).map((x) => [x.url, f.picked[x.url] ?? x.name])))}>${t("all")}</button>
        <button type="button" data-action="g2-none" @click=${() => this.set("picked", {})}>${t("none")}</button></div>
      ${this.g2.streams.map((x) => {
        const taken = used.has(x.url), on = x.url in f.picked;
        return html`<div class="stream" data-stream=${x.name}>
          <label class="inline"><input type="checkbox" name="g2pick" .checked=${on} ?disabled=${taken}
            @change=${(e: Event) => { const next = { ...f.picked }; if ((e.target as HTMLInputElement).checked) next[x.url] = x.name; else delete next[x.url]; this.set("picked", next); }} />
            ${x.name}${taken ? html` <span class="dim">(${t("alreadyAdded")})</span>` : nothing}</label>
          ${on ? html`<input class="rowname" name="g2name" aria-label=${t("name")} .value=${f.picked[x.url]} @input=${(e: Event) => this.set("picked", { ...f.picked, [x.url]: (e.target as HTMLInputElement).value })} />` : nothing}
        </div>`;
      })}</div>`;
  }

  private renderRows(f: Form) {
    const t = this.t;
    const upd = (key: number, patch: Partial<Row>) => this.set("rows", f.rows.map((r) => (r.key === key ? { ...r, ...patch } : r)));
    return html`<fieldset class="rows"><legend>${f.type === "go2rtc" ? t("otherAddresses") : t("camerasToAdd")}</legend>
      ${repeat(f.rows, (r) => r.key, (r, i) => html`<div class="rowline" data-row=${i}>
        <input name="row-name" placeholder=${t("name")} aria-label=${t("name")} .value=${r.name} @input=${(e: Event) => upd(r.key, { name: (e.target as HTMLInputElement).value })} />
        <input name="row-url" placeholder="rtsp://…" aria-label=${t("address")} .value=${r.url} @input=${(e: Event) => upd(r.key, { url: (e.target as HTMLInputElement).value })} />
        <button type="button" data-action="row-remove" aria-label=${t("remove")} ?disabled=${f.rows.length === 1 && !r.url && !r.name}
          @click=${() => this.set("rows", f.rows.length === 1 ? [newRow()] : f.rows.filter((x) => x.key !== r.key))}>✕</button></div>`)}
      <div class="gridbar"><button type="button" data-action="row-add" @click=${() => this.set("rows", [...f.rows, newRow()])}>${t("addRow")}</button></div>
      <details class="paste"><summary>${t("pasteList")}</summary>
        <textarea name="paste" rows="4" placeholder="Salon, rtsp://192.168.1.20:554/stream1&#10;rtsp://192.168.1.21:554/stream1"></textarea>
        <small>${t("pasteHelp")}</small>
        <div class="gridbar"><button type="button" data-action="paste-add" @click=${(e: Event) => {
          const ta = (e.target as HTMLElement).closest("details")!.querySelector("textarea")!;
          const parsed = parseList(ta.value);
          if (!parsed.length) return;
          ta.value = "";
          this.set("rows", [...f.rows.filter((r) => r.url.trim() || r.name.trim()), ...parsed]);
        }}>${t("pasteAdd")}</button></div></details>
      <small>${f.type === "go2rtc" ? t("rowsHelpGo2rtc") : t("addressHelp")}</small>
    </fieldset>`;
  }

  /** Kind of place (recommendations) and adaptive sensitivity of the source. The place follows the type of the room in Home Structure unless one is chosen. */
  private renderPlace(f: Form) {
    const t = this.t, hs = f.area ? this.hsPlace : null;
    const auto = hs?.environment ? this.environments.find((e) => e.id === hs.environment) : undefined;
    const env = this.environments.find((e) => e.id === f.environment) ?? (f.environment === "" ? auto : undefined);
    const autoLabel = !f.area ? t("placeNone") : auto ? t("placeAuto", { place: auto.name }) : hs?.described ? t("placeAutoNone") : t("placeNone");
    return html`<fieldset class="place"><legend>${t("placeLabel")}</legend>
      <label>${t("placeLabel")}<select name="environment" aria-label=${t("placeLabel")} @change=${(e: Event) => this.set("environment", (e.target as HTMLSelectElement).value)}>
        <option value="" ?selected=${f.environment === ""}>${autoLabel}</option>
        ${this.environments.map((x) => html`<option value=${x.id} ?selected=${f.environment === x.id}>${x.name}</option>`)}</select>
        <small data-place-help>${f.environment === "" && auto ? t("placeAutoHelp", { type: hs!.room_type }) : f.environment === "" && hs?.described ? t("placeAutoNoneHelp", { room: hs.room ?? "" }) : env ? env.why : t("placeHelp")}</small></label>
      ${env ? html`<details class="tips" data-tips><summary>${t("placeTips")}</summary><ul>${env.tips.map((x) => html`<li>${x}</li>`)}</ul></details>` : nothing}
      <label class="inline"><input type="checkbox" name="adaptive" .checked=${f.adaptive} @change=${(e: Event) => this.set("adaptive", (e.target as HTMLInputElement).checked)} />${t("adaptiveLabel")}</label>
      <small>${t("adaptiveHelp")}</small>
      ${f.adaptive ? html`<label>${t("adaptiveMax")}<input name="adaptiveMax" type="number" step="0.05" min="0" max="0.4" placeholder="0.15" .value=${f.adaptiveMax} @input=${(e: Event) => this.set("adaptiveMax", (e.target as HTMLInputElement).value)} /></label>` : nothing}
    </fieldset>`;
  }

  private renderForm(f: Form) {
    const t = this.t;
    return html`
      <form @submit=${(e: Event) => void this.submit(e)}>
        <h2>${f.isNew ? t("addSources") : f.name}</h2>
        ${this.errors.length ? this.renderErrors() : nothing}
        ${f.isNew ? nothing : html`
        <label>${t("name")}<input name="name" required .value=${f.name} @input=${(e: Event) => this.set("name", (e.target as HTMLInputElement).value)} /></label>`}
        <label>${t("type")}<select name="type" .value=${f.type} @change=${(e: Event) => this.set("type", (e.target as HTMLSelectElement).value)}>
          ${TYPES.map(([k, key]) => html`<option value=${k} ?selected=${f.type === k}>${t(key)}</option>`)}</select></label>
        ${f.type === "go2rtc" ? this.renderGo2rtc(f) : nothing}
        ${f.isNew ? this.renderRows(f) : html`
        <label>${t("address")}<input name="url" required .value=${f.url} @input=${(e: Event) => this.set("url", (e.target as HTMLInputElement).value)} /><small>${t("addressHelp")}</small></label>`}
        ${this.areas.length ? this.renderRoom(f) : nothing}
        ${this.renderPlace(f)}
        ${f.isNew
          ? html`<details class="adv"><summary>${t("advancedSettings")}</summary><div class="advbody">
        <label class="inline"><input type="checkbox" name="enabled" .checked=${f.enabled} @change=${(e: Event) => this.set("enabled", (e.target as HTMLInputElement).checked)} />${t("enabled")}</label>
        <div class="two">
          <label>${t("thresholdOffset")}<input name="offset" type="number" step="0.01" min="-1" max="1" .value=${f.offset} @input=${(e: Event) => this.set("offset", (e.target as HTMLInputElement).value)} /><small>${t("thresholdOffsetHelp")}</small></label>
          <label>${t("minVolume")}<input name="minVolume" type="number" step="1" min="-90" max="0" .value=${f.minVolume} @input=${(e: Event) => this.set("minVolume", (e.target as HTMLInputElement).value)} /><small>${t("minVolumeHelp")}</small></label>
        </div>
        <fieldset>
          <legend>${t("listenMode")}</legend>
          <label class="inline"><input type="radio" name="mode" value="continuous" .checked=${!f.scheduled} @change=${() => this.set("scheduled", false)} />${t("continuous")}</label>
          <label class="inline"><input type="radio" name="mode" value="scheduled" .checked=${f.scheduled} @change=${() => this.set("scheduled", true)} />${t("scheduled")}</label>
          ${f.scheduled ? html`
            <p class="dim">${t("gridHelp")}</p>
            <sr-schedule-grid .cells=${f.cells} .language=${this.language} @cells-changed=${(e: CustomEvent<boolean[]>) => this.set("cells", e.detail)}></sr-schedule-grid>
            <div class="gridbar">
              <span class="dim">${t("hoursPerWeek", { h: hoursPerWeek(f.cells) })}</span>
              <button type="button" @click=${() => this.set("cells", new Array(336).fill(true))}>${t("all")}</button>
              <button type="button" @click=${() => this.set("cells", new Array(336).fill(false))}>${t("none")}</button>
            </div>
            ${f.cells.some(Boolean) ? nothing : html`<p class="note error">${t("pickSomething")}</p>`}` : nothing}
        </fieldset>
        <fieldset>
          <legend>${t("clipsAllowed")}</legend>
          <label class="inline"><input type="checkbox" name="clipsAllowed" .checked=${f.clipsAllowed} @change=${(e: Event) => this.set("clipsAllowed", (e.target as HTMLInputElement).checked)} />${t("clipsAllowed")}</label>
          ${f.clipsAllowed ? html`<label>${t("clipsMaxDays")}<input name="clipsMaxDays" type="number" min="0" max="3650" step="1" .value=${f.clipsMaxDays} @input=${(e: Event) => this.set("clipsMaxDays", (e.target as HTMLInputElement).value)} /></label>` : nothing}
        </fieldset>
          </div></details>`
          : html`
        <label class="inline"><input type="checkbox" name="enabled" .checked=${f.enabled} @change=${(e: Event) => this.set("enabled", (e.target as HTMLInputElement).checked)} />${t("enabled")}</label>
        <div class="two">
          <label>${t("thresholdOffset")}<input name="offset" type="number" step="0.01" min="-1" max="1" .value=${f.offset} @input=${(e: Event) => this.set("offset", (e.target as HTMLInputElement).value)} /><small>${t("thresholdOffsetHelp")}</small></label>
          <label>${t("minVolume")}<input name="minVolume" type="number" step="1" min="-90" max="0" .value=${f.minVolume} @input=${(e: Event) => this.set("minVolume", (e.target as HTMLInputElement).value)} /><small>${t("minVolumeHelp")}</small></label>
        </div>
        <fieldset>
          <legend>${t("listenMode")}</legend>
          <label class="inline"><input type="radio" name="mode" value="continuous" .checked=${!f.scheduled} @change=${() => this.set("scheduled", false)} />${t("continuous")}</label>
          <label class="inline"><input type="radio" name="mode" value="scheduled" .checked=${f.scheduled} @change=${() => this.set("scheduled", true)} />${t("scheduled")}</label>
          ${f.scheduled ? html`
            <p class="dim">${t("gridHelp")}</p>
            <sr-schedule-grid .cells=${f.cells} .language=${this.language} @cells-changed=${(e: CustomEvent<boolean[]>) => this.set("cells", e.detail)}></sr-schedule-grid>
            <div class="gridbar">
              <span class="dim">${t("hoursPerWeek", { h: hoursPerWeek(f.cells) })}</span>
              <button type="button" @click=${() => this.set("cells", new Array(336).fill(true))}>${t("all")}</button>
              <button type="button" @click=${() => this.set("cells", new Array(336).fill(false))}>${t("none")}</button>
            </div>
            ${f.cells.some(Boolean) ? nothing : html`<p class="note error">${t("pickSomething")}</p>`}` : nothing}
        </fieldset>
        <fieldset>
          <legend>${t("clipsAllowed")}</legend>
          <label class="inline"><input type="checkbox" name="clipsAllowed" .checked=${f.clipsAllowed} @change=${(e: Event) => this.set("clipsAllowed", (e.target as HTMLInputElement).checked)} />${t("clipsAllowed")}</label>
          ${f.clipsAllowed ? html`<label>${t("clipsMaxDays")}<input name="clipsMaxDays" type="number" min="0" max="3650" step="1" .value=${f.clipsMaxDays} @input=${(e: Event) => this.set("clipsMaxDays", (e.target as HTMLInputElement).value)} /></label>` : nothing}
        </fieldset>`}
        <div class="buttons">
          <button type="button" data-action="cancel" @click=${() => { this.form = null; this.errors = []; }}>${t("cancel")}</button>
          <button type="submit" class="primary" data-action="save" ?disabled=${this.busy}>${this.busy ? t("saving") : t("save")}</button>
        </div>
      </form>`;
  }

  static styles = css`
    :host { display: block; }
    h2 { font-size: 1.05rem; font-weight: 500; margin: 0 0 12px; }
    .note { color: var(--secondary-text-color); } .note.error { color: var(--error-color, #db4437); }
    .dim, small { color: var(--secondary-text-color); font-size: 0.85rem; }
    .toolbar { display: flex; justify-content: flex-end; margin-bottom: 12px; }
    button { font: inherit; cursor: pointer; padding: 8px 14px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); }
    button.primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: transparent; }
    button.danger { background: var(--error-color, #db4437); color: #fff; border-color: transparent; }
    button.link { border: 0; background: none; color: var(--primary-color); padding: 4px 0; }
    button:disabled { opacity: 0.6; cursor: default; }
    .list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 10px; }
    .list li { display: flex; gap: 12px; align-items: center; justify-content: space-between; flex-wrap: wrap; padding: 14px 16px; background: var(--card-background-color); border: 1px solid var(--divider-color); border-radius: 12px; }
    .info { display: flex; flex-direction: column; gap: 2px; min-width: 0; flex: 1 1 260px; }
    .info .dim { overflow-wrap: anywhere; }
    .actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
    .notice { background: color-mix(in srgb, var(--success-color, #43a047) 18%, var(--card-background-color)); border-radius: 10px; padding: 10px 14px; margin-bottom: 12px; }
    .notice details { margin: 6px 0; } .notice summary { cursor: pointer; }
    .notice ul, .errors ul { margin: 6px 0 6px 18px; padding: 0; }
    .errors { background: color-mix(in srgb, var(--error-color, #db4437) 15%, var(--card-background-color)); border-radius: 10px; padding: 10px 14px; margin-bottom: 12px; }
    form { display: flex; flex-direction: column; gap: 14px; max-width: 760px; background: var(--card-background-color); border: 1px solid var(--divider-color); border-radius: 12px; padding: 16px; }
    label { display: flex; flex-direction: column; gap: 4px; font-size: 0.9rem; }
    label.inline { flex-direction: row; align-items: center; gap: 8px; }
    input:not([type=checkbox]):not([type=radio]), select { font: inherit; padding: 9px 10px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--primary-background-color); color: var(--primary-text-color); min-width: 0; }
    .two { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; }
    fieldset { border: 1px solid var(--divider-color); border-radius: 10px; padding: 10px 14px 14px; display: flex; flex-direction: column; gap: 8px; min-width: 0; }
    legend { padding: 0 6px; font-size: 0.9rem; }
    .gridbar { display: flex; gap: 8px; align-items: center; } .gridbar .dim { flex: 1; }
    .row { display: flex; gap: 8px; } .row input { flex: 1; }
    .streams { display: flex; flex-direction: column; gap: 6px; } .stream { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; min-height: 34px; } .stream label { min-width: 140px; } .stream .rowname { flex: 1; min-width: 160px; }
    .rowline { display: grid; grid-template-columns: minmax(100px, 1fr) minmax(160px, 2fr) auto; gap: 8px; }
    textarea { font: inherit; padding: 9px 10px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--primary-background-color); color: var(--primary-text-color); width: 100%; box-sizing: border-box; margin: 6px 0; }
    details.adv, details.paste { border: 1px solid var(--divider-color); border-radius: 10px; padding: 8px 14px; } details.paste { border: 0; padding: 0; }
    details > summary { cursor: pointer; font-size: 0.9rem; } .advbody { display: flex; flex-direction: column; gap: 14px; margin-top: 12px; }
    .hs { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; } .hs.recommend { background: var(--card-background-color); border: 1px solid var(--divider-color); border-radius: 12px; padding: 14px 16px; } .hs p { margin: 0; }
    a.btn { font: inherit; padding: 8px 14px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); text-decoration: none; } a.btn.primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: transparent; }
    .ok { color: var(--success-color, #43a047); }
    .links { margin-top: 22px; } .linkform { display: flex; flex-direction: column; gap: 12px; max-width: 760px; margin-top: 12px; }
    .devs { display: flex; flex-direction: column; gap: 6px; margin: 8px 0; } .dev { min-height: 28px; }
    .devsum p { margin: 4px 0; } .expert { margin-top: 8px; } .expert summary { cursor: pointer; color: var(--secondary-text-color); }
    .buttons { display: flex; justify-content: flex-end; gap: 10px; }
  `;
}
customElements.define("sound-recognition-sources", SourcesView);
