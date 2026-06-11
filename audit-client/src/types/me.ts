export type Role = "admin" | "partner" | "manager" | "auditor";

export interface Me {
  user_id: string;
  session_id: string | null;
  role: Role | null;
}
