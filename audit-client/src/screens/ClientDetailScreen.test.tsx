import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ClientRecord } from "../types/clients";
import type { Me } from "../types/me";
import ClientDetailScreen from "./ClientDetailScreen";

const apiMock = { get: vi.fn(), patch: vi.fn(), delete: vi.fn() };
const meState: { me: Me | null } = { me: null };

vi.mock("../hooks/useApi", () => ({
  useApi: () => apiMock,
}));
vi.mock("../contexts/MeContext", () => ({
  useMe: () => ({ me: meState.me, loading: false, error: null }),
}));

const client: ClientRecord = {
  id: "44444444-4444-4444-4444-444444444444",
  name: "Kilimanjaro Traders Ltd",
  industry: "Retail",
  risk_rating: "medium",
  contacts: [],
  archived: false,
  created_at: "2026-06-11T08:00:00Z",
  updated_at: "2026-06-11T08:00:00Z",
};

function renderScreen() {
  return render(
    <MemoryRouter initialEntries={[`/clients/${client.id}`]}>
      <Routes>
        <Route path="clients/:clientId" element={<ClientDetailScreen />} />
        <Route path="clients" element={<p>client list</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  apiMock.get.mockImplementation((path: string) =>
    path.startsWith("/api/engagements") ? Promise.resolve([]) : Promise.resolve(client),
  );
  apiMock.patch.mockResolvedValue(client);
  apiMock.delete.mockResolvedValue({ ...client, archived: true });
  meState.me = { user_id: "user_1", session_id: null, role: "partner" };
});

describe("ClientDetailScreen", () => {
  it("loads the client and its engagements", async () => {
    renderScreen();
    expect(await screen.findByText("Kilimanjaro Traders Ltd")).toBeInTheDocument();
    expect(apiMock.get).toHaveBeenCalledWith(`/api/clients/${client.id}`);
    expect(apiMock.get).toHaveBeenCalledWith(`/api/engagements?client_id=${client.id}`);
    expect(screen.getByText("No engagements for this client yet.")).toBeInTheDocument();
  });

  it("saves edits including contacts", async () => {
    renderScreen();
    await screen.findByText("Kilimanjaro Traders Ltd");

    fireEvent.click(screen.getByRole("button", { name: "Add contact" }));
    fireEvent.change(screen.getByLabelText("Contact 1 name"), { target: { value: "Ali H" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(apiMock.patch).toHaveBeenCalledWith(`/api/clients/${client.id}`, {
        name: "Kilimanjaro Traders Ltd",
        industry: "Retail",
        risk_rating: "medium",
        contacts: [{ name: "Ali H", position: null, email: null, phone: null }],
      }),
    );
  });

  it("archives the client and navigates back to the list", async () => {
    renderScreen();
    await screen.findByText("Kilimanjaro Traders Ltd");

    fireEvent.click(screen.getByRole("button", { name: "Archive client" }));

    await waitFor(() => expect(apiMock.delete).toHaveBeenCalledWith(`/api/clients/${client.id}`));
    expect(await screen.findByText("client list")).toBeInTheDocument();
  });

  it("hides editing from auditors", async () => {
    meState.me = { user_id: "user_2", session_id: null, role: "auditor" };
    renderScreen();
    await screen.findByText("Kilimanjaro Traders Ltd");
    expect(screen.queryByRole("button", { name: "Save" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Archive client" })).not.toBeInTheDocument();
  });
});
