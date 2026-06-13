export type ReviewNoteStatus = "open" | "responded" | "cleared";

export interface ReviewNoteRecord {
  id: string;
  engagement_id: string;
  working_paper_id: string | null;
  text: string;
  raised_by: string;
  assigned_to: string | null;
  status: ReviewNoteStatus;
  response: string | null;
  responded_by: string | null;
  responded_at: string | null;
  cleared_by: string | null;
  cleared_at: string | null;
  created_at: string;
}
