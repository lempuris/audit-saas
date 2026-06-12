import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import { useMe } from "../contexts/MeContext";
import { useApi } from "../hooks/useApi";
import {
  PROCEDURE_STATUSES,
  type ProcedureRecord,
  type ProcedureStatus,
  type SeedResult,
} from "../types/auditPrograms";
import type { RiskRecord } from "../types/risks";
import { FS_AREAS, fsAreaLabel } from "../types/trialBalance";

const EMPTY_CUSTOM = { fs_area: "", title: "", description: "", isa_reference: "" };

export default function AuditProgramScreen() {
  const { engagementId } = useParams<{ engagementId: string }>();
  const api = useApi();
  const { me } = useMe();
  const canWrite = me?.role === "admin" || me?.role === "partner" || me?.role === "manager";

  const [procedures, setProcedures] = useState<ProcedureRecord[]>([]);
  const [risks, setRisks] = useState<RiskRecord[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showCustom, setShowCustom] = useState(false);
  const [custom, setCustom] = useState(EMPTY_CUSTOM);
  const [linksOpenFor, setLinksOpenFor] = useState<string | null>(null);

  const base = `/api/engagements/${engagementId}/procedures`;

  const load = useCallback(() => {
    if (!engagementId) return;
    api
      .get<ProcedureRecord[]>(base)
      .then((rows) => {
        setProcedures(rows);
        setError(null);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoaded(true));
    api
      .get<RiskRecord[]>(`/api/engagements/${engagementId}/risks`)
      .then(setRisks)
      .catch(() => setRisks([]));
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

  function loadStandardProgram() {
    void run(async () => {
      // Make sure the firm library exists, then pull it into this engagement.
      await api.post<SeedResult>("/api/procedure-templates/seed");
      await api.post<ProcedureRecord[]>(`${base}/from-templates`, {});
    }, "Standard ISA program loaded");
  }

  function addCustom(event: FormEvent) {
    event.preventDefault();
    void run(
      () =>
        api.post(base, {
          fs_area: custom.fs_area,
          title: custom.title,
          description: custom.description,
          isa_reference: custom.isa_reference || null,
        }),
      "Procedure added",
    ).then(() => {
      setCustom(EMPTY_CUSTOM);
      setShowCustom(false);
    });
  }

  function changeStatus(procedure: ProcedureRecord, status: ProcedureStatus) {
    void run(
      () => api.patch(`${base}/${procedure.id}/status`, { status }),
      "Status updated",
    );
  }

  function patchProcedure(procedureId: string, body: Record<string, unknown>, message: string) {
    void run(() => api.patch(`${base}/${procedureId}`, body), message);
  }

  function remove(procedureId: string) {
    void run(() => api.delete(`${base}/${procedureId}`), "Procedure removed");
  }

  function toggleRiskLink(procedure: ProcedureRecord, riskId: string) {
    const linked = procedure.linked_risk_ids.includes(riskId);
    const next = linked
      ? procedure.linked_risk_ids.filter((id) => id !== riskId)
      : [...procedure.linked_risk_ids, riskId];
    void run(
      () => api.put(`${base}/${procedure.id}/risks`, { risk_ids: next }),
      linked ? "Risk unlinked" : "Risk linked",
    );
  }

  const byArea = useMemo(() => {
    const groups = new Map<string, ProcedureRecord[]>();
    for (const procedure of procedures) {
      const group = groups.get(procedure.fs_area) ?? [];
      group.push(procedure);
      groups.set(procedure.fs_area, group);
    }
    return [...groups.entries()];
  }, [procedures]);

  if (!loaded && !error) {
    return <p className="text-slate-500">Loading…</p>;
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-800">Audit program</h2>
          <p className="mt-0.5 text-sm text-slate-500">
            <Link to={`/engagements/${engagementId}`} className="underline">
              Back to engagement
            </Link>
          </p>
        </div>
        {canWrite && (
          <div className="flex gap-2">
            <button
              type="button"
              disabled={busy}
              onClick={loadStandardProgram}
              className="rounded border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              Load standard ISA program
            </button>
            <button
              type="button"
              onClick={() => setShowCustom((previous) => !previous)}
              className="rounded bg-slate-800 px-3 py-1.5 text-sm font-medium text-white"
            >
              Add custom procedure
            </button>
          </div>
        )}
      </div>

      {notice && <p className="mt-3 text-sm text-green-700">{notice}</p>}
      {error && <p className="mt-3 break-all text-sm text-red-700">{error}</p>}

      {showCustom && (
        <form
          onSubmit={addCustom}
          className="mt-4 flex flex-wrap items-end gap-3 rounded border border-slate-200 bg-white p-4"
        >
          <label className="flex flex-col text-sm text-slate-600">
            FS area
            <select
              required
              value={custom.fs_area}
              onChange={(e) => setCustom((prev) => ({ ...prev, fs_area: e.target.value }))}
              className="mt-1 w-52 rounded border border-slate-300 bg-white px-2 py-1.5"
            >
              <option value="">Select…</option>
              {FS_AREAS.map((area) => (
                <option key={area} value={area}>
                  {fsAreaLabel(area)}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col text-sm text-slate-600">
            Title
            <input
              required
              value={custom.title}
              onChange={(e) => setCustom((prev) => ({ ...prev, title: e.target.value }))}
              className="mt-1 w-64 rounded border border-slate-300 px-2 py-1.5"
            />
          </label>
          <label className="flex flex-col text-sm text-slate-600">
            Description
            <input
              required
              value={custom.description}
              onChange={(e) => setCustom((prev) => ({ ...prev, description: e.target.value }))}
              className="mt-1 w-80 rounded border border-slate-300 px-2 py-1.5"
            />
          </label>
          <label className="flex flex-col text-sm text-slate-600">
            ISA reference
            <input
              value={custom.isa_reference}
              onChange={(e) => setCustom((prev) => ({ ...prev, isa_reference: e.target.value }))}
              placeholder="e.g. ISA 505"
              className="mt-1 w-32 rounded border border-slate-300 px-2 py-1.5"
            />
          </label>
          <button
            type="submit"
            disabled={busy}
            className="rounded bg-slate-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            Add
          </button>
        </form>
      )}

      {procedures.length === 0 && (
        <p className="mt-6 text-slate-500">
          No procedures on this engagement yet.
          {canWrite && " Load the standard ISA program or add custom procedures."}
        </p>
      )}

      {byArea.map(([area, areaProcedures]) => (
        <section key={area}>
          <h3 className="mt-8 text-sm font-semibold text-slate-700">{fsAreaLabel(area)}</h3>
          <div className="mt-2 overflow-x-auto rounded border border-slate-200 bg-white">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-slate-500">
                  <th className="px-4 py-2 font-medium">Procedure</th>
                  <th className="px-4 py-2 font-medium">Assigned to</th>
                  <th className="px-4 py-2 font-medium">Due</th>
                  <th className="px-4 py-2 font-medium">Status</th>
                  <th className="px-4 py-2 font-medium">Risks</th>
                  {canWrite && <th className="px-4 py-2 font-medium">Actions</th>}
                </tr>
              </thead>
              <tbody>
                {areaProcedures.map((procedure) => (
                  <tr key={procedure.id} className="border-b border-slate-100 align-top">
                    <td className="max-w-md px-4 py-2">
                      <p className="font-medium text-slate-800">
                        {procedure.title}
                        {procedure.isa_reference && (
                          <span className="ml-2 rounded bg-slate-100 px-1.5 py-0.5 text-xs font-normal text-slate-600">
                            {procedure.isa_reference}
                          </span>
                        )}
                      </p>
                      <p className="mt-0.5 text-xs text-slate-500">{procedure.description}</p>
                    </td>
                    <td className="px-4 py-2">
                      {canWrite ? (
                        <input
                          aria-label={`Assignee for ${procedure.title}`}
                          defaultValue={procedure.assigned_to ?? ""}
                          placeholder="user_…"
                          onBlur={(e) => {
                            const value = e.target.value.trim();
                            if (value !== (procedure.assigned_to ?? "")) {
                              patchProcedure(
                                procedure.id,
                                { assigned_to: value || null },
                                "Assignee updated",
                              );
                            }
                          }}
                          className="w-36 rounded border border-slate-300 px-2 py-1 text-xs"
                        />
                      ) : (
                        <span className="text-slate-600">{procedure.assigned_to ?? "—"}</span>
                      )}
                    </td>
                    <td className="px-4 py-2">
                      {canWrite ? (
                        <input
                          type="date"
                          aria-label={`Due date for ${procedure.title}`}
                          defaultValue={procedure.due_date ?? ""}
                          onBlur={(e) => {
                            const value = e.target.value;
                            if (value !== (procedure.due_date ?? "")) {
                              patchProcedure(
                                procedure.id,
                                { due_date: value || null },
                                "Due date updated",
                              );
                            }
                          }}
                          className="rounded border border-slate-300 px-2 py-1 text-xs"
                        />
                      ) : (
                        <span className="text-slate-600">{procedure.due_date ?? "—"}</span>
                      )}
                    </td>
                    <td className="px-4 py-2">
                      <select
                        aria-label={`Status of ${procedure.title}`}
                        value={procedure.status}
                        disabled={busy}
                        onChange={(e) =>
                          changeStatus(procedure, e.target.value as ProcedureStatus)
                        }
                        className="rounded border border-slate-300 bg-white px-2 py-1 text-xs"
                      >
                        {PROCEDURE_STATUSES.map((status) => (
                          <option key={status} value={status}>
                            {status.replaceAll("_", " ")}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-2">
                      <button
                        type="button"
                        disabled={!canWrite && procedure.linked_risk_ids.length === 0}
                        onClick={() =>
                          setLinksOpenFor((previous) =>
                            previous === procedure.id ? null : procedure.id,
                          )
                        }
                        className="rounded border border-slate-300 px-2 py-1 text-xs text-slate-700 hover:bg-slate-50"
                      >
                        {procedure.linked_risk_ids.length} linked
                      </button>
                      {linksOpenFor === procedure.id && (
                        <div className="mt-2 space-y-1">
                          {risks.length === 0 && (
                            <p className="text-xs text-slate-400">No risks documented.</p>
                          )}
                          {risks.map((risk) => (
                            <label
                              key={risk.id}
                              className="flex items-start gap-1.5 text-xs text-slate-600"
                            >
                              <input
                                type="checkbox"
                                disabled={!canWrite || busy}
                                checked={procedure.linked_risk_ids.includes(risk.id)}
                                onChange={() => toggleRiskLink(procedure, risk.id)}
                              />
                              {risk.description}
                            </label>
                          ))}
                        </div>
                      )}
                    </td>
                    {canWrite && (
                      <td className="px-4 py-2">
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => remove(procedure.id)}
                          className="rounded border border-red-300 px-3 py-1 text-xs text-red-700 hover:bg-red-50 disabled:opacity-50"
                        >
                          Remove
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}
    </div>
  );
}
