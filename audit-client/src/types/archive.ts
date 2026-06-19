export interface ArchiveRecord {
  id: string;
  engagement_id: string;
  archived_by: string;
  archived_at: string;
  retention_years: number;
  retention_until: string;
  note: string | null;
  created_at: string;
  archived_by_name: string | null;
}
