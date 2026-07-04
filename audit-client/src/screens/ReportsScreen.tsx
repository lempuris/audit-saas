import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useMe } from "../contexts/MeContext";
import { formatApiError } from "../services/api";
import { useApi } from "../hooks/useApi";
import type { EngagementRecord } from "../types/engagements";
import {
  OPINION_TYPES,
  reportTypeLabel,
  type OpinionType,
  type ReportRecord,
  type ReportSection,
} from "../types/reports";

type Draft = {
  title: string;
  letterhead: string;
  opinion: OpinionType | null;
  sections: ReportSection[];
};

function toDraft(report: ReportRecord): Draft {
  return {
    title: report.title,
    letterhead: report.letterhead,
    opinion: report.opinion_type,
    sections: report.sections.map((s) => ({ ...s })),
  };
}

export default function ReportsScreen() {
  const { engagementId } = useParams<{ engagementId: string }>();
  const api = useApi();
  const { me } = useMe();
  const role = me?.role ?? null;
  const canManage = role === "admin" || role === "partner" || role === "manager";
  const canFinalize = role === "admin" || role === "partner";

  const [reports, setReports] = useState<ReportRecord[]>([]);
  const [engagement, setEngagement] = useState<EngagementRecord | null>(null);
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  // Report the message belongs to, so it renders next to that report's buttons
  // instead of at the top of the page; null for screen-level actions.
  const [actionReportId, setActionReportId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [newOpinion, setNewOpinion] = useState<OpinionType>("unmodified");

  const base = `/api/engagements/${engagementId}/reports`;

  const load = useCallback(() => {
    if (!engagementId) return;
    api
      .get<EngagementRecord>(`/api/engagements/${engagementId}`)
      .then(setEngagement)
      .catch(() => setEngagement(null));
    api
      .get<ReportRecord[]>(base)
      .then((rows) => {
        setReports(rows);
        setDrafts(Object.fromEntries(rows.map((r) => [r.id, toDraft(r)])));
        setError(null);
      })
      .catch((err: unknown) => {
        setActionReportId(null);
        setError(formatApiError(err));
      })
      .finally(() => setLoaded(true));
  }, [api, base, engagementId]);

  useEffect(load, [load]);

  // A completed engagement is archived and read-only, except that the API
  // lets a Partner/Admin still amend its reports (post-assembly opinion
  // changes, documented in the audit trail). Creating and deleting reports
  // stay locked for everyone.
  const isArchived = engagement?.status === "completed";
  const archiveLocked = isArchived && !canFinalize;

  async function run(action: () => Promise<unknown>, successNotice: string, reportId?: string) {
    setBusy(true);
    setNotice(null);
    setError(null);
    setActionReportId(reportId ?? null);
    try {
      await action();
      setNotice(successNotice);
      load();
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setBusy(false);
    }
  }

  const hasType = (type: string) => reports.some((r) => r.report_type === type);

  function createAuditReport() {
    void run(
      () => api.post(base, { report_type: "audit_report", opinion_type: newOpinion }),
      "Audit report created",
    );
  }

  function createManagementLetter() {
    void run(() => api.post(base, { report_type: "management_letter" }), "Management letter created");
  }

  function patchDraft(reportId: string, patch: Partial<Draft>) {
    setDrafts((prev) => ({ ...prev, [reportId]: { ...prev[reportId], ...patch } }));
  }

  function patchSection(reportId: string, index: number, patch: Partial<ReportSection>) {
    setDrafts((prev) => {
      const draft = prev[reportId];
      const sections = draft.sections.map((s, i) => (i === index ? { ...s, ...patch } : s));
      return { ...prev, [reportId]: { ...draft, sections } };
    });
  }

  function save(report: ReportRecord) {
    const draft = drafts[report.id];
    if (!draft) return;
    void run(
      () =>
        api.patch(`${base}/${report.id}`, {
          title: draft.title,
          letterhead: draft.letterhead,
          sections: draft.sections,
          // Audit reports only; the backend regenerates the Opinion and Basis
          // sections when this differs from the saved opinion.
          ...(draft.opinion ? { opinion_type: draft.opinion } : {}),
        }),
      "Report saved",
      report.id,
    );
  }

  function finalize(report: ReportRecord) {
    void run(
      () => api.patch(`${base}/${report.id}`, { status: "final" }),
      "Report finalized",
      report.id,
    );
  }

  function reopen(report: ReportRecord) {
    void run(
      () => api.patch(`${base}/${report.id}`, { status: "draft" }),
      "Report reopened",
      report.id,
    );
  }

  function remove(report: ReportRecord) {
    void run(() => api.delete(`${base}/${report.id}`), "Report deleted");
  }

  async function downloadPdf(report: ReportRecord) {
    setBusy(true);
    setError(null);
    setActionReportId(report.id);
    try {
      const blob = await api.getBlob(`${base}/${report.id}/pdf`);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${report.report_type}-${report.id}.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
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
        <h2 className="text-xl font-semibold text-slate-800">Reports</h2>
        <p className="mt-0.5 text-sm text-slate-500">
          <Link to={`/engagements/${engagementId}`} className="underline">
            Back to engagement
          </Link>
        </p>
      </div>

      {isArchived && (
        <div className="mt-4 rounded border border-slate-300 bg-slate-50 p-3 text-sm text-slate-700">
          <span className="font-medium">Archived &amp; read-only.</span>{" "}
          {canFinalize
            ? "This engagement is completed. As a Partner/Admin you can still amend its " +
              "reports; every change is documented in the audit trail (ISA 230)."
            : "This engagement is completed, so its reports can be viewed and downloaded " +
              "but no longer changed."}
        </div>
      )}

      {notice && actionReportId === null && (
        <p className="mt-3 text-sm text-green-700">{notice}</p>
      )}
      {error && actionReportId === null && (
        <p className="mt-3 break-all text-sm text-red-700">{error}</p>
      )}

      {canManage && !isArchived && (!hasType("audit_report") || !hasType("management_letter")) && (
        <div className="mt-4 flex flex-wrap items-end gap-3 rounded border border-slate-200 bg-white p-4">
          {!hasType("audit_report") && (
            <div className="flex items-end gap-2">
              <label className="flex flex-col text-sm text-slate-600">
                Opinion
                <select
                  aria-label="Opinion type"
                  value={newOpinion}
                  onChange={(e) => setNewOpinion(e.target.value as OpinionType)}
                  className="mt-1 w-44 rounded border border-slate-300 bg-white px-2 py-1.5 capitalize"
                >
                  {OPINION_TYPES.map((opinion) => (
                    <option key={opinion} value={opinion}>
                      {opinion}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                disabled={busy}
                onClick={createAuditReport}
                className="rounded bg-slate-800 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                Create audit report
              </button>
            </div>
          )}
          {!hasType("management_letter") && (
            <button
              type="button"
              disabled={busy}
              onClick={createManagementLetter}
              className="rounded border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              Create management letter
            </button>
          )}
        </div>
      )}

      {reports.length === 0 && (
        <p className="mt-6 text-slate-500">No reports yet for this engagement.</p>
      )}

      {reports.map((report) => {
        const draft = drafts[report.id];
        const isFinal = report.status === "final";
        const editable = !archiveLocked && canManage && (!isFinal || canFinalize);
        return (
          <section
            key={report.id}
            className="mt-6 rounded border border-slate-200 bg-white p-4"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-sm font-semibold text-slate-700">
                {reportTypeLabel(report.report_type)}
                {report.opinion_type ? ` · ${report.opinion_type}` : ""}
              </h3>
              <div className="flex items-center gap-2">
                <span
                  className={`rounded px-2 py-0.5 text-xs font-medium capitalize ${
                    isFinal ? "bg-green-100 text-green-800" : "bg-slate-100 text-slate-600"
                  }`}
                >
                  {report.status}
                </span>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => downloadPdf(report)}
                  className="rounded border border-slate-300 px-2 py-1 text-xs text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                >
                  Download PDF
                </button>
              </div>
            </div>

            {draft && (
              <div className="mt-3 space-y-3">
                <label className="flex flex-col text-sm text-slate-600">
                  Title
                  <input
                    aria-label={`Title of ${reportTypeLabel(report.report_type)}`}
                    value={draft.title}
                    disabled={!editable}
                    onChange={(e) => patchDraft(report.id, { title: e.target.value })}
                    className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 disabled:bg-slate-50"
                  />
                </label>
                <label className="flex flex-col text-sm text-slate-600">
                  Letterhead
                  <textarea
                    aria-label="Letterhead"
                    value={draft.letterhead}
                    disabled={!editable}
                    onChange={(e) => patchDraft(report.id, { letterhead: e.target.value })}
                    rows={3}
                    className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 font-mono text-xs disabled:bg-slate-50"
                  />
                </label>

                {report.report_type === "audit_report" && (
                  <label className="flex flex-col text-sm text-slate-600">
                    Type of opinion
                    <select
                      aria-label="Type of opinion"
                      value={draft.opinion ?? "unmodified"}
                      disabled={!editable}
                      onChange={(e) =>
                        patchDraft(report.id, { opinion: e.target.value as OpinionType })
                      }
                      className="mt-1 w-44 rounded border border-slate-300 bg-white px-2 py-1.5 capitalize disabled:bg-slate-50"
                    >
                      {OPINION_TYPES.map((opinion) => (
                        <option key={opinion} value={opinion}>
                          {opinion}
                        </option>
                      ))}
                    </select>
                    {draft.opinion !== report.opinion_type && (
                      <span className="mt-1 text-xs text-amber-700">
                        Saving will replace the Opinion and Basis for Opinion sections with the
                        standard wording for a {draft.opinion} opinion. Other sections are kept.
                      </span>
                    )}
                  </label>
                )}

                {draft.sections.map((section, index) => (
                  <div key={section.key} className="rounded border border-slate-100 p-3">
                    <input
                      aria-label={`Heading for ${section.key}`}
                      value={section.heading}
                      disabled={!editable}
                      onChange={(e) => patchSection(report.id, index, { heading: e.target.value })}
                      className="w-full rounded border border-slate-200 px-2 py-1 text-sm font-medium text-slate-800 disabled:bg-slate-50"
                    />
                    <textarea
                      aria-label={`Body for ${section.key}`}
                      value={section.body}
                      disabled={!editable}
                      onChange={(e) => patchSection(report.id, index, { body: e.target.value })}
                      rows={4}
                      className="mt-2 w-full rounded border border-slate-200 px-2 py-1.5 text-sm disabled:bg-slate-50"
                    />
                  </div>
                ))}

                {notice && actionReportId === report.id && (
                  <p className="text-sm text-green-700">{notice}</p>
                )}
                {error && actionReportId === report.id && (
                  <p className="break-all text-sm text-red-700">{error}</p>
                )}

                {!archiveLocked && (editable || canFinalize) && (
                  <div className="flex flex-wrap gap-2">
                    {editable && (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => save(report)}
                        className="rounded bg-slate-800 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
                      >
                        Save
                      </button>
                    )}
                    {canFinalize && !isFinal && (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => finalize(report)}
                        className="rounded border border-green-300 px-3 py-1.5 text-sm text-green-700 hover:bg-green-50 disabled:opacity-50"
                      >
                        Finalize
                      </button>
                    )}
                    {canFinalize && isFinal && (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => reopen(report)}
                        className="rounded border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                      >
                        Reopen
                      </button>
                    )}
                    {canFinalize && !isArchived && (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => remove(report)}
                        className="rounded border border-red-300 px-3 py-1.5 text-sm text-red-700 hover:bg-red-50 disabled:opacity-50"
                      >
                        Delete
                      </button>
                    )}
                  </div>
                )}
              </div>
            )}
          </section>
        );
      })}
    </div>
  );
}
