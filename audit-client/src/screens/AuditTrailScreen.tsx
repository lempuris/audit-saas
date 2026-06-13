import { useCallback, useEffect, useState } from "react";

import { useApi } from "../hooks/useApi";
import type { AuditTrailPage } from "../types/auditTrail";

const PAGE_SIZE = 50;

function describeChange(value: Record<string, unknown> | null): string {
  if (!value) return "—";
  return Object.entries(value)
    .map(([key, val]) => `${key}: ${JSON.stringify(val)}`)
    .join(", ");
}

export default function AuditTrailScreen() {
  const api = useApi();
  const [page, setPage] = useState<AuditTrailPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [entityType, setEntityType] = useState("");
  const [actor, setActor] = useState("");
  const [offset, setOffset] = useState(0);

  const load = useCallback(() => {
    const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(offset) });
    if (entityType) params.set("entity_type", entityType);
    if (actor) params.set("actor", actor);
    api
      .get<AuditTrailPage>(`/api/audit-trail?${params.toString()}`)
      .then((result) => {
        setPage(result);
        setError(null);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, [api, entityType, actor, offset]);

  useEffect(load, [load]);

  return (
    <div>
      <h2 className="text-xl font-semibold text-slate-800">Audit trail</h2>

      <div className="mt-4 flex flex-wrap items-end gap-3">
        <label className="flex flex-col text-sm text-slate-600">
          Entity type
          <select
            value={entityType}
            onChange={(e) => {
              setOffset(0);
              setEntityType(e.target.value);
            }}
            className="mt-1 rounded border border-slate-300 bg-white px-2 py-1.5"
          >
            <option value="">All</option>
            <option value="client">Client</option>
            <option value="engagement">Engagement</option>
            <option value="engagement_team_member">Engagement team</option>
            <option value="user">User</option>
            <option value="invitation">Invitation</option>
            <option value="session">Login</option>
          </select>
        </label>
        <label className="flex flex-col text-sm text-slate-600">
          Actor (user id)
          <input
            value={actor}
            onChange={(e) => {
              setOffset(0);
              setActor(e.target.value);
            }}
            placeholder="user_…"
            className="mt-1 w-56 rounded border border-slate-300 px-2 py-1.5"
          />
        </label>
      </div>

      {error && <p className="mt-3 text-sm text-red-700">{error}</p>}

      <div className="mt-4 overflow-x-auto rounded border border-slate-200 bg-white">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left text-slate-500">
              <th className="px-4 py-2 font-medium">When</th>
              <th className="px-4 py-2 font-medium">Actor</th>
              <th className="px-4 py-2 font-medium">Action</th>
              <th className="px-4 py-2 font-medium">Entity</th>
              <th className="px-4 py-2 font-medium">Before</th>
              <th className="px-4 py-2 font-medium">After</th>
            </tr>
          </thead>
          <tbody>
            {page?.items.map((entry) => (
              <tr key={entry.id} className="border-b border-slate-100 align-top">
                <td className="whitespace-nowrap px-4 py-2 text-slate-600">
                  {new Date(entry.created_at).toLocaleString()}
                </td>
                <td className="px-4 py-2 text-slate-700">
                  {entry.actor_name ? (
                    <>
                      {entry.actor_name}
                      <span className="block font-mono text-xs text-slate-400">
                        {entry.actor_email ?? entry.actor_clerk_user_id}
                      </span>
                    </>
                  ) : (
                    <span className="font-mono text-xs text-slate-600">
                      {entry.actor_clerk_user_id}
                    </span>
                  )}
                </td>
                <td className="px-4 py-2">
                  <span className="rounded bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                    {entry.action}
                  </span>
                </td>
                <td className="px-4 py-2 text-slate-800">
                  {entry.entity_type}
                  {entry.entity_id && (
                    <span className="block font-mono text-xs text-slate-400">
                      {entry.entity_id}
                    </span>
                  )}
                </td>
                <td className="max-w-xs px-4 py-2 text-xs text-slate-500">
                  {describeChange(entry.before)}
                </td>
                <td className="max-w-xs px-4 py-2 text-xs text-slate-500">
                  {describeChange(entry.after)}
                </td>
              </tr>
            ))}
            {page && page.items.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-slate-500">
                  No audit entries match.
                </td>
              </tr>
            )}
          </tbody>
        </table>
        {!page && !error && <p className="p-4 text-slate-500">Loading…</p>}
      </div>

      {page && page.total > PAGE_SIZE && (
        <div className="mt-3 flex items-center gap-3 text-sm text-slate-600">
          <button
            type="button"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            className="rounded border border-slate-300 px-3 py-1 disabled:opacity-50"
          >
            Previous
          </button>
          <span>
            {offset + 1}–{Math.min(offset + PAGE_SIZE, page.total)} of {page.total}
          </span>
          <button
            type="button"
            disabled={offset + PAGE_SIZE >= page.total}
            onClick={() => setOffset(offset + PAGE_SIZE)}
            className="rounded border border-slate-300 px-3 py-1 disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
