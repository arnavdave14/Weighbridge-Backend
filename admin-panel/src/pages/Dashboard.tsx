import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  AppWindow, KeyRound, CheckCircle2, XCircle, Ban,
  Bell, TrendingUp,
} from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts'
import api from '../services/api'

interface Stats {
  total_apps: number
  total_keys: number
  active_keys: number
  expired_keys: number
  revoked_keys: number
  recent_notifications: number
}

const AREA_DATA = Array.from({ length: 10 }, (_, i) => ({
  day: `Apr ${i + 1}`,
  activations: Math.floor(Math.random() * 40 + 10),
  revocations: Math.floor(Math.random() * 8),
}))

const PIE_COLORS = ['#22c55e', '#f59e0b', '#ef4444']

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1, y: 0,
    transition: { delay: i * 0.08, duration: 0.4, ease: 'easeOut' },
  }),
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null)

  useEffect(() => {
    api.get('/apps/dashboard/stats').then((r) => setStats(r.data)).catch(console.error)
  }, [])

  const pieData = stats
    ? [
        { name: 'Active', value: stats.active_keys },
        { name: 'Expired', value: stats.expired_keys },
        { name: 'Revoked', value: stats.revoked_keys },
      ]
    : []

  const CARDS = [
    {
      label: 'Total Applications',
      value: stats?.total_apps ?? '–',
      icon: AppWindow,
      color: 'text-brand-600',
      bg: 'bg-brand-50',
      border: 'border-brand-100',
    },
    {
      label: 'Total Licenses',
      value: stats?.total_keys ?? '–',
      icon: KeyRound,
      color: 'text-violet-600',
      bg: 'bg-violet-50',
      border: 'border-violet-100',
    },
    {
      label: 'Active Licenses',
      value: stats?.active_keys ?? '–',
      icon: CheckCircle2,
      color: 'text-emerald-600',
      bg: 'bg-emerald-50',
      border: 'border-emerald-100',
    },
    {
      label: 'Expired Licenses',
      value: stats?.expired_keys ?? '–',
      icon: XCircle,
      color: 'text-amber-600',
      bg: 'bg-amber-50',
      border: 'border-amber-100',
    },
    {
      label: 'Revoked Licenses',
      value: stats?.revoked_keys ?? '–',
      icon: Ban,
      color: 'text-red-600',
      bg: 'bg-red-50',
      border: 'border-red-100',
    },
    {
      label: 'Security Alerts',
      value: stats?.recent_notifications ?? '–',
      icon: Bell,
      color: 'text-orange-600',
      bg: 'bg-orange-50',
      border: 'border-orange-100',
    },
  ]

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="page-title">Platform Overview</h1>
          <p className="page-subtitle">Real-time SaaS metrics and license health</p>
        </div>
        <div className="flex items-center gap-2 text-xs font-medium glass px-4 py-2 rounded-full border border-emerald-100 text-emerald-700">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          All Systems Operational
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        {CARDS.map((card, i) => (
          <motion.div
            key={card.label}
            custom={i}
            initial="hidden"
            animate="visible"
            variants={cardVariants}
            className={`stat-card border ${card.border}`}
          >
            <div className="flex items-center gap-4">
              <div className={`p-3 rounded-xl ${card.bg}`}>
                <card.icon className={`w-5 h-5 ${card.color}`} />
              </div>
              <div>
                <p className="text-xs font-medium text-surface-500">{card.label}</p>
                <p className="text-3xl font-bold text-surface-900">{card.value}</p>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Area Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.4 }}
          className="glass rounded-2xl p-6 lg:col-span-2 border border-white/50"
        >
          <div className="flex items-center gap-2 mb-5">
            <TrendingUp className="w-4 h-4 text-brand-600" />
            <h2 className="text-sm font-bold text-surface-800">Activation Activity (10 Days)</h2>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={AREA_DATA}>
              <defs>
                <linearGradient id="gAct" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gRev" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.1)', fontSize: 12 }}
              />
              <Area type="monotone" dataKey="activations" stroke="#3b82f6" strokeWidth={2.5} fill="url(#gAct)" name="Activations" />
              <Area type="monotone" dataKey="revocations" stroke="#ef4444" strokeWidth={2} fill="url(#gRev)" name="Revocations" />
            </AreaChart>
          </ResponsiveContainer>
        </motion.div>

        {/* Pie Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.4 }}
          className="glass rounded-2xl p-6 border border-white/50"
        >
          <h2 className="text-sm font-bold text-surface-800 mb-5">License Distribution</h2>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={80} paddingAngle={4} dataKey="value">
                  {pieData.map((_, index) => (
                    <Cell key={index} fill={PIE_COLORS[index]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ borderRadius: 10, fontSize: 12 }} />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-48 text-surface-400 text-sm">No data yet</div>
          )}
        </motion.div>
      </div>
    </div>
  )
}
