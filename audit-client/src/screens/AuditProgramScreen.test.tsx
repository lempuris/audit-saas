import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ProcedureRecord } from "../types/auditPrograms";
import type { EngagementDetail, TeamMemberRecord } from "../types/engagements";
import type { Me } from "../types/me";
import type { RiskRecord } from "../types/risks";
import AuditProgramScreen from "./AuditProgramScreen";

const apiMock = { get: vi.fn(), post: vi.fn(), patch: vi.fn(), put: vi.fn(), delete: vi.fn() };
const meState: { me: Me | null } = { me: null };

vi.mock("../hooks/useApi", () => ({
  useApi: () => apiMock,
}));
vi.mock("../contexts/MeContext", () => ({
  useMe: () => ({ me: meState.me, loading: false, error: null }),
}));

const engagementId = "55555555-5555-5555-5555-555555555555";

const procedure: ProcedureRecord = {
  id: "22222222-2222-2222-2222-222222222222",
  engagement_id: engagementId,
  template_id: null,
  fs_area: "revenue",
  title: "Revenue cutoff testing",
  description: "Test transactions either side of year end.",
  isa_reference: "ISA 500",
  assertions: ["cutoff"],
  assigned_to: null,
  status: "not_started",
  due_date: null,
  sort_order: 10,
  created_by: "user_1",
  created_at: "2026-06-12T08:00:00Z",
  updated_at: "2026-06-12T08:00:00Z",
  linked_risk_ids: [],
};

const risk: RiskRecord = {
  id: "11111111-1111-1111-1111-111111111111",
  engagement_id: engagementId,
  level: "assertion",
  fs_area: "revenue",
  assertions: ["occurrence"],
  description: "Revenue may be overstated",
  inherent_rating: "high",
  control_rating: "medium",
  combined_rating: "high",
  is_significant: true,
  planned_response: null,
  created_by: "user_1",
  created_at: "2026-06-12T08:00:00Z",
  updated_at: "2026-06-12T08:00:00Z",
};

const teamMember: TeamMemberRecord = {
  clerk_user_id: "user_aud",
  display_name: "Aud Itor",
  email: "aud@firm.example",
  role_on_engagement: "auditor",
  independence_confirmed: true,
  independence_confirmed_at: null,
};

const engagementDetail: EngagementDetail = {
  id: engagementId,
  client_id: "66666666-6666-6666-6666-666666666666",
  engagement_type: "audit",
  fiscal_year: 2026,
  status: "planning",
  created_at: "2026-06-12T08:00:00Z",
  updated_at: "2026-06-12T08:00:00Z",
  team: [teamMember],
};

function renderScreen() {
  return render(
    <MemoryRouter initialEntries={[`/engagements/${engagementId}/program`]}>
      <Routes>
        <Route path="/engagements/:engagementId/program" element={<AuditProgramScreen />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  apiMock.get.mockImplementation((path: string) => {
    if (path.endsWith("/risks")) return Promise.resolve([risk]);
    if (path.endsWith("/procedures")) return Promise.resolve([procedure]);
    return Promise.resolve(engagementDetail);
  });
  apiMock.post.mockResolvedValue({});
  apiMock.patch.mockResolvedValue(procedure);
  apiMock.put.mockResolvedValue(procedure);
  apiMock.delete.mockResolvedValue(undefined);
  meState.me = { user_id: "user_1", session_id: null, role: "manager" };
});

describe("AuditProgramScreen", () => {
  it("groups procedures by FS area with ISA references", async () => {
    renderScreen();
    expect(await screen.findByText("Revenue cutoff testing")).toBeInTheDocument();
    expect(screen.getByText("Revenue")).toBeInTheDocument();
    expect(screen.getByText("ISA 500")).toBeInTheDocument();
  });

  it("loads the standard program by seeding then bulk-adding", async () => {
    renderScreen();
    await screen.findByText("Revenue cutoff testing");

    fireEvent.click(screen.getByRole("button", { name: "Load standard ISA program" }));

    await waitFor(() => {
      expect(apiMock.post).toHaveBeenCalledWith("/api/procedure-templates/seed");
      expect(apiMock.post).toHaveBeenCalledWith(
        `/api/engagements/${engagementId}/procedures/from-templates`,
        {},
      );
    });
  });

  it("updates status through the dedicated endpoint", async () => {
    renderScreen();
    await screen.findByText("Revenue cutoff testing");

    fireEvent.change(screen.getByLabelText("Status of Revenue cutoff testing"), {
      target: { value: "in_progress" },
    });

    await waitFor(() =>
      expect(apiMock.patch).toHaveBeenCalledWith(
        `/api/engagements/${engagementId}/procedures/${procedure.id}/status`,
        { status: "in_progress" },
      ),
    );
  });

  it("assigns a team member via the dropdown and sets a due date via PATCH", async () => {
    renderScreen();
    await screen.findByText("Revenue cutoff testing");

    const assignee = await screen.findByLabelText("Assignee for Revenue cutoff testing");
    // The dropdown lists team members by name, not raw Clerk ids.
    expect(within(assignee).getByRole("option", { name: "Aud Itor" })).toBeInTheDocument();
    fireEvent.change(assignee, { target: { value: "user_aud" } });

    await waitFor(() =>
      expect(apiMock.patch).toHaveBeenCalledWith(
        `/api/engagements/${engagementId}/procedures/${procedure.id}`,
        { assigned_to: "user_aud" },
      ),
    );

    const due = screen.getByLabelText("Due date for Revenue cutoff testing");
    fireEvent.change(due, { target: { value: "2026-07-31" } });
    fireEvent.blur(due);

    await waitFor(() =>
      expect(apiMock.patch).toHaveBeenCalledWith(
        `/api/engagements/${engagementId}/procedures/${procedure.id}`,
        { due_date: "2026-07-31" },
      ),
    );
  });

  it("prompts to add team members when the engagement has none", async () => {
    apiMock.get.mockImplementation((path: string) => {
      if (path.endsWith("/risks")) return Promise.resolve([risk]);
      if (path.endsWith("/procedures")) return Promise.resolve([procedure]);
      return Promise.resolve({ ...engagementDetail, team: [] });
    });
    renderScreen();
    await screen.findByText("Revenue cutoff testing");

    expect(await screen.findByRole("link", { name: "Add team members" })).toBeInTheDocument();
    expect(
      screen.queryByLabelText("Assignee for Revenue cutoff testing"),
    ).not.toBeInTheDocument();
  });

  it("links a risk to a procedure", async () => {
    renderScreen();
    await screen.findByText("Revenue cutoff testing");

    fireEvent.click(screen.getByRole("button", { name: "0 linked" }));
    fireEvent.click(await screen.findByLabelText("Revenue may be overstated"));

    await waitFor(() =>
      expect(apiMock.put).toHaveBeenCalledWith(
        `/api/engagements/${engagementId}/procedures/${procedure.id}/risks`,
        { risk_ids: [risk.id] },
      ),
    );
  });

  it("auditors can change status but not tailor", async () => {
    meState.me = { user_id: "user_a", session_id: null, role: "auditor" };
    renderScreen();
    await screen.findByText("Revenue cutoff testing");

    expect(screen.getByLabelText("Status of Revenue cutoff testing")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Load standard ISA program" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Remove" })).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText("Assignee for Revenue cutoff testing"),
    ).not.toBeInTheDocument();
  });
});
