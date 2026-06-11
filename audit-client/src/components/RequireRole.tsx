import type { ReactNode } from "react";

import { useMe } from "../contexts/MeContext";
import type { Role } from "../types/me";

export default function RequireRole({
  roles,
  children,
}: {
  roles: Role[];
  children: ReactNode;
}) {
  const { me, loading, error } = useMe();

  if (loading) {
    return <p className="text-slate-500">Loading…</p>;
  }
  if (error) {
    return <p className="text-red-700">Could not load your profile: {error}</p>;
  }
  if (!me?.role || !roles.includes(me.role)) {
    return <p className="text-slate-600">You do not have permission to view this page.</p>;
  }
  return <>{children}</>;
}
