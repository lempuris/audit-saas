import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import CrossReferencePanel from "../components/CrossReferencePanel";
import ReviewNotesPanel from "../components/ReviewNotesPanel";
import { useMe } from "../contexts/MeContext";
import { useApi } from "../hooks/useApi";
import type { CrossRefCandidate } from "../types/crossReferences";
import type { DocumentRecord } from "../types/documents";
import type { EngagementDetail, TeamMemberRecord } from "../types/engagements";
import {
  FS_AREAS,
  fsAreaLabel,
  type TrialBalanceDetail,
  type TrialBalanceLineRecord,
} from "../types/trialBalance";
import {
  WORKING_PAPER_STATUSES,
  type WorkingPaperRecord,
  type WorkingPaperStatus,
  type WorkingPaperVersionRecord,
} from "../types/workingPapers";

const EMPTY_NEW = {
  fs_area: "",
  index_ref: "",
  title: "",
  objective: "",
  result: "",
  conclusion: "",
};

type EditDraft = {
  index_ref: string;
  title: string;
  objective: string;
  result: string;
  conclusion: string;
};

function toDraft(wp: WorkingPaperRecord): EditDraft {
  return {
    index_ref: wp.index_ref,
    title: wp.title,
    objective: wp.objective,
    result: wp.result,
    conclusion: wp.conclusion,
  };
}

export default function WorkingPapersScreen() {
  const { engagementId } = useParams<{ engagementId: string }>();
  const api = useApi();
  const { me } = useMe();
  const role = me?.role ?? null;
  const canWrite = role !== null; // all signed-in staff prepare working papers
  const canDelete = role === "admin" || role === "partner" || role === "manager";

  const [papers, setPapers] = useState<WorkingPaperRecord[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [showNew, setShowNew] = useState(false);
  const [draft, setDraft] = useState(EMPTY_NEW);
  const [editId, setEditId] = useState<string | null>(null);
  const [edit, setEdit] = useState<EditDraft | null>(null);
  const [versionsFor, setVersionsFor] = useState<string | null>(null);
  const [versions, setVersions] = useState<WorkingPaperVersionRecord[]>([]);
  const [linksFor, setLinksFor] = useState<string | null>(null);
  const [notesFor, setNotesFor] = useState<string | null>(null);
  const [tbLines, setTbLines] = useState<TrialBalanceLineRecord[]>([]);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [team, setTeam] = useState<TeamMemberRecord[]>([]);

  const base = `/api/engagements/${engagementId}/working-papers`;

  const load = useCallback(() => {
    if (!engagementId) return;
    api
      .get<WorkingPaperRecord[]>(base)
      .then((rows) => {
        setPapers(rows);
        setError(null);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoaded(true));
    // Candidate cross-reference targets across the engagement.
    api
      .get<TrialBalanceDetail>(`/api/engagements/${engagementId}/trial-balance`)
      .then((tb) => setTbLines(tb.lines))
      .catch(() => setTbLines([]));
    api
      .get<DocumentRecord[]>(`/api/engagements/${engagementId}/documents`)
      .then(setDocuments)
      .catch(() => setDocuments([]));
    api
      .get<EngagementDetail>(`/api/engagements/${engagementId}`)
      .then((detail) => setTeam(detail.team))
      .catch(() => setTeam([]));
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

  function createPaper(event: FormEvent) {
    event.preventDefault();
    void run(
      () =>
        api.post(base, {
          fs_area: draft.fs_area,
          index_ref: draft.index_ref,
          title: draft.title,
          objective: draft.objective,
          result: draft.result,
          conclusion: draft.conclusion,
        }),
      "Working paper created",
    ).then(() => {
      setDraft(EMPTY_NEW);
      setShowNew(false);
    });
  }

  function startEdit(wp: WorkingPaperRecord) {
    setEditId(wp.id);
    setEdit(toDraft(wp));
  }

  function saveEdit(wpId: string) {
    if (!edit) return;
    void run(() => api.patch(`${base}/${wpId}`, edit), "Working paper updated").then(() => {
      setEditId(null);
      setEdit(null);
    });
  }

  function changeStatus(wp: WorkingPaperRecord, status: WorkingPaperStatus) {
    void run(() => api.patch(`${base}/${wp.id}/status`, { status }), "Status updated");
  }

  function remove(wpId: string) {
    void run(() => api.delete(`${base}/${wpId}`), "Working paper removed");
  }

  function toggleVersions(wp: WorkingPaperRecord) {
    if (versionsFor === wp.id) {
      setVersionsFor(null);
      return;
    }
    setVersionsFor(wp.id);
    api
      .get<WorkingPaperVersionRecord[]>(`${base}/${wp.id}/versions`)
      .then(setVersions)
      .catch(() => setVersions([]));
  }

  const candidates = useMemo<CrossRefCandidate[]>(
    () => [
      ...papers.map((p) => ({
        type: "working_paper" as const,
        id: p.id,
        label: `${p.index_ref} ${p.title}`,
      })),
      ...tbLines.map((l) => ({
        type: "trial_balance_line" as const,
        id: l.id,
        label: `${l.account_code} ${l.account_name}`,
      })),
      ...documents.map((d) => ({ type: "document" as const, id: d.id, label: d.filename })),
    ],
    [papers, tbLines, documents],
  );

  const byArea = useMemo(() => {
    const groups = new Map<string, WorkingPaperRecord[]>();
    for (const wp of papers) {
      const group = groups.get(wp.fs_area) ?? [];
      group.push(wp);
      groups.set(wp.fs_area, group);
    }
    return [...groups.entries()];
  }, [papers]);

  if (!loaded && !error) {
    return <p className="text-slate-500">Loading…</p>;
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-800">Working papers</h2>
          <p className="mt-0.5 text-sm text-slate-500">
            <Link to={`/engagements/${engagementId}`} className="underline">
              Back to engagement
            </Link>
          </p>
        </div>
        {canWrite && (
          <button
            type="button"
            onClick={() => setShowNew((previous) => !previous)}
            className="rounded bg-slate-800 px-3 py-1.5 text-sm font-medium text-white"
          >
            New working paper
          </button>
        )}
      </div>

      {notice && <p className="mt-3 text-sm text-green-700">{notice}</p>}
      {error && <p className="mt-3 break-all text-sm text-red-700">{error}</p>}

      {showNew && (
        <form
          onSubmit={createPaper}
          className="mt-4 space-y-3 rounded border border-slate-200 bg-white p-4"
        >
          <div className="flex flex-wrap gap-3">
            <label className="flex flex-col text-sm text-slate-600">
              FS area
              <select
                required
                value={draft.fs_area}
                onChange={(e) => setDraft((prev) => ({ ...prev, fs_area: e.target.value }))}
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
              Index ref
              <input
                required
                value={draft.index_ref}
                onChange={(e) => setDraft((prev) => ({ ...prev, index_ref: e.target.value }))}
                placeholder="e.g. C-1"
                className="mt-1 w-28 rounded border border-slate-300 px-2 py-1.5"
              />
            </label>
            <label className="flex flex-1 flex-col text-sm text-slate-600">
              Title
              <input
                required
                value={draft.title}
                onChange={(e) => setDraft((prev) => ({ ...prev, title: e.target.value }))}
                className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5"
              />
            </label>
          </div>
          <label className="flex flex-col text-sm text-slate-600">
            Objective
            <textarea
              value={draft.objective}
              onChange={(e) => setDraft((prev) => ({ ...prev, objective: e.target.value }))}
              rows={2}
              className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5"
            />
          </label>
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={busy}
              className="rounded bg-slate-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              Create
            </button>
          </div>
        </form>
      )}

      {papers.length === 0 && (
        <p className="mt-6 text-slate-500">No working papers on this engagement yet.</p>
      )}

      {byArea.map(([area, areaPapers]) => (
        <section key={area}>
          <h3 className="mt-8 text-sm font-semibold text-slate-700">{fsAreaLabel(area)}</h3>
          <div className="mt-2 space-y-3">
            {areaPapers.map((wp) => (
              <article key={wp.id} className="rounded border border-slate-200 bg-white p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-medium text-slate-800">
                      <span className="mr-2 rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">
                        {wp.index_ref}
                      </span>
                      {wp.title}
                    </p>
                    <p className="mt-0.5 text-xs text-slate-400">
                      v{wp.current_version}
                      {wp.status === "prepared" && wp.prepared_by
                        ? ` · prepared by ${wp.prepared_by_name ?? wp.prepared_by}`
                        : ""}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {canWrite ? (
                      <select
                        aria-label={`Status of ${wp.index_ref}`}
                        value={wp.status}
                        disabled={busy}
                        onChange={(e) => changeStatus(wp, e.target.value as WorkingPaperStatus)}
                        className="rounded border border-slate-300 bg-white px-2 py-1 text-xs capitalize"
                      >
                        {WORKING_PAPER_STATUSES.map((status) => (
                          <option key={status} value={status}>
                            {status}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <span className="text-xs capitalize text-slate-600">{wp.status}</span>
                    )}
                    <button
                      type="button"
                      onClick={() => setLinksFor((previous) => (previous === wp.id ? null : wp.id))}
                      className="rounded border border-slate-300 px-2 py-1 text-xs text-slate-700 hover:bg-slate-50"
                    >
                      Links
                    </button>
                    <button
                      type="button"
                      onClick={() => setNotesFor((previous) => (previous === wp.id ? null : wp.id))}
                      className="rounded border border-slate-300 px-2 py-1 text-xs text-slate-700 hover:bg-slate-50"
                    >
                      Notes
                    </button>
                    <button
                      type="button"
                      onClick={() => toggleVersions(wp)}
                      className="rounded border border-slate-300 px-2 py-1 text-xs text-slate-700 hover:bg-slate-50"
                    >
                      History
                    </button>
                  </div>
                </div>

                {editId === wp.id && edit ? (
                  <div className="mt-3 space-y-2">
                    <label className="flex flex-col text-xs text-slate-500">
                      Objective
                      <textarea
                        aria-label={`Objective for ${wp.index_ref}`}
                        value={edit.objective}
                        onChange={(e) => setEdit((prev) => prev && { ...prev, objective: e.target.value })}
                        rows={2}
                        className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
                      />
                    </label>
                    <label className="flex flex-col text-xs text-slate-500">
                      Result
                      <textarea
                        aria-label={`Result for ${wp.index_ref}`}
                        value={edit.result}
                        onChange={(e) => setEdit((prev) => prev && { ...prev, result: e.target.value })}
                        rows={2}
                        className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
                      />
                    </label>
                    <label className="flex flex-col text-xs text-slate-500">
                      Conclusion
                      <textarea
                        aria-label={`Conclusion for ${wp.index_ref}`}
                        value={edit.conclusion}
                        onChange={(e) =>
                          setEdit((prev) => prev && { ...prev, conclusion: e.target.value })
                        }
                        rows={2}
                        className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
                      />
                    </label>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => saveEdit(wp.id)}
                        className="rounded bg-slate-800 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
                      >
                        Save
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setEditId(null);
                          setEdit(null);
                        }}
                        className="rounded border border-slate-300 px-3 py-1.5 text-xs text-slate-700"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <dl className="mt-3 space-y-1.5 text-sm text-slate-600">
                    <Field label="Objective" value={wp.objective} />
                    <Field label="Result" value={wp.result} />
                    <Field label="Conclusion" value={wp.conclusion} />
                  </dl>
                )}

                {editId !== wp.id && (canWrite || canDelete) && (
                  <div className="mt-3 flex gap-2">
                    {canWrite && (
                      <button
                        type="button"
                        onClick={() => startEdit(wp)}
                        className="rounded border border-slate-300 px-3 py-1 text-xs text-slate-700 hover:bg-slate-50"
                      >
                        Edit
                      </button>
                    )}
                    {canDelete && (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => remove(wp.id)}
                        className="rounded border border-red-300 px-3 py-1 text-xs text-red-700 hover:bg-red-50 disabled:opacity-50"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                )}

                {linksFor === wp.id && (
                  <CrossReferencePanel
                    engagementId={engagementId ?? ""}
                    sourceType="working_paper"
                    sourceId={wp.id}
                    candidates={candidates}
                    canWrite={canWrite}
                  />
                )}

                {notesFor === wp.id && (
                  <ReviewNotesPanel
                    engagementId={engagementId ?? ""}
                    workingPaperId={wp.id}
                    team={team}
                  />
                )}

                {versionsFor === wp.id && (
                  <div className="mt-3 rounded border border-slate-100 bg-slate-50 p-3">
                    <p className="text-xs font-semibold text-slate-600">Version history</p>
                    {versions.length === 0 ? (
                      <p className="mt-1 text-xs text-slate-400">No versions recorded.</p>
                    ) : (
                      <ul className="mt-1 space-y-1 text-xs text-slate-600">
                        {versions.map((v) => (
                          <li key={v.id}>
                            v{v.version_no} · {v.status} · {v.title} ·{" "}
                            {new Date(v.created_at).toLocaleString()} ·{" "}
                            {v.edited_by_name ?? v.edited_by}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </article>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2">
      <dt className="w-24 shrink-0 text-xs font-medium uppercase tracking-wide text-slate-400">
        {label}
      </dt>
      <dd className="whitespace-pre-wrap">{value || <span className="text-slate-400">—</span>}</dd>
    </div>
  );
}
