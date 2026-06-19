import type { Role } from "../types/me";

export interface NavItem {
  label: string;
  to: string;
  /** Roles that see this item; "any" = every signed-in staff member. */
  roles: Role[] | "any";
}

export const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", to: "/", roles: "any" },
  { label: "Firm dashboard", to: "/firm-dashboard", roles: ["admin", "partner", "manager"] },
  { label: "Clients", to: "/clients", roles: "any" },
  { label: "Engagements", to: "/engagements", roles: "any" },
  { label: "Audit trail", to: "/audit-trail", roles: ["admin", "partner"] },
  { label: "Users", to: "/users", roles: ["admin"] },
];

export function navItemsForRole(role: Role | null): NavItem[] {
  return NAV_ITEMS.filter(
    (item) => item.roles === "any" || (role !== null && item.roles.includes(role)),
  );
}
