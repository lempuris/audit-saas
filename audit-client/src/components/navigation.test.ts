import { describe, expect, it } from "vitest";

import { navItemsForRole } from "./navigation";

const labels = (role: Parameters<typeof navItemsForRole>[0]) =>
  navItemsForRole(role).map((item) => item.label);

describe("navItemsForRole", () => {
  it("shows everything to admins", () => {
    expect(labels("admin")).toEqual([
      "Dashboard",
      "Firm dashboard",
      "Clients",
      "Engagements",
      "Audit trail",
      "Users",
    ]);
  });

  it("shows the audit trail but not users to partners", () => {
    expect(labels("partner")).toEqual([
      "Dashboard",
      "Firm dashboard",
      "Clients",
      "Engagements",
      "Audit trail",
    ]);
  });

  it("shows the firm dashboard to managers but hides admin-only items", () => {
    expect(labels("manager")).toEqual([
      "Dashboard",
      "Firm dashboard",
      "Clients",
      "Engagements",
    ]);
    expect(labels("auditor")).toEqual(["Dashboard", "Clients", "Engagements"]);
  });

  it("shows only unrestricted items when the role is missing", () => {
    expect(labels(null)).toEqual(["Dashboard", "Clients", "Engagements"]);
  });
});
