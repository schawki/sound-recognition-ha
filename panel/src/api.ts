import type { UpdateInfo, Advice, HaArea, HaDevice, HaOpening, StructureInfo, Catalog, EsphomeDevice, Go2rtcStreams, Hass, HsPlace, LiveMessage, Overview, Recommendation, ServiceConfig, SoundEvent, ClipFilter, ClipsDeleted, ClipsPage, Stats, Validation } from "./types";

export class PanelApi {
  constructor(private hass: Hass, public language: string) {}

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
  /** Marks a detection as false (or clears the mark). */
  feedback(eventId: string, isFalse: boolean): Promise<unknown> {
    return this.hass.callWS({ type: "sound_recognition/event_feedback", event_id: eventId, false: isFalse });
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
  async esphomeDevices(): Promise<EsphomeDevice[]> {
    return (await this.hass.callWS<{ devices: EsphomeDevice[] }>({ type: "sound_recognition/esphome_devices" })).devices;
  }
  subscribe(cb: (m: LiveMessage) => void): Promise<() => void> {
    return this.hass.connection.subscribeMessage<LiveMessage>(cb, { type: "sound_recognition/subscribe", language: this.language });
  }
}
