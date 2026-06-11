export type RiskRating = "low" | "medium" | "high";

export interface ClientContact {
  name: string;
  position: string | null;
  email: string | null;
  phone: string | null;
}

export interface ClientRecord {
  id: string;
  name: string;
  industry: string | null;
  risk_rating: RiskRating | null;
  contacts: ClientContact[];
  archived: boolean;
  created_at: string;
  updated_at: string;
}

export const RISK_RATINGS: RiskRating[] = ["low", "medium", "high"];
