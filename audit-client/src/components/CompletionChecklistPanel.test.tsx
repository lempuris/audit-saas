import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ChecklistItemRecord, CompletionReadiness } from "../types/completion";
import CompletionChecklistPanel from "./CompletionChecklistPanel";

const apiMock = { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() };

vi.mock("../hooks/useApi", () => ({
  useApi: () => apiMock,
}));

const engagementId = "55555555-5555-5555-5555-555555555555";
const base = `/api/engagements/${engagementId}/completion-checklist`;

const item: ChecklistItemRecord = {
  id: "11111111-1111-1111-1111-111111111111",
  engagement_id: engagementId,
  item_key: "going_concern",
  category: "Going concern",
  title: "Conclude on going concern",
  isa_reference: "ISA 570",
  status: "open",
  note: null,
  resolved_by: null,
  resolved_at: null,
  sort_order: 0,
  created_at: "2026-06-19T08:00:00Z",
  updated_at: "2026-06-19T08:00:00Z",
  resolved_by_name: null,
};

function mock(items: ChecklistItemRecord[], readiness: CompletionReadiness) {
  apiMock.get.mockImplementation((path: string) => {
    if (path.endsWith("/readiness")) return Promise.resolve(readiness);
    return Promise.resolve(items);
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  apiMock.post.mockResolvedValue([]);
  apiMock.patch.mockResolvedValue(item);
});

describe("CompletionChecklistPanel", () => {
  it("offers to seed an empty checklist for a manager", async () => {
    mock([], { ready: false, total_items: 0, open_items: 0, uncleared_notes: 0 });
    render(<CompletionChecklistPanel engagementId={engagementId} canManage />);

    fireEvent.click(await screen.findByRole("button", { name: "Load standard checklist" }));

    await waitFor(() => expect(apiMock.post).toHaveBeenCalledWith(`${base}/seed`, {}));
  });

  it("hides the seed button when the user cannot manage", async () => {
    mock([], { ready: false, total_items: 0, open_items: 0, uncleared_notes: 0 });
    render(<CompletionChecklistPanel engagementId={engagementId} canManage={false} />);

    await screen.findByText(/has not been initialized/);
    expect(
      screen.queryByRole("button", { name: "Load standard checklist" }),
    ).not.toBeInTheDocument();
  });

  it("warns when not ready to close", async () => {
    mock([item], { ready: false, total_items: 1, open_items: 1, uncleared_notes: 2 });
    render(<CompletionChecklistPanel engagementId={engagementId} canManage />);

    expect(await screen.findByText(/Not ready to close/)).toBeInTheDocument();
    expect(screen.getByText(/1 open item/)).toBeInTheDocument();
    expect(screen.getByText(/2 uncleared review notes/)).toBeInTheDocument();
  });

  it("confirms readiness when everything is resolved", async () => {
    const done = { ...item, status: "complete" as const };
    mock([done], { ready: true, total_items: 1, open_items: 0, uncleared_notes: 0 });
    render(<CompletionChecklistPanel engagementId={engagementId} canManage />);

    expect(await screen.findByText(/ready to close/)).toBeInTheDocument();
  });

  it("resolves an item through PATCH", async () => {
    mock([item], { ready: false, total_items: 1, open_items: 1, uncleared_notes: 0 });
    render(<CompletionChecklistPanel engagementId={engagementId} canManage />);

    fireEvent.change(await screen.findByLabelText("Status of Conclude on going concern"), {
      target: { value: "complete" },
    });

    await waitFor(() =>
      expect(apiMock.patch).toHaveBeenCalledWith(`${base}/${item.id}`, {
        status: "complete",
        note: null,
      }),
    );
  });

  it("shows badges instead of selects for read-only users", async () => {
    mock([item], { ready: false, total_items: 1, open_items: 1, uncleared_notes: 0 });
    render(<CompletionChecklistPanel engagementId={engagementId} canManage={false} />);

    await screen.findByText("Conclude on going concern");
    expect(screen.queryByLabelText(/Status of/)).not.toBeInTheDocument();
    expect(screen.getByText("open")).toBeInTheDocument();
  });
});
