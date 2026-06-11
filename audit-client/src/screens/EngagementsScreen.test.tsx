import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ClientRecord } from "../types/clients";
import type { EngagementRecord } from "../types/engagements";
import type { Me } from "../types/me";
import EngagementsScreen from "./EngagementsScreen";

const apiMock = { get: vi.fn(), post: vi.fn() };
const meState: { me: Me | null } = { me: null };

vi.mock("../hooks/useApi", () => ({
  useApi: () => apiMock,
}));
vi.mock("../contexts/MeContext", () => ({
  useMe: () => ({ me: meState.me, loading: false, error: null }),
}));

const clientRow: ClientRecord = {
  id: "44444444-4444-4444-4444-444444444444",
  name: "Kilimanjaro Traders Ltd",
  industry: null,
  risk_rating: null,
  contacts: [],
  archived: false,
  created_at: "2026-06-11T08:00:00Z",
  updated_at: "2026-06-11T08:00:00Z",
};

const engagements: EngagementRecord[] = [
  {
    id: "55555555-5555-5555-5555-555555555555",
    client_id: clientRow.id,
    engagement_type: "audit",
    fiscal_year: 2026,
    status: "draft",
    created_at: "2026-06-11T08:00:00Z",
    updated_at: "2026-06-11T08:00:00Z",
  },
];

function renderScreen() {
  return render(
    <MemoryRouter>
      <EngagementsScreen />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  apiMock.get.mockImplementation((path: string) =>
    path.startsWith("/api/clients") ? Promise.resolve([clientRow]) : Promise.resolve(engagements),
  );
  apiMock.post.mockResolvedValue(engagements[0]);
  meState.me = { user_id: "user_1", session_id: null, role: "manager" };
});

describe("EngagementsScreen", () => {
  it("lists engagements with resolved client names", async () => {
    renderScreen();
    expect(await screen.findByText("Kilimanjaro Traders Ltd")).toBeInTheDocument();
    expect(screen.getByText("FY2026")).toBeInTheDocument();
    expect(screen.getByText("draft")).toBeInTheDocument();
  });

  it("creates an engagement", async () => {
    renderScreen();
    await screen.findByText("Kilimanjaro Traders Ltd");

    fireEvent.click(screen.getByRole("button", { name: "New engagement" }));
    fireEvent.change(screen.getByLabelText("Client"), { target: { value: clientRow.id } });
    fireEvent.change(screen.getByLabelText("Fiscal year"), { target: { value: "2025" } });
    fireEvent.click(screen.getByRole("button", { name: "Create" }));

    await waitFor(() =>
      expect(apiMock.post).toHaveBeenCalledWith("/api/engagements", {
        client_id: clientRow.id,
        engagement_type: "audit",
        fiscal_year: 2025,
      }),
    );
  });

  it("hides creation from auditors", async () => {
    meState.me = { user_id: "user_2", session_id: null, role: "auditor" };
    renderScreen();
    await screen.findByText("Kilimanjaro Traders Ltd");
    expect(screen.queryByRole("button", { name: "New engagement" })).not.toBeInTheDocument();
  });
});
