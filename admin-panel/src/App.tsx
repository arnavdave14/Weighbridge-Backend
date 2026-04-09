import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import AppsManager from './pages/AppsManager'
import KeyManager from './pages/KeyManager'
import Notifications from './pages/Notifications'
import AppHistory from './pages/AppHistory'
import DLQDashboard from './pages/DLQDashboard'
import Receipts from './pages/Receipts'
import { ToastProvider } from './context/ToastContext'
import { Toaster } from './components/Toaster'

export default function App() {
  return (
    <ToastProvider>
      <Toaster />
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="apps" element={<AppsManager />} />
            <Route path="apps/history" element={<AppHistory />} />
            <Route path="keys" element={<KeyManager />} />
            <Route path="notifications" element={<Notifications />} />
            <Route path="dlq" element={<DLQDashboard />} />
            <Route path="receipts" element={<Receipts />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  )
}
