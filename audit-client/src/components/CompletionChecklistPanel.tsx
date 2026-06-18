import { useCallback, useEffect, useState } from "react";

import { useApi } from "../hooks/useApi";
import {
  CHECKLIST_STATUSES,
  type ChecklistItemRecord,
  type ChecklistItemStatus,
  type CompletionReadiness,
} from "../types/completion";

interface Props {
  engagementId: string;
  // Manager and above may seed and resolve items.
  canManage: boolean;
}

const STATUS_BADGE: Record<ChecklistItemStatus, string> = {
  open: "bg-amber-100 text-amber-800",
  complete: "bg-green-100 text-green-800",
  not_applicable: "bg-slate-100 text-slate-600",
};

function statusLabel(status: ChecklistItemStatus): string {
  return status === "not_applicable" ? "n/a" : status;
}

export default function CompletionChecklistPanel({ engagementId, canManage }: Props) {
  const api = useApi();
  const base = `/api/engagements/${engagementId}/completion-checklist`;

  const [items, setItems] = useState<ChecklistItemRecord[]>([]);
  const [readiness, setReadiness] = useState<CompletionReadiness | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api
      .get<ChecklistItemRecord[]>(base)
      .then((rows) => {
        setItems(rows);
        setError(null);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoaded(true));
    api
      .get<CompletionReadiness>(`${base}/readiness`)
      .then(setReadiness)
      .catch(() => setReadiness(null));
  }, [api, base]);

  useEffect(load, [load]);

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  function seed() {
    void run(() => api.post(`${base}/seed`, {}));
  }

  function setStatus(item: ChecklistItemRecord, status: ChecklistItemStatus) {
    void run(() => api.patch(`${base}/${item.id}`, { status, note: item.note }));
  }

  if (!loaded && !error) {
    return <p className="mt-2 text-sm text-slate-500">Loading checklist…</p>;
  }

  return (
    <div className="mt-2">
      {error && <p className="break-all text-sm text-red-700">{error}</p>}

      {readiness && (
        <div
          className={`rounded border p-3 text-sm ${
            readiness.ready
              ? "border-green-200 bg-green-50 text-green-800"
              : "border-amber-200 bg-amber-50 text-amber-800"
          }`}
        >
          {readiness.ready ? (
            <span>All completion items resolved and no uncleared review notes — ready to close.</span>
          ) : (
            <span>
              Not ready to close: {readiness.open_items} open item
              {readiness.open_items === 1 ? "" : "s"}, {readiness.uncleared_notes} uncleared review
              note{readiness.uncleared_notes === 1 ? "" : "s"}.
            </span>
          )}
        </div>
      )}

      {items.length === 0 ? (
        <div className="mt-3 rounded border border-slate-200 bg-white p-4">
          <p className="text-sm text-slate-600">
            The ISA completion checklist has not been initialized for this engagement.
          </p>
          {canManage && (
            <button
              type="button"
              disabled={busy}
              onClick={seed}
              className="mt-2 rounded bg-slate-800 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
            >
              Load standard checklist
            </button>
          )}
        </div>
      ) : (
        <ul className="mt-3 space-y-2">
          {items.map((item) => (
            <li key={item.id} className="rounded border border-slate-200 bg-white p-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-slate-800">{item.title}</p>
                  <p className="mt-0.5 text-xs text-slate-400">
                    {item.category}
                    {item.isa_reference ? ` · ${item.isa_reference}` : ""}
                    {item.resolved_by
                      ? ` · by ${item.resolved_by_name ?? item.resolved_by}`
                      : ""}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {canManage ? (
                    <select
                      aria-label={`Status of ${item.title}`}
                      value={item.status}
                      disabled={busy}
                      onChange={(e) => setStatus(item, e.target.value as ChecklistItemStatus)}
                      className="rounded border border-slate-300 bg-white px-2 py-1 text-xs"
                    >
                      {CHECKLIST_STATUSES.map((status) => (
                        <option key={status} value={status}>
                          {statusLabel(status)}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <span
                      className={`rounded px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[item.status]}`}
                    >
                      {statusLabel(item.status)}
                    </span>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
