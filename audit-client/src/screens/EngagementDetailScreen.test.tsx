import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { EngagementDetail } from "../types/engagements";
import type { Me } from "../types/me";
import EngagementDetailScreen from "./EngagementDetailScreen";

const apiMock = { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() };
const meState: { me: Me | null } = { me: null };

vi.mock("../hooks/useApi", () => ({
  useApi: () => apiMock,
}));
vi.mock("../contexts/MeContext", () => ({
  useMe: () => ({ me: meState.me, loading: false, error: null }),
}));

const engagement: EngagementDetail = {
  id: "55555555-5555-5555-5555-555555555555",
  client_id: "44444444-4444-4444-4444-444444444444",
  engagement_type: "audit",
  fiscal_year: 2026,
  status: "planning",
  created_at: "2026-06-11T08:00:00Z",
  updated_at: "2026-06-11T08:00:00Z",
  team: [
    {
      clerk_user_id: "user_me",
      role_on_engagement: "staff",
      independence_confirmed: false,
      independence_confirmed_at: null,
    },
  ],
};

function renderScreen() {
  return render(
    <MemoryRouter initialEntries={[`/engagements/${engagement.id}`]}>
      <Routes>
        <Route path="engagements/:engagementId" element={<EngagementDetailScreen />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  apiMock.get.mockImplementation((path: string) => {
    if (path.startsWith("/api/engagements/")) return Promise.resolve(engagement);
    if (path.startsWith("/api/clients/")) return Promise.reject(new Error("no client"));
    return Promise.resolve([]);
  });
  apiMock.post.mockResolvedValue({});
  apiMock.patch.mockResolvedValue(engagement);
  apiMock.delete.mockResolvedValue(undefined);
  meState.me = { user_id: "user_me", session_id: null, role: "manager" };
});

describe("EngagementDetailScreen", () => {
  it("shows status, team, and pending independence", async () => {
    renderScreen();
    expect(await screen.findByText("planning")).toBeInTheDocument();
    expect(screen.getByText("user_me")).toBeInTheDocument();
    expect(screen.getByText("pending")).toBeInTheDocument();
  });

  it("offers only valid next statuses", async () => {
    renderScreen();
    await screen.findByText("planning");
    expect(screen.getByRole("button", { name: "fieldwork" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "completed" })).not.toBeInTheDocument();
  });

  it("changes status through the API", async () => {
    renderScreen();
    await screen.findByText("planning");

    fireEvent.click(screen.getByRole("button", { name: "fieldwork" }));

    await waitFor(() =>
      expect(apiMock.patch).toHaveBeenCalledWith(`/api/engagements/${engagement.id}/status`, {
        status: "fieldwork",
      }),
    );
  });

  it("lets the signed-in team member confirm independence", async () => {
    renderScreen();
    await screen.findByText("planning");

    fireEvent.click(screen.getByRole("button", { name: "Confirm my independence" }));

    await waitFor(() =>
      expect(apiMock.post).toHaveBeenCalledWith(
        `/api/engagements/${engagement.id}/team/confirm-independence`,
      ),
    );
  });

  it("adds a team member", async () => {
    renderScreen();
    await screen.findByText("planning");

    fireEvent.change(screen.getByLabelText("Member"), { target: { value: "user_new" } });
    fireEvent.change(screen.getByLabelText("Engagement role"), {
      target: { value: "engagement partner" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add to team" }));

    await waitFor(() =>
      expect(apiMock.post).toHaveBeenCalledWith(`/api/engagements/${engagement.id}/team`, {
        clerk_user_id: "user_new",
        role_on_engagement: "engagement partner",
      }),
    );
  });

  it("hides write controls from auditors", async () => {
    meState.me = { user_id: "user_other", session_id: null, role: "auditor" };
    renderScreen();
    await screen.findByText("planning");
    expect(screen.queryByRole("button", { name: "fieldwork" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add to team" })).not.toBeInTheDocument();
    // not on the team, so no confirm button either
    expect(
      screen.queryByRole("button", { name: "Confirm my independence" }),
    ).not.toBeInTheDocument();
  });
});
