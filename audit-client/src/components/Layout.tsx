import { UserButton } from "@clerk/clerk-react";
import { NavLink, Outlet } from "react-router-dom";

import { useMe } from "../contexts/MeContext";
import { navItemsForRole } from "./navigation";

export default function Layout() {
  const { me } = useMe();

  return (
    <div className="flex min-h-screen bg-slate-50">
      <aside className="flex w-56 flex-col border-r border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-4 py-4">
          <h1 className="text-lg font-semibold text-slate-800">AuditSaaS</h1>
          {me?.role && <p className="mt-0.5 text-xs capitalize text-slate-500">{me.role}</p>}
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {navItemsForRole(me?.role ?? null).map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `block rounded px-3 py-2 text-sm ${
                  isActive
                    ? "bg-slate-800 font-medium text-white"
                    : "text-slate-600 hover:bg-slate-100"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex flex-1 flex-col">
        <header className="flex items-center justify-end border-b border-slate-200 bg-white px-6 py-3">
          <UserButton />
        </header>
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
