# ESP32 microphone (ESPHome)

An ESP32 with an I2S microphone becomes a Sound Recognition source: it streams its audio over your network and the service listens to it, like a camera. This page covers the device; the service itself is installed with [Installing the service](install-service.en.md).

> **Status: not tried on a real microphone yet.** The device code is checked on a PC against the service (audio, wrong password, takeover) and compiled by the project's CI, but the first run on real hardware is still to come. If something does not work, please open an issue with the ESPHome log.

## What you need

- An **ESP32 or ESP32-S3** board (ESP-IDF framework; other chips are not covered) and the ESPHome add-on or another way to flash it.
- An **I2S MEMS microphone**, for example an INMP441.
- Home Assistant with the **ESPHome** integration, and the Sound Recognition integration connected to the service.

## Wiring (INMP441)

| INMP441 | ESP32-S3 (example) |
|---|---|
| VDD | 3.3 V |
| GND | GND |
| SCK | GPIO4 |
| WS | GPIO5 |
| SD | GPIO6 |
| L/R | GND (left channel) |

Any free pins work: change them in the YAML. Keep the wires short, and avoid pins your board uses for flash or PSRAM.

## ESPHome configuration

Copy [esphome/example.yaml](../esphome/example.yaml) (the panel shows it too, in *Sources → Add → ESP32 microphone*) into a new ESPHome device, then add to `secrets.yaml`:

```yaml
wifi_ssid: "your Wi-Fi"
wifi_password: "your Wi-Fi password"
sound_recognition_password: "a password of your own, 8 characters or more"
```

Flash it. The `sound_recognition_stream` block takes:

| Option | Meaning |
|---|---|
| `microphone` | The `i2s_audio` microphone to stream (required). |
| `password` | Required, 8 characters or more. Keep it in `secrets.yaml`. |
| `port` | TCP port of the stream, 6055 by default. |
| `gain` | Multiplier for a quiet microphone, 1.0 by default (up to 32). Raise it if the level shown in the panel stays very low. |

## Add it to Sound Recognition

Open the panel, *Sources → Add*, choose **ESP32 microphone (ESPHome)**. The devices that run the component are listed (Home Assistant already knows their address and room): press **Use**, type the stream password, choose the sounds as for any source, and save. A device you add by hand needs its address `tcp://address:port`.

If the list is empty, the device is probably not flashed yet or not connected to Home Assistant. The detection looks for a diagnostic sensor named *Sound Recognition stream* on ESPHome devices.

## How the stream is protected

- The device waits on its port; **the service connects to it**. Nobody else is sent any audio.
- The password is **mandatory**, and it never travels on the network: the device sends a random number, the service answers with a signature of it computed with the password, and the device checks it. A wrong answer closes the connection before any sound is sent.
- A new connection that proves the password replaces the previous one, so a service that restarts can reconnect at once.
- The service stores the password in its configuration and never shows it again.

**What it does not do:** the audio itself is **not encrypted** on the network. Someone who can intercept the traffic of your local network could hear it. At home this is a low risk; for more, put your connected devices on their own network (a VLAN, a guest network) and allow the stream port only from the service address. Encryption of the stream may come later.

## Problems

- *The source stays "Disconnected"*: check the address and port (`tcp://…:6055`), that the device is online, and the password. The panel shows the reason; the ESPHome log of the device shows wrong-password attempts.
- *"the device refused the password"*: the password in the panel differs from `secrets.yaml` (case and spaces count). After changing it in `secrets.yaml`, flash the device again.
- *Detections are rare or the level is very low*: raise `gain`, or check that the L/R pin of the INMP441 is wired to match `channel: left`.
- *Choppy audio*: weak Wi-Fi. The stream needs about 32 kB/s.
