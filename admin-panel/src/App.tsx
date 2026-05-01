import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import PageLoader from './components/PageLoader'
import { ToastProvider } from './context/ToastContext'
import { Toaster } from './components/Toaster'

// ── Lazy-loaded pages (each page becomes its own JS chunk) ──────────────────
const Layout           = lazy(() => import('./components/Layout'))
const Login            = lazy(() => import('./pages/Login'))
const Dashboard        = lazy(() => import('./pages/Dashboard'))
const AppsManager      = lazy(() => import('./pages/AppsManager'))
const KeyManager       = lazy(() => import('./pages/KeyManager'))
const Notifications    = lazy(() => import('./pages/Notifications'))
const AppHistory       = lazy(() => import('./pages/AppHistory'))
const DLQDashboard     = lazy(() => import('./pages/DLQDashboard'))
const Receipts         = lazy(() => import('./pages/Receipts'))
const Employees        = lazy(() => import('./pages/Employees'))
const DocumentDashboard = lazy(() => import('./pages/DocumentDashboard'))

export default function App() {
  return (
    <ToastProvider>
      <Toaster />
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        {/* Suspense wraps the whole router so every lazy page shows the loader */}
        <Suspense fallback={<PageLoader />}>
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
              <Route path="documents" element={<DocumentDashboard />} />
              <Route path="employees" element={<Employees />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </Suspense>
      </BrowserRouter>
    </ToastProvider>
  )
}
