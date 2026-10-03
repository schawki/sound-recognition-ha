import type { Advice, Catalog, Hass, LiveMessage, Overview, ServiceConfig, SoundEvent, Validation } from "./types";

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
  config(): Promise<ServiceConfig> {
    return this.hass.callWS({ type: "sound_recognition/config" });
  }
  validate(config: ServiceConfig): Promise<Validation> {
    return this.hass.callWS({ type: "sound_recognition/config_validate", language: this.language, config });
  }
  save(config: ServiceConfig): Promise<unknown> {
    return this.hass.callWS({ type: "sound_recognition/config_save", language: this.language, config });
  }
  subscribe(cb: (m: LiveMessage) => void): Promise<() => void> {
    return this.hass.connection.subscribeMessage<LiveMessage>(cb, { type: "sound_recognition/subscribe", language: this.language });
  }
}
