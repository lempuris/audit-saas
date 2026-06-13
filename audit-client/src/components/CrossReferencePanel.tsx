import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useApi } from "../hooks/useApi";
import {
  CROSS_REF_TYPE_LABELS,
  type CrossRefCandidate,
  type CrossRefType,
  type CrossReferenceRecord,
} from "../types/crossReferences";

interface Props {
  engagementId: string;
  sourceType: CrossRefType;
  sourceId: string;
  /** Linkable targets across the engagement (WPs, TB lines, documents). */
  candidates: CrossRefCandidate[];
  canWrite: boolean;
}

export default function CrossReferencePanel({
  engagementId,
  sourceType,
  sourceId,
  candidates,
  canWrite,
}: Props) {
  const api = useApi();
  const navigate = useNavigate();
  const base = `/api/engagements/${engagementId}/cross-references`;

  const [refs, setRefs] = useState<CrossReferenceRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [targetType, setTargetType] = useState<CrossRefType>("trial_balance_line");
  const [targetId, setTargetId] = useState("");

  const load = useCallback(() => {
    api
      .get<CrossReferenceRecord[]>(`${base}?source_type=${sourceType}&source_id=${sourceId}`)
      .then(setRefs)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, [api, base, sourceType, sourceId]);

  useEffect(load, [load]);

  // Don't offer the source itself as a target.
  const options = candidates.filter(
    (c) => !(c.type === sourceType && c.id === sourceId),
  );
  const optionsForType = options.filter((c) => c.type === targetType);

  async function add() {
    if (!targetId) return;
    setBusy(true);
    setError(null);
    try {
      await api.post(base, {
        source_type: sourceType,
        source_id: sourceId,
        target_type: targetType,
        target_id: targetId,
      });
      setTargetId("");
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
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
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  function navigateTo(type: CrossRefType) {
    if (type === "working_paper") navigate(`/engagements/${engagementId}/working-papers`);
    else if (type === "trial_balance_line") navigate(`/engagements/${engagementId}/trial-balance`);
    else navigate(`/engagements/${engagementId}/documents`);
  }

  return (
    <div className="mt-3 rounded border border-slate-100 bg-slate-50 p-3">
      <p className="text-xs font-semibold text-slate-600">Cross-references</p>
      {error && <p className="mt-1 break-all text-xs text-red-700">{error}</p>}

      <div className="mt-1.5 flex flex-wrap gap-1.5">
        {refs.length === 0 && <span className="text-xs text-slate-400">None yet.</span>}
        {refs.map((ref) => (
          <span
            key={ref.id}
            className="inline-flex items-center gap-1 rounded-full border border-slate-300 bg-white px-2 py-0.5 text-xs text-slate-700"
          >
            <button
              type="button"
              onClick={() => navigateTo(ref.target_type)}
              className="underline-offset-2 hover:underline"
              title={CROSS_REF_TYPE_LABELS[ref.target_type]}
            >
              {ref.target_label}
            </button>
            {canWrite && (
              <button
                type="button"
                aria-label={`Remove cross-reference to ${ref.target_label}`}
                disabled={busy}
                onClick={() => void remove(ref.id)}
                className="text-slate-400 hover:text-red-600"
              >
                ×
              </button>
            )}
          </span>
        ))}
      </div>

      {canWrite && (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <select
            aria-label="Cross-reference target type"
            value={targetType}
            onChange={(e) => {
              setTargetType(e.target.value as CrossRefType);
              setTargetId("");
            }}
            className="rounded border border-slate-300 bg-white px-2 py-1 text-xs"
          >
            <option value="trial_balance_line">TB line</option>
            <option value="document">Document</option>
            <option value="working_paper">Working paper</option>
          </select>
          <select
            aria-label="Cross-reference target"
            value={targetId}
            onChange={(e) => setTargetId(e.target.value)}
            className="w-56 rounded border border-slate-300 bg-white px-2 py-1 text-xs"
          >
            <option value="">Select…</option>
            {optionsForType.map((c) => (
              <option key={c.id} value={c.id}>
                {c.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            disabled={busy || !targetId}
            onClick={() => void add()}
            className="rounded border border-slate-300 px-2 py-1 text-xs text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            Link
          </button>
        </div>
      )}
    </div>
  );
}
