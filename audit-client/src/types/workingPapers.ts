export type WorkingPaperStatus = "draft" | "prepared";

export const WORKING_PAPER_STATUSES: WorkingPaperStatus[] = ["draft", "prepared"];

export interface WorkingPaperRecord {
  id: string;
  engagement_id: string;
  fs_area: string;
  index_ref: string;
  title: string;
  objective: string;
  result: string;
  conclusion: string;
  status: WorkingPaperStatus;
  procedure_id: string | null;
  prepared_by: string | null;
  prepared_at: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
  current_version: number;
  prepared_by_name: string | null;
}

export interface WorkingPaperVersionRecord {
  id: string;
  working_paper_id: string;
  version_no: number;
  index_ref: string;
  fs_area: string;
  title: string;
  objective: string;
  result: string;
  conclusion: string;
  status: string;
  edited_by: string;
  created_at: string;
  edited_by_name: string | null;
}
