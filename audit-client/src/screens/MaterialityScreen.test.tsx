import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../services/api";
import type { MaterialityRecord } from "../types/materiality";
import type { Me } from "../types/me";
import MaterialityScreen from "./MaterialityScreen";

const apiMock = { get: vi.fn(), put: vi.fn(), post: vi.fn() };
const meState: { me: Me | null } = { me: null };

vi.mock("../hooks/useApi", () => ({
  useApi: () => apiMock,
}));
vi.mock("../contexts/MeContext", () => ({
  useMe: () => ({ me: meState.me, loading: false, error: null }),
}));

const engagementId = "55555555-5555-5555-5555-555555555555";

const record: MaterialityRecord = {
  id: "99999999-9999-9999-9999-999999999999",
  engagement_id: engagementId,
  benchmark: "revenue",
  benchmark_amount: "1000000.00",
  overall_percentage: "1.00",
  overall_materiality: "10000.00",
  performance_percentage: "75.00",
  performance_materiality: "7500.00",
  clearly_trivial_percentage: "5.00",
  clearly_trivial_threshold: "500.00",
  rationale: "Revenue is stable",
  status: "draft",
  approved_by: null,
  approved_at: null,
  created_at: "2026-06-12T08:00:00Z",
  updated_at: "2026-06-12T08:00:00Z",
};

function renderScreen() {
  return render(
    <MemoryRouter initialEntries={[`/engagements/${engagementId}/materiality`]}>
      <Routes>
        <Route path="/engagements/:engagementId/materiality" element={<MaterialityScreen />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  meState.me = { user_id: "user_1", session_id: null, role: "manager" };
});

describe("MaterialityScreen", () => {
  it("saves a new assessment", async () => {
    apiMock.get.mockRejectedValue(new ApiError(404, "none"));
    apiMock.put.mockResolvedValue(record);
    renderScreen();

    fireEvent.change(await screen.findByLabelText(/Benchmark amount/), {
      target: { value: "1000000" },
    });
    fireEvent.change(screen.getByLabelText(/Rationale/), {
      target: { value: "Revenue is stable" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(apiMock.put).toHaveBeenCalledWith(
        `/api/engagements/${engagementId}/materiality`,
        {
          benchmark: "revenue",
          benchmark_amount: "1000000",
          overall_percentage: "1",
          performance_percentage: "75",
          clearly_trivial_percentage: "5",
          rationale: "Revenue is stable",
        },
      ),
    );
  });

  it("shows computed thresholds and lets a partner approve", async () => {
    meState.me = { user_id: "user_p", session_id: null, role: "partner" };
    apiMock.get.mockResolvedValue(record);
    apiMock.post.mockResolvedValue({ ...record, status: "approved" });
    renderScreen();

    expect(await screen.findByText("10000.00")).toBeInTheDocument();
    expect(screen.getByText("7500.00")).toBeInTheDocument();
    expect(screen.getByText("500.00")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Approve and lock" }));
    await waitFor(() =>
      expect(apiMock.post).toHaveBeenCalledWith(
        `/api/engagements/${engagementId}/materiality/approve`,
      ),
    );
  });

  it("managers cannot approve", async () => {
    apiMock.get.mockResolvedValue(record);
    renderScreen();
    await screen.findByText("10000.00");
    expect(screen.queryByRole("button", { name: "Approve and lock" })).not.toBeInTheDocument();
  });

  it("locks the form when approved and offers reopen to partners", async () => {
    meState.me = { user_id: "user_p", session_id: null, role: "partner" };
    apiMock.get.mockResolvedValue({
      ...record,
      status: "approved",
      approved_by: "user_p",
      approved_at: "2026-06-12T09:00:00Z",
    });
    renderScreen();

    expect(await screen.findByText(/Approved and locked by user_p/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Save" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reopen" })).toBeInTheDocument();
  });

  it("auditors see thresholds but no form", async () => {
    meState.me = { user_id: "user_a", session_id: null, role: "auditor" };
    apiMock.get.mockResolvedValue(record);
    renderScreen();
    expect(await screen.findByText("10000.00")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Save" })).not.toBeInTheDocument();
  });
});
