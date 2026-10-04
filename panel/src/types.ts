export interface Hass {
  language: string;
  callWS<T>(msg: Record<string, unknown>): Promise<T>;
  connection: { subscribeMessage<T>(cb: (m: T) => void, msg: Record<string, unknown>): Promise<() => void> };
}

export interface SourceStatus {
  id: string; name: string; type: string; enabled: boolean;
  connected: boolean; error: string | null; level_dbfs: number | null; below_gate: boolean;
  active_classes: string[]; last_window?: unknown; windows: number; inferences: number;
  active_contexts?: string[]; ambient_dbfs?: number | null; baseline_dbfs?: number | null; adaptive_enabled?: boolean; adaptive_offset?: number;
  external_offset?: number; external_reasons?: string[]; external_detail?: { label: string; value: number }[];
}

export interface Advice { rule: string; kind: string; level: "info" | "warning" | "danger"; source: string; classes: string[]; safety?: boolean; message: string }

export interface SoundEvent {
  id: string; ts: number; source: string; mid: string; name?: string; class?: string; score: number;
  duration_s?: number; clip?: string | null; clip_url?: string; clip_expires?: string | null;
  threshold?: number; feedback?: string | null;
}

export interface Overview {
  entry_id: string; entries: { entry_id: string; title: string }[]; version: string | null; language: string;
  sources: SourceStatus[]; warnings: Advice[]; config: Record<string, unknown>;
}

export interface Suggestions { threshold: number; min_duration_s: number; cooldown_s: number; pre_roll_s: number; post_roll_s: number; clip_retention_days: number }
export interface CatalogClass {
  mid: string; name: string; audioset_name: string; category: string; role: string; interest: "monitor" | "optional" | "context" | "ignore";
  privacy: "normal" | "sensitive" | "confidential"; clip_forbidden: boolean; suggestions: Suggestions; note_text?: string;
  false_positives: { level: "low" | "medium" | "high"; cause_labels: string[] }; usages: string[]; descendants: string[]; groups: string[];
  inhibiting_contexts: string[];
}
export interface Environment { id: string; contexts: string[]; adaptive: boolean; name: string; why: string; tips: string[] }
export interface Catalog {
  classes: CatalogClass[]; categories: Record<string, string>; usages: Record<string, string>; setting_help: Record<string, string>;
  environments: Environment[];
}

/** What a recommendation changes once the administrator applies it (merged into the stored configuration). */
export interface Patch { source: string; source_patch?: Record<string, unknown>; class_patch?: Record<string, ClassBlock> }
export interface Recommendation { rule: string; level: "info" | "warning" | "danger"; source: string; classes: string[]; message: string; apply: Patch | null }
export interface StatBlock { total: number; by_source: Record<string, number>; by_class: { source: string; mid: string; class: string; count: number }[]; hourly: number[] }
export interface Stats { hours: number; since: number; detections: StatBlock; masked: StatBlock; false: StatBlock }

export interface ClassBlock {
  enabled?: boolean; threshold?: number; min_duration_s?: number; cooldown_s?: number; pre_roll_s?: number; post_roll_s?: number;
  clip_retention_days?: number; min_volume_dbfs?: number | null; schedule?: Schedule;
}
export type ClassBlocks = Record<string, ClassBlock>;
export interface Resolved {
  enabled: boolean; threshold: number; min_duration_s: number; cooldown_s: number; pre_roll_s: number; post_roll_s: number;
  min_volume_dbfs: number | null; schedule: Schedule; clip_retention_days: number; provenance: Record<string, string>;
}

export type LiveMessage =
  | { type: "hello" | "status"; sources: SourceStatus[] }
  | { type: "active"; source: string; active_classes: string[] }
  | { type: "source_state"; source: string; state: string; error?: string | null }
  | { type: "detection"; id: string; source: string; mid: string; name?: string; class: string; score: number; duration_s: number; detected_at: string; threshold?: number; offset?: number }
  | { type: "masked"; id: string; source: string; mid: string; name?: string; class: string; score: number; threshold: number; base_threshold: number; offset: number; reasons: string[]; detected_at: string }
  | { type: "context"; source: string; active_contexts: string[]; ambient_dbfs: number | null; baseline_dbfs: number | null; adaptive_enabled: boolean; adaptive_offset: number; external_offset?: number; external_reasons?: string[]; external_detail?: { label: string; value: number }[] }
  | { type: "clip_ready"; id: string; source: string; mid: string; clip: string; clip_url: string; expires_at: string };

export interface ScheduleWindow { days?: string[]; from: string; to: string }
export interface Schedule { mode: "continuous" | "scheduled"; windows?: ScheduleWindow[] }
export interface SourceCfg {
  id: string; name?: string; type: string; url: string; enabled?: boolean; threshold_offset?: number;
  min_volume_dbfs?: number | null; schedule?: Schedule; clips?: { allowed?: boolean; max_retention_days?: number };
  environment?: string; adaptive?: { enabled?: boolean; max_offset?: number };
  area?: string; devices?: { enabled?: boolean; max_offset?: number; exclude?: string[]; include?: string[] };
  advice?: Record<string, AdviceSetting>;
  [extra: string]: unknown;
}
export type AdviceLevel = "default" | "info" | "warning" | "danger" | "ignore";
export type AdviceSetting = AdviceLevel | { level: AdviceLevel; confirm?: boolean };
export type SeparationType = "open_space" | "opening" | "door" | "glass_door" | "window" | "shutter" | "wall";
export interface AreaLink { a: string; b: string; type: SeparationType | "open"; sensor?: string; open_factor?: number; closed_factor?: number }
export interface StructureLink { a: string; b: string; a_name: string; b_name: string; type: SeparationType; sensor: string | null; state: "open" | "closed" | "partial" | "unknown" }
/** Where the description of the home comes from. */
export interface StructureInfo { status: "not_installed" | "not_configured" | "ready"; origin: "home_structure" | "internal"; links: StructureLink[]; url: string }
export interface HaArea { area_id: string; name: string }
export interface HaOpening { entity_id: string; name: string; area_id: string | null; state: string; domain: "binary_sensor" | "cover"; device_class: string | null }
export interface HaDevice { entity_id: string; name: string; domain: string; state: string; available: boolean; has_volume: boolean; duplicate_of: string | null; area_id: string; area: string }
export interface ServiceConfig {
  area_links?: AreaLink[];
  advice?: Record<string, AdviceSetting>; sources?: SourceCfg[]; classes?: ClassBlocks; defaults?: { min_volume_dbfs?: number | null; schedule?: Schedule; clips?: { allowed?: boolean; max_retention_days?: number } }; [extra: string]: unknown }
export interface Validation { errors: string[]; warnings: Advice[] }

export interface Go2rtcStreams { configured: boolean; url: string; streams: { name: string; url: string }[] }

export interface UpdateStatus { state: "idle" | "requested" | "running" | "done" | "failed"; message?: string; log?: string; stalled?: boolean; updated?: number | null }
export interface UpdateInfo {
  installed: string | null; latest: string | null; available: boolean; outdated: boolean; capable: boolean; installing: boolean;
  status: UpdateStatus | Record<string, never>; release_url: string; manual_command: string; api_level: number; min_api_level: number;
}
