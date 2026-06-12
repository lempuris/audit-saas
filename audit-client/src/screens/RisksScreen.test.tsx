import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Me } from "../types/me";
import type { RiskRecord } from "../types/risks";
import RisksScreen from "./RisksScreen";

const apiMock = { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() };
const meState: { me: Me | null } = { me: null };

vi.mock("../hooks/useApi", () => ({
  useApi: () => apiMock,
}));
vi.mock("../contexts/MeContext", () => ({
  useMe: () => ({ me: meState.me, loading: false, error: null }),
}));

const engagementId = "55555555-5555-5555-5555-555555555555";

const risk: RiskRecord = {
  id: "11111111-1111-1111-1111-111111111111",
  engagement_id: engagementId,
  level: "assertion",
  fs_area: "revenue",
  assertions: ["occurrence", "cutoff"],
  description: "Revenue may be overstated near year end",
  inherent_rating: "high",
  control_rating: "medium",
  combined_rating: "high",
  is_significant: true,
  planned_response: "Extended cutoff testing",
  created_by: "user_1",
  created_at: "2026-06-12T08:00:00Z",
  updated_at: "2026-06-12T08:00:00Z",
};

function renderScreen() {
  return render(
    <MemoryRouter initialEntries={[`/engagements/${engagementId}/risks`]}>
      <Routes>
        <Route path="/engagements/:engagementId/risks" element={<RisksScreen />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  apiMock.get.mockResolvedValue([risk]);
  meState.me = { user_id: "user_1", session_id: null, role: "manager" };
});

describe("RisksScreen", () => {
  it("lists risks with ratings and significant flag", async () => {
    renderScreen();
    expect(
      await screen.findByText("Revenue may be overstated near year end"),
    ).toBeInTheDocument();
    expect(screen.getByText("significant")).toBeInTheDocument();
    expect(screen.getByText("occurrence, cutoff")).toBeInTheDocument();
    expect(screen.getAllByText("high")).toHaveLength(2); // inherent + combined
    expect(screen.getByText("medium")).toBeInTheDocument();
  });

  it("creates an assertion-level risk", async () => {
    apiMock.post.mockResolvedValue(risk);
    renderScreen();
    await screen.findByText("Revenue may be overstated near year end");

    fireEvent.click(screen.getByRole("button", { name: "New risk" }));
    fireEvent.change(screen.getByLabelText("FS area"), { target: { value: "revenue" } });
    fireEvent.click(screen.getByLabelText("occurrence"));
    fireEvent.change(screen.getByLabelText("Description"), {
      target: { value: "New risk description" },
    });
    fireEvent.change(screen.getByLabelText("Inherent risk"), { target: { value: "high" } });
    fireEvent.click(screen.getByRole("button", { name: "Add risk" }));

    await waitFor(() =>
      expect(apiMock.post).toHaveBeenCalledWith(`/api/engagements/${engagementId}/risks`, {
        level: "assertion",
        fs_area: "revenue",
        assertions: ["occurrence"],
        description: "New risk description",
        inherent_rating: "high",
        control_rating: "medium",
        is_significant: false,
        planned_response: null,
      }),
    );
  });

  it("edits a risk without sending level", async () => {
    apiMock.patch.mockResolvedValue(risk);
    renderScreen();
    await screen.findByText("Revenue may be overstated near year end");

    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    fireEvent.change(screen.getByLabelText("Description"), {
      target: { value: "Updated description" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

    await waitFor(() =>
      expect(apiMock.patch).toHaveBeenCalledWith(
        `/api/engagements/${engagementId}/risks/${risk.id}`,
        {
          fs_area: "revenue",
          assertions: ["occurrence", "cutoff"],
          description: "Updated description",
          inherent_rating: "high",
          control_rating: "medium",
          is_significant: true,
          planned_response: "Extended cutoff testing",
        },
      ),
    );
  });

  it("deletes a risk", async () => {
    apiMock.delete.mockResolvedValue(undefined);
    renderScreen();
    await screen.findByText("Revenue may be overstated near year end");
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    await waitFor(() =>
      expect(apiMock.delete).toHaveBeenCalledWith(
        `/api/engagements/${engagementId}/risks/${risk.id}`,
      ),
    );
  });

  it("auditors get a read-only register", async () => {
    meState.me = { user_id: "user_a", session_id: null, role: "auditor" };
    renderScreen();
    await screen.findByText("Revenue may be overstated near year end");
    expect(screen.queryByRole("button", { name: "New risk" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
  });
});
