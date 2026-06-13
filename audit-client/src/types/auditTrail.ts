export interface AuditTrailRecord {
  id: string;
  created_at: string;
  actor_clerk_user_id: string;
  /** Resolved from the users mirror; null for system actors (e.g. webhook). */
  actor_name: string | null;
  actor_email: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
}

export interface AuditTrailPage {
  total: number;
  limit: number;
  offset: number;
  items: AuditTrailRecord[];
}
