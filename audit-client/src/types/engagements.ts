export type EngagementType = "audit" | "review" | "agreed_upon_procedures" | "other";

export type EngagementStatus = "draft" | "planning" | "fieldwork" | "review" | "completed";

export interface EngagementRecord {
  id: string;
  client_id: string;
  engagement_type: EngagementType;
  fiscal_year: number;
  status: EngagementStatus;
  created_at: string;
  updated_at: string;
}

export interface TeamMemberRecord {
  clerk_user_id: string;
  role_on_engagement: string | null;
  independence_confirmed: boolean;
  independence_confirmed_at: string | null;
}

export interface EngagementDetail extends EngagementRecord {
  team: TeamMemberRecord[];
}

export const ENGAGEMENT_TYPES: EngagementType[] = [
  "audit",
  "review",
  "agreed_upon_procedures",
  "other",
];

/** Transitions the API will accept, mirrored for the UI. */
export const NEXT_STATUSES: Record<EngagementStatus, EngagementStatus[]> = {
  draft: ["planning"],
  planning: ["fieldwork"],
  fieldwork: ["review"],
  review: ["fieldwork", "completed"],
  completed: [],
};
