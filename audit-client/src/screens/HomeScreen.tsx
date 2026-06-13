import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useApi } from "../hooks/useApi";
import type { HealthResponse } from "../types/health";
import type { MyProcedure } from "../types/planning";
import type { ReviewNoteRecord } from "../types/reviewNotes";
import { fsAreaLabel } from "../types/trialBalance";

export default function HomeScreen() {
  const api = useApi();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [procedures, setProcedures] = useState<MyProcedure[]>([]);
  const [proceduresLoaded, setProceduresLoaded] = useState(false);
  const [reviewNotes, setReviewNotes] = useState<ReviewNoteRecord[]>([]);
  const [reviewNotesLoaded, setReviewNotesLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<HealthResponse>("/api/health")
      .then(setHealth)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
    api
      .get<MyProcedure[]>("/api/my-procedures")
      .then(setProcedures)
      .catch(() => setProcedures([]))
      .finally(() => setProceduresLoaded(true));
    api
      .get<ReviewNoteRecord[]>("/api/me/review-notes")
      .then(setReviewNotes)
      .catch(() => setReviewNotes([]))
      .finally(() => setReviewNotesLoaded(true));
  }, [api]);

  return (
    <div>
      <h2 className="text-xl font-semibold text-slate-800">Dashboard</h2>

      <h3 className="mb-2 mt-6 text-sm font-medium text-slate-500">My assigned procedures</h3>
      {proceduresLoaded && procedures.length === 0 && (
        <p className="text-sm text-slate-500">Nothing assigned to you right now.</p>
      )}
      {procedures.length > 0 && (
        <div className="overflow-x-auto rounded border border-slate-200 bg-white">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-slate-500">
                <th className="px-4 py-2 font-medium">Engagement</th>
                <th className="px-4 py-2 font-medium">FS area</th>
                <th className="px-4 py-2 font-medium">Procedure</th>
                <th className="px-4 py-2 font-medium">Due</th>
                <th className="px-4 py-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {procedures.map((procedure) => (
                <tr key={procedure.id} className="border-b border-slate-100">
                  <td className="px-4 py-2">
                    <Link
                      to={`/engagements/${procedure.engagement_id}/program`}
                      className="text-slate-800 underline"
                    >
                      {procedure.client_name ?? "Engagement"} FY{procedure.fiscal_year}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-slate-600">{fsAreaLabel(procedure.fs_area)}</td>
                  <td className="px-4 py-2 text-slate-800">{procedure.title}</td>
                  <td className="px-4 py-2 text-slate-600">
                    {procedure.due_date ?? "—"}
                    {procedure.overdue && (
                      <span className="ml-2 rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800">
                        overdue
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2 capitalize text-slate-600">
                    {procedure.status.replaceAll("_", " ")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h3 className="mb-2 mt-8 text-sm font-medium text-slate-500">My open review notes</h3>
      {reviewNotesLoaded && reviewNotes.length === 0 && (
        <p className="text-sm text-slate-500">No open review notes assigned to you.</p>
      )}
      {reviewNotes.length > 0 && (
        <ul className="space-y-2">
          {reviewNotes.map((note) => (
            <li
              key={note.id}
              className="rounded border border-slate-200 bg-white p-3 text-sm"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-slate-800">{note.text}</span>
                <span
                  className={
                    note.status === "responded"
                      ? "rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800"
                      : "rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800"
                  }
                >
                  {note.status}
                </span>
              </div>
              <Link
                to={
                  note.working_paper_id
                    ? `/engagements/${note.engagement_id}/working-papers`
                    : `/engagements/${note.engagement_id}`
                }
                className="mt-1 inline-block text-xs text-slate-500 underline"
              >
                Go to engagement
              </Link>
            </li>
          ))}
        </ul>
      )}

      <h3 className="mb-2 mt-8 text-sm font-medium text-slate-500">API status</h3>
      {health && (
        <p className="text-slate-800">
          API: <span className="font-semibold text-green-700">{health.status}</span> · Database:{" "}
          <span className="font-semibold text-green-700">{health.database}</span> · Environment:{" "}
          {health.environment}
        </p>
      )}
      {error && <p className="text-red-700">API unreachable: {error}</p>}
      {!health && !error && <p className="text-slate-500">Checking…</p>}
    </div>
  );
}
