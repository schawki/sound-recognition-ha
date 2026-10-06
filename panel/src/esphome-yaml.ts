/** Example ESPHome configuration shown in the Sources form (kept in sync with esphome/example.yaml, checked by a test). */
export const ESPHOME_YAML = `esphome:
  name: sound-mic

esp32:
  board: esp32-s3-devkitc-1
  framework:
    type: esp-idf

logger:
api:
ota:
  - platform: esphome
wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password

external_components:
  - source: github://schawki/sound-recognition-ha
    components: [sound_recognition_stream]

i2s_audio:
  i2s_lrclk_pin: GPIO5      # WS
  i2s_bclk_pin: GPIO4       # SCK

microphone:
  - platform: i2s_audio
    id: mic
    adc_type: external
    i2s_din_pin: GPIO6      # SD
    pdm: false
    channel: left           # L/R pin of the INMP441 wired to GND
    sample_rate: 16000
    bits_per_sample: 32bit

sound_recognition_stream:
  microphone: mic
  password: !secret sound_recognition_password   # 8+ characters, set in secrets.yaml
  port: 6055
`;
