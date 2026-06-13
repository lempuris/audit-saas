import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AuditTrailPage } from "../types/auditTrail";
import AuditTrailScreen from "./AuditTrailScreen";

const apiMock = { get: vi.fn() };

vi.mock("../hooks/useApi", () => ({
  useApi: () => apiMock,
}));

const page: AuditTrailPage = {
  total: 1,
  limit: 50,
  offset: 0,
  items: [
    {
      id: "22222222-2222-2222-2222-222222222222",
      created_at: "2026-06-11T09:30:00Z",
      actor_clerk_user_id: "user_admin",
      actor_name: "Ada Partner",
      actor_email: "ada@firm.example",
      action: "update",
      entity_type: "client",
      entity_id: "33333333-3333-3333-3333-333333333333",
      before: { risk_rating: "medium" },
      after: { risk_rating: "high" },
    },
  ],
};

beforeEach(() => {
  vi.clearAllMocks();
  apiMock.get.mockResolvedValue(page);
});

describe("AuditTrailScreen", () => {
  it("renders entries with the resolved actor and before/after changes", async () => {
    render(<AuditTrailScreen />);
    expect(await screen.findByText("Ada Partner")).toBeInTheDocument();
    expect(screen.getByText("ada@firm.example")).toBeInTheDocument();
    expect(screen.getByText("update")).toBeInTheDocument();
    expect(screen.getByText('risk_rating: "medium"')).toBeInTheDocument();
    expect(screen.getByText('risk_rating: "high"')).toBeInTheDocument();
    expect(apiMock.get).toHaveBeenCalledWith("/api/audit-trail?limit=50&offset=0");
  });

  it("applies the entity type filter", async () => {
    render(<AuditTrailScreen />);
    await screen.findByText("Ada Partner");

    fireEvent.change(screen.getByLabelText("Entity type"), { target: { value: "client" } });

    await waitFor(() =>
      expect(apiMock.get).toHaveBeenCalledWith(
        "/api/audit-trail?limit=50&offset=0&entity_type=client",
      ),
    );
  });

  it("surfaces API failures", async () => {
    apiMock.get.mockRejectedValue(new Error("forbidden"));
    render(<AuditTrailScreen />);
    expect(await screen.findByText("forbidden")).toBeInTheDocument();
  });
});
