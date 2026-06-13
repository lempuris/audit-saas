import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../services/api";
import type { Me } from "../types/me";
import type { TickMarkApplicationRecord, TickMarkRecord } from "../types/tickMarks";
import type {
  FSAreaSummary,
  TrialBalanceDetail,
  TrialBalancePreview,
} from "../types/trialBalance";
import TrialBalanceScreen from "./TrialBalanceScreen";

const apiMock = {
  get: vi.fn(),
  postForm: vi.fn(),
  patch: vi.fn(),
  post: vi.fn(),
  delete: vi.fn(),
};
const meState: { me: Me | null } = { me: null };

vi.mock("../hooks/useApi", () => ({
  useApi: () => apiMock,
}));
vi.mock("../contexts/MeContext", () => ({
  useMe: () => ({ me: meState.me, loading: false, error: null }),
}));

const engagementId = "55555555-5555-5555-5555-555555555555";

const detail: TrialBalanceDetail = {
  id: "66666666-6666-6666-6666-666666666666",
  engagement_id: engagementId,
  source_filename: "tb.xlsx",
  imported_by: "user_1",
  created_at: "2026-06-12T08:00:00Z",
  updated_at: "2026-06-12T08:00:00Z",
  lines: [
    {
      id: "77777777-7777-7777-7777-777777777777",
      account_code: "1000",
      account_name: "Cash at bank",
      balance: "1000.00",
      prior_year_balance: "800.00",
      fs_area: "cash_and_bank",
    },
    {
      id: "88888888-8888-8888-8888-888888888888",
      account_code: "9999",
      account_name: "Suspense",
      balance: "-1000.00",
      prior_year_balance: "-800.00",
      fs_area: null,
    },
  ],
};

const summary: FSAreaSummary[] = [
  {
    fs_area: "cash_and_bank",
    line_count: 1,
    balance: "1000.00",
    prior_year_balance: "800.00",
    movement: "200.00",
  },
];

const preview: TrialBalancePreview = {
  columns: ["Acc No", "Account Name", "Balance", "Prior Year"],
  rows: [{ "Acc No": "1000", "Account Name": "Cash", Balance: "1000", "Prior Year": "800" }],
  total_rows: 10,
};

const tickMark: TickMarkRecord = {
  id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
  symbol: "✓",
  meaning: "Agreed to supporting documentation",
  sort_order: 10,
};

let tickApplications: TickMarkApplicationRecord[] = [];

/** Shared GET handler covering TB + tick-mark endpoints. */
function tbGet(path: string): Promise<unknown> {
  if (path.endsWith("/summary")) return Promise.resolve(summary);
  if (path.includes("/tick-mark-applications")) return Promise.resolve(tickApplications);
  if (path === "/api/tick-marks") return Promise.resolve([tickMark]);
  return Promise.resolve(detail);
}

function renderScreen() {
  return render(
    <MemoryRouter initialEntries={[`/engagements/${engagementId}/trial-balance`]}>
      <Routes>
        <Route
          path="/engagements/:engagementId/trial-balance"
          element={<TrialBalanceScreen />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  tickApplications = [];
  meState.me = { user_id: "user_1", session_id: null, role: "manager" };
});

describe("TrialBalanceScreen", () => {
  it("shows the import wizard when no TB exists", async () => {
    apiMock.get.mockRejectedValue(new ApiError(404, "not found"));
    renderScreen();
    expect(await screen.findByText("Import trial balance")).toBeInTheDocument();
  });

  it("previews a file and imports with the chosen mapping", async () => {
    apiMock.get.mockRejectedValue(new ApiError(404, "not found"));
    apiMock.postForm.mockImplementation((path: string) =>
      path.endsWith("/preview") ? Promise.resolve(preview) : Promise.resolve(detail),
    );
    renderScreen();

    const fileInput = (await screen.findByLabelText(/XLSX or CSV file/)) as HTMLInputElement;
    const file = new File(["data"], "tb.xlsx");
    fireEvent.change(fileInput, { target: { files: [file] } });

    // Columns are guessed from the headers after preview.
    const codeSelect = (await screen.findByLabelText(
      "Account code column",
    )) as HTMLSelectElement;
    expect(codeSelect.value).toBe("Acc No");
    expect((screen.getByLabelText("Account name column") as HTMLSelectElement).value).toBe(
      "Account Name",
    );
    expect((screen.getByLabelText("Balance column") as HTMLSelectElement).value).toBe("Balance");
    expect(
      (screen.getByLabelText("Prior-year column (optional)") as HTMLSelectElement).value,
    ).toBe("Prior Year");

    fireEvent.click(screen.getByRole("button", { name: "Import" }));

    await waitFor(() => {
      const calls = apiMock.postForm.mock.calls.filter(
        ([path]) => path === `/api/engagements/${engagementId}/trial-balance`,
      );
      expect(calls).toHaveLength(1);
      const form = calls[0][1] as FormData;
      expect(JSON.parse(form.get("mapping") as string)).toEqual({
        account_code: "Acc No",
        account_name: "Account Name",
        balance: "Balance",
        debit: null,
        credit: null,
        prior_year_balance: "Prior Year",
      });
    });
  });

  it("renders lines and FS-area summary with movement", async () => {
    apiMock.get.mockImplementation(tbGet);
    renderScreen();

    expect(await screen.findByText("Cash at bank")).toBeInTheDocument();
    expect(screen.getByText("200.00")).toBeInTheDocument(); // movement
    expect(screen.getByText(/tb\.xlsx · 2 lines/)).toBeInTheDocument();
  });

  it("saves regrouped lines", async () => {
    apiMock.get.mockImplementation(tbGet);
    apiMock.patch.mockResolvedValue([]);
    renderScreen();
    await screen.findByText("Cash at bank");

    fireEvent.change(screen.getByLabelText("FS area for 9999"), {
      target: { value: "other_assets" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save grouping (1)" }));

    await waitFor(() =>
      expect(apiMock.patch).toHaveBeenCalledWith(
        `/api/engagements/${engagementId}/trial-balance/fs-areas`,
        [{ line_id: "88888888-8888-8888-8888-888888888888", fs_area: "other_assets" }],
      ),
    );
  });

  it("hides import and editing from auditors", async () => {
    meState.me = { user_id: "user_2", session_id: null, role: "auditor" };
    apiMock.get.mockImplementation(tbGet);
    renderScreen();
    await screen.findByText("Cash at bank");
    expect(screen.queryByRole("button", { name: "Re-import" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("FS area for 9999")).not.toBeInTheDocument();
    expect(screen.getByText("Unmapped")).toBeInTheDocument();
  });

  it("renders the tick-mark legend and applies a mark to a line", async () => {
    apiMock.get.mockImplementation(tbGet);
    apiMock.post.mockResolvedValue({});
    renderScreen();
    await screen.findByText("Cash at bank");

    // Legend lists the library entry (as a list item, distinct from the apply dropdown).
    expect(screen.getByText("Tick-mark legend")).toBeInTheDocument();
    expect(screen.getByRole("listitem")).toHaveTextContent(
      "Agreed to supporting documentation",
    );

    fireEvent.change(screen.getByLabelText("Apply tick mark to 1000"), {
      target: { value: tickMark.id },
    });

    await waitFor(() =>
      expect(apiMock.post).toHaveBeenCalledWith(
        `/api/engagements/${engagementId}/tick-mark-applications`,
        {
          tick_mark_id: tickMark.id,
          target_type: "trial_balance_line",
          target_id: "77777777-7777-7777-7777-777777777777",
        },
      ),
    );
  });

  it("shows an applied tick mark and lets a manager remove it", async () => {
    tickApplications = [
      {
        id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        engagement_id: engagementId,
        tick_mark_id: tickMark.id,
        target_type: "trial_balance_line",
        target_id: "77777777-7777-7777-7777-777777777777",
        note: null,
        applied_by: "user_1",
        created_at: "2026-06-13T08:00:00Z",
        symbol: "✓",
        meaning: "Agreed to supporting documentation",
      },
    ];
    apiMock.get.mockImplementation(tbGet);
    apiMock.delete.mockResolvedValue(undefined);
    renderScreen();
    await screen.findByText("Cash at bank");

    fireEvent.click(screen.getByTitle("Agreed to supporting documentation — click to remove"));

    await waitFor(() =>
      expect(apiMock.delete).toHaveBeenCalledWith(
        `/api/engagements/${engagementId}/tick-mark-applications/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb`,
      ),
    );
  });
});
