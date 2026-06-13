import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import { useMe } from "../contexts/MeContext";
import { useApi } from "../hooks/useApi";
import { formatApiError } from "../services/api";
import {
  CONFIDENCE_LEVELS,
  SAMPLE_METHODS,
  type SampleComputation,
  type SampleMethod,
  type SampleRecord,
} from "../types/sampling";
import { FS_AREAS, fsAreaLabel } from "../types/trialBalance";
import type { WorkingPaperRecord } from "../types/workingPapers";

const EMPTY = {
  method: "monetary_unit" as SampleMethod,
  population_description: "",
  population_value: "",
  tolerable_misstatement: "",
  expected_misstatement: "0",
  confidence_level: 95,
  population_size: "",
  fs_area: "",
  working_paper_id: "",
};

function needsPopulationSize(method: SampleMethod): boolean {
  return method === "random" || method === "systematic";
}

export default function SamplingScreen() {
  const { engagementId } = useParams<{ engagementId: string }>();
  const api = useApi();
  const { me } = useMe();
  const canWrite = me?.role != null;

  const [form, setForm] = useState(EMPTY);
  const [computation, setComputation] = useState<SampleComputation | null>(null);
  const [samples, setSamples] = useState<SampleRecord[]>([]);
  const [papers, setPapers] = useState<WorkingPaperRecord[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

  const base = `/api/engagements/${engagementId}/samples`;

  const load = useCallback(() => {
    if (!engagementId) return;
    api
      .get<SampleRecord[]>(base)
      .then((rows) => {
        setSamples(rows);
        setError(null);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoaded(true));
    api
      .get<WorkingPaperRecord[]>(`/api/engagements/${engagementId}/working-papers`)
      .then(setPapers)
      .catch(() => setPapers([]));
  }, [api, base, engagementId]);

  useEffect(load, [load]);

  function buildPayload(): Record<string, unknown> {
    return {
      method: form.method,
      population_description: form.population_description,
      population_value: form.population_value,
      tolerable_misstatement: form.tolerable_misstatement,
      expected_misstatement: form.expected_misstatement || "0",
      confidence_level: form.confidence_level,
      population_size: needsPopulationSize(form.method)
        ? Number(form.population_size)
        : null,
      fs_area: form.fs_area || null,
      working_paper_id: form.working_paper_id || null,
    };
  }

  async function preview(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const result = await api.post<SampleComputation>(`${base}/preview`, buildPayload());
      setComputation(result);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await api.post<SampleRecord>(base, buildPayload());
      setNotice("Sample saved");
      setComputation(null);
      setForm(EMPTY);
      load();
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    setBusy(true);
    setError(null);
    try {
      await api.delete(`${base}/${id}`);
      load();
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setBusy(false);
    }
  }

  if (!loaded && !error) {
    return <p className="text-slate-500">Loading…</p>;
  }

  return (
    <div>
      <div>
        <h2 className="text-xl font-semibold text-slate-800">Sampling</h2>
        <p className="mt-0.5 text-sm text-slate-500">
          <Link to={`/engagements/${engagementId}`} className="underline">
            Back to engagement
          </Link>
        </p>
      </div>

      {notice && <p className="mt-3 text-sm text-green-700">{notice}</p>}
      {error && <p className="mt-3 break-all text-sm text-red-700">{error}</p>}

      {canWrite && (
        <form onSubmit={preview} className="mt-4 space-y-3 rounded border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap gap-3">
            <label className="flex flex-col text-sm text-slate-600">
              Method
              <select
                value={form.method}
                onChange={(e) => {
                  setForm((p) => ({ ...p, method: e.target.value as SampleMethod }));
                  setComputation(null);
                }}
                className="mt-1 w-52 rounded border border-slate-300 bg-white px-2 py-1.5"
              >
                {SAMPLE_METHODS.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-1 flex-col text-sm text-slate-600">
              Population description
              <input
                required
                value={form.population_description}
                onChange={(e) =>
                  setForm((p) => ({ ...p, population_description: e.target.value }))
                }
                className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5"
              />
            </label>
          </div>
          <div className="flex flex-wrap gap-3">
            <label className="flex flex-col text-sm text-slate-600">
              Population value
              <input
                required
                type="number"
                step="0.01"
                value={form.population_value}
                onChange={(e) => setForm((p) => ({ ...p, population_value: e.target.value }))}
                className="mt-1 w-40 rounded border border-slate-300 px-2 py-1.5"
              />
            </label>
            <label className="flex flex-col text-sm text-slate-600">
              Tolerable misstatement
              <input
                required
                type="number"
                step="0.01"
                value={form.tolerable_misstatement}
                onChange={(e) =>
                  setForm((p) => ({ ...p, tolerable_misstatement: e.target.value }))
                }
                className="mt-1 w-40 rounded border border-slate-300 px-2 py-1.5"
              />
            </label>
            <label className="flex flex-col text-sm text-slate-600">
              Expected misstatement
              <input
                type="number"
                step="0.01"
                value={form.expected_misstatement}
                onChange={(e) =>
                  setForm((p) => ({ ...p, expected_misstatement: e.target.value }))
                }
                className="mt-1 w-40 rounded border border-slate-300 px-2 py-1.5"
              />
            </label>
            <label className="flex flex-col text-sm text-slate-600">
              Confidence
              <select
                value={form.confidence_level}
                onChange={(e) =>
                  setForm((p) => ({ ...p, confidence_level: Number(e.target.value) }))
                }
                className="mt-1 w-24 rounded border border-slate-300 bg-white px-2 py-1.5"
              >
                {CONFIDENCE_LEVELS.map((level) => (
                  <option key={level} value={level}>
                    {level}%
                  </option>
                ))}
              </select>
            </label>
            {needsPopulationSize(form.method) && (
              <label className="flex flex-col text-sm text-slate-600">
                Population size (items)
                <input
                  required
                  type="number"
                  value={form.population_size}
                  onChange={(e) => setForm((p) => ({ ...p, population_size: e.target.value }))}
                  className="mt-1 w-40 rounded border border-slate-300 px-2 py-1.5"
                />
              </label>
            )}
          </div>
          <div className="flex flex-wrap gap-3">
            <label className="flex flex-col text-sm text-slate-600">
              FS area (optional)
              <select
                value={form.fs_area}
                onChange={(e) => setForm((p) => ({ ...p, fs_area: e.target.value }))}
                className="mt-1 w-52 rounded border border-slate-300 bg-white px-2 py-1.5"
              >
                <option value="">None</option>
                {FS_AREAS.map((area) => (
                  <option key={area} value={area}>
                    {fsAreaLabel(area)}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col text-sm text-slate-600">
              Working paper (optional)
              <select
                value={form.working_paper_id}
                onChange={(e) => setForm((p) => ({ ...p, working_paper_id: e.target.value }))}
                className="mt-1 w-64 rounded border border-slate-300 bg-white px-2 py-1.5"
              >
                <option value="">None</option>
                {papers.map((wp) => (
                  <option key={wp.id} value={wp.id}>
                    {wp.index_ref} {wp.title}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={busy}
              className="rounded border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              Compute sample
            </button>
            {computation && (
              <>
                <span className="text-sm text-slate-700">
                  Sample size: <strong>{computation.sample_size}</strong> (reliability factor{" "}
                  {computation.reliability_factor})
                </span>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void save()}
                  className="rounded bg-slate-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
                >
                  Save sample
                </button>
              </>
            )}
          </div>
        </form>
      )}

      <h3 className="mt-8 text-sm font-semibold text-slate-700">Samples</h3>
      {samples.length === 0 ? (
        <p className="mt-2 text-slate-500">No samples drawn yet.</p>
      ) : (
        <div className="mt-2 space-y-3">
          {samples.map((sample) => (
            <article key={sample.id} className="rounded border border-slate-200 bg-white p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-medium text-slate-800">{sample.population_description}</p>
                  <p className="mt-0.5 text-xs text-slate-500">
                    {sample.method.replaceAll("_", " ")} · size {sample.sample_size} · population{" "}
                    {sample.population_value} · tolerable {sample.tolerable_misstatement} ·{" "}
                    {sample.confidence_level}%
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setExpanded((p) => (p === sample.id ? null : sample.id))}
                    className="rounded border border-slate-300 px-2 py-1 text-xs text-slate-700 hover:bg-slate-50"
                  >
                    Selection
                  </button>
                  {canWrite && (
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => void remove(sample.id)}
                      className="rounded border border-red-300 px-2 py-1 text-xs text-red-700 hover:bg-red-50 disabled:opacity-50"
                    >
                      Remove
                    </button>
                  )}
                </div>
              </div>
              {expanded === sample.id && (
                <pre className="mt-2 max-h-48 overflow-auto rounded bg-slate-50 p-2 text-xs text-slate-600">
                  {JSON.stringify(sample.selection_basis, null, 2)}
                </pre>
              )}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
