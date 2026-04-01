import { NavLink, Outlet, Navigate } from 'react-router-dom'
import { useAuthStore } from '../store/useStore'
import {
  LayoutDashboard, AppWindow, KeyRound, Bell, LogOut, Scale,
} from 'lucide-react'

const NAV = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard', end: true },
  { to: '/apps', icon: AppWindow, label: 'Applications' },
  { to: '/keys', icon: KeyRound, label: 'License Keys' },
  { to: '/notifications', icon: Bell, label: 'Alerts' },
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
            className="nav-item w-full text-red-500 hover:bg-red-50 hover:text-red-600"
          >
            <LogOut className="w-4.5 h-4.5" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* ── Main ── */}
      <main className="flex-1 overflow-y-auto bg-gradient-to-br from-surface-50 via-blue-50/30 to-indigo-50/20 relative">
        {/* Decorative blobs */}
        <div className="pointer-events-none fixed top-10 right-10 w-80 h-80 bg-blue-200/30 rounded-full blur-3xl animate-blob" />
        <div className="pointer-events-none fixed top-40 right-60 w-64 h-64 bg-indigo-200/25 rounded-full blur-3xl animate-blob animation-delay-2000" />

        <div className="relative z-10 p-8 max-w-7xl mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
