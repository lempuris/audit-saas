export type CrossRefType = "working_paper" | "trial_balance_line" | "document";

export const CROSS_REF_TYPE_LABELS: Record<CrossRefType, string> = {
  working_paper: "Working paper",
  trial_balance_line: "TB line",
  document: "Document",
};

export interface CrossReferenceRecord {
  id: string;
  engagement_id: string;
  source_type: CrossRefType;
  source_id: string;
  target_type: CrossRefType;
  target_id: string;
  label: string | null;
  created_by: string;
  created_at: string;
  source_label: string;
  target_label: string;
}

/** A choosable cross-reference target: an artifact's id plus a display label. */
export interface CrossRefCandidate {
  type: CrossRefType;
  id: string;
  label: string;
}
