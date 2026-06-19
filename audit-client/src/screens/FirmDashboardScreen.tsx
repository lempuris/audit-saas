import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useApi } from "../hooks/useApi";
import type { FirmDashboard } from "../types/firmDashboard";
import { fsAreaLabel } from "../types/trialBalance";

// Workflow order, so the status tiles read left-to-right like the lifecycle.
const STATUS_ORDER = ["draft", "planning", "fieldwork", "review", "completed"];

export default function FirmDashboardScreen() {
  const api = useApi();
  const [data, setData] = useState<FirmDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<FirmDashboard>("/api/firm-dashboard")
      .then(setData)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, [api]);

  if (error) return <p className="text-red-700">Could not load the firm dashboard: {error}</p>;
  if (!data) return <p className="text-slate-500">Loading…</p>;

  return (
    <div>
      <h2 className="text-xl font-semibold text-slate-800">Firm dashboard</h2>

      <h3 className="mb-2 mt-6 text-sm font-medium text-slate-500">Engagements by status</h3>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {STATUS_ORDER.map((status) => (
          <div key={status} className="rounded border border-slate-200 bg-white p-3">
            <div className="text-2xl font-semibold text-slate-800">
              {data.engagements.by_status[status] ?? 0}
            </div>
            <div className="text-xs capitalize text-slate-500">{status}</div>
          </div>
        ))}
        <div className="rounded border border-slate-300 bg-slate-50 p-3">
          <div className="text-2xl font-semibold text-slate-800">{data.engagements.total}</div>
          <div className="text-xs text-slate-500">total</div>
        </div>
      </div>

      <h3 className="mb-2 mt-8 text-sm font-medium text-slate-500">
        Review queue · {data.review_queue.length} working paper(s) awaiting sign-off
      </h3>
      {data.review_queue.length === 0 ? (
        <p className="text-sm text-slate-500">No working papers are awaiting review.</p>
      ) : (
        <div className="overflow-x-auto rounded border border-slate-200 bg-white">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-slate-500">
                <th className="px-4 py-2 font-medium">Engagement</th>
                <th className="px-4 py-2 font-medium">Ref</th>
                <th className="px-4 py-2 font-medium">Working paper</th>
                <th className="px-4 py-2 font-medium">Prepared by</th>
                <th className="px-4 py-2 font-medium">Awaiting</th>
              </tr>
            </thead>
            <tbody>
              {data.review_queue.map((item) => (
                <tr key={item.working_paper_id} className="border-b border-slate-100">
                  <td className="px-4 py-2">
                    <Link
                      to={`/engagements/${item.engagement_id}/working-papers`}
                      className="text-slate-800 underline"
                    >
                      {item.client_name ?? "Engagement"} FY{item.fiscal_year}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-slate-600">{item.index_ref}</td>
                  <td className="px-4 py-2 text-slate-800">
                    {item.title}
                    <span className="ml-2 text-xs text-slate-400">{fsAreaLabel(item.fs_area)}</span>
                  </td>
                  <td className="px-4 py-2 text-slate-600">{item.prepared_by_name ?? "—"}</td>
                  <td className="px-4 py-2">
                    <span className="rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                      {item.status === "reviewed" ? "partner approval" : "review"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h3 className="mb-2 mt-8 text-sm font-medium text-slate-500">
        Overdue procedures · {data.overdue_procedures.length}
      </h3>
      {data.overdue_procedures.length === 0 ? (
        <p className="text-sm text-slate-500">No overdue procedures.</p>
      ) : (
        <div className="overflow-x-auto rounded border border-slate-200 bg-white">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-slate-500">
                <th className="px-4 py-2 font-medium">Engagement</th>
                <th className="px-4 py-2 font-medium">Procedure</th>
                <th className="px-4 py-2 font-medium">Assignee</th>
                <th className="px-4 py-2 font-medium">Due</th>
              </tr>
            </thead>
            <tbody>
              {data.overdue_procedures.map((procedure) => (
                <tr key={procedure.id} className="border-b border-slate-100">
                  <td className="px-4 py-2">
                    <Link
                      to={`/engagements/${procedure.engagement_id}/program`}
                      className="text-slate-800 underline"
                    >
                      {procedure.client_name ?? "Engagement"} FY{procedure.fiscal_year}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-slate-800">
                    {procedure.title}
                    <span className="ml-2 text-xs text-slate-400">
                      {fsAreaLabel(procedure.fs_area)}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-slate-600">{procedure.assignee_name ?? "—"}</td>
                  <td className="px-4 py-2 text-slate-600">
                    {procedure.due_date}
                    <span className="ml-2 rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800">
                      {procedure.days_overdue}d overdue
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="mt-8 text-sm text-slate-600">
        <span className="font-medium text-slate-800">{data.open_review_notes}</span> uncleared review
        note(s) across active engagements.
      </p>
    </div>
  );
}
