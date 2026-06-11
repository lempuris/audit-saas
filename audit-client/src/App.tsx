import { SignedIn, SignedOut } from "@clerk/clerk-react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import Layout from "./components/Layout";
import RequireRole from "./components/RequireRole";
import { MeProvider } from "./contexts/MeContext";
import AuditTrailScreen from "./screens/AuditTrailScreen";
import ClientDetailScreen from "./screens/ClientDetailScreen";
import ClientsScreen from "./screens/ClientsScreen";
import EngagementDetailScreen from "./screens/EngagementDetailScreen";
import EngagementsScreen from "./screens/EngagementsScreen";
import HomeScreen from "./screens/HomeScreen";
import SignInScreen from "./screens/SignInScreen";
import UsersScreen from "./screens/UsersScreen";

export default function App() {
  return (
    <>
      <SignedOut>
        <SignInScreen />
      </SignedOut>
      <SignedIn>
        <MeProvider>
          <BrowserRouter>
            <Routes>
              <Route element={<Layout />}>
                <Route index element={<HomeScreen />} />
                <Route path="clients" element={<ClientsScreen />} />
                <Route path="clients/:clientId" element={<ClientDetailScreen />} />
                <Route path="engagements" element={<EngagementsScreen />} />
                <Route
                  path="engagements/:engagementId"
                  element={<EngagementDetailScreen />}
                />
                <Route
                  path="audit-trail"
                  element={
                    <RequireRole roles={["admin", "partner"]}>
                      <AuditTrailScreen />
                    </RequireRole>
                  }
                />
                <Route
                  path="users"
                  element={
                    <RequireRole roles={["admin"]}>
                      <UsersScreen />
                    </RequireRole>
                  }
                />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </MeProvider>
      </SignedIn>
    </>
  );
}
