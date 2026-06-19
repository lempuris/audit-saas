import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { FirmDashboard } from "../types/firmDashboard";
import FirmDashboardScreen from "./FirmDashboardScreen";

const apiMock = { get: vi.fn() };

vi.mock("../hooks/useApi", () => ({
  useApi: () => apiMock,
}));

const dashboard: FirmDashboard = {
  engagements: {
    by_status: { draft: 1, planning: 0, fieldwork: 2, review: 1, completed: 3 },
    total: 7,
  },
  review_queue: [
    {
      working_paper_id: "wp1",
      engagement_id: "eng1",
      client_name: "Acme Ltd",
      fiscal_year: 2026,
      fs_area: "cash_and_bank",
      index_ref: "A-1",
      title: "Bank reconciliation",
      status: "reviewed",
      prepared_at: "2026-06-10T08:00:00Z",
      prepared_by_name: "Ann Auditor",
    },
  ],
  overdue_procedures: [
    {
      id: "p1",
      engagement_id: "eng1",
      client_name: "Acme Ltd",
      fiscal_year: 2026,
      fs_area: "revenue",
      title: "Revenue cutoff testing",
      isa_reference: "ISA 500",
      status: "in_progress",
      due_date: "2026-06-01",
      days_overdue: 18,
      assignee_name: "Ann Auditor",
    },
  ],
  open_review_notes: 4,
};

beforeEach(() => {
  vi.clearAllMocks();
  apiMock.get.mockResolvedValue(dashboard);
});

function renderScreen() {
  render(
    <MemoryRouter>
      <FirmDashboardScreen />
    </MemoryRouter>,
  );
}

describe("FirmDashboardScreen", () => {
  it("shows engagement status counts and the total", async () => {
    renderScreen();
    expect(await screen.findByText("Firm dashboard")).toBeInTheDocument();
    // total tile
    expect(screen.getByText("7")).toBeInTheDocument();
    expect(screen.getByText("fieldwork")).toBeInTheDocument();
  });

  it("lists the review queue and overdue procedures", async () => {
    renderScreen();
    expect(await screen.findByText("Bank reconciliation")).toBeInTheDocument();
    expect(screen.getByText("partner approval")).toBeInTheDocument();
    expect(screen.getByText("Revenue cutoff testing")).toBeInTheDocument();
    expect(screen.getByText("18d overdue")).toBeInTheDocument();
    expect(screen.getByText(/4/)).toBeInTheDocument();
  });

  it("shows empty states when nothing is queued", async () => {
    apiMock.get.mockResolvedValue({
      ...dashboard,
      review_queue: [],
      overdue_procedures: [],
    });
    renderScreen();
    expect(
      await screen.findByText("No working papers are awaiting review."),
    ).toBeInTheDocument();
    expect(screen.getByText("No overdue procedures.")).toBeInTheDocument();
  });
});
