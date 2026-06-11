import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Me } from "../types/me";
import type { ClientRecord } from "../types/clients";
import ClientsScreen from "./ClientsScreen";

const apiMock = { get: vi.fn(), post: vi.fn() };
const meState: { me: Me | null } = { me: null };

vi.mock("../hooks/useApi", () => ({
  useApi: () => apiMock,
}));
vi.mock("../contexts/MeContext", () => ({
  useMe: () => ({ me: meState.me, loading: false, error: null }),
}));

const clients: ClientRecord[] = [
  {
    id: "44444444-4444-4444-4444-444444444444",
    name: "Kilimanjaro Traders Ltd",
    industry: "Retail",
    risk_rating: "medium",
    contacts: [{ name: "Neema J", position: "CFO", email: null, phone: null }],
    archived: false,
    created_at: "2026-06-11T08:00:00Z",
    updated_at: "2026-06-11T08:00:00Z",
  },
];

function renderScreen() {
  return render(
    <MemoryRouter>
      <ClientsScreen />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  apiMock.get.mockResolvedValue(clients);
  apiMock.post.mockResolvedValue(clients[0]);
  meState.me = { user_id: "user_1", session_id: null, role: "manager" };
});

describe("ClientsScreen", () => {
  it("lists clients with risk and contacts", async () => {
    renderScreen();
    expect(await screen.findByText("Kilimanjaro Traders Ltd")).toBeInTheDocument();
    expect(screen.getByText("Retail")).toBeInTheDocument();
    expect(screen.getByText("medium")).toBeInTheDocument();
    expect(screen.getByText("Neema J")).toBeInTheDocument();
  });

  it("creates a client from the form", async () => {
    renderScreen();
    await screen.findByText("Kilimanjaro Traders Ltd");

    fireEvent.click(screen.getByRole("button", { name: "New client" }));
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Serengeti Mills" } });
    fireEvent.change(screen.getByLabelText("Risk rating"), { target: { value: "high" } });
    fireEvent.click(screen.getByRole("button", { name: "Create" }));

    await waitFor(() =>
      expect(apiMock.post).toHaveBeenCalledWith("/api/clients", {
        name: "Serengeti Mills",
        industry: null,
        risk_rating: "high",
      }),
    );
  });

  it("hides the create button from auditors", async () => {
    meState.me = { user_id: "user_2", session_id: null, role: "auditor" };
    renderScreen();
    await screen.findByText("Kilimanjaro Traders Ltd");
    expect(screen.queryByRole("button", { name: "New client" })).not.toBeInTheDocument();
  });
});
