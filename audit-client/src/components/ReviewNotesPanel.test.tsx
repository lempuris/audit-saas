import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { TeamMemberRecord } from "../types/engagements";
import type { Me } from "../types/me";
import type { ReviewNoteRecord } from "../types/reviewNotes";
import ReviewNotesPanel from "./ReviewNotesPanel";

const apiMock = { get: vi.fn(), post: vi.fn(), patch: vi.fn(), put: vi.fn(), delete: vi.fn() };
const meState: { me: Me | null } = { me: null };

vi.mock("../hooks/useApi", () => ({ useApi: () => apiMock }));
vi.mock("../contexts/MeContext", () => ({
  useMe: () => ({ me: meState.me, loading: false, error: null }),
}));

const engagementId = "55555555-5555-5555-5555-555555555555";
const wpId = "77777777-7777-7777-7777-777777777777";
const base = `/api/engagements/${engagementId}/review-notes`;

const team: TeamMemberRecord[] = [
  {
    clerk_user_id: "user_aud",
    display_name: "Aud Itor",
    email: "aud@firm.example",
    role_on_engagement: "auditor",
    independence_confirmed: true,
    independence_confirmed_at: null,
  },
];

const openNote: ReviewNoteRecord = {
  id: "11111111-1111-1111-1111-111111111111",
  engagement_id: engagementId,
  working_paper_id: wpId,
  text: "Explain the reconciling item",
  raised_by: "user_mgr",
  assigned_to: "user_aud",
  status: "open",
  response: null,
  responded_by: null,
  responded_at: null,
  cleared_by: null,
  cleared_at: null,
  created_at: "2026-06-13T08:00:00Z",
};

function renderPanel() {
  return render(
    <ReviewNotesPanel engagementId={engagementId} workingPaperId={wpId} team={team} />,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  apiMock.get.mockResolvedValue([openNote]);
  apiMock.post.mockResolvedValue({});
  apiMock.patch.mockResolvedValue({});
  meState.me = { user_id: "user_aud", session_id: null, role: "auditor" };
});

describe("ReviewNotesPanel", () => {
  it("lists notes scoped to the working paper", async () => {
    renderPanel();
    expect(await screen.findByText("Explain the reconciling item")).toBeInTheDocument();
    expect(apiMock.get).toHaveBeenCalledWith(`${base}?working_paper_id=${wpId}`);
  });

  it("lets an assignee respond", async () => {
    renderPanel();
    await screen.findByText("Explain the reconciling item");

    fireEvent.change(screen.getByLabelText(`Respond to note ${openNote.id}`), {
      target: { value: "Agreed to bank confirmation" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Respond" }));

    await waitFor(() =>
      expect(apiMock.patch).toHaveBeenCalledWith(`${base}/${openNote.id}/respond`, {
        response: "Agreed to bank confirmation",
      }),
    );
  });

  it("hides the raise form and clear button from a non-reviewer non-author", async () => {
    renderPanel();
    await screen.findByText("Explain the reconciling item");
    expect(screen.queryByLabelText("New review note")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Clear" })).not.toBeInTheDocument();
  });

  it("lets a reviewer raise and clear notes", async () => {
    meState.me = { user_id: "user_mgr", session_id: null, role: "manager" };
    renderPanel();
    await screen.findByText("Explain the reconciling item");

    fireEvent.change(screen.getByLabelText("New review note"), {
      target: { value: "Add the lead schedule reference" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Raise" }));
    await waitFor(() =>
      expect(apiMock.post).toHaveBeenCalledWith(
        base,
        expect.objectContaining({
          text: "Add the lead schedule reference",
          working_paper_id: wpId,
        }),
      ),
    );

    fireEvent.click(screen.getByRole("button", { name: "Clear" }));
    await waitFor(() =>
      expect(apiMock.patch).toHaveBeenCalledWith(`${base}/${openNote.id}/clear`, {}),
    );
  });
});
