import { useAuth } from "@clerk/clerk-react";
import { useMemo } from "react";

import { ApiClient } from "../services/api";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:5000";

export function useApi(): ApiClient {
  const { getToken } = useAuth();
  return useMemo(() => new ApiClient(API_URL, getToken), [getToken]);
}
