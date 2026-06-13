export interface TickMarkRecord {
  id: string;
  symbol: string;
  meaning: string;
  sort_order: number;
}

export type TickMarkTargetType = "trial_balance_line" | "working_paper";

export interface TickMarkApplicationRecord {
  id: string;
  engagement_id: string;
  tick_mark_id: string;
  target_type: TickMarkTargetType;
  target_id: string;
  note: string | null;
  applied_by: string;
  created_at: string;
  symbol: string;
  meaning: string;
}

export interface SeedResult {
  created: number;
  skipped: number;
}
