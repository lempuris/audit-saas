import { useCallback, useEffect, useState, type FormEvent } from "react";

import { useApi } from "../hooks/useApi";
import type { Role } from "../types/me";
import { ASSIGNABLE_ROLES, type UserRecord } from "../types/users";

export default function UsersScreen() {
  const api = useApi();
  const [users, setUsers] = useState<UserRecord[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<Role>("auditor");
  const [notice, setNotice] = useState<string | null>(null);
  const [showInactive, setShowInactive] = useState(false);

  // Deactivated/deleted users are kept (for audit authorship) but hidden by
  // default so the list shows the active team. See firm "no direct Clerk" rule.
  const inactiveCount = users?.filter((user) => !user.is_active).length ?? 0;
  const visibleUsers = users?.filter((user) => showInactive || user.is_active) ?? null;

  const load = useCallback(() => {
    api
      .get<UserRecord[]>("/api/users")
      .then((rows) => {
        setUsers(rows);
        setError(null);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, [api]);

  useEffect(load, [load]);

  async function run(action: () => Promise<unknown>, successNotice: string) {
    setBusy(true);
    setNotice(null);
    setError(null);
    try {
      await action();
      setNotice(successNotice);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  function invite(event: FormEvent) {
    event.preventDefault();
    void run(
      () => api.post("/api/users/invitations", { email: inviteEmail, role: inviteRole }),
      `Invitation sent to ${inviteEmail}`,
    ).then(() => setInviteEmail(""));
  }

  function changeRole(user: UserRecord, role: Role) {
    void run(
      () => api.patch(`/api/users/${user.clerk_user_id}/role`, { role }),
      `Role updated for ${user.email ?? user.clerk_user_id}`,
    );
  }

  function toggleActive(user: UserRecord) {
    const verb = user.is_active ? "deactivate" : "reactivate";
    void run(
      () => api.post(`/api/users/${user.clerk_user_id}/${verb}`),
      `${user.email ?? user.clerk_user_id} ${verb}d`,
    );
  }

  return (
    <div>
      <h2 className="text-xl font-semibold text-slate-800">Users</h2>

      <form
        onSubmit={invite}
        className="mt-4 flex flex-wrap items-end gap-3 rounded border border-slate-200 bg-white p-4"
      >
        <label className="flex flex-col text-sm text-slate-600">
          Email
          <input
            type="email"
            required
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            className="mt-1 w-64 rounded border border-slate-300 px-2 py-1.5"
            placeholder="colleague@firm.example"
          />
        </label>
        <label className="flex flex-col text-sm text-slate-600">
          Role
          <select
            value={inviteRole}
            onChange={(e) => setInviteRole(e.target.value as Role)}
            className="mt-1 rounded border border-slate-300 px-2 py-1.5 capitalize"
          >
            {ASSIGNABLE_ROLES.map((role) => (
              <option key={role} value={role}>
                {role}
              </option>
            ))}
          </select>
        </label>
        <button
          type="submit"
          disabled={busy}
          className="rounded bg-slate-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Invite
        </button>
      </form>

      {notice && <p className="mt-3 text-sm text-green-700">{notice}</p>}
      {error && <p className="mt-3 text-sm text-red-700">{error}</p>}

      {inactiveCount > 0 && (
        <label className="mt-4 flex items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={showInactive}
            onChange={(e) => setShowInactive(e.target.checked)}
          />
          Show inactive ({inactiveCount})
        </label>
      )}

      <div className="mt-4 overflow-x-auto rounded border border-slate-200 bg-white">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left text-slate-500">
              <th className="px-4 py-2 font-medium">Name</th>
              <th className="px-4 py-2 font-medium">Email</th>
              <th className="px-4 py-2 font-medium">Role</th>
              <th className="px-4 py-2 font-medium">Status</th>
              <th className="px-4 py-2 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {visibleUsers?.map((user) => (
              <tr key={user.id} className="border-b border-slate-100">
                <td className="px-4 py-2 text-slate-800">{user.display_name}</td>
                <td className="px-4 py-2 text-slate-600">{user.email ?? "—"}</td>
                <td className="px-4 py-2">
                  <select
                    value={user.role ?? ""}
                    disabled={busy}
                    onChange={(e) => changeRole(user, e.target.value as Role)}
                    className="rounded border border-slate-300 px-2 py-1 capitalize"
                    aria-label={`Role for ${user.email ?? user.clerk_user_id}`}
                  >
                    {user.role === null && <option value="">unassigned</option>}
                    {ASSIGNABLE_ROLES.map((role) => (
                      <option key={role} value={role}>
                        {role}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="px-4 py-2">
                  <span
                    className={
                      user.is_active
                        ? "rounded bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800"
                        : "rounded bg-slate-200 px-2 py-0.5 text-xs font-medium text-slate-600"
                    }
                  >
                    {user.is_active ? "active" : "inactive"}
                  </span>
                </td>
                <td className="px-4 py-2">
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => toggleActive(user)}
                    className="rounded border border-slate-300 px-3 py-1 text-xs text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                  >
                    {user.is_active ? "Deactivate" : "Reactivate"}
                  </button>
                </td>
              </tr>
            ))}
            {visibleUsers && visibleUsers.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-slate-500">
                  {users && users.length > 0
                    ? "No active users — tick “Show inactive” to see deactivated accounts."
                    : "No users yet — invitations appear here once accepted."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
        {!users && !error && <p className="p-4 text-slate-500">Loading…</p>}
      </div>
    </div>
  );
}
