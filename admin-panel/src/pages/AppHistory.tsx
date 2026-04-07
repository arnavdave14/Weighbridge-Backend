import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { AppWindow, Loader2, History, ArrowLeft, Calendar, Trash2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'
import { format } from 'date-fns'
import { useToast } from '../context/ToastContext'

interface DeletedApp {
  id: string
  app_id: string
  app_name: string
  description?: string
  created_at: string
  deleted_at?: string
}

export default function AppHistory() {
  const navigate = useNavigate()
  const toast = useToast()
  const [apps, setApps] = useState<DeletedApp[]>([])
  const [loading, setLoading] = useState(true)

  const fetchHistory = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/apps/history')
      setApps(data)
    } catch (err) {
      console.error('[AppHistory: Fetch] Failed:', err)
      toast.error('Could not load deletion history.')
    } finally {
      setLoading(false)
    }
  }, [toast])

  useEffect(() => { fetchHistory() }, [fetchHistory])

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={() => navigate('/apps')} className="p-2 rounded-xl glass hover:bg-white/40 transition-colors">
          <ArrowLeft className="w-5 h-5 text-surface-600" />
        </button>
        <div>
          <h1 className="page-title flex items-center gap-2">
            <History className="w-6 h-6 text-brand-600" />
            Deletion History
          </h1>
          <p className="page-subtitle">View applications that were previously deleted.</p>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-24 text-surface-400">
          <Loader2 className="w-8 h-8 animate-spin" />
        </div>
      ) : apps.length === 0 ? (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          className="text-center py-24 text-surface-400 glass rounded-3xl border border-white/40"
        >
          <Trash2 className="w-14 h-14 mx-auto mb-3 opacity-20" />
          <p className="font-medium text-lg text-surface-600">History is empty</p>
          <p className="text-sm">No deleted applications were found.</p>
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {apps.map((app, i) => (
            <motion.div
              key={app.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="glass p-5 rounded-2xl border border-white/50 flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-surface-100 flex items-center justify-center text-surface-400 shrink-0">
                  <AppWindow className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="font-bold text-surface-900">{app.app_name}</h3>
                  <code className="text-[10px] text-brand-600 font-mono bg-brand-50 px-1.5 py-0.5 rounded mr-2">
                    {app.app_id}
                  </code>
                  {app.description && <span className="text-xs text-surface-500">{app.description}</span>}
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-6">
                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-surface-400" />
                  <div className="text-[11px]">
                    <p className="text-surface-400 uppercase font-semibold tracking-wider">Created</p>
                    <p className="text-surface-700 font-medium">{format(new Date(app.created_at), 'MMM d, yyyy')}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Trash2 className="w-4 h-4 text-red-400" />
                  <div className="text-[11px]">
                    <p className="text-red-400 uppercase font-semibold tracking-wider">Deleted</p>
                    <p className="text-surface-700 font-medium">
                      {app.deleted_at ? format(new Date(app.deleted_at), 'MMM d, yyyy HH:mm') : 'Unknown'}
                    </p>
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}
