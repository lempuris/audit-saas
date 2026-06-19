export type ChecklistItemStatus = "open" | "complete" | "not_applicable";

export const CHECKLIST_STATUSES: ChecklistItemStatus[] = ["open", "complete", "not_applicable"];

export interface ChecklistItemRecord {
  id: string;
  engagement_id: string;
  item_key: string;
  category: string;
  title: string;
  isa_reference: string | null;
  status: ChecklistItemStatus;
  note: string | null;
  resolved_by: string | null;
  resolved_at: string | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
  resolved_by_name: string | null;
}

export interface CompletionReadiness {
  ready: boolean;
  total_items: number;
  open_items: number;
  uncleared_notes: number;
}
