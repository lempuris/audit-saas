import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Me } from "../types/me";
import type { ReportRecord } from "../types/reports";
import ReportsScreen from "./ReportsScreen";

const apiMock = {
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
  getBlob: vi.fn(),
};
const meState: { me: Me | null } = { me: null };

vi.mock("../hooks/useApi", () => ({
  useApi: () => apiMock,
}));
vi.mock("../contexts/MeContext", () => ({
  useMe: () => ({ me: meState.me, loading: false, error: null }),
}));

const engagementId = "55555555-5555-5555-5555-555555555555";

const auditReport: ReportRecord = {
  id: "22222222-2222-2222-2222-222222222222",
  engagement_id: engagementId,
  report_type: "audit_report",
  opinion_type: "unmodified",
  title: "Independent Auditor's Report",
  letterhead: "[Firm Name]",
  sections: [{ key: "opinion", heading: "Opinion", body: "In our opinion…" }],
  status: "draft",
  created_by: "user_1",
  created_at: "2026-06-19T08:00:00Z",
  updated_at: "2026-06-19T08:00:00Z",
};

function renderScreen() {
  return render(
    <MemoryRouter initialEntries={[`/engagements/${engagementId}/reports`]}>
      <Routes>
        <Route path="/engagements/:engagementId/reports" element={<ReportsScreen />} />
      </Routes>
    </MemoryRouter>,
  );
}

function mockReports(reports: ReportRecord[]) {
  apiMock.get.mockImplementation(() => Promise.resolve(reports));
}

beforeEach(() => {
  vi.clearAllMocks();
  mockReports([auditReport]);
  apiMock.post.mockResolvedValue(auditReport);
  apiMock.patch.mockResolvedValue(auditReport);
  apiMock.delete.mockResolvedValue(undefined);
  meState.me = { user_id: "user_1", session_id: null, role: "manager" };
});

describe("ReportsScreen", () => {
  it("creates an audit report with the chosen opinion type", async () => {
    mockReports([]);
    renderScreen();
    await screen.findByRole("button", { name: "Create audit report" });

    fireEvent.change(screen.getByLabelText("Opinion type"), { target: { value: "qualified" } });
    fireEvent.click(screen.getByRole("button", { name: "Create audit report" }));

    await waitFor(() =>
      expect(apiMock.post).toHaveBeenCalledWith(`/api/engagements/${engagementId}/reports`, {
        report_type: "audit_report",
        opinion_type: "qualified",
      }),
    );
  });

  it("edits a section body and saves via PATCH", async () => {
    renderScreen();
    await screen.findByText(/Audit report/);

    fireEvent.change(screen.getByLabelText("Body for opinion"), {
      target: { value: "Revised opinion." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(apiMock.patch).toHaveBeenCalledWith(
        `/api/engagements/${engagementId}/reports/${auditReport.id}`,
        expect.objectContaining({
          sections: [
            expect.objectContaining({ key: "opinion", body: "Revised opinion." }),
          ],
        }),
      ),
    );
  });

  it("changes the opinion type and sends it on save", async () => {
    renderScreen();
    await screen.findByText(/Audit report/);

    fireEvent.change(screen.getByLabelText("Type of opinion"), { target: { value: "adverse" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(apiMock.patch).toHaveBeenCalledWith(
        `/api/engagements/${engagementId}/reports/${auditReport.id}`,
        expect.objectContaining({ opinion_type: "adverse" }),
      ),
    );
  });

  it("hides finalize and delete from managers", async () => {
    renderScreen();
    await screen.findByText(/Audit report/);

    expect(screen.getByRole("button", { name: "Save" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Finalize" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
  });

  it("lets a partner finalize", async () => {
    meState.me = { user_id: "user_2", session_id: null, role: "partner" };
    renderScreen();
    await screen.findByText(/Audit report/);

    fireEvent.click(screen.getByRole("button", { name: "Finalize" }));

    await waitFor(() =>
      expect(apiMock.patch).toHaveBeenCalledWith(
        `/api/engagements/${engagementId}/reports/${auditReport.id}`,
        { status: "final" },
      ),
    );
  });

  it("locks a finalized report's fields from a manager", async () => {
    mockReports([{ ...auditReport, status: "final" }]);
    renderScreen();
    await screen.findByText(/Audit report/);

    expect(screen.getByLabelText("Body for opinion")).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Save" })).not.toBeInTheDocument();
  });

  it("downloads a report PDF with the auth-bearing client", async () => {
    const created: string[] = [];
    URL.createObjectURL = vi.fn(() => {
      created.push("blob:fake");
      return "blob:fake";
    });
    URL.revokeObjectURL = vi.fn();
    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);
    apiMock.getBlob.mockResolvedValue(new Blob(["%PDF"], { type: "application/pdf" }));

    renderScreen();
    await screen.findByText(/Audit report/);
    fireEvent.click(screen.getByRole("button", { name: "Download PDF" }));

    await waitFor(() =>
      expect(apiMock.getBlob).toHaveBeenCalledWith(
        `/api/engagements/${engagementId}/reports/${auditReport.id}/pdf`,
      ),
    );
    expect(created).toHaveLength(1);
    clickSpy.mockRestore();
  });

  it("hides create controls from auditors", async () => {
    mockReports([]);
    meState.me = { user_id: "user_3", session_id: null, role: "auditor" };
    renderScreen();
    await screen.findByText("No reports yet for this engagement.");

    expect(screen.queryByRole("button", { name: "Create audit report" })).not.toBeInTheDocument();
  });
});
