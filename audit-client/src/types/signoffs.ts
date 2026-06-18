export type SignoffAction = "review" | "approve" | "return";

export type SignoffTargetType = "working_paper" | "fs_area";

export interface SignoffRecord {
  id: string;
  engagement_id: string;
  target_type: SignoffTargetType;
  target_id: string;
  // Past-tense event: reviewed / approved / returned.
  action: string;
  resulting_status: string;
  signed_by: string;
  note: string | null;
  created_at: string;
  signed_by_name: string | null;
}
