import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { MyProcedure } from "../types/planning";
import type { ReviewNoteRecord } from "../types/reviewNotes";
import HomeScreen from "./HomeScreen";

const apiMock = { get: vi.fn() };

vi.mock("../hooks/useApi", () => ({
  useApi: () => apiMock,
}));

const reviewNote: ReviewNoteRecord = {
  id: "99999999-9999-9999-9999-999999999999",
  engagement_id: "55555555-5555-5555-5555-555555555555",
  working_paper_id: "77777777-7777-7777-7777-777777777777",
  text: "Explain the reconciling item",
  raised_by: "user_mgr",
  assigned_to: "user_1",
  status: "open",
  response: null,
  responded_by: null,
  responded_at: null,
  cleared_by: null,
  cleared_at: null,
  created_at: "2026-06-13T08:00:00Z",
};

function getImpl(reviewNotes: ReviewNoteRecord[], procedures: MyProcedure[]) {
  return (path: string) => {
    if (path === "/api/my-procedures") return Promise.resolve(procedures);
    if (path === "/api/me/review-notes") return Promise.resolve(reviewNotes);
    return Promise.resolve({ status: "ok", database: "ok", environment: "test" });
  };
}

const myProcedures: MyProcedure[] = [
  {
    id: "22222222-2222-2222-2222-222222222222",
    engagement_id: "55555555-5555-5555-5555-555555555555",
    engagement_status: "planning",
    fiscal_year: 2026,
    client_name: "Acme Ltd",
    fs_area: "revenue",
    title: "Revenue cutoff testing",
    isa_reference: "ISA 500",
    status: "not_started",
    due_date: "2026-06-01",
    overdue: true,
  },
];

beforeEach(() => {
  vi.clearAllMocks();
  apiMock.get.mockImplementation(getImpl([], myProcedures));
});

describe("HomeScreen", () => {
  it("lists my assigned procedures with overdue badge", async () => {
    render(
      <MemoryRouter>
        <HomeScreen />
      </MemoryRouter>,
    );
    expect(await screen.findByText("Revenue cutoff testing")).toBeInTheDocument();
    expect(screen.getByText("Acme Ltd FY2026")).toBeInTheDocument();
    expect(screen.getByText("overdue")).toBeInTheDocument();
  });

  it("shows an empty state when nothing is assigned", async () => {
    apiMock.get.mockImplementation(getImpl([], []));
    render(
      <MemoryRouter>
        <HomeScreen />
      </MemoryRouter>,
    );
    expect(await screen.findByText("Nothing assigned to you right now.")).toBeInTheDocument();
    expect(
      await screen.findByText("No open review notes assigned to you."),
    ).toBeInTheDocument();
  });

  it("lists my open review notes", async () => {
    apiMock.get.mockImplementation(getImpl([reviewNote], []));
    render(
      <MemoryRouter>
        <HomeScreen />
      </MemoryRouter>,
    );
    expect(await screen.findByText("Explain the reconciling item")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Go to engagement" })).toHaveAttribute(
      "href",
      "/engagements/55555555-5555-5555-5555-555555555555/working-papers",
    );
  });
});
