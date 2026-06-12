export type ProcedureStatus = "not_started" | "in_progress" | "completed" | "not_applicable";

export const PROCEDURE_STATUSES: ProcedureStatus[] = [
  "not_started",
  "in_progress",
  "completed",
  "not_applicable",
];

export interface TemplateRecord {
  id: string;
  fs_area: string;
  title: string;
  description: string;
  isa_reference: string | null;
  assertions: string[];
  sort_order: number;
}

export interface SeedResult {
  created: number;
  skipped: number;
}

export interface ProcedureRecord {
  id: string;
  engagement_id: string;
  template_id: string | null;
  fs_area: string;
  title: string;
  description: string;
  isa_reference: string | null;
  assertions: string[];
  assigned_to: string | null;
  status: ProcedureStatus;
  due_date: string | null;
  sort_order: number;
  created_by: string;
  created_at: string;
  updated_at: string;
  linked_risk_ids: string[];
}
