import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Bell, AlertTriangle, Info, RefreshCw, Loader2 } from 'lucide-react'
import api from '../services/api'
import { format, formatDistanceToNow } from 'date-fns'
import { useToast } from '../context/ToastContext'

interface Notification {
  id: string
  message: string
  type: string
  created_at: string
  app_id?: string
  activation_key_id?: string
}

const typeConfig = {
  error: { icon: AlertTriangle, cls: 'text-red-600 bg-red-50 border-red-100', dot: 'bg-red-500' },
  warning: { icon: AlertTriangle, cls: 'text-amber-600 bg-amber-50 border-amber-100', dot: 'bg-amber-500' },
  info: { icon: Info, cls: 'text-brand-600 bg-brand-50 border-brand-100', dot: 'bg-brand-500' },
}

export default function Notifications() {
  const toast = useToast()
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('all')

  const fetchNotifications = async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/notifications')
      setNotifications(data)
    } catch (err) {
      console.error('[Notifications: Fetch] Failed:', err)
      toast.error('Could not load security alerts.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchNotifications() }, [])

  const filtered = filter === 'all' ? notifications : notifications.filter((n) => n.type === filter)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Security Alerts</h1>
          <p className="page-subtitle">Invalid activations, wrong app selections, and system events</p>
        </div>
        <button onClick={fetchNotifications} className="btn-secondary">
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2">
        {['all', 'error', 'warning', 'info'].map((t) => (
          <button
            key={t}
            onClick={() => setFilter(t)}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold capitalize transition-all
              ${filter === t
                ? 'bg-brand-600 text-white shadow-sm'
                : 'bg-white border border-surface-200 text-surface-600 hover:border-brand-300 hover:text-brand-600'
              }`}
          >
            {t} {t === 'all' ? `(${notifications.length})` : `(${notifications.filter((n) => n.type === t).length})`}
          </button>
        ))}
      </div>

      {/* List */}
      {loading ? (
        <div className="flex items-center justify-center py-24 text-surface-400">
          <Loader2 className="w-8 h-8 animate-spin" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-24 text-surface-400">
          <Bell className="w-14 h-14 mx-auto mb-3 opacity-20" />
          <p className="font-medium">No alerts found.</p>
          <p className="text-sm mt-1">Security events will appear here when they occur.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((n, i) => {
            const cfg = typeConfig[n.type as keyof typeof typeConfig] ?? typeConfig.info
            return (
              <motion.div
                key={n.id}
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.04 }}
                className={`glass rounded-xl border p-4 flex items-start gap-4 ${cfg.cls}`}
              >
                <span className={`mt-1 w-2 h-2 rounded-full shrink-0 ${cfg.dot}`} />
                <cfg.icon className="w-4 h-4 shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium leading-snug">{n.message}</p>
                  <div className="flex items-center gap-3 mt-1.5 text-xs opacity-60">
                    <span>{format(new Date(n.created_at), 'dd MMM yyyy, HH:mm')}</span>
                    <span>·</span>
                    <span>{formatDistanceToNow(new Date(n.created_at), { addSuffix: true })}</span>
                  </div>
                </div>
                <span className="text-[10px] uppercase font-bold tracking-wider opacity-60 shrink-0">{n.type}</span>
              </motion.div>
            )
          })}
        </div>
      )}
    </div>
  )
}
