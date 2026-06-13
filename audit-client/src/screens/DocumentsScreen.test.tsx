import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { DocumentRecord } from "../types/documents";
import type { Me } from "../types/me";
import type { WorkingPaperRecord } from "../types/workingPapers";
import DocumentsScreen from "./DocumentsScreen";

const apiMock = { get: vi.fn(), post: vi.fn(), patch: vi.fn(), put: vi.fn(), delete: vi.fn() };
const meState: { me: Me | null } = { me: null };

vi.mock("../hooks/useApi", () => ({
  useApi: () => apiMock,
}));
vi.mock("../contexts/MeContext", () => ({
  useMe: () => ({ me: meState.me, loading: false, error: null }),
}));

const engagementId = "55555555-5555-5555-5555-555555555555";
const base = `/api/engagements/${engagementId}/documents`;

const wp: WorkingPaperRecord = {
  id: "77777777-7777-7777-7777-777777777777",
  engagement_id: engagementId,
  fs_area: "cash_and_bank",
  index_ref: "C-1",
  title: "Bank reconciliation",
  objective: "",
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

const doc: DocumentRecord = {
  id: "22222222-2222-2222-2222-222222222222",
  engagement_id: engagementId,
  working_paper_id: wp.id,
  filename: "bank-statement.pdf",
  content_type: "application/pdf",
  size_bytes: 2048,
  status: "available",
  uploaded_by: "user_1",
  created_at: "2026-06-13T08:00:00Z",
  updated_at: "2026-06-13T08:00:00Z",
};

const fetchMock = vi.fn();
const openMock = vi.fn();

function renderScreen() {
  return render(
    <MemoryRouter initialEntries={[`/engagements/${engagementId}/documents`]}>
      <Routes>
        <Route path="/engagements/:engagementId/documents" element={<DocumentsScreen />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  apiMock.get.mockImplementation((path: string) => {
    if (path.endsWith("/working-papers")) return Promise.resolve([wp]);
    if (path.endsWith("/download")) return Promise.resolve({ download_url: "https://s3.test/get" });
    return Promise.resolve([doc]);
  });
  apiMock.post.mockImplementation((path: string) => {
    if (path.endsWith("/presign-upload"))
      return Promise.resolve({ document_id: "doc-2", upload_url: "https://s3.test/put" });
    return Promise.resolve({});
  });
  apiMock.delete.mockResolvedValue(undefined);
  fetchMock.mockResolvedValue({ ok: true, status: 200 });
  vi.stubGlobal("fetch", fetchMock);
  vi.stubGlobal("open", openMock);
  meState.me = { user_id: "user_1", session_id: null, role: "auditor" };
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("DocumentsScreen", () => {
  it("lists documents with size and linked working paper", async () => {
    renderScreen();
    expect(await screen.findByText("bank-statement.pdf")).toBeInTheDocument();
    expect(screen.getByText("2.0 KB")).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "C-1 Bank reconciliation" })).toBeInTheDocument();
  });

  it("uploads via presign → S3 PUT → confirm", async () => {
    renderScreen();
    await screen.findByText("bank-statement.pdf");

    const input = screen.getByLabelText("Evidence file");
    const file = new File(["evidence"], "ev.pdf", { type: "application/pdf" });
    fireEvent.change(input, { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: "Upload" }));

    await waitFor(() =>
      expect(apiMock.post).toHaveBeenCalledWith(
        `${base}/presign-upload`,
        expect.objectContaining({ filename: "ev.pdf", content_type: "application/pdf" }),
      ),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "https://s3.test/put",
      expect.objectContaining({ method: "PUT" }),
    );
    await waitFor(() => expect(apiMock.post).toHaveBeenCalledWith(`${base}/doc-2/confirm`));
  });

  it("downloads via a presigned GET url", async () => {
    renderScreen();
    await screen.findByText("bank-statement.pdf");

    fireEvent.click(screen.getByRole("button", { name: "Download" }));

    await waitFor(() => expect(apiMock.get).toHaveBeenCalledWith(`${base}/${doc.id}/download`));
    await waitFor(() =>
      expect(openMock).toHaveBeenCalledWith("https://s3.test/get", "_blank", "noopener"),
    );
  });

  it("lets the uploader remove their document", async () => {
    renderScreen();
    await screen.findByText("bank-statement.pdf");

    fireEvent.click(screen.getByRole("button", { name: "Remove" }));

    await waitFor(() => expect(apiMock.delete).toHaveBeenCalledWith(`${base}/${doc.id}`));
  });

  it("hides remove from a non-uploader auditor", async () => {
    meState.me = { user_id: "other_user", session_id: null, role: "auditor" };
    renderScreen();
    await screen.findByText("bank-statement.pdf");

    expect(screen.queryByRole("button", { name: "Remove" })).not.toBeInTheDocument();
  });
});
