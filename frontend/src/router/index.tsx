import { lazy, Suspense } from "react";
import { Skeleton } from "antd";
import { Routes, Route, Navigate } from "react-router-dom";
import BasicLayout from "../layout/BasicLayout";
import Login from "../pages/Login";
const Dashboard = lazy(() => import("../pages/Dashboard"));
const SubscriptionPage = lazy(() => import("../pages/Subscription"));
const ContentPage = lazy(() => import("../pages/Content"));
const ApprovalPage = lazy(() => import("../pages/Approval"));
const NotificationPage = lazy(() => import("../pages/Notification"));
const Tasks = lazy(() => import("../pages/Tasks"));
const PushSettings = lazy(() => import("../pages/PushSettings"));
const Sources = lazy(() => import("../pages/Sources"));
import { useAuthStore } from "../store/auth";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  return user?.role === "admin" ? (
    <>{children}</>
  ) : (
    <Navigate to="/dashboard" replace />
  );
}

function AppRouter() {
  return (
    <Suspense fallback={<Skeleton active paragraph={{ rows: 6 }} />}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <BasicLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="subscriptions" element={<SubscriptionPage />} />
          <Route path="sources" element={<Sources />} />
          <Route path="contents" element={<ContentPage />} />
          <Route
            path="approvals"
            element={
              <AdminRoute>
                <ApprovalPage />
              </AdminRoute>
            }
          />
          <Route path="tasks" element={<Tasks />} />
          <Route path="push" element={<PushSettings />} />
          <Route path="notifications" element={<NotificationPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Suspense>
  );
}

export default AppRouter;
