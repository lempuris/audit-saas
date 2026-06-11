import type { Role } from "./me";

export interface UserRecord {
  id: string;
  clerk_user_id: string;
  email: string | null;
  first_name: string | null;
  last_name: string | null;
  role: Role | null;
  is_active: boolean;
  created_at: string;
}

export const ASSIGNABLE_ROLES: Role[] = ["admin", "partner", "manager", "auditor"];
