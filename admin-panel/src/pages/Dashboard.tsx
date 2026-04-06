import { useEffect, useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import {
  AppWindow, KeyRound, CheckCircle2, XCircle, Ban,
  Bell, TrendingUp, Loader2,
} from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts'
import api from '../services/api'
import { useToast } from '../context/ToastContext'

interface Stats {
  total_apps: number
  total_keys: number
  active_keys: number
  expired_keys: number
  revoked_keys: number
  recent_notifications: number
}

const PIE_COLORS = ['#22c55e', '#f59e0b', '#ef4444']

const CARDS_CONFIG = [
  { label: 'Total Applications', icon: AppWindow, color: 'text-brand-600', bg: 'bg-brand-50', border: 'border-brand-100', key: 'total_apps' },
  { label: 'Total Licenses', icon: KeyRound, color: 'text-violet-600', bg: 'bg-violet-50', border: 'border-violet-100', key: 'total_keys' },
  { label: 'Active Licenses', icon: CheckCircle2, color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-100', key: 'active_keys' },
  { label: 'Expired Licenses', icon: XCircle, color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-100', key: 'expired_keys' },
  { label: 'Revoked Licenses', icon: Ban, color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-100', key: 'revoked_keys' },
  { label: 'Security Alerts', icon: Bell, color: 'text-orange-600', bg: 'bg-orange-50', border: 'border-orange-100', key: 'recent_notifications' },
]

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1, y: 0,
    transition: { delay: i * 0.08, duration: 0.4, ease: 'easeOut' },
  }),
}

export default function Dashboard() {
  const toast = useToast()
  const [stats, setStats] = useState<Stats | null>(null)
  const [activity, setActivity] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        const [statsRes, activityRes] = await Promise.all([
          api.get('/apps/dashboard/stats'),
          api.get('/apps/dashboard/activity')
        ])
        setStats(statsRes.data)
        setActivity(activityRes.data)
      } catch (err) {
        console.error('[Dashboard: Fetch] Failed:', err)
        toast.error('Could not load dashboard information.')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const pieData = useMemo(() => {
    if (!stats) return []
    return [
      { name: 'Active', value: stats.active_keys },
      { name: 'Expired', value: stats.expired_keys },
      { name: 'Revoked', value: stats.revoked_keys },
    ]
  }, [stats])

  const cards = useMemo(() => {
    return CARDS_CONFIG.map((c) => ({
      ...c,
      value: stats ? (stats as any)[c.key] : '–'
    }))
  }, [stats])

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

      {loading ? (
        <div className="flex items-center justify-center py-20 text-surface-400">
          <Loader2 className="w-8 h-8 animate-spin" />
        </div>
      ) : (
        <>
          {/* Stat Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
            {cards.map((card, i) => (
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
                <AreaChart data={activity}>
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
        </>
      )}
    </div>
  )
}
