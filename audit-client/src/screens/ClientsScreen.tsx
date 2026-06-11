import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import RiskBadge from "../components/RiskBadge";
import { useMe } from "../contexts/MeContext";
import { useApi } from "../hooks/useApi";
import { RISK_RATINGS, type ClientRecord, type RiskRating } from "../types/clients";

export default function ClientsScreen() {
  const api = useApi();
  const { me } = useMe();
  const canWrite = me?.role === "admin" || me?.role === "partner" || me?.role === "manager";

  const [clients, setClients] = useState<ClientRecord[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [busy, setBusy] = useState(false);

  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("");
  const [riskRating, setRiskRating] = useState<RiskRating | "">("");

  const load = useCallback(() => {
    api
      .get<ClientRecord[]>("/api/clients")
      .then((rows) => {
        setClients(rows);
        setError(null);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, [api]);

  useEffect(load, [load]);

  async function create(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post("/api/clients", {
        name,
        industry: industry || null,
        risk_rating: riskRating || null,
      });
      setName("");
      setIndustry("");
      setRiskRating("");
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
        <h2 className="text-xl font-semibold text-slate-800">Clients</h2>
        {canWrite && (
          <button
            type="button"
            onClick={() => setShowForm(!showForm)}
            className="rounded bg-slate-800 px-4 py-2 text-sm font-medium text-white"
          >
            {showForm ? "Cancel" : "New client"}
          </button>
        )}
      </div>

      {showForm && (
        <form
          onSubmit={create}
          className="mt-4 flex flex-wrap items-end gap-3 rounded border border-slate-200 bg-white p-4"
        >
          <label className="flex flex-col text-sm text-slate-600">
            Name
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 w-64 rounded border border-slate-300 px-2 py-1.5"
            />
          </label>
          <label className="flex flex-col text-sm text-slate-600">
            Industry
            <input
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              className="mt-1 w-48 rounded border border-slate-300 px-2 py-1.5"
            />
          </label>
          <label className="flex flex-col text-sm text-slate-600">
            Risk rating
            <select
              value={riskRating}
              onChange={(e) => setRiskRating(e.target.value as RiskRating | "")}
              className="mt-1 rounded border border-slate-300 bg-white px-2 py-1.5 capitalize"
            >
              <option value="">unrated</option>
              {RISK_RATINGS.map((rating) => (
                <option key={rating} value={rating}>
                  {rating}
                </option>
              ))}
            </select>
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
              <th className="px-4 py-2 font-medium">Name</th>
              <th className="px-4 py-2 font-medium">Industry</th>
              <th className="px-4 py-2 font-medium">Risk</th>
              <th className="px-4 py-2 font-medium">Contacts</th>
            </tr>
          </thead>
          <tbody>
            {clients?.map((row) => (
              <tr key={row.id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="px-4 py-2">
                  <Link to={`/clients/${row.id}`} className="font-medium text-slate-800 underline">
                    {row.name}
                  </Link>
                </td>
                <td className="px-4 py-2 text-slate-600">{row.industry ?? "—"}</td>
                <td className="px-4 py-2">
                  <RiskBadge rating={row.risk_rating} />
                </td>
                <td className="px-4 py-2 text-slate-600">
                  {row.contacts.length > 0
                    ? row.contacts.map((contact) => contact.name).join(", ")
                    : "—"}
                </td>
              </tr>
            ))}
            {clients && clients.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-slate-500">
                  No clients yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
        {!clients && !error && <p className="p-4 text-slate-500">Loading…</p>}
      </div>
    </div>
  );
}
