import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Me } from "../types/me";
import type { SampleComputation, SampleRecord } from "../types/sampling";
import SamplingScreen from "./SamplingScreen";

const apiMock = { get: vi.fn(), post: vi.fn(), patch: vi.fn(), put: vi.fn(), delete: vi.fn() };
const meState: { me: Me | null } = { me: null };

vi.mock("../hooks/useApi", () => ({ useApi: () => apiMock }));
vi.mock("../contexts/MeContext", () => ({
  useMe: () => ({ me: meState.me, loading: false, error: null }),
}));

const engagementId = "55555555-5555-5555-5555-555555555555";
const base = `/api/engagements/${engagementId}/samples`;

const computation: SampleComputation = {
  method: "monetary_unit",
  sample_size: 60,
  reliability_factor: "3.00",
  selection_basis: { interval: "16666.67", random_seed: 123, selected_monetary_units: [1, 2] },
};

const sample: SampleRecord = {
  id: "22222222-2222-2222-2222-222222222222",
  engagement_id: engagementId,
  working_paper_id: null,
  fs_area: "revenue",
  population_description: "Revenue invoices",
  method: "monetary_unit",
  population_size: null,
  population_value: "1000000.00",
  tolerable_misstatement: "50000.00",
  expected_misstatement: "0.00",
  confidence_level: 95,
  reliability_factor: "3.00",
  sample_size: 60,
  selection_basis: { interval: "16666.67" },
  created_by: "user_1",
  created_at: "2026-06-13T08:00:00Z",
};

function renderScreen() {
  return render(
    <MemoryRouter initialEntries={[`/engagements/${engagementId}/sampling`]}>
      <Routes>
        <Route path="/engagements/:engagementId/sampling" element={<SamplingScreen />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  apiMock.get.mockImplementation((path: string) => {
    if (path.endsWith("/working-papers")) return Promise.resolve([]);
    return Promise.resolve([sample]);
  });
  apiMock.post.mockResolvedValue(computation);
  apiMock.delete.mockResolvedValue(undefined);
  meState.me = { user_id: "user_1", session_id: null, role: "auditor" };
});

describe("SamplingScreen", () => {
  it("lists existing samples", async () => {
    renderScreen();
    expect(await screen.findByText("Revenue invoices")).toBeInTheDocument();
    expect(screen.getByText(/size 60/)).toBeInTheDocument();
  });

  it("computes a sample then saves it", async () => {
    renderScreen();
    await screen.findByText("Revenue invoices");

    const desc = screen.getByText("Population description").closest("label")!.querySelector("input")!;
    fireEvent.change(desc, { target: { value: "Revenue invoices" } });
    fireEvent.change(
      screen.getByText("Population value").closest("label")!.querySelector("input")!,
      { target: { value: "1000000" } },
    );
    fireEvent.change(
      screen.getByText("Tolerable misstatement").closest("label")!.querySelector("input")!,
      { target: { value: "50000" } },
    );

    fireEvent.click(screen.getByRole("button", { name: "Compute sample" }));

    await waitFor(() =>
      expect(apiMock.post).toHaveBeenCalledWith(
        `${base}/preview`,
        expect.objectContaining({ method: "monetary_unit", population_value: "1000000" }),
      ),
    );
    // The computed size is shown and a Save button appears.
    expect(await screen.findByText(/Sample size:/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Save sample" }));
    await waitFor(() =>
      expect(apiMock.post).toHaveBeenCalledWith(
        base,
        expect.objectContaining({ method: "monetary_unit" }),
      ),
    );
  });

  it("requires population size for random sampling", async () => {
    renderScreen();
    await screen.findByText("Revenue invoices");

    fireEvent.change(screen.getByText("Method").closest("label")!.querySelector("select")!, {
      target: { value: "random" },
    });
    expect(screen.getByText("Population size (items)")).toBeInTheDocument();
  });

  it("removes a sample", async () => {
    renderScreen();
    await screen.findByText("Revenue invoices");
    fireEvent.click(screen.getByRole("button", { name: "Remove" }));
    await waitFor(() => expect(apiMock.delete).toHaveBeenCalledWith(`${base}/${sample.id}`));
  });
});
