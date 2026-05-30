import { Routes, Route, Navigate } from 'react-router-dom'
import BasicLayout from '../layout/BasicLayout'
import Login from '../pages/Login'
import Dashboard from '../pages/Dashboard'
import SubscriptionPage from '../pages/Subscription'
import ContentPage from '../pages/Content'
import ApprovalPage from '../pages/Approval'
import NotificationPage from '../pages/Notification'

function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<BasicLayout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="subscriptions" element={<SubscriptionPage />} />
        <Route path="contents" element={<ContentPage />} />
        <Route path="approvals" element={<ApprovalPage />} />
        <Route path="notifications" element={<NotificationPage />} />
      </Route>
    </Routes>
  )
}

export default AppRouter
