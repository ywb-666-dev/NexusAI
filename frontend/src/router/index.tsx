import { Routes, Route, Navigate } from 'react-router-dom'
import BasicLayout from '../layout/BasicLayout'
import Login from '../pages/Login'
import Dashboard from '../pages/Dashboard'
import SubscriptionPage from '../pages/Subscription'
import ContentPage from '../pages/Content'
import ApprovalPage from '../pages/Approval'
import NotificationPage from '../pages/Notification'
import AgentMonitor from '../pages/AgentMonitor'
import { useAuthStore } from '../store/auth'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token)
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

function AppRouter() {
  return (
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
        <Route path="contents" element={<ContentPage />} />
        <Route path="approvals" element={<ApprovalPage />} />
        <Route path="notifications" element={<NotificationPage />} />
        <Route path="agent-monitor" element={<AgentMonitor />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

export default AppRouter
