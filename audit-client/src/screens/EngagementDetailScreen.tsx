import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import { useMe } from "../contexts/MeContext";
import { useApi } from "../hooks/useApi";
import type { ClientRecord } from "../types/clients";
import type { PlanningSummary } from "../types/planning";
import {
  NEXT_STATUSES,
  type EngagementDetail,
  type EngagementStatus,
} from "../types/engagements";
import type { UserRecord } from "../types/users";

export default function EngagementDetailScreen() {
  const { engagementId } = useParams<{ engagementId: string }>();
  const api = useApi();
  const { me } = useMe();
  const canWrite = me?.role === "admin" || me?.role === "partner" || me?.role === "manager";
  const isAdmin = me?.role === "admin";

  const [engagement, setEngagement] = useState<EngagementDetail | null>(null);
  const [client, setClient] = useState<ClientRecord | null>(null);
  const [planning, setPlanning] = useState<PlanningSummary | null>(null);
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [newMemberId, setNewMemberId] = useState("");
  const [newMemberRole, setNewMemberRole] = useState("");

  const load = useCallback(() => {
    if (!engagementId) return;
    api
      .get<EngagementDetail>(`/api/engagements/${engagementId}`)
      .then((row) => {
        setEngagement(row);
        setError(null);
        api
          .get<ClientRecord>(`/api/clients/${row.client_id}`)
          .then(setClient)
          .catch(() => setClient(null));
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
    api
      .get<PlanningSummary>(`/api/engagements/${engagementId}/planning-summary`)
      .then((summary) => setPlanning(summary.trial_balance ? summary : null))
      .catch(() => setPlanning(null));
  }, [api, engagementId]);

  useEffect(load, [load]);

  // The users list is admin-only server-side; others type/paste a user id.
  useEffect(() => {
    if (!isAdmin) return;
    api
      .get<UserRecord[]>("/api/users")
      .then(setUsers)
      .catch(() => setUsers([]));
  }, [api, isAdmin]);

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

  function changeStatus(status: EngagementStatus) {
    void run(
      () => api.patch(`/api/engagements/${engagementId}/status`, { status }),
      `Moved to ${status}`,
    );
  }

  function addMember(event: FormEvent) {
    event.preventDefault();
    void run(
      () =>
        api.post(`/api/engagements/${engagementId}/team`, {
          clerk_user_id: newMemberId,
          role_on_engagement: newMemberRole || null,
        }),
      "Team member added",
    ).then(() => {
      setNewMemberId("");
      setNewMemberRole("");
    });
  }

  function removeMember(clerkUserId: string) {
    void run(
      () => api.delete(`/api/engagements/${engagementId}/team/${clerkUserId}`),
      "Team member removed",
    );
  }

  function confirmIndependence() {
    void run(
      () => api.post(`/api/engagements/${engagementId}/team/confirm-independence`),
      "Independence confirmed",
    );
  }

  if (!engagement && !error) {
    return <p className="text-slate-500">Loading…</p>;
  }
  if (error && !engagement) {
    return <p className="text-red-700">{error}</p>;
  }
  if (!engagement) return null;

  const userLabel = (clerkUserId: string) => {
    const user = users.find((row) => row.clerk_user_id === clerkUserId);
    if (!user) return clerkUserId;
    return [user.first_name, user.last_name].filter(Boolean).join(" ") || user.email || clerkUserId;
  };
  const onTeam = engagement.team.some((member) => member.clerk_user_id === me?.user_id);
  const myConfirmation = engagement.team.find(
    (member) => member.clerk_user_id === me?.user_id,
  )?.independence_confirmed;

  return (
    <div>
      <h2 className="text-xl font-semibold text-slate-800">
        {client ? (
          <Link to={`/clients/${client.id}`} className="underline">
            {client.name}
          </Link>
        ) : (
          "Engagement"
        )}{" "}
        · FY{engagement.fiscal_year}
      </h2>
      <p className="mt-0.5 text-sm capitalize text-slate-500">
        {engagement.engagement_type.replaceAll("_", " ")} ·{" "}
        <span className="rounded bg-slate-100 px-2 py-0.5 font-medium text-slate-700">
          {engagement.status}
        </span>
      </p>

      {notice && <p className="mt-3 text-sm text-green-700">{notice}</p>}
      {error && <p className="mt-3 text-sm text-red-700">{error}</p>}

      {canWrite && NEXT_STATUSES[engagement.status].length > 0 && (
        <div className="mt-4 flex items-center gap-2">
          <span className="text-sm text-slate-600">Move to:</span>
          {NEXT_STATUSES[engagement.status].map((status) => (
            <button
              key={status}
              type="button"
              disabled={busy}
              onClick={() => changeStatus(status)}
              className="rounded border border-slate-300 px-3 py-1.5 text-sm capitalize text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              {status}
            </button>
          ))}
        </div>
      )}

      <h3 className="mt-8 text-sm font-semibold text-slate-700">Planning</h3>
      <div className="mt-2 flex flex-wrap gap-2">
        <Link
          to={`/engagements/${engagementId}/trial-balance`}
          className="rounded border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
        >
          Trial balance
        </Link>
        <Link
          to={`/engagements/${engagementId}/materiality`}
          className="rounded border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
        >
          Materiality
        </Link>
        <Link
          to={`/engagements/${engagementId}/risks`}
          className="rounded border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
        >
          Risks
        </Link>
        <Link
          to={`/engagements/${engagementId}/program`}
          className="rounded border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
        >
          Audit program
        </Link>
        <Link
          to={`/engagements/${engagementId}/lead-schedules`}
          className="rounded border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
        >
          Lead schedules
        </Link>
      </div>

      <h3 className="mt-8 text-sm font-semibold text-slate-700">Fieldwork</h3>
      <div className="mt-2 flex flex-wrap gap-2">
        <Link
          to={`/engagements/${engagementId}/working-papers`}
          className="rounded border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
        >
          Working papers
        </Link>
        <Link
          to={`/engagements/${engagementId}/documents`}
          className="rounded border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
        >
          Documents
        </Link>
      </div>

      {planning && (
        <div className="mt-3 grid max-w-3xl grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded border border-slate-200 bg-white p-3">
            <p className="text-xs text-slate-500">Trial balance</p>
            <p className="mt-1 text-sm font-medium text-slate-800">
              {planning.trial_balance.imported
                ? `${planning.trial_balance.line_count} lines`
                : "Not imported"}
            </p>
            {planning.trial_balance.unmapped_count > 0 && (
              <p className="text-xs text-amber-700">
                {planning.trial_balance.unmapped_count} unmapped
              </p>
            )}
          </div>
          <div className="rounded border border-slate-200 bg-white p-3">
            <p className="text-xs text-slate-500">Materiality</p>
            <p className="mt-1 text-sm font-medium capitalize text-slate-800">
              {planning.materiality?.status ?? "Not set"}
            </p>
            {planning.materiality && (
              <p className="text-xs text-slate-500">
                OM {planning.materiality.overall_materiality}
              </p>
            )}
          </div>
          <div className="rounded border border-slate-200 bg-white p-3">
            <p className="text-xs text-slate-500">Risks</p>
            <p className="mt-1 text-sm font-medium text-slate-800">{planning.risks.total}</p>
            {planning.risks.significant > 0 && (
              <p className="text-xs text-red-700">{planning.risks.significant} significant</p>
            )}
          </div>
          <div className="rounded border border-slate-200 bg-white p-3">
            <p className="text-xs text-slate-500">Procedures</p>
            <p className="mt-1 text-sm font-medium text-slate-800">
              {planning.procedures.by_status.completed ?? 0}/{planning.procedures.total} done
            </p>
            {planning.procedures.overdue > 0 && (
              <p className="text-xs text-red-700">{planning.procedures.overdue} overdue</p>
            )}
          </div>
        </div>
      )}

      <h3 className="mt-8 text-sm font-semibold text-slate-700">
        Team &amp; independence confirmations
      </h3>
      <div className="mt-2 overflow-x-auto rounded border border-slate-200 bg-white">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left text-slate-500">
              <th className="px-4 py-2 font-medium">Member</th>
              <th className="px-4 py-2 font-medium">Engagement role</th>
              <th className="px-4 py-2 font-medium">Independence</th>
              {canWrite && <th className="px-4 py-2 font-medium">Actions</th>}
            </tr>
          </thead>
          <tbody>
            {engagement.team.map((member) => (
              <tr key={member.clerk_user_id} className="border-b border-slate-100">
                <td className="px-4 py-2 text-slate-800">{userLabel(member.clerk_user_id)}</td>
                <td className="px-4 py-2 text-slate-600">{member.role_on_engagement ?? "—"}</td>
                <td className="px-4 py-2">
                  {member.independence_confirmed ? (
                    <span className="rounded bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
                      confirmed
                    </span>
                  ) : (
                    <span className="rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                      pending
                    </span>
                  )}
                </td>
                {canWrite && (
                  <td className="px-4 py-2">
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => removeMember(member.clerk_user_id)}
                      className="rounded border border-slate-300 px-3 py-1 text-xs text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                    >
                      Remove
                    </button>
                  </td>
                )}
              </tr>
            ))}
            {engagement.team.length === 0 && (
              <tr>
                <td colSpan={canWrite ? 4 : 3} className="px-4 py-6 text-center text-slate-500">
                  No team assigned yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {onTeam && !myConfirmation && (
        <button
          type="button"
          disabled={busy}
          onClick={confirmIndependence}
          className="mt-3 rounded bg-green-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Confirm my independence
        </button>
      )}

      {canWrite && (
        <form
          onSubmit={addMember}
          className="mt-4 flex flex-wrap items-end gap-3 rounded border border-slate-200 bg-white p-4"
        >
          <label className="flex flex-col text-sm text-slate-600">
            Member
            {isAdmin && users.length > 0 ? (
              <select
                required
                value={newMemberId}
                onChange={(e) => setNewMemberId(e.target.value)}
                className="mt-1 w-64 rounded border border-slate-300 bg-white px-2 py-1.5"
              >
                <option value="">Select a user…</option>
                {users
                  .filter((user) => user.is_active)
                  .map((user) => (
                    <option key={user.clerk_user_id} value={user.clerk_user_id}>
                      {userLabel(user.clerk_user_id)}
                    </option>
                  ))}
              </select>
            ) : (
              <input
                required
                value={newMemberId}
                onChange={(e) => setNewMemberId(e.target.value)}
                placeholder="user_…"
                className="mt-1 w-64 rounded border border-slate-300 px-2 py-1.5"
              />
            )}
          </label>
          <label className="flex flex-col text-sm text-slate-600">
            Engagement role
            <input
              value={newMemberRole}
              onChange={(e) => setNewMemberRole(e.target.value)}
              placeholder="e.g. engagement partner"
              className="mt-1 w-56 rounded border border-slate-300 px-2 py-1.5"
            />
          </label>
          <button
            type="submit"
            disabled={busy}
            className="rounded bg-slate-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            Add to team
          </button>
        </form>
      )}
    </div>
  );
}
