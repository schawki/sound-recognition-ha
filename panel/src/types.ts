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

/** A way out of an advice between close sounds: keep this one, switch the others off. */
export interface Choice { keep: string; recommended?: boolean; apply: Patch }
export interface Advice { rule: string; kind: string; level: "info" | "warning" | "danger"; source: string; classes: string[]; safety?: boolean; message: string; apply?: Patch | null; applied?: boolean; choices?: Choice[] }

export interface SoundEvent {
  id: string; ts: number; source: string; mid: string; name?: string; class?: string; score: number;
  duration_s?: number; clip?: string | null; clip_url?: string; clip_expires?: string | null;
  threshold?: number; feedback?: string | null; clip_reason?: string | null;
}

export interface ClipRow { id: string; ts: number; source: string; mid: string; name: string; class?: string; score: number; clip: string; clip_url: string; clip_expires: string | null; size: number; threshold?: number; feedback?: string | null }
export interface ClipFilter { source?: string; mid?: string; usage?: string; since?: number; until?: number }
export interface ClipsPage { clips: ClipRow[]; total: number; total_bytes: number; sounds: { mid: string; name: string; count: number }[]; disk: { clips: number; bytes: number; free_bytes: number | null } }
export interface ClipsDeleted { count: number; bytes: number; dry_run: boolean }

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
export interface Patch {
  source: string; source_patch?: Record<string, unknown>; class_patch?: Record<string, ClassBlock>;
  /** Set when the patch answers an advice: what is kept on the source so the advice can be undone (see AppliedAdvice). */
  rule?: string; message?: string; level?: "info" | "warning" | "danger"; classes?: string[];
}
/** A trace kept on the source of an advice applied with its button: what changed, and when. Undoing removes those settings. */
export interface AppliedAdvice {
  rule: string; classes: string[]; at: string; level: "info" | "warning" | "danger"; message: string;
  patch: { source_patch?: Record<string, unknown>; class_patch?: Record<string, ClassBlock> };
}
export interface Recommendation { rule: string; level: "info" | "warning" | "danger"; source: string; classes: string[]; message: string; apply: Patch | null; applied?: boolean }
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
  advice?: Record<string, AdviceSetting>; applied_advice?: AppliedAdvice[];
  [extra: string]: unknown;
}
export type AdviceLevel = "default" | "info" | "warning" | "danger" | "ignore";
export type AdviceSetting = AdviceLevel | { level: AdviceLevel; confirm?: boolean };
export type SeparationType = "open_space" | "opening" | "door" | "glass_door" | "grille" | "window" | "shutter" | "wall";
export interface StructureLink { a: string; b: string; a_name: string; b_name: string; type: SeparationType; sensor: string | null; state: "open" | "closed" | "partial" | "unknown"; shutter_state?: "open" | "closed" | "partial" | "unknown" | null }
/** Where the description of the home comes from. */
export type SepState = "open" | "closed" | "partial" | "unknown";
export interface PlanSpace { id: string; name: string; kind: string; room_type?: string | null; in_home: boolean; x: number; y: number }
export interface PlanSeparation { type: SeparationType; state: SepState; shutter_state?: SepState | null }
export interface PlanConnection { a: string; b: string; separations: PlanSeparation[] }
export interface StructurePlan { spaces: PlanSpace[]; connections: PlanConnection[] }
export interface StructureInfo { status: "not_installed" | "not_configured" | "ready"; origin: "home_structure" | "none"; links: StructureLink[]; plan?: StructurePlan | null; url: string }
export interface HaArea { area_id: string; name: string }
export interface HaOpening { entity_id: string; name: string; area_id: string | null; state: string; domain: "binary_sensor" | "cover"; device_class: string | null }
export interface HaDevice { entity_id: string; name: string; domain: string; state: string; available: boolean; has_volume: boolean; duplicate_of: string | null; area_id: string; area: string; weight: number }
export interface HsPlace { described: boolean; environment: string | null; room_type: string; room: string | null }
export interface ServiceConfig {
  advice?: Record<string, AdviceSetting>; sources?: SourceCfg[]; classes?: ClassBlocks; defaults?: { min_volume_dbfs?: number | null; schedule?: Schedule; clips?: { allowed?: boolean; max_retention_days?: number } }; [extra: string]: unknown }
export interface Validation { errors: string[]; warnings: Advice[] }

export interface EsphomeDevice { device_id: string; name: string; host: string; port: number; url: string; area_id: string }
export interface Go2rtcStreams { configured: boolean; url: string; streams: { name: string; url: string }[] }

export interface UpdateStatus { state: "idle" | "requested" | "running" | "done" | "failed"; message?: string; log?: string; stalled?: boolean; updated?: number | null }
export interface UpdateInfo {
  installed: string | null; latest: string | null; available: boolean; outdated: boolean; capable: boolean; installing: boolean;
  status: UpdateStatus | Record<string, never>; release_url: string; manual_command: string; api_level: number; min_api_level: number;
}
