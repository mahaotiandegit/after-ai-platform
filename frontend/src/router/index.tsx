import React from "react";
import { Navigate, RouteObject } from "react-router-dom";
import AdminLayout from "../layouts/AdminLayout";
import LoginPage from "../pages/LoginPage";
import DashboardPage from "../pages/DashboardPage";
import KnowledgeAskPage from "../pages/KnowledgeAskPage";
import TicketListPage from "../pages/TicketListPage";
import TicketCreatePage from "../pages/TicketCreatePage";
import AnalyticsNl2SqlPage from "../pages/AnalyticsNl2SqlPage";
import AiAuditLogsPage from "../pages/AiAuditLogsPage";
import AiQualityPage from "../pages/AiQualityPage";
import BadCasesPage from "../pages/BadCasesPage";
import { getToken } from "../utils/token";

function RequireAuth({ children }: { children: React.ReactElement }) {
  const token = getToken();
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export const routes: RouteObject[] = [
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/",
    element: (
      <RequireAuth>
        <AdminLayout />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: "dashboard", element: <DashboardPage /> },
      { path: "knowledge/ask", element: <KnowledgeAskPage /> },
      { path: "tickets", element: <TicketListPage /> },
      { path: "tickets/create", element: <TicketCreatePage /> },
      { path: "analytics/nl2sql", element: <AnalyticsNl2SqlPage /> },
      { path: "ai-audit-logs", element: <AiAuditLogsPage /> },
      { path: "ai-quality", element: <AiQualityPage /> },
      { path: "bad-cases", element: <BadCasesPage /> },
    ],
  },
  {
    path: "*",
    element: <Navigate to="/dashboard" replace />,
  },
];
