import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { useMe } from "../contexts/MeContext";
import { useApi } from "../hooks/useApi";
import type { ClientRecord } from "../types/clients";
import {
  ENGAGEMENT_TYPES,
  type EngagementRecord,
  type EngagementType,
} from "../types/engagements";

const CURRENT_YEAR = new Date().getFullYear();

export default function EngagementsScreen() {
  const api = useApi();
  const { me } = useMe();
  const canWrite = me?.role === "admin" || me?.role === "partner" || me?.role === "manager";

  const [engagements, setEngagements] = useState<EngagementRecord[] | null>(null);
  const [clients, setClients] = useState<ClientRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [busy, setBusy] = useState(false);

  const [clientId, setClientId] = useState("");
  const [engagementType, setEngagementType] = useState<EngagementType>("audit");
  const [fiscalYear, setFiscalYear] = useState(CURRENT_YEAR);

  const load = useCallback(() => {
    api
      .get<EngagementRecord[]>("/api/engagements")
      .then((rows) => {
        setEngagements(rows);
        setError(null);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
    api
      .get<ClientRecord[]>("/api/clients")
      .then(setClients)
      .catch(() => setClients([]));
  }, [api]);

  useEffect(load, [load]);

  const clientName = (id: string) => clients.find((row) => row.id === id)?.name ?? id;

  async function create(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post("/api/engagements", {
        client_id: clientId,
        engagement_type: engagementType,
        fiscal_year: fiscalYear,
      });
      setShowForm(false);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-slate-800">Engagements</h2>
        {canWrite && (
          <button
            type="button"
            onClick={() => setShowForm(!showForm)}
            className="rounded bg-slate-800 px-4 py-2 text-sm font-medium text-white"
          >
            {showForm ? "Cancel" : "New engagement"}
          </button>
        )}
      </div>

      {showForm && (
        <form
          onSubmit={create}
          className="mt-4 flex flex-wrap items-end gap-3 rounded border border-slate-200 bg-white p-4"
        >
          <label className="flex flex-col text-sm text-slate-600">
            Client
            <select
              required
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
              className="mt-1 w-64 rounded border border-slate-300 bg-white px-2 py-1.5"
            >
              <option value="">Select a client…</option>
              {clients
                .filter((row) => !row.archived)
                .map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name}
                  </option>
                ))}
            </select>
          </label>
          <label className="flex flex-col text-sm text-slate-600">
            Type
            <select
              value={engagementType}
              onChange={(e) => setEngagementType(e.target.value as EngagementType)}
              className="mt-1 rounded border border-slate-300 bg-white px-2 py-1.5"
            >
              {ENGAGEMENT_TYPES.map((value) => (
                <option key={value} value={value}>
                  {value.replaceAll("_", " ")}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col text-sm text-slate-600">
            Fiscal year
            <input
              type="number"
              min={2000}
              max={2100}
              value={fiscalYear}
              onChange={(e) => setFiscalYear(Number(e.target.value))}
              className="mt-1 w-28 rounded border border-slate-300 px-2 py-1.5"
            />
          </label>
          <button
            type="submit"
            disabled={busy}
            className="rounded bg-slate-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            Create
          </button>
        </form>
      )}

      {error && <p className="mt-3 text-sm text-red-700">{error}</p>}

      <div className="mt-4 overflow-x-auto rounded border border-slate-200 bg-white">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left text-slate-500">
              <th className="px-4 py-2 font-medium">Client</th>
              <th className="px-4 py-2 font-medium">Fiscal year</th>
              <th className="px-4 py-2 font-medium">Type</th>
              <th className="px-4 py-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {engagements?.map((engagement) => (
              <tr key={engagement.id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="px-4 py-2">
                  <Link
                    to={`/engagements/${engagement.id}`}
                    className="font-medium text-slate-800 underline"
                  >
                    {clientName(engagement.client_id)}
                  </Link>
                </td>
                <td className="px-4 py-2 text-slate-600">FY{engagement.fiscal_year}</td>
                <td className="px-4 py-2 capitalize text-slate-600">
                  {engagement.engagement_type.replaceAll("_", " ")}
                </td>
                <td className="px-4 py-2 capitalize text-slate-600">{engagement.status}</td>
              </tr>
            ))}
            {engagements && engagements.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-slate-500">
                  No engagements yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
        {!engagements && !error && <p className="p-4 text-slate-500">Loading…</p>}
      </div>
    </div>
  );
}
