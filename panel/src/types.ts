export interface Hass {
  language: string;
  callWS<T>(msg: Record<string, unknown>): Promise<T>;
  connection: { subscribeMessage<T>(cb: (m: T) => void, msg: Record<string, unknown>): Promise<() => void> };
}

export interface SourceStatus {
  id: string; name: string; type: string; enabled: boolean;
  connected: boolean; error: string | null; level_dbfs: number | null; below_gate: boolean;
  active_classes: string[]; last_window?: unknown; windows: number; inferences: number;
}

export interface Advice { rule: string; kind: string; level: "info" | "warning" | "danger"; source: string; classes: string[]; safety?: boolean; message: string }

export interface SoundEvent {
  id: string; ts: number; source: string; mid: string; name?: string; class?: string; score: number;
  duration_s?: number; clip?: string | null; clip_url?: string; clip_expires?: string | null;
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
}
export interface Catalog {
  classes: CatalogClass[]; categories: Record<string, string>; usages: Record<string, string>; setting_help: Record<string, string>;
}

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
  | { type: "detection"; id: string; source: string; mid: string; name?: string; class: string; score: number; duration_s: number; detected_at: string }
  | { type: "clip_ready"; id: string; source: string; mid: string; clip: string; clip_url: string; expires_at: string };

export interface ScheduleWindow { days?: string[]; from: string; to: string }
export interface Schedule { mode: "continuous" | "scheduled"; windows?: ScheduleWindow[] }
export interface SourceCfg {
  id: string; name?: string; type: string; url: string; enabled?: boolean; threshold_offset?: number;
  min_volume_dbfs?: number | null; schedule?: Schedule; clips?: { allowed?: boolean; max_retention_days?: number };
  advice?: Record<string, AdviceSetting>;
  [extra: string]: unknown;
}
export type AdviceLevel = "default" | "info" | "warning" | "danger" | "ignore";
export type AdviceSetting = AdviceLevel | { level: AdviceLevel; confirm?: boolean };
export interface ServiceConfig {
  advice?: Record<string, AdviceSetting>; sources?: SourceCfg[]; classes?: ClassBlocks; defaults?: { min_volume_dbfs?: number | null; schedule?: Schedule; clips?: { allowed?: boolean; max_retention_days?: number } }; [extra: string]: unknown }
export interface Validation { errors: string[]; warnings: Advice[] }
