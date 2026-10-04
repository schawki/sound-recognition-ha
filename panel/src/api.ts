import type { Advice, Catalog, Go2rtcStreams, Hass, LiveMessage, Overview, Recommendation, ServiceConfig, SoundEvent, Stats, Validation } from "./types";

export class PanelApi {
  constructor(private hass: Hass, public language: string) {}

  overview(): Promise<Overview> {
    return this.hass.callWS({ type: "sound_recognition/overview", language: this.language });
  }
  catalog(): Promise<Catalog> {
    return this.hass.callWS({ type: "sound_recognition/catalog", language: this.language });
  }
  async events(limit = 50): Promise<SoundEvent[]> {
    const r = await this.hass.callWS<{ events: SoundEvent[] }>({ type: "sound_recognition/events", language: this.language, limit });
    return r.events;
  }
  async warnings(overrides = true): Promise<Advice[]> {
    const r = await this.hass.callWS<{ warnings: Advice[] }>({ type: "sound_recognition/warnings", language: this.language, overrides });
    return r.warnings;
  }
  async recommendations(): Promise<Recommendation[]> {
    const r = await this.hass.callWS<{ recommendations: Recommendation[] }>({ type: "sound_recognition/recommendations", language: this.language });
    return r.recommendations;
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
  subscribe(cb: (m: LiveMessage) => void): Promise<() => void> {
    return this.hass.connection.subscribeMessage<LiveMessage>(cb, { type: "sound_recognition/subscribe", language: this.language });
  }
}
