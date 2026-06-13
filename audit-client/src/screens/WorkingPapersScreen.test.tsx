import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Me } from "../types/me";
import type { WorkingPaperRecord, WorkingPaperVersionRecord } from "../types/workingPapers";
import WorkingPapersScreen from "./WorkingPapersScreen";

const apiMock = { get: vi.fn(), post: vi.fn(), patch: vi.fn(), put: vi.fn(), delete: vi.fn() };
const meState: { me: Me | null } = { me: null };

vi.mock("../hooks/useApi", () => ({
  useApi: () => apiMock,
}));
vi.mock("../contexts/MeContext", () => ({
  useMe: () => ({ me: meState.me, loading: false, error: null }),
}));

const engagementId = "55555555-5555-5555-5555-555555555555";

const paper: WorkingPaperRecord = {
  id: "22222222-2222-2222-2222-222222222222",
  engagement_id: engagementId,
  fs_area: "cash_and_bank",
  index_ref: "C-1",
  title: "Bank reconciliation",
  objective: "Confirm the year-end bank balance.",
  result: "",
  conclusion: "",
  status: "draft",
  procedure_id: null,
  prepared_by: null,
  prepared_at: null,
  created_by: "user_1",
  created_at: "2026-06-13T08:00:00Z",
  updated_at: "2026-06-13T08:00:00Z",
  current_version: 1,
};

const version: WorkingPaperVersionRecord = {
  id: "33333333-3333-3333-3333-333333333333",
  working_paper_id: paper.id,
  version_no: 1,
  index_ref: "C-1",
  fs_area: "cash_and_bank",
  title: "Bank reconciliation",
  objective: "Confirm the year-end bank balance.",
  result: "",
  conclusion: "",
  status: "draft",
  edited_by: "user_1",
  created_at: "2026-06-13T08:00:00Z",
};

function renderScreen() {
  return render(
    <MemoryRouter initialEntries={[`/engagements/${engagementId}/working-papers`]}>
      <Routes>
        <Route
          path="/engagements/:engagementId/working-papers"
          element={<WorkingPapersScreen />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  apiMock.get.mockImplementation((path: string) => {
    if (path.endsWith("/versions")) return Promise.resolve([version]);
    if (path.includes("/trial-balance")) return Promise.resolve({ lines: [] });
    if (path.includes("/documents")) return Promise.resolve([]);
    if (path.includes("/cross-references")) return Promise.resolve([]);
    return Promise.resolve([paper]);
  });
  apiMock.post.mockResolvedValue(paper);
  apiMock.patch.mockResolvedValue(paper);
  apiMock.delete.mockResolvedValue(undefined);
  meState.me = { user_id: "user_1", session_id: null, role: "auditor" };
});

describe("WorkingPapersScreen", () => {
  it("groups papers by FS area and shows the index ref and current version", async () => {
    renderScreen();
    expect(await screen.findByText("Bank reconciliation")).toBeInTheDocument();
    expect(screen.getByText("Cash and bank")).toBeInTheDocument();
    expect(screen.getByText("C-1")).toBeInTheDocument();
    expect(screen.getByText(/v1/)).toBeInTheDocument();
  });

  it("creates a working paper", async () => {
    renderScreen();
    await screen.findByText("Bank reconciliation");

    fireEvent.click(screen.getByRole("button", { name: "New working paper" }));
    const fsArea = screen.getByText("FS area").closest("label")!.querySelector("select")!;
    fireEvent.change(fsArea, { target: { value: "cash_and_bank" } });
    fireEvent.change(screen.getByPlaceholderText("e.g. C-1"), { target: { value: "C-2" } });
    const title = screen.getByText("Title").closest("label")!.querySelector("input")!;
    fireEvent.change(title, { target: { value: "Cash count" } });
    fireEvent.click(screen.getByRole("button", { name: "Create" }));

    await waitFor(() =>
      expect(apiMock.post).toHaveBeenCalledWith(
        `/api/engagements/${engagementId}/working-papers`,
        expect.objectContaining({ fs_area: "cash_and_bank", index_ref: "C-2", title: "Cash count" }),
      ),
    );
  });

  it("edits objective/result/conclusion via PATCH", async () => {
    renderScreen();
    await screen.findByText("Bank reconciliation");

    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    fireEvent.change(screen.getByLabelText("Result for C-1"), {
      target: { value: "No exceptions." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(apiMock.patch).toHaveBeenCalledWith(
        `/api/engagements/${engagementId}/working-papers/${paper.id}`,
        expect.objectContaining({ result: "No exceptions." }),
      ),
    );
  });

  it("changes status through the dedicated endpoint", async () => {
    renderScreen();
    await screen.findByText("Bank reconciliation");

    fireEvent.change(screen.getByLabelText("Status of C-1"), { target: { value: "prepared" } });

    await waitFor(() =>
      expect(apiMock.patch).toHaveBeenCalledWith(
        `/api/engagements/${engagementId}/working-papers/${paper.id}/status`,
        { status: "prepared" },
      ),
    );
  });

  it("loads version history on demand", async () => {
    renderScreen();
    await screen.findByText("Bank reconciliation");

    fireEvent.click(screen.getByRole("button", { name: "History" }));

    await waitFor(() =>
      expect(apiMock.get).toHaveBeenCalledWith(
        `/api/engagements/${engagementId}/working-papers/${paper.id}/versions`,
      ),
    );
    expect(await screen.findByText("Version history")).toBeInTheDocument();
  });

  it("hides delete for auditors but keeps edit", async () => {
    renderScreen();
    await screen.findByText("Bank reconciliation");

    expect(screen.getByRole("button", { name: "Edit" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Remove" })).not.toBeInTheDocument();
  });

  it("shows delete for managers", async () => {
    meState.me = { user_id: "user_2", session_id: null, role: "manager" };
    renderScreen();
    await screen.findByText("Bank reconciliation");

    expect(screen.getByRole("button", { name: "Remove" })).toBeInTheDocument();
  });
});
