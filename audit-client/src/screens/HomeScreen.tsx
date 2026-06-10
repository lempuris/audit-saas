import { UserButton } from "@clerk/clerk-react";
import { useEffect, useState } from "react";

import { useApi } from "../hooks/useApi";
import type { HealthResponse } from "../types/health";

export default function HomeScreen() {
  const api = useApi();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<HealthResponse>("/api/health")
      .then(setHealth)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, [api]);

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
        <h1 className="text-lg font-semibold text-slate-800">AuditSaaS</h1>
        <UserButton />
      </header>
      <main className="p-6">
        <h2 className="mb-2 text-sm font-medium text-slate-500">API status</h2>
        {health && (
          <p className="text-slate-800">
            API: <span className="font-semibold text-green-700">{health.status}</span> · Database:{" "}
            <span className="font-semibold text-green-700">{health.database}</span> · Environment:{" "}
            {health.environment}
          </p>
        )}
        {error && <p className="text-red-700">API unreachable: {error}</p>}
        {!health && !error && <p className="text-slate-500">Checking…</p>}
      </main>
    </div>
  );
}
