# Per-source settings: specification

Status: design, validated by a reference resolver (`tools/resolve.py`) and its tests (`tools/test_resolve.py`). Example: `examples/config.example.yaml`.

## 1. Principles

- One YAML file is the single source of truth; the Home Assistant UI reads and writes the same structure.
- Every parameter can be set at four levels. The most specific level wins, and the UI shows **where each value comes from** (its provenance).
- Nothing is hard-wired: threshold, minimum volume, schedule and clip retention are all configurable per source, per class, and per source × class.
- **Continuous monitoring is explicit and is the default** (`schedule: {mode: continuous}`). A schedule only restricts listening when you ask for it.

## 2. Resolution order

Strongest first: **source × class** > **class (user)** > **source** > **defaults** > **catalog suggestion**.

| Parameter | How it resolves |
|---|---|
| `enabled` | A disabled source disables everything. Otherwise source × class, then class, then off. |
| `threshold` | Source × class value is **absolute** (the source offset is ignored). Otherwise class value (or catalog suggestion) **plus the source's `threshold_offset`**, clamped to 0.05–0.99. |
| `min_duration_s`, `cooldown_s`, `pre_roll_s`, `post_roll_s` | Source × class, then class, then catalog suggestion. |
| `min_volume_dbfs` | Explicit source × class wins. Otherwise the **stricter (higher) of** the class gate and the source/default gate. |
| `schedule` | Source × class, then class, then source, then defaults, then continuous. |
| `clip_retention_days` | Source × class, then class, then catalog; **capped** by the source and global `max_retention_days`; forced to 0 if the source has `clips.allowed: false`, and **always 0 when the catalog marks the class `clip_forbidden`** (conversations). |

## 3. Minimum volume gate

- Measured as the RMS level of the analysis window (0.96 s) in dBFS, before the classifier runs. Range −90 to 0; `null` disables the gate.
- If the window is below the gate of **every** class enabled on that source, inference is skipped (saves CPU) and the source reports `below_gate`. If at least one enabled class has a lower gate, inference still runs and each class is then filtered by its own gate.
- The level depends on the microphone gain, so the source-level value is the natural place to calibrate. A class-level gate is therefore combined with it using "stricter wins", unless you set an explicit source × class value.
- Planned helper: measure the ambient level of a source over a few hours and suggest a gate (for example the 90th percentile of the quiet periods plus a margin).

## 4. Schedules and continuous monitoring

```yaml
schedule: {mode: continuous}          # listen 24/7 (default)
schedule:
  mode: scheduled
  windows:
    - {days: [mon, tue, wed, thu, fri], from: "07:00", to: "23:00"}
    - {days: [fri], from: "22:00", to: "06:00"}   # crosses midnight: belongs to the day it starts on
```

- Times use the Home Assistant time zone. Several windows are combined (union). `days` omitted means every day.
- A class can have its own schedule. This is how a smoke alarm stays **24/7 on a source that is otherwise scheduled**.
- Reserved for later: conditions on Home Assistant states (for example "only when the house is empty").

## 5. Clips per source

`clips.allowed: false` means no audio is ever stored from that source (for example a nursery). `clips.max_retention_days` caps every class on that source. The catalog's `clip_forbidden` for conversations can never be overridden.

## 6. Warnings added for these settings

A *safety class* is a class recommended as an alert (`interest: monitor`) whose primary usage is `fire`, `security` or `baby`.

| Rule | Level | Trigger |
|---|---|---|
| `schedule_gap_safety` | warning | The source schedule has gaps and a safety class has no schedule of its own. |
| `volume_gate_safety` | warning | The effective minimum volume is above −40 dBFS on a safety class. |
| `clip_source_disallowed` | info | Clips are disabled on the source while the class would keep clips. |

Texts are in `catalog/i18n/*.yaml` (`auto_rules`); the UI groups identical warnings across classes.

## 7. To verify at implementation

- How each audio source type exposes continuous audio (ESPHome has no standard stream; go2rtc and RTSP are straightforward).
- Whether the gate should use RMS or a short-term loudness measure on real microphones.
- Whether Home Assistant retranslates dynamic entity names when the user language changes (otherwise entity names follow the server language and only the panel follows the user).
