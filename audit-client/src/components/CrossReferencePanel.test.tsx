import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { CrossRefCandidate, CrossReferenceRecord } from "../types/crossReferences";
import CrossReferencePanel from "./CrossReferencePanel";

const apiMock = { get: vi.fn(), post: vi.fn(), patch: vi.fn(), put: vi.fn(), delete: vi.fn() };
const navigateMock = vi.fn();

vi.mock("../hooks/useApi", () => ({ useApi: () => apiMock }));
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => navigateMock };
});

const engagementId = "55555555-5555-5555-5555-555555555555";
const wpId = "11111111-1111-1111-1111-111111111111";
const base = `/api/engagements/${engagementId}/cross-references`;

const existing: CrossReferenceRecord = {
  id: "99999999-9999-9999-9999-999999999999",
  engagement_id: engagementId,
  source_type: "working_paper",
  source_id: wpId,
  target_type: "trial_balance_line",
  target_id: "tb-line-1",
  label: null,
  created_by: "user_1",
  created_at: "2026-06-13T08:00:00Z",
  source_label: "C-1 Bank rec",
  target_label: "1000 Cash at bank",
};

const candidates: CrossRefCandidate[] = [
  { type: "trial_balance_line", id: "tb-line-2", label: "2000 Trade receivables" },
  { type: "document", id: "doc-1", label: "invoice.pdf" },
  { type: "working_paper", id: wpId, label: "C-1 Bank rec" },
];

function renderPanel() {
  return render(
    <MemoryRouter>
      <CrossReferencePanel
        engagementId={engagementId}
        sourceType="working_paper"
        sourceId={wpId}
        candidates={candidates}
        canWrite
      />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  apiMock.get.mockResolvedValue([existing]);
  apiMock.post.mockResolvedValue({});
  apiMock.delete.mockResolvedValue(undefined);
});

describe("CrossReferencePanel", () => {
  it("lists existing references for the source", async () => {
    renderPanel();
    expect(await screen.findByText("1000 Cash at bank")).toBeInTheDocument();
    expect(apiMock.get).toHaveBeenCalledWith(
      `${base}?source_type=working_paper&source_id=${wpId}`,
    );
  });

  it("adds a cross-reference", async () => {
    renderPanel();
    await screen.findByText("1000 Cash at bank");

    fireEvent.change(screen.getByLabelText("Cross-reference target"), {
      target: { value: "tb-line-2" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Link" }));

    await waitFor(() =>
      expect(apiMock.post).toHaveBeenCalledWith(base, {
        source_type: "working_paper",
        source_id: wpId,
        target_type: "trial_balance_line",
        target_id: "tb-line-2",
      }),
    );
  });

  it("excludes the source itself from the target options", async () => {
    renderPanel();
    await screen.findByText("1000 Cash at bank");

    // Switch to working-paper targets; the source WP must not be offered.
    fireEvent.change(screen.getByLabelText("Cross-reference target type"), {
      target: { value: "working_paper" },
    });
    const targetSelect = screen.getByLabelText("Cross-reference target");
    expect(targetSelect).not.toHaveTextContent("C-1 Bank rec");
  });

  it("removes a cross-reference", async () => {
    renderPanel();
    await screen.findByText("1000 Cash at bank");

    fireEvent.click(
      screen.getByRole("button", { name: "Remove cross-reference to 1000 Cash at bank" }),
    );

    await waitFor(() => expect(apiMock.delete).toHaveBeenCalledWith(`${base}/${existing.id}`));
  });

  it("navigates when a reference chip is clicked", async () => {
    renderPanel();
    fireEvent.click(await screen.findByText("1000 Cash at bank"));
    expect(navigateMock).toHaveBeenCalledWith(`/engagements/${engagementId}/trial-balance`);
  });
});
