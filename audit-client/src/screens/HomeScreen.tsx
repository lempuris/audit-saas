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
    <div>
      <h2 className="text-xl font-semibold text-slate-800">Dashboard</h2>
      <h3 className="mb-2 mt-4 text-sm font-medium text-slate-500">API status</h3>
      {health && (
        <p className="text-slate-800">
          API: <span className="font-semibold text-green-700">{health.status}</span> · Database:{" "}
          <span className="font-semibold text-green-700">{health.database}</span> · Environment:{" "}
          {health.environment}
        </p>
      )}
      {error && <p className="text-red-700">API unreachable: {error}</p>}
      {!health && !error && <p className="text-slate-500">Checking…</p>}
    </div>
  );
}
