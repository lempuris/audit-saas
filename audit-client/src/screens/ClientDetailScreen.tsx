import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import RiskBadge from "../components/RiskBadge";
import { useMe } from "../contexts/MeContext";
import { useApi } from "../hooks/useApi";
import {
  RISK_RATINGS,
  type ClientContact,
  type ClientRecord,
  type RiskRating,
} from "../types/clients";
import type { EngagementRecord } from "../types/engagements";

const EMPTY_CONTACT: ClientContact = { name: "", position: null, email: null, phone: null };

export default function ClientDetailScreen() {
  const { clientId } = useParams<{ clientId: string }>();
  const api = useApi();
  const { me } = useMe();
  const navigate = useNavigate();
  const canWrite = me?.role === "admin" || me?.role === "partner" || me?.role === "manager";
  const canArchive = me?.role === "admin" || me?.role === "partner";

  const [record, setRecord] = useState<ClientRecord | null>(null);
  const [engagements, setEngagements] = useState<EngagementRecord[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("");
  const [riskRating, setRiskRating] = useState<RiskRating | "">("");
  const [contacts, setContacts] = useState<ClientContact[]>([]);

  const load = useCallback(() => {
    if (!clientId) return;
    api
      .get<ClientRecord>(`/api/clients/${clientId}`)
      .then((row) => {
        setRecord(row);
        setName(row.name);
        setIndustry(row.industry ?? "");
        setRiskRating(row.risk_rating ?? "");
        setContacts(row.contacts);
        setError(null);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
    api
      .get<EngagementRecord[]>(`/api/engagements?client_id=${clientId}`)
      .then(setEngagements)
      .catch(() => setEngagements([]));
  }, [api, clientId]);

  useEffect(load, [load]);

  function setContact(index: number, field: keyof ClientContact, value: string) {
    setContacts((current) =>
      current.map((contact, i) =>
        i === index ? { ...contact, [field]: value || null } : contact,
      ),
    );
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setNotice(null);
    setError(null);
    try {
      await api.patch(`/api/clients/${clientId}`, {
        name,
        industry: industry || null,
        risk_rating: riskRating || null,
        contacts: contacts.filter((contact) => contact.name.trim() !== ""),
      });
      setNotice("Saved");
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function archive() {
    setBusy(true);
    setError(null);
    try {
      await api.delete(`/api/clients/${clientId}`);
      await navigate("/clients");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setBusy(false);
    }
  }

  if (!record && !error) {
    return <p className="text-slate-500">Loading…</p>;
  }
  if (error && !record) {
    return <p className="text-red-700">{error}</p>;
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-800">
            {record?.name}{" "}
            {record?.archived && (
              <span className="ml-2 rounded bg-slate-200 px-2 py-0.5 text-xs font-medium text-slate-600">
                archived
              </span>
            )}
          </h2>
          <p className="mt-0.5 text-sm text-slate-500">
            {record?.industry ?? "No industry"} · <RiskBadge rating={record?.risk_rating ?? null} />
          </p>
        </div>
        {canArchive && !record?.archived && (
          <button
            type="button"
            disabled={busy}
            onClick={() => void archive()}
            className="rounded border border-red-300 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
          >
            Archive client
          </button>
        )}
      </div>

      {notice && <p className="mt-3 text-sm text-green-700">{notice}</p>}
      {error && <p className="mt-3 text-sm text-red-700">{error}</p>}

      {canWrite && !record?.archived && (
        <form onSubmit={save} className="mt-6 rounded border border-slate-200 bg-white p-4">
          <h3 className="text-sm font-semibold text-slate-700">Details</h3>
          <div className="mt-3 flex flex-wrap gap-3">
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
          </div>

          <h3 className="mt-5 text-sm font-semibold text-slate-700">Contacts</h3>
          {contacts.map((contact, index) => (
            <div key={index} className="mt-2 flex flex-wrap items-center gap-2">
              <input
                placeholder="Name"
                aria-label={`Contact ${index + 1} name`}
                value={contact.name}
                onChange={(e) => setContact(index, "name", e.target.value)}
                className="w-44 rounded border border-slate-300 px-2 py-1.5 text-sm"
              />
              <input
                placeholder="Position"
                value={contact.position ?? ""}
                onChange={(e) => setContact(index, "position", e.target.value)}
                className="w-36 rounded border border-slate-300 px-2 py-1.5 text-sm"
              />
              <input
                placeholder="Email"
                type="email"
                value={contact.email ?? ""}
                onChange={(e) => setContact(index, "email", e.target.value)}
                className="w-56 rounded border border-slate-300 px-2 py-1.5 text-sm"
              />
              <input
                placeholder="Phone"
                value={contact.phone ?? ""}
                onChange={(e) => setContact(index, "phone", e.target.value)}
                className="w-36 rounded border border-slate-300 px-2 py-1.5 text-sm"
              />
              <button
                type="button"
                onClick={() => setContacts(contacts.filter((_, i) => i !== index))}
                className="text-sm text-red-600 hover:underline"
              >
                Remove
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={() => setContacts([...contacts, EMPTY_CONTACT])}
            className="mt-2 text-sm text-slate-600 underline"
          >
            Add contact
          </button>

          <div className="mt-4">
            <button
              type="submit"
              disabled={busy}
              className="rounded bg-slate-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              Save
            </button>
          </div>
        </form>
      )}

      <h3 className="mt-8 text-sm font-semibold text-slate-700">Engagements</h3>
      <div className="mt-2 overflow-x-auto rounded border border-slate-200 bg-white">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left text-slate-500">
              <th className="px-4 py-2 font-medium">Fiscal year</th>
              <th className="px-4 py-2 font-medium">Type</th>
              <th className="px-4 py-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {engagements?.map((engagement) => (
              <tr key={engagement.id} className="border-b border-slate-100">
                <td className="px-4 py-2">
                  <Link
                    to={`/engagements/${engagement.id}`}
                    className="font-medium text-slate-800 underline"
                  >
                    FY{engagement.fiscal_year}
                  </Link>
                </td>
                <td className="px-4 py-2 capitalize text-slate-600">
                  {engagement.engagement_type.replaceAll("_", " ")}
                </td>
                <td className="px-4 py-2 capitalize text-slate-600">{engagement.status}</td>
              </tr>
            ))}
            {engagements && engagements.length === 0 && (
              <tr>
                <td colSpan={3} className="px-4 py-6 text-center text-slate-500">
                  No engagements for this client yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
