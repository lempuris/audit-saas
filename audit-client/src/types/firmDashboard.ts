export interface EngagementStatusBreakdown {
  by_status: Record<string, number>;
  total: number;
}

export interface ReviewQueueItem {
  working_paper_id: string;
  engagement_id: string;
  client_name: string | null;
  fiscal_year: number;
  fs_area: string;
  index_ref: string;
  title: string;
  status: string;
  prepared_at: string | null;
  prepared_by_name: string | null;
}

export interface OverdueProcedure {
  id: string;
  engagement_id: string;
  client_name: string | null;
  fiscal_year: number;
  fs_area: string;
  title: string;
  isa_reference: string | null;
  status: string;
  due_date: string;
  days_overdue: number;
  assignee_name: string | null;
}

export interface FirmDashboard {
  engagements: EngagementStatusBreakdown;
  review_queue: ReviewQueueItem[];
  overdue_procedures: OverdueProcedure[];
  open_review_notes: number;
}
