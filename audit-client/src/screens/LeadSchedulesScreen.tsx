import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useApi } from "../hooks/useApi";
import { ApiError } from "../services/api";
import type { LeadSchedule, LeadScheduleSummary } from "../types/planning";
import { fsAreaLabel } from "../types/trialBalance";

export default function LeadSchedulesScreen() {
  const { engagementId } = useParams<{ engagementId: string }>();
  const api = useApi();

  const [schedules, setSchedules] = useState<LeadScheduleSummary[]>([]);
  const [detail, setDetail] = useState<LeadSchedule | null>(null);
  const [noTb, setNoTb] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const base = `/api/engagements/${engagementId}/lead-schedules`;

  const load = useCallback(() => {
    if (!engagementId) return;
    api
      .get<LeadScheduleSummary[]>(base)
      .then((rows) => {
        setSchedules(rows);
        setNoTb(false);
        setError(null);
      })
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 404) {
          setNoTb(true);
        } else {
          setError(err instanceof Error ? err.message : String(err));
        }
      })
      .finally(() => setLoaded(true));
  }, [api, base, engagementId]);

  useEffect(load, [load]);

  function open(area: string) {
    api
      .get<LeadSchedule>(`${base}/${area}`)
      .then((row) => {
        setDetail(row);
        setError(null);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }

  if (!loaded) {
    return <p className="text-slate-500">Loading…</p>;
  }

  const hasPrior = schedules.some((schedule) => schedule.prior_year_balance !== null);

  return (
    <div>
      <h2 className="text-xl font-semibold text-slate-800">Lead schedules</h2>
      <p className="mt-0.5 text-sm text-slate-500">
        <Link to={`/engagements/${engagementId}`} className="underline">
          Back to engagement
        </Link>
      </p>

      {error && <p className="mt-3 break-all text-sm text-red-700">{error}</p>}

      {noTb && (
        <p className="mt-4 text-slate-500">
          Lead schedules are generated from the trial balance —{" "}
          <Link to={`/engagements/${engagementId}/trial-balance`} className="underline">
            import one first
          </Link>
          .
        </p>
      )}

      {!noTb && (
        <div className="mt-4 overflow-x-auto rounded border border-slate-200 bg-white">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-slate-500">
                <th className="px-4 py-2 font-medium">FS area</th>
                <th className="px-4 py-2 text-right font-medium">Lines</th>
                <th className="px-4 py-2 text-right font-medium">Balance</th>
                {hasPrior && (
                  <>
                    <th className="px-4 py-2 text-right font-medium">Prior year</th>
                    <th className="px-4 py-2 text-right font-medium">Movement</th>
                  </>
                )}
              </tr>
            </thead>
            <tbody>
              {schedules.map((schedule) => (
                <tr key={schedule.fs_area} className="border-b border-slate-100">
                  <td className="px-4 py-2">
                    <button
                      type="button"
                      onClick={() => open(schedule.fs_area)}
                      className="text-slate-800 underline"
                    >
                      {fsAreaLabel(schedule.fs_area)}
                    </button>
                  </td>
                  <td className="px-4 py-2 text-right text-slate-600">{schedule.line_count}</td>
                  <td className="px-4 py-2 text-right tabular-nums text-slate-800">
                    {schedule.balance}
                  </td>
                  {hasPrior && (
                    <>
                      <td className="px-4 py-2 text-right tabular-nums text-slate-600">
                        {schedule.prior_year_balance ?? "—"}
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums text-slate-600">
                        {schedule.movement ?? "—"}
                      </td>
                    </>
                  )}
                </tr>
              ))}
              {schedules.length === 0 && (
                <tr>
                  <td colSpan={hasPrior ? 5 : 3} className="px-4 py-6 text-center text-slate-500">
                    No trial balance lines are grouped into FS areas yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {detail && (
        <>
          <h3 className="mt-8 text-sm font-semibold text-slate-700">
            {fsAreaLabel(detail.fs_area)} — {detail.line_count} accounts
          </h3>
          <div className="mt-2 overflow-x-auto rounded border border-slate-200 bg-white">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-slate-500">
                  <th className="px-4 py-2 font-medium">Code</th>
                  <th className="px-4 py-2 font-medium">Account</th>
                  <th className="px-4 py-2 text-right font-medium">Balance</th>
                  <th className="px-4 py-2 text-right font-medium">Prior year</th>
                  <th className="px-4 py-2 text-right font-medium">Movement</th>
                </tr>
              </thead>
              <tbody>
                {detail.lines.map((line) => (
                  <tr key={line.line_id} className="border-b border-slate-100">
                    <td className="px-4 py-2 text-slate-600">{line.account_code}</td>
                    <td className="px-4 py-2 text-slate-800">{line.account_name}</td>
                    <td className="px-4 py-2 text-right tabular-nums text-slate-800">
                      {line.balance}
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums text-slate-600">
                      {line.prior_year_balance ?? "—"}
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums text-slate-600">
                      {line.movement ?? "—"}
                    </td>
                  </tr>
                ))}
                <tr className="bg-slate-50 font-medium">
                  <td className="px-4 py-2" />
                  <td className="px-4 py-2 text-slate-700">Total</td>
                  <td className="px-4 py-2 text-right tabular-nums text-slate-800">
                    {detail.balance}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums text-slate-700">
                    {detail.prior_year_balance ?? "—"}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums text-slate-700">
                    {detail.movement ?? "—"}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
