import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import RiskBadge from "../components/RiskBadge";
import { useMe } from "../contexts/MeContext";
import { useApi } from "../hooks/useApi";
import { FS_AREAS, fsAreaLabel } from "../types/trialBalance";
import {
  ASSERTIONS,
  RISK_RATINGS,
  type Assertion,
  type RiskLevel,
  type RiskRating,
  type RiskRecord,
} from "../types/risks";

const EMPTY_FORM = {
  level: "assertion" as RiskLevel,
  fs_area: "",
  assertions: [] as Assertion[],
  description: "",
  inherent_rating: "medium" as RiskRating,
  control_rating: "medium" as RiskRating,
  is_significant: false,
  planned_response: "",
};

export default function RisksScreen() {
  const { engagementId } = useParams<{ engagementId: string }>();
  const api = useApi();
  const { me } = useMe();
  const canWrite = me?.role === "admin" || me?.role === "partner" || me?.role === "manager";

  const [risks, setRisks] = useState<RiskRecord[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);

  const base = `/api/engagements/${engagementId}/risks`;

  const load = useCallback(() => {
    if (!engagementId) return;
    api
      .get<RiskRecord[]>(base)
      .then((rows) => {
        setRisks(rows);
        setError(null);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
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

  function openCreate() {
    setForm(EMPTY_FORM);
    setEditingId(null);
    setShowForm(true);
  }

  function openEdit(risk: RiskRecord) {
    setForm({
      level: risk.level,
      fs_area: risk.fs_area ?? "",
      assertions: risk.assertions,
      description: risk.description,
      inherent_rating: risk.inherent_rating,
      control_rating: risk.control_rating,
      is_significant: risk.is_significant,
      planned_response: risk.planned_response ?? "",
    });
    setEditingId(risk.id);
    setShowForm(true);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    const entityLevel = form.level === "entity";
    const payload = {
      ...(editingId === null && { level: form.level }),
      fs_area: entityLevel ? null : form.fs_area || null,
      assertions: entityLevel ? [] : form.assertions,
      description: form.description,
      inherent_rating: form.inherent_rating,
      control_rating: form.control_rating,
      is_significant: form.is_significant,
      planned_response: form.planned_response || null,
    };
    void run(
      () => (editingId ? api.patch(`${base}/${editingId}`, payload) : api.post(base, payload)),
      editingId ? "Risk updated" : "Risk added",
    ).then(() => {
      setShowForm(false);
      setEditingId(null);
    });
  }

  function remove(riskId: string) {
    void run(() => api.delete(`${base}/${riskId}`), "Risk deleted");
  }

  function toggleAssertion(assertion: Assertion) {
    setForm((prev) => ({
      ...prev,
      assertions: prev.assertions.includes(assertion)
        ? prev.assertions.filter((a) => a !== assertion)
        : [...prev.assertions, assertion],
    }));
  }

  if (!loaded && !error) {
    return <p className="text-slate-500">Loading…</p>;
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-800">Risk assessment</h2>
          <p className="mt-0.5 text-sm text-slate-500">
            <Link to={`/engagements/${engagementId}`} className="underline">
              Back to engagement
            </Link>
          </p>
        </div>
        {canWrite && !showForm && (
          <button
            type="button"
            onClick={openCreate}
            className="rounded bg-slate-800 px-4 py-2 text-sm font-medium text-white"
          >
            New risk
          </button>
        )}
      </div>

      {notice && <p className="mt-3 text-sm text-green-700">{notice}</p>}
      {error && <p className="mt-3 break-all text-sm text-red-700">{error}</p>}

      {showForm && (
        <form
          onSubmit={submit}
          className="mt-4 space-y-4 rounded border border-slate-200 bg-white p-4"
        >
          <h3 className="text-sm font-semibold text-slate-700">
            {editingId ? "Edit risk" : "New risk"}
          </h3>
          <div className="flex flex-wrap gap-4">
            <label className="flex flex-col text-sm text-slate-600">
              Level
              <select
                value={form.level}
                disabled={editingId !== null}
                onChange={(e) => setForm((prev) => ({ ...prev, level: e.target.value as RiskLevel }))}
                className="mt-1 w-40 rounded border border-slate-300 bg-white px-2 py-1.5 disabled:bg-slate-100"
              >
                <option value="assertion">Assertion level</option>
                <option value="entity">Entity level</option>
              </select>
            </label>
            {form.level === "assertion" && (
              <label className="flex flex-col text-sm text-slate-600">
                FS area
                <select
                  required
                  value={form.fs_area}
                  onChange={(e) => setForm((prev) => ({ ...prev, fs_area: e.target.value }))}
                  className="mt-1 w-56 rounded border border-slate-300 bg-white px-2 py-1.5"
                >
                  <option value="">Select…</option>
                  {FS_AREAS.map((area) => (
                    <option key={area} value={area}>
                      {fsAreaLabel(area)}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <label className="flex flex-col text-sm text-slate-600">
              Inherent risk
              <select
                value={form.inherent_rating}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, inherent_rating: e.target.value as RiskRating }))
                }
                className="mt-1 w-32 rounded border border-slate-300 bg-white px-2 py-1.5"
              >
                {RISK_RATINGS.map((rating) => (
                  <option key={rating}>{rating}</option>
                ))}
              </select>
            </label>
            <label className="flex flex-col text-sm text-slate-600">
              Control risk
              <select
                value={form.control_rating}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, control_rating: e.target.value as RiskRating }))
                }
                className="mt-1 w-32 rounded border border-slate-300 bg-white px-2 py-1.5"
              >
                {RISK_RATINGS.map((rating) => (
                  <option key={rating}>{rating}</option>
                ))}
              </select>
            </label>
            <label className="mt-5 flex items-center gap-2 text-sm text-slate-600">
              <input
                type="checkbox"
                checked={form.is_significant}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, is_significant: e.target.checked }))
                }
              />
              Significant risk
            </label>
          </div>

          {form.level === "assertion" && (
            <fieldset className="text-sm text-slate-600">
              <legend>Assertions</legend>
              <div className="mt-1 flex flex-wrap gap-3">
                {ASSERTIONS.map((assertion) => (
                  <label key={assertion} className="flex items-center gap-1.5">
                    <input
                      type="checkbox"
                      checked={form.assertions.includes(assertion)}
                      onChange={() => toggleAssertion(assertion)}
                    />
                    {assertion.replaceAll("_", " ")}
                  </label>
                ))}
              </div>
            </fieldset>
          )}

          <label className="flex flex-col text-sm text-slate-600">
            Description
            <textarea
              required
              value={form.description}
              onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
              rows={2}
              className="mt-1 rounded border border-slate-300 px-2 py-1.5"
            />
          </label>
          <label className="flex flex-col text-sm text-slate-600">
            Planned response
            <textarea
              value={form.planned_response}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, planned_response: e.target.value }))
              }
              rows={2}
              className="mt-1 rounded border border-slate-300 px-2 py-1.5"
            />
          </label>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={busy}
              className="rounded bg-slate-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {editingId ? "Save changes" : "Add risk"}
            </button>
            <button
              type="button"
              onClick={() => {
                setShowForm(false);
                setEditingId(null);
              }}
              className="rounded border border-slate-300 px-4 py-2 text-sm text-slate-700"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      <div className="mt-4 overflow-x-auto rounded border border-slate-200 bg-white">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left text-slate-500">
              <th className="px-4 py-2 font-medium">Risk</th>
              <th className="px-4 py-2 font-medium">Level / area</th>
              <th className="px-4 py-2 font-medium">Inherent</th>
              <th className="px-4 py-2 font-medium">Control</th>
              <th className="px-4 py-2 font-medium">Combined</th>
              <th className="px-4 py-2 font-medium">Planned response</th>
              {canWrite && <th className="px-4 py-2 font-medium">Actions</th>}
            </tr>
          </thead>
          <tbody>
            {risks.map((risk) => (
              <tr key={risk.id} className="border-b border-slate-100 align-top">
                <td className="px-4 py-2 text-slate-800">
                  {risk.description}
                  {risk.is_significant && (
                    <span className="ml-2 rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800">
                      significant
                    </span>
                  )}
                  {risk.assertions.length > 0 && (
                    <p className="mt-1 text-xs text-slate-500">
                      {risk.assertions.map((a) => a.replaceAll("_", " ")).join(", ")}
                    </p>
                  )}
                </td>
                <td className="px-4 py-2 text-slate-600">
                  {risk.level === "entity" ? "Entity" : fsAreaLabel(risk.fs_area)}
                </td>
                <td className="px-4 py-2">
                  <RiskBadge rating={risk.inherent_rating} />
                </td>
                <td className="px-4 py-2">
                  <RiskBadge rating={risk.control_rating} />
                </td>
                <td className="px-4 py-2">
                  <RiskBadge rating={risk.combined_rating} />
                </td>
                <td className="px-4 py-2 text-slate-600">{risk.planned_response ?? "—"}</td>
                {canWrite && (
                  <td className="px-4 py-2">
                    <div className="flex gap-2">
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => openEdit(risk)}
                        className="rounded border border-slate-300 px-3 py-1 text-xs text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => remove(risk.id)}
                        className="rounded border border-red-300 px-3 py-1 text-xs text-red-700 hover:bg-red-50 disabled:opacity-50"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                )}
              </tr>
            ))}
            {risks.length === 0 && (
              <tr>
                <td colSpan={canWrite ? 7 : 6} className="px-4 py-6 text-center text-slate-500">
                  No risks documented yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
