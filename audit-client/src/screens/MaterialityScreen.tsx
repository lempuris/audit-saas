import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import { useMe } from "../contexts/MeContext";
import { useApi } from "../hooks/useApi";
import { ApiError } from "../services/api";
import {
  MATERIALITY_BENCHMARKS,
  type MaterialityBenchmark,
  type MaterialityRecord,
} from "../types/materiality";

function benchmarkLabel(benchmark: string): string {
  return benchmark.replaceAll("_", " ").replace(/^./, (c) => c.toUpperCase());
}

/** Client-side preview of what the API will compute; the server remains
 * authoritative and stores the rounded amounts. */
function previewAmount(base: string, percentage: string): string {
  const baseNum = Number(base);
  const pct = Number(percentage);
  if (!Number.isFinite(baseNum) || !Number.isFinite(pct) || baseNum <= 0 || pct <= 0) return "—";
  return ((baseNum * pct) / 100).toLocaleString("en", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export default function MaterialityScreen() {
  const { engagementId } = useParams<{ engagementId: string }>();
  const api = useApi();
  const { me } = useMe();
  const canWrite = me?.role === "admin" || me?.role === "partner" || me?.role === "manager";
  const canApprove = me?.role === "admin" || me?.role === "partner";

  const [record, setRecord] = useState<MaterialityRecord | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [benchmark, setBenchmark] = useState<MaterialityBenchmark>("revenue");
  const [benchmarkAmount, setBenchmarkAmount] = useState("");
  const [overallPct, setOverallPct] = useState("1");
  const [performancePct, setPerformancePct] = useState("75");
  const [trivialPct, setTrivialPct] = useState("5");
  const [rationale, setRationale] = useState("");

  const base = `/api/engagements/${engagementId}/materiality`;

  const load = useCallback(() => {
    if (!engagementId) return;
    api
      .get<MaterialityRecord>(base)
      .then((row) => {
        setRecord(row);
        setBenchmark(row.benchmark);
        setBenchmarkAmount(row.benchmark_amount);
        setOverallPct(row.overall_percentage);
        setPerformancePct(row.performance_percentage);
        setTrivialPct(row.clearly_trivial_percentage);
        setRationale(row.rationale ?? "");
        setError(null);
      })
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 404) {
          setRecord(null);
        } else {
          setError(err instanceof Error ? err.message : String(err));
        }
      })
      .finally(() => setLoaded(true));
  }, [api, base, engagementId]);

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

  function save(event: FormEvent) {
    event.preventDefault();
    void run(
      () =>
        api.put(base, {
          benchmark,
          benchmark_amount: benchmarkAmount,
          overall_percentage: overallPct,
          performance_percentage: performancePct,
          clearly_trivial_percentage: trivialPct,
          rationale: rationale || null,
        }),
      "Materiality saved",
    );
  }

  if (!loaded) {
    return <p className="text-slate-500">Loading…</p>;
  }

  const locked = record?.status === "approved";
  const editable = canWrite && !locked;

  return (
    <div>
      <h2 className="text-xl font-semibold text-slate-800">Materiality</h2>
      <p className="mt-0.5 text-sm text-slate-500">
        <Link to={`/engagements/${engagementId}`} className="underline">
          Back to engagement
        </Link>
      </p>

      {notice && <p className="mt-3 text-sm text-green-700">{notice}</p>}
      {error && <p className="mt-3 break-all text-sm text-red-700">{error}</p>}

      {locked && record && (
        <div className="mt-4 rounded border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
          Approved and locked by {record.approved_by}
          {record.approved_at && <> on {new Date(record.approved_at).toLocaleDateString()}</>}.
          {canApprove && (
            <button
              type="button"
              disabled={busy}
              onClick={() => void run(() => api.post(`${base}/reopen`), "Reopened for editing")}
              className="ml-3 rounded border border-green-300 px-2 py-0.5 text-xs hover:bg-green-100 disabled:opacity-50"
            >
              Reopen
            </button>
          )}
        </div>
      )}

      {record && (
        <div className="mt-4 grid max-w-xl grid-cols-3 gap-3">
          <div className="rounded border border-slate-200 bg-white p-4">
            <p className="text-xs text-slate-500">Overall materiality</p>
            <p className="mt-1 text-lg font-semibold tabular-nums text-slate-800">
              {record.overall_materiality}
            </p>
          </div>
          <div className="rounded border border-slate-200 bg-white p-4">
            <p className="text-xs text-slate-500">Performance materiality</p>
            <p className="mt-1 text-lg font-semibold tabular-nums text-slate-800">
              {record.performance_materiality}
            </p>
          </div>
          <div className="rounded border border-slate-200 bg-white p-4">
            <p className="text-xs text-slate-500">Clearly trivial</p>
            <p className="mt-1 text-lg font-semibold tabular-nums text-slate-800">
              {record.clearly_trivial_threshold}
            </p>
          </div>
        </div>
      )}

      {record && !locked && canApprove && (
        <button
          type="button"
          disabled={busy}
          onClick={() => void run(() => api.post(`${base}/approve`), "Materiality approved")}
          className="mt-4 rounded bg-green-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Approve and lock
        </button>
      )}

      {!record && !canWrite && (
        <p className="mt-4 text-slate-500">Materiality has not been assessed yet.</p>
      )}

      {editable && (
        <form
          onSubmit={save}
          className="mt-6 max-w-xl space-y-4 rounded border border-slate-200 bg-white p-4"
        >
          <h3 className="text-sm font-semibold text-slate-700">
            {record ? "Update assessment" : "New assessment"}
          </h3>
          <div className="flex flex-wrap gap-4">
            <label className="flex flex-col text-sm text-slate-600">
              Benchmark
              <select
                value={benchmark}
                onChange={(e) => setBenchmark(e.target.value as MaterialityBenchmark)}
                className="mt-1 w-52 rounded border border-slate-300 bg-white px-2 py-1.5"
              >
                {MATERIALITY_BENCHMARKS.map((option) => (
                  <option key={option} value={option}>
                    {benchmarkLabel(option)}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col text-sm text-slate-600">
              Benchmark amount
              <input
                required
                type="number"
                step="0.01"
                min="0.01"
                value={benchmarkAmount}
                onChange={(e) => setBenchmarkAmount(e.target.value)}
                className="mt-1 w-44 rounded border border-slate-300 px-2 py-1.5"
              />
            </label>
          </div>
          <div className="flex flex-wrap gap-4">
            <label className="flex flex-col text-sm text-slate-600">
              Overall %
              <input
                required
                type="number"
                step="0.01"
                min="0.01"
                max="100"
                value={overallPct}
                onChange={(e) => setOverallPct(e.target.value)}
                className="mt-1 w-28 rounded border border-slate-300 px-2 py-1.5"
              />
              <span className="mt-1 text-xs text-slate-400">
                = {previewAmount(benchmarkAmount, overallPct)}
              </span>
            </label>
            <label className="flex flex-col text-sm text-slate-600">
              Performance % (of overall)
              <input
                required
                type="number"
                step="0.01"
                min="0.01"
                max="100"
                value={performancePct}
                onChange={(e) => setPerformancePct(e.target.value)}
                className="mt-1 w-28 rounded border border-slate-300 px-2 py-1.5"
              />
              <span className="mt-1 text-xs text-slate-400">
                = {previewAmount(previewAmount(benchmarkAmount, overallPct).replaceAll(",", ""), performancePct)}
              </span>
            </label>
            <label className="flex flex-col text-sm text-slate-600">
              Clearly trivial % (of overall)
              <input
                required
                type="number"
                step="0.01"
                min="0.01"
                max="100"
                value={trivialPct}
                onChange={(e) => setTrivialPct(e.target.value)}
                className="mt-1 w-28 rounded border border-slate-300 px-2 py-1.5"
              />
            </label>
          </div>
          <label className="flex flex-col text-sm text-slate-600">
            Rationale for benchmark selection
            <textarea
              value={rationale}
              onChange={(e) => setRationale(e.target.value)}
              rows={3}
              className="mt-1 rounded border border-slate-300 px-2 py-1.5"
            />
          </label>
          <button
            type="submit"
            disabled={busy}
            className="rounded bg-slate-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            Save
          </button>
        </form>
      )}
    </div>
  );
}
