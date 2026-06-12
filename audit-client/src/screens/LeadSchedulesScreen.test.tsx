import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../services/api";
import type { LeadSchedule, LeadScheduleSummary } from "../types/planning";
import LeadSchedulesScreen from "./LeadSchedulesScreen";

const apiMock = { get: vi.fn() };

vi.mock("../hooks/useApi", () => ({
  useApi: () => apiMock,
}));
vi.mock("../contexts/MeContext", () => ({
  useMe: () => ({ me: { user_id: "user_1", session_id: null, role: "manager" } }),
}));

const engagementId = "55555555-5555-5555-5555-555555555555";

const index: LeadScheduleSummary[] = [
  {
    fs_area: "cash_and_bank",
    line_count: 2,
    balance: "150.00",
    prior_year_balance: "150.00",
    movement: "0.00",
  },
];

const detail: LeadSchedule = {
  ...index[0],
  lines: [
    {
      line_id: "77777777-7777-7777-7777-777777777777",
      account_code: "1000",
      account_name: "Cash at bank",
      balance: "100.00",
      prior_year_balance: "80.00",
      movement: "20.00",
    },
    {
      line_id: "88888888-8888-8888-8888-888888888888",
      account_code: "1010",
      account_name: "Petty cash",
      balance: "50.00",
      prior_year_balance: "70.00",
      movement: "-20.00",
    },
  ],
};

function renderScreen() {
  return render(
    <MemoryRouter initialEntries={[`/engagements/${engagementId}/lead-schedules`]}>
      <Routes>
        <Route
          path="/engagements/:engagementId/lead-schedules"
          element={<LeadSchedulesScreen />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("LeadSchedulesScreen", () => {
  it("lists per-area totals and opens a schedule", async () => {
    apiMock.get.mockImplementation((path: string) =>
      path.endsWith("/lead-schedules") ? Promise.resolve(index) : Promise.resolve(detail),
    );
    renderScreen();

    fireEvent.click(await screen.findByRole("button", { name: "Cash and bank" }));

    expect(await screen.findByText("Cash at bank")).toBeInTheDocument();
    expect(screen.getByText("Petty cash")).toBeInTheDocument();
    expect(screen.getByText("20.00")).toBeInTheDocument();
    expect(screen.getByText("Total")).toBeInTheDocument();
    expect(apiMock.get).toHaveBeenCalledWith(
      `/api/engagements/${engagementId}/lead-schedules/cash_and_bank`,
    );
  });

  it("points to the TB import when none exists", async () => {
    apiMock.get.mockRejectedValue(new ApiError(404, "no tb"));
    renderScreen();
    expect(
      await screen.findByText(/Lead schedules are generated from the trial balance/),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "import one first" })).toBeInTheDocument();
  });
});
