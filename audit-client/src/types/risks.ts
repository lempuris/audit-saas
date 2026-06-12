export type RiskLevel = "entity" | "assertion";

export type RiskRating = "low" | "medium" | "high";

export const RISK_RATINGS: RiskRating[] = ["low", "medium", "high"];

export const ASSERTIONS = [
  "existence",
  "completeness",
  "accuracy",
  "valuation",
  "rights_and_obligations",
  "cutoff",
  "occurrence",
  "classification",
  "presentation",
] as const;

export type Assertion = (typeof ASSERTIONS)[number];

export interface RiskCreate {
  level: RiskLevel;
  fs_area: string | null;
  assertions: Assertion[];
  description: string;
  inherent_rating: RiskRating;
  control_rating: RiskRating;
  is_significant: boolean;
  planned_response: string | null;
}

export interface RiskRecord extends RiskCreate {
  id: string;
  engagement_id: string;
  combined_rating: RiskRating;
  created_by: string;
  created_at: string;
  updated_at: string;
}
