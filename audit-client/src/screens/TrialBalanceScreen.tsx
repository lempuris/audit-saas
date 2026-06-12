import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useMe } from "../contexts/MeContext";
import { useApi } from "../hooks/useApi";
import { ApiError } from "../services/api";
import {
  FS_AREAS,
  fsAreaLabel,
  type ColumnMapping,
  type FSAreaSummary,
  type TrialBalanceDetail,
  type TrialBalancePreview,
} from "../types/trialBalance";

type AmountMode = "balance" | "debit_credit";

/** Pick a likely column for a TB field from the detected headers. */
function guessColumn(columns: string[], hints: string[]): string {
  const lower = columns.map((column) => column.toLowerCase());
  for (const hint of hints) {
    const index = lower.findIndex((column) => column.includes(hint));
    if (index >= 0) return columns[index];
  }
  return "";
}

export default function TrialBalanceScreen() {
  const { engagementId } = useParams<{ engagementId: string }>();
  const api = useApi();
  const { me } = useMe();
  const canWrite = me?.role === "admin" || me?.role === "partner" || me?.role === "manager";

  const [tb, setTb] = useState<TrialBalanceDetail | null>(null);
  const [summary, setSummary] = useState<FSAreaSummary[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Import wizard
  const [showImport, setShowImport] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<TrialBalancePreview | null>(null);
  const [codeCol, setCodeCol] = useState("");
  const [nameCol, setNameCol] = useState("");
  const [amountMode, setAmountMode] = useState<AmountMode>("balance");
  const [balanceCol, setBalanceCol] = useState("");
  const [debitCol, setDebitCol] = useState("");
  const [creditCol, setCreditCol] = useState("");
  const [priorCol, setPriorCol] = useState("");

  // Regrouping edits not yet saved: line id -> new FS area ("" = unmapped).
  const [pendingAreas, setPendingAreas] = useState<Record<string, string>>({});

  const base = `/api/engagements/${engagementId}/trial-balance`;

  const load = useCallback(() => {
    if (!engagementId) return;
    api
      .get<TrialBalanceDetail>(base)
      .then((detail) => {
        setTb(detail);
        setError(null);
        api.get<FSAreaSummary[]>(`${base}/summary`).then(setSummary).catch(() => setSummary([]));
      })
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 404) {
          setTb(null);
          setSummary([]);
        } else {
          setError(err instanceof Error ? err.message : String(err));
        }
      })
      .finally(() => setLoaded(true));
  }, [api, base, engagementId]);

  useEffect(load, [load]);

  function fail(err: unknown) {
    setError(err instanceof Error ? err.message : String(err));
  }

  async function previewFile(selected: File) {
    setFile(selected);
    setPreview(null);
    setError(null);
    setBusy(true);
    try {
      const form = new FormData();
      form.append("file", selected);
      const result = await api.postForm<TrialBalancePreview>(`${base}/preview`, form);
      setPreview(result);
      setCodeCol(guessColumn(result.columns, ["code", "number", "no"]));
      setNameCol(guessColumn(result.columns, ["name", "description", "account"]));
      setBalanceCol(guessColumn(result.columns, ["balance", "amount", "current"]));
      setDebitCol(guessColumn(result.columns, ["debit", "dr"]));
      setCreditCol(guessColumn(result.columns, ["credit", "cr"]));
      setPriorCol(guessColumn(result.columns, ["prior", "previous", "py", "last"]));
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }

  async function importFile() {
    if (!file) return;
    const mapping: ColumnMapping = {
      account_code: codeCol,
      account_name: nameCol,
      balance: amountMode === "balance" ? balanceCol : null,
      debit: amountMode === "debit_credit" ? debitCol : null,
      credit: amountMode === "debit_credit" ? creditCol : null,
      prior_year_balance: priorCol || null,
    };
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("mapping", JSON.stringify(mapping));
      await api.postForm<TrialBalanceDetail>(base, form);
      setNotice("Trial balance imported");
      setShowImport(false);
      setFile(null);
      setPreview(null);
      setPendingAreas({});
      load();
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }

  async function saveGrouping() {
    const updates = Object.entries(pendingAreas).map(([lineId, area]) => ({
      line_id: lineId,
      fs_area: area || null,
    }));
    if (updates.length === 0) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await api.patch(`${base}/fs-areas`, updates);
      setNotice("Account grouping saved");
      setPendingAreas({});
      load();
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }

  const mappingComplete =
    codeCol &&
    nameCol &&
    (amountMode === "balance" ? balanceCol : debitCol && creditCol);

  const hasPrior = useMemo(
    () => (tb?.lines ?? []).some((line) => line.prior_year_balance !== null),
    [tb],
  );

  if (!loaded) {
    return <p className="text-slate-500">Loading…</p>;
  }

  const importWizard = (
    <div className="mt-4 rounded border border-slate-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-slate-700">
        {tb ? "Re-import trial balance (replaces the current one)" : "Import trial balance"}
      </h3>
      <label className="mt-3 block text-sm text-slate-600">
        XLSX or CSV file
        <input
          type="file"
          accept=".xlsx,.csv"
          disabled={busy}
          onChange={(e) => {
            const selected = e.target.files?.[0];
            if (selected) void previewFile(selected);
          }}
          className="mt-1 block text-sm"
        />
      </label>

      {preview && (
        <>
          <p className="mt-3 text-xs text-slate-500">
            {preview.total_rows} rows detected. Map the columns below, then import.
          </p>
          <div className="mt-2 overflow-x-auto rounded border border-slate-100">
            <table className="min-w-full text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-left text-slate-500">
                  {preview.columns.map((column) => (
                    <th key={column} className="px-3 py-1.5 font-medium">
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.rows.slice(0, 5).map((row, index) => (
                  <tr key={index} className="border-b border-slate-100">
                    {preview.columns.map((column) => (
                      <td key={column} className="px-3 py-1.5 text-slate-600">
                        {row[column] ?? ""}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex flex-wrap gap-4">
            <label className="flex flex-col text-sm text-slate-600">
              Account code column
              <select
                value={codeCol}
                onChange={(e) => setCodeCol(e.target.value)}
                className="mt-1 rounded border border-slate-300 bg-white px-2 py-1.5"
              >
                <option value="">Select…</option>
                {preview.columns.map((column) => (
                  <option key={column}>{column}</option>
                ))}
              </select>
            </label>
            <label className="flex flex-col text-sm text-slate-600">
              Account name column
              <select
                value={nameCol}
                onChange={(e) => setNameCol(e.target.value)}
                className="mt-1 rounded border border-slate-300 bg-white px-2 py-1.5"
              >
                <option value="">Select…</option>
                {preview.columns.map((column) => (
                  <option key={column}>{column}</option>
                ))}
              </select>
            </label>
            <label className="flex flex-col text-sm text-slate-600">
              Amounts
              <select
                value={amountMode}
                onChange={(e) => setAmountMode(e.target.value as AmountMode)}
                className="mt-1 rounded border border-slate-300 bg-white px-2 py-1.5"
              >
                <option value="balance">Single balance column</option>
                <option value="debit_credit">Debit and credit columns</option>
              </select>
            </label>
            {amountMode === "balance" ? (
              <label className="flex flex-col text-sm text-slate-600">
                Balance column
                <select
                  value={balanceCol}
                  onChange={(e) => setBalanceCol(e.target.value)}
                  className="mt-1 rounded border border-slate-300 bg-white px-2 py-1.5"
                >
                  <option value="">Select…</option>
                  {preview.columns.map((column) => (
                    <option key={column}>{column}</option>
                  ))}
                </select>
              </label>
            ) : (
              <>
                <label className="flex flex-col text-sm text-slate-600">
                  Debit column
                  <select
                    value={debitCol}
                    onChange={(e) => setDebitCol(e.target.value)}
                    className="mt-1 rounded border border-slate-300 bg-white px-2 py-1.5"
                  >
                    <option value="">Select…</option>
                    {preview.columns.map((column) => (
                      <option key={column}>{column}</option>
                    ))}
                  </select>
                </label>
                <label className="flex flex-col text-sm text-slate-600">
                  Credit column
                  <select
                    value={creditCol}
                    onChange={(e) => setCreditCol(e.target.value)}
                    className="mt-1 rounded border border-slate-300 bg-white px-2 py-1.5"
                  >
                    <option value="">Select…</option>
                    {preview.columns.map((column) => (
                      <option key={column}>{column}</option>
                    ))}
                  </select>
                </label>
              </>
            )}
            <label className="flex flex-col text-sm text-slate-600">
              Prior-year column (optional)
              <select
                value={priorCol}
                onChange={(e) => setPriorCol(e.target.value)}
                className="mt-1 rounded border border-slate-300 bg-white px-2 py-1.5"
              >
                <option value="">None</option>
                {preview.columns.map((column) => (
                  <option key={column}>{column}</option>
                ))}
              </select>
            </label>
          </div>

          <button
            type="button"
            disabled={busy || !mappingComplete}
            onClick={() => void importFile()}
            className="mt-4 rounded bg-slate-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            Import
          </button>
        </>
      )}
    </div>
  );

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-800">Trial balance</h2>
          <p className="mt-0.5 text-sm text-slate-500">
            <Link to={`/engagements/${engagementId}`} className="underline">
              Back to engagement
            </Link>
            {tb && (
              <>
                {" "}
                · {tb.source_filename} · {tb.lines.length} lines
              </>
            )}
          </p>
        </div>
        {canWrite && tb && !showImport && (
          <button
            type="button"
            onClick={() => setShowImport(true)}
            className="rounded border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
          >
            Re-import
          </button>
        )}
      </div>

      {notice && <p className="mt-3 text-sm text-green-700">{notice}</p>}
      {error && <p className="mt-3 break-all text-sm text-red-700">{error}</p>}

      {!tb && !canWrite && (
        <p className="mt-4 text-slate-500">No trial balance has been imported yet.</p>
      )}
      {canWrite && (!tb || showImport) && importWizard}

      {tb && summary.length > 0 && (
        <>
          <h3 className="mt-8 text-sm font-semibold text-slate-700">
            Financial statement areas
          </h3>
          <div className="mt-2 overflow-x-auto rounded border border-slate-200 bg-white">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-slate-500">
                  <th className="px-4 py-2 font-medium">Area</th>
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
                {summary.map((row) => (
                  <tr key={row.fs_area ?? "unmapped"} className="border-b border-slate-100">
                    <td className="px-4 py-2 text-slate-800">{fsAreaLabel(row.fs_area)}</td>
                    <td className="px-4 py-2 text-right text-slate-600">{row.line_count}</td>
                    <td className="px-4 py-2 text-right tabular-nums text-slate-800">
                      {row.balance}
                    </td>
                    {hasPrior && (
                      <>
                        <td className="px-4 py-2 text-right tabular-nums text-slate-600">
                          {row.prior_year_balance ?? "—"}
                        </td>
                        <td className="px-4 py-2 text-right tabular-nums text-slate-600">
                          {row.movement ?? "—"}
                        </td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {tb && (
        <>
          <div className="mt-8 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-700">Accounts</h3>
            {canWrite && Object.keys(pendingAreas).length > 0 && (
              <button
                type="button"
                disabled={busy}
                onClick={() => void saveGrouping()}
                className="rounded bg-slate-800 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
              >
                Save grouping ({Object.keys(pendingAreas).length})
              </button>
            )}
          </div>
          <div className="mt-2 overflow-x-auto rounded border border-slate-200 bg-white">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-slate-500">
                  <th className="px-4 py-2 font-medium">Code</th>
                  <th className="px-4 py-2 font-medium">Account</th>
                  <th className="px-4 py-2 text-right font-medium">Balance</th>
                  {hasPrior && <th className="px-4 py-2 text-right font-medium">Prior year</th>}
                  <th className="px-4 py-2 font-medium">FS area</th>
                </tr>
              </thead>
              <tbody>
                {tb.lines.map((line) => (
                  <tr key={line.id} className="border-b border-slate-100">
                    <td className="px-4 py-2 text-slate-600">{line.account_code}</td>
                    <td className="px-4 py-2 text-slate-800">{line.account_name}</td>
                    <td className="px-4 py-2 text-right tabular-nums text-slate-800">
                      {line.balance}
                    </td>
                    {hasPrior && (
                      <td className="px-4 py-2 text-right tabular-nums text-slate-600">
                        {line.prior_year_balance ?? "—"}
                      </td>
                    )}
                    <td className="px-4 py-2">
                      {canWrite ? (
                        <select
                          aria-label={`FS area for ${line.account_code}`}
                          value={pendingAreas[line.id] ?? line.fs_area ?? ""}
                          onChange={(e) =>
                            setPendingAreas((prev) => ({ ...prev, [line.id]: e.target.value }))
                          }
                          className="rounded border border-slate-300 bg-white px-2 py-1 text-xs"
                        >
                          <option value="">Unmapped</option>
                          {FS_AREAS.map((area) => (
                            <option key={area} value={area}>
                              {fsAreaLabel(area)}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <span className="text-slate-600">{fsAreaLabel(line.fs_area)}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
