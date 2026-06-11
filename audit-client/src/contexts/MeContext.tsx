import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { useApi } from "../hooks/useApi";
import type { Me } from "../types/me";

interface MeState {
  me: Me | null;
  loading: boolean;
  error: string | null;
}

const MeContext = createContext<MeState>({ me: null, loading: true, error: null });

export function MeProvider({ children }: { children: ReactNode }) {
  const api = useApi();
  const [state, setState] = useState<MeState>({ me: null, loading: true, error: null });

  useEffect(() => {
    let cancelled = false;
    api
      .get<Me>("/api/me")
      .then((me) => {
        if (!cancelled) setState({ me, loading: false, error: null });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setState({
            me: null,
            loading: false,
            error: err instanceof Error ? err.message : String(err),
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [api]);

  return <MeContext.Provider value={state}>{children}</MeContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useMe(): MeState {
  return useContext(MeContext);
}
