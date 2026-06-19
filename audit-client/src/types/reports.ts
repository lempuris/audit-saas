export type ReportType = "audit_report" | "management_letter";

export type OpinionType = "unmodified" | "qualified" | "adverse" | "disclaimer";

export const OPINION_TYPES: OpinionType[] = ["unmodified", "qualified", "adverse", "disclaimer"];

export type ReportStatus = "draft" | "final";

export interface ReportSection {
  key: string;
  heading: string;
  body: string;
}

export interface ReportRecord {
  id: string;
  engagement_id: string;
  report_type: ReportType;
  opinion_type: OpinionType | null;
  title: string;
  letterhead: string;
  sections: ReportSection[];
  status: ReportStatus;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export function reportTypeLabel(type: ReportType): string {
  return type === "management_letter" ? "Management letter" : "Audit report";
}
