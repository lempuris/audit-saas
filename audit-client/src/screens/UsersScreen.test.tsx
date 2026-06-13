import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { UserRecord } from "../types/users";
import UsersScreen from "./UsersScreen";

const apiMock = {
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
};

vi.mock("../hooks/useApi", () => ({
  useApi: () => apiMock,
}));

const users: UserRecord[] = [
  {
    id: "11111111-1111-1111-1111-111111111111",
    clerk_user_id: "user_abc",
    email: "asha@firm.example",
    first_name: "Asha",
    last_name: "Mushi",
    display_name: "Asha Mushi",
    role: "auditor",
    is_active: true,
    created_at: "2026-06-11T08:00:00Z",
  },
];

beforeEach(() => {
  vi.clearAllMocks();
  apiMock.get.mockResolvedValue(users);
  apiMock.post.mockResolvedValue(undefined);
  apiMock.patch.mockResolvedValue(users[0]);
});

describe("UsersScreen", () => {
  it("lists users from the API", async () => {
    render(<UsersScreen />);
    expect(await screen.findByText("Asha Mushi")).toBeInTheDocument();
    expect(screen.getByText("asha@firm.example")).toBeInTheDocument();
    expect(screen.getByText("active")).toBeInTheDocument();
    expect(apiMock.get).toHaveBeenCalledWith("/api/users");
  });

  it("sends an invitation", async () => {
    render(<UsersScreen />);
    await screen.findByText("Asha Mushi");

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "new@firm.example" },
    });
    fireEvent.change(screen.getByLabelText("Role"), { target: { value: "manager" } });
    fireEvent.click(screen.getByRole("button", { name: "Invite" }));

    await waitFor(() =>
      expect(apiMock.post).toHaveBeenCalledWith("/api/users/invitations", {
        email: "new@firm.example",
        role: "manager",
      }),
    );
    expect(await screen.findByText(/Invitation sent/)).toBeInTheDocument();
  });

  it("updates a user's role", async () => {
    render(<UsersScreen />);
    await screen.findByText("Asha Mushi");

    fireEvent.change(screen.getByLabelText("Role for asha@firm.example"), {
      target: { value: "manager" },
    });

    await waitFor(() =>
      expect(apiMock.patch).toHaveBeenCalledWith("/api/users/user_abc/role", {
        role: "manager",
      }),
    );
  });

  it("deactivates an active user", async () => {
    render(<UsersScreen />);
    await screen.findByText("Asha Mushi");

    fireEvent.click(screen.getByRole("button", { name: "Deactivate" }));

    await waitFor(() =>
      expect(apiMock.post).toHaveBeenCalledWith("/api/users/user_abc/deactivate"),
    );
  });

  it("hides inactive users until the toggle is ticked", async () => {
    apiMock.get.mockResolvedValue([
      users[0],
      {
        ...users[0],
        id: "22222222-2222-2222-2222-222222222222",
        clerk_user_id: "user_gone",
        email: "lempuris@hotmail.com",
        first_name: null,
        last_name: null,
        display_name: "lempuris",
        is_active: false,
      },
    ]);
    render(<UsersScreen />);
    await screen.findByText("Asha Mushi");

    // Inactive user hidden by default.
    expect(screen.queryByText("lempuris@hotmail.com")).not.toBeInTheDocument();

    fireEvent.click(screen.getByLabelText(/Show inactive/));
    expect(await screen.findByText("lempuris@hotmail.com")).toBeInTheDocument();
  });

  it("surfaces API failures", async () => {
    apiMock.get.mockRejectedValue(new Error("forbidden"));
    render(<UsersScreen />);
    expect(await screen.findByText("forbidden")).toBeInTheDocument();
  });
});
