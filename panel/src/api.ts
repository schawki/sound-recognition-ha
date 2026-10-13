import type { UpdateInfo, Advice, HaArea, HaDevice, HaOpening, StructureInfo, Catalog, EsphomeState, ConnectionInfo, MoveInfo, StorageInfo, Go2rtcStreams, Hass, HsPlace, NoiseInfo, LiveMessage, Overview, Recommendation, ServiceConfig, SoundEvent, ClipFilter, ClipsDeleted, ClipsPage, Stats, Validation } from "./types";

export class PanelApi {
  constructor(private hass: Hass, public language: string) {}

  /** Entities of Home Assistant (for the conditions), sorted; empty when the page cannot list them. */
  entityIds(): string[] {
    return Object.keys(this.hass.states ?? {}).sort();
  }
  /** States an entity can have, when Home Assistant lists them (selects, input_select). */
  entityOptions(entity: string): string[] {
    return this.hass.states?.[entity]?.attributes?.options ?? [];
  }
  overview(): Promise<Overview> {
    return this.hass.callWS({ type: "sound_recognition/overview", language: this.language });
  }
  update(refresh = false): Promise<UpdateInfo> {
    return this.hass.callWS({ type: "sound_recognition/update", refresh });
  }
  updateInstall(): Promise<UpdateInfo> {
    return this.hass.callWS({ type: "sound_recognition/update_install" });
  }
  catalog(): Promise<Catalog> {
    return this.hass.callWS({ type: "sound_recognition/catalog", language: this.language });
  }
  async events(limit = 50): Promise<SoundEvent[]> {
    const r = await this.hass.callWS<{ events: SoundEvent[] }>({ type: "sound_recognition/events", language: this.language, limit });
    return r.events;
  }
  clips(filter: ClipFilter, limit = 100, offset = 0): Promise<ClipsPage> {
    return this.hass.callWS({ type: "sound_recognition/clips", language: this.language, ...filter, limit, offset });
  }
  connection(): Promise<ConnectionInfo> {
    return this.hass.callWS({ type: "sound_recognition/connection" });
  }
  storage(): Promise<StorageInfo> {
    return this.hass.callWS({ type: "sound_recognition/storage" });
  }
  /** Asks the service to move the clips to another folder. Rejects with code `invalid_path` and the reasons (codes) separated by commas in `message`. */
  storageMove(path: string): Promise<MoveInfo> {
    return this.hass.callWS({ type: "sound_recognition/storage_move", path });
  }
  /** Asks the service to have the clips left in an old folder (kept after a move) deleted. */
  storageOldDelete(path: string): Promise<MoveInfo> {
    return this.hass.callWS({ type: "sound_recognition/storage_old_delete", path });
  }
  /** Noise measured on each source and the minimum volume suggested from it (service API level 13). */
  noise(): Promise<NoiseInfo> {
    return this.hass.callWS({ type: "sound_recognition/noise" });
  }
  /** Forgets the noise measurements of one source, or of all of them. */
  noiseDelete(source?: string): Promise<{ deleted: number }> {
    return this.hass.callWS({ type: "sound_recognition/noise_delete", ...(source ? { source } : {}) });
  }
  /** Changes the token between Home Assistant and the service; the new one is stored by the integration and never reaches the panel. */
  rotateToken(): Promise<unknown> {
    return this.hass.callWS({ type: "sound_recognition/token_rotate" });
  }
  /** Deletes clips by event ids or by filter (an empty filter = all of them); `dryRun` only counts, for the confirmation. */
  deleteClips(what: { ids: string[] } | { filter: ClipFilter }, dryRun = false): Promise<ClipsDeleted> {
    return this.hass.callWS({ type: "sound_recognition/clips_delete", ...what, dry_run: dryRun });
  }
  async warnings(overrides = true): Promise<Advice[]> {
    const r = await this.hass.callWS<{ warnings: Advice[] }>({ type: "sound_recognition/warnings", language: this.language, overrides });
    return r.warnings;
  }
  async recommendations(): Promise<Recommendation[]> {
    const r = await this.hass.callWS<{ recommendations: Recommendation[] }>({ type: "sound_recognition/recommendations", language: this.language });
    return r.recommendations;
  }
  async areas(): Promise<HaArea[]> {
    return (await this.hass.callWS<{ areas: HaArea[] }>({ type: "sound_recognition/areas" })).areas;
  }
  async openings(): Promise<HaOpening[]> {
    return (await this.hass.callWS<{ openings: HaOpening[] }>({ type: "sound_recognition/openings" })).openings;
  }
  /** Devices of a room and of the rooms connected to it in the Home Structure plan. */
  async devices(areaId: string): Promise<HaDevice[]> {
    return (await this.hass.callWS<{ devices: HaDevice[] }>({ type: "sound_recognition/devices", area_id: areaId })).devices;
  }
  /** What Home Structure says about a room: the place it implies and the name of its type. */
  place(areaId: string): Promise<HsPlace> {
    return this.hass.callWS({ type: "sound_recognition/place", area_id: areaId, language: this.language });
  }
  structure(): Promise<StructureInfo> {
    return this.hass.callWS({ type: "sound_recognition/structure" });
  }
  stats(hours = 24): Promise<Stats> {
    return this.hass.callWS({ type: "sound_recognition/stats", hours });
  }
  /** Marks a detection as wrong (or clears the mark). */
  feedback(eventId: string, isFalse: boolean): Promise<unknown> {
    return this.hass.callWS({ type: "sound_recognition/event_feedback", event_id: eventId, false: isFalse });
  }
  /** Confirms a detection as good (or clears the confirmation). */
  confirm(eventId: string, isGood: boolean): Promise<unknown> {
    return this.hass.callWS({ type: "sound_recognition/event_feedback", event_id: eventId, good: isGood });
  }
  /** Detections with no clip and no verdict (cannot be checked): how many match, or delete them. Marked and confirmed ones stay. */
  deleteClipless(filter: ClipFilter, dryRun = false): Promise<{ count: number; dry_run: boolean }> {
    return this.hass.callWS({ type: "sound_recognition/events_delete_clipless", filter, dry_run: dryRun });
  }
  config(): Promise<ServiceConfig> {
    return this.hass.callWS({ type: "sound_recognition/config" });
  }
  validate(config: ServiceConfig): Promise<Validation> {
    return this.hass.callWS({ type: "sound_recognition/config_validate", language: this.language, config });
  }
  save(config: ServiceConfig): Promise<unknown> {
    return this.hass.callWS({ type: "sound_recognition/config_save", language: this.language, config });
  }
  /** Streams of the go2rtc server; with `url`, tries that address and lets Home Assistant remember it when it answers. */
  go2rtcStreams(url?: string): Promise<Go2rtcStreams> {
    return this.hass.callWS({ type: "sound_recognition/go2rtc_streams", ...(url === undefined ? {} : { url }) });
  }
  /** ESPHome devices that run the Sound Recognition microphone component (found through their diagnostic sensor). */
  esphomeState(): Promise<EsphomeState> {
    return this.hass.callWS<EsphomeState>({ type: "sound_recognition/esphome_devices" });
  }
  /** Ignores a device (it is no longer offered as a microphone to add) or stops ignoring it. */
  esphomeIgnore(device: string, ignored: boolean): Promise<EsphomeState> {
    return this.hass.callWS<EsphomeState>({ type: "sound_recognition/esphome_ignore", device, ignored });
  }
  subscribe(cb: (m: LiveMessage) => void): Promise<() => void> {
    return this.hass.connection.subscribeMessage<LiveMessage>(cb, { type: "sound_recognition/subscribe", language: this.language });
  }
}
