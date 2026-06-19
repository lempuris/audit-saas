import { SignedIn, SignedOut } from "@clerk/clerk-react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import Layout from "./components/Layout";
import RequireRole from "./components/RequireRole";
import { MeProvider } from "./contexts/MeContext";
import AuditProgramScreen from "./screens/AuditProgramScreen";
import AuditTrailScreen from "./screens/AuditTrailScreen";
import ClientDetailScreen from "./screens/ClientDetailScreen";
import ClientsScreen from "./screens/ClientsScreen";
import DocumentsScreen from "./screens/DocumentsScreen";
import EngagementDetailScreen from "./screens/EngagementDetailScreen";
import EngagementsScreen from "./screens/EngagementsScreen";
import HomeScreen from "./screens/HomeScreen";
import LeadSchedulesScreen from "./screens/LeadSchedulesScreen";
import MaterialityScreen from "./screens/MaterialityScreen";
import ReportsScreen from "./screens/ReportsScreen";
import RisksScreen from "./screens/RisksScreen";
import SamplingScreen from "./screens/SamplingScreen";
import SignInScreen from "./screens/SignInScreen";
import TrialBalanceScreen from "./screens/TrialBalanceScreen";
import UsersScreen from "./screens/UsersScreen";
import WorkingPapersScreen from "./screens/WorkingPapersScreen";

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
                  path="engagements/:engagementId/trial-balance"
                  element={<TrialBalanceScreen />}
                />
                <Route
                  path="engagements/:engagementId/materiality"
                  element={<MaterialityScreen />}
                />
                <Route
                  path="engagements/:engagementId/risks"
                  element={<RisksScreen />}
                />
                <Route
                  path="engagements/:engagementId/program"
                  element={<AuditProgramScreen />}
                />
                <Route
                  path="engagements/:engagementId/lead-schedules"
                  element={<LeadSchedulesScreen />}
                />
                <Route
                  path="engagements/:engagementId/working-papers"
                  element={<WorkingPapersScreen />}
                />
                <Route
                  path="engagements/:engagementId/documents"
                  element={<DocumentsScreen />}
                />
                <Route
                  path="engagements/:engagementId/sampling"
                  element={<SamplingScreen />}
                />
                <Route
                  path="engagements/:engagementId/reports"
                  element={<ReportsScreen />}
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
