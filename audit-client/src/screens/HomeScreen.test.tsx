import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { MyProcedure } from "../types/planning";
import HomeScreen from "./HomeScreen";

const apiMock = { get: vi.fn() };

vi.mock("../hooks/useApi", () => ({
  useApi: () => apiMock,
}));

const myProcedures: MyProcedure[] = [
  {
    id: "22222222-2222-2222-2222-222222222222",
    engagement_id: "55555555-5555-5555-5555-555555555555",
    engagement_status: "planning",
    fiscal_year: 2026,
    client_name: "Acme Ltd",
    fs_area: "revenue",
    title: "Revenue cutoff testing",
    isa_reference: "ISA 500",
    status: "not_started",
    due_date: "2026-06-01",
    overdue: true,
  },
];

beforeEach(() => {
  vi.clearAllMocks();
  apiMock.get.mockImplementation((path: string) =>
    path === "/api/my-procedures"
      ? Promise.resolve(myProcedures)
      : Promise.resolve({ status: "ok", database: "ok", environment: "test" }),
  );
});

describe("HomeScreen", () => {
  it("lists my assigned procedures with overdue badge", async () => {
    render(
      <MemoryRouter>
        <HomeScreen />
      </MemoryRouter>,
    );
    expect(await screen.findByText("Revenue cutoff testing")).toBeInTheDocument();
    expect(screen.getByText("Acme Ltd FY2026")).toBeInTheDocument();
    expect(screen.getByText("overdue")).toBeInTheDocument();
  });

  it("shows an empty state when nothing is assigned", async () => {
    apiMock.get.mockImplementation((path: string) =>
      path === "/api/my-procedures"
        ? Promise.resolve([])
        : Promise.resolve({ status: "ok", database: "ok", environment: "test" }),
    );
    render(
      <MemoryRouter>
        <HomeScreen />
      </MemoryRouter>,
    );
    expect(await screen.findByText("Nothing assigned to you right now.")).toBeInTheDocument();
  });
});
