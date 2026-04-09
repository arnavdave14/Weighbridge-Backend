import { NavLink, Outlet, Navigate } from 'react-router-dom'
import { useAuthStore } from '../store/useStore'
import {
  LayoutDashboard, AppWindow, KeyRound, Bell, LogOut, Scale, History, AlertTriangle, ClipboardList
} from 'lucide-react'

const NAV = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard', end: true },
  { to: '/apps', icon: AppWindow, label: 'Applications' },
  { to: '/apps/history', icon: History, label: 'Deletion History' },
  { to: '/keys', icon: KeyRound, label: 'License Keys' },
  { to: '/notifications', icon: Bell, label: 'Alerts' },
  { to: '/dlq', icon: AlertTriangle, label: 'Failed Notifications' },
  { to: '/receipts', icon: ClipboardList, label: 'Receipts' },
]

export default function Layout() {
  const { isAuthenticated, logout } = useAuthStore()
  if (!isAuthenticated) return <Navigate to="/login" replace />

  return (
    <div className="flex h-screen overflow-hidden">
      {/* ── Sidebar ── */}
      <aside className="w-64 shrink-0 glass border-r border-white/50 flex flex-col">
        {/* Logo */}
        <div className="px-6 py-5 border-b border-white/30">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-600 to-indigo-600 flex items-center justify-center shadow-glow">
              <Scale className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-[15px] font-bold text-surface-900 leading-tight">WeighAdmin</h1>
              <p className="text-[10px] text-brand-600 font-semibold uppercase tracking-widest">SaaS Control</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {NAV.map(({ to, icon: Icon, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `nav-item ${isActive ? 'active' : ''}`
              }
            >
              <Icon className="w-4.5 h-4.5 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-3 py-4 border-t border-white/30">
          <button
            onClick={logout}
            className="nav-item w-full text-red-600 hover:bg-red-50 hover:text-red-700"
            aria-label="Sign out of the admin panel"
          >
            <LogOut className="w-4.5 h-4.5" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* ── Main ── */}
      <main className="flex-1 overflow-y-auto bg-gradient-to-br from-surface-50 via-blue-50/20 to-indigo-50/10 relative">
        {/* Simplified decorative glows (no heavy blur-3xl) */}
        <div className="pointer-events-none fixed top-10 right-10 w-96 h-96 bg-blue-100/40 rounded-full blur-2xl" />
        <div className="pointer-events-none fixed top-1/2 right-0 w-64 h-64 bg-indigo-100/30 rounded-full blur-2xl" />

        <div className="relative z-10 p-8 max-w-7xl mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
