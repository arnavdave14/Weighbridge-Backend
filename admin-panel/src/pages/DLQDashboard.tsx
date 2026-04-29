import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  AlertCircle, 
  RotateCcw, 
  CheckCircle2, 
  Clock, 
  Mail, 
  MessageSquare, 
  Filter, 
  Info,
  Loader2,
  Trash2
} from 'lucide-react'
import api from '../services/api'
import { format } from 'date-fns'
import { useToast } from '../context/ToastContext'

interface FailedNotification {
  id: string
  channel: 'email' | 'whatsapp'
  target: string
  payload: any
  error_reason: string
  retry_count: string
  status: 'pending' | 'retried' | 'resolved'
  failed_at: string
  resolved_at?: string
}

export default function DLQDashboard() {
  const toast = useToast()
  const [entries, setEntries] = useState<FailedNotification[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<'pending' | 'retried' | 'resolved' | 'all'>(
    () => (localStorage.getItem('dlq_filter') || 'all') as 'pending' | 'retried' | 'resolved' | 'all'
  )

  useEffect(() => { localStorage.setItem('dlq_filter', filter) }, [filter])
  const [selectedEntry, setSelectedEntry] = useState<FailedNotification | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const fetchDLQ = useCallback(async () => {
    setLoading(true)
    try {
      const statusParam = filter === 'all' ? '' : `?status=${filter}`
      const { data } = await api.get(`/dlq${statusParam}`)
      setEntries(data)
    } catch (err) {
      console.error('[DLQ: Fetch] Failed:', err)
      toast.error('Failed to load Dead Letter Queue.')
    } finally {
      setLoading(false)
    }
  }, [filter, toast])

  useEffect(() => {
    fetchDLQ()
  }, [fetchDLQ])

  const handleRetry = async (id: string) => {
    setActionLoading(id)
    try {
      await api.post(`/dlq/${id}/retry`)
      toast.success('Notification re-queued for delivery.')
      fetchDLQ()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Retry failed.')
    } finally {
      setActionLoading(null)
    }
  }

  const handleResolve = async (id: string) => {
    setActionLoading(id)
    try {
      await api.patch(`/dlq/${id}/resolve`)
      toast.success('Marked as resolved.')
      fetchDLQ()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Update failed.')
    } finally {
      setActionLoading(null)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <AlertCircle className="w-8 h-8 text-red-500" />
            Dead Letter Queue
          </h1>
          <p className="page-subtitle">Track and manually resolve permanently failed notifications.</p>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 glass px-3 py-1.5 rounded-xl border border-white/40">
            <Filter className="w-4 h-4 text-surface-400" />
            <select 
              value={filter}
              onChange={(e) => setFilter(e.target.value as any)}
              className="bg-transparent text-sm font-medium text-surface-700 outline-none cursor-pointer"
            >
              <option value="all">All Status</option>
              <option value="pending">Pending</option>
              <option value="retried">Retried</option>
              <option value="resolved">Resolved</option>
            </select>
          </div>
          <button onClick={fetchDLQ} className="p-2 glass rounded-xl border border-white/40 text-brand-600 hover:bg-white/50 transition-colors">
            <RotateCcw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="glass rounded-2xl border border-white/50 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-surface-50/50 border-b border-surface-100">
                <th className="px-6 py-4 text-xs font-bold text-surface-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-4 text-xs font-bold text-surface-500 uppercase tracking-wider">Channel</th>
                <th className="px-6 py-4 text-xs font-bold text-surface-500 uppercase tracking-wider">Target</th>
                <th className="px-6 py-4 text-xs font-bold text-surface-500 uppercase tracking-wider">Error</th>
                <th className="px-6 py-4 text-xs font-bold text-surface-500 uppercase tracking-wider">Failed At</th>
                <th className="px-6 py-4 text-xs font-bold text-surface-500 uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-100">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-surface-400">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                    Loading failures...
                  </td>
                </tr>
              ) : entries.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-surface-400">
                    <CheckCircle2 className="w-8 h-8 text-emerald-500 opacity-20 mx-auto mb-2" />
                    No failed notifications found.
                  </td>
                </tr>
              ) : entries.map((entry) => (
                <tr key={entry.id} className="hover:bg-white/30 transition-colors">
                  <td className="px-6 py-4">
                    <StatusBadge status={entry.status} />
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      {entry.channel === 'email' ? <Mail className="w-4 h-4 text-blue-500" /> : <MessageSquare className="w-4 h-4 text-emerald-500" />}
                      <span className="text-sm font-medium capitalize">{entry.channel}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-sm text-surface-700 font-mono">{entry.target}</span>
                  </td>
                  <td className="px-6 py-4">
                    <p className="text-sm text-red-600 max-w-[200px] truncate" title={entry.error_reason}>
                      {entry.error_reason}
                    </p>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-xs text-surface-500 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {format(new Date(entry.failed_at), 'MMM d, HH:mm')}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                       <button 
                        onClick={() => setSelectedEntry(entry)}
                        className="p-1.5 rounded-lg hover:bg-surface-100 text-surface-500"
                        title="View Details"
                      >
                        <Info className="w-4 h-4" />
                      </button>
                      
                      {entry.status === 'pending' && (
                        <>
                          <button 
                            onClick={() => handleRetry(entry.id)}
                            disabled={actionLoading === entry.id}
                            className="p-1.5 rounded-lg hover:bg-brand-50 text-brand-600 disabled:opacity-50"
                            title="Retry Delivery"
                          >
                            <RotateCcw className={`w-4 h-4 ${actionLoading === entry.id ? 'animate-spin' : ''}`} />
                          </button>
                          <button 
                            onClick={() => handleResolve(entry.id)}
                            disabled={actionLoading === entry.id}
                            className="p-1.5 rounded-lg hover:bg-emerald-50 text-emerald-600 disabled:opacity-50"
                            title="Mark as Resolved"
                          >
                            <CheckCircle2 className="w-4 h-4" />
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <AnimatePresence>
        {selectedEntry && (
          <PayloadModal 
            entry={selectedEntry} 
            onClose={() => setSelectedEntry(null)} 
          />
        )}
      </AnimatePresence>
    </div>
  )
}

function StatusBadge({ status }: { status: FailedNotification['status'] }) {
  const styles = {
    pending: 'bg-red-50 text-red-700 border-red-100',
    retried: 'bg-brand-50 text-brand-700 border-brand-100',
    resolved: 'bg-emerald-50 text-emerald-700 border-emerald-100'
  }
  
  return (
    <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border ${styles[status]}`}>
      {status}
    </span>
  )
}

function PayloadModal({ entry, onClose }: { entry: FailedNotification, onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <motion.div 
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 bg-black/40 backdrop-blur-sm"
      />
      <motion.div 
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        className="relative w-full max-w-2xl glass rounded-2xl border border-white/50 p-6 shadow-2xl overflow-hidden"
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-surface-900">Failure Details</h2>
          <button onClick={onClose} className="p-2 hover:bg-surface-100 rounded-xl text-surface-500">
            <Trash2 className="w-5 h-5 rotate-45" /> 
          </button>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="p-3 bg-surface-50 rounded-xl border border-surface-100">
              <span className="text-xs text-surface-400 block mb-1">Channel</span>
              <span className="font-medium capitalize">{entry.channel}</span>
            </div>
            <div className="p-3 bg-surface-50 rounded-xl border border-surface-100">
              <span className="text-xs text-surface-400 block mb-1">Retries Attempted</span>
              <span className="font-medium">{entry.retry_count} / 5</span>
            </div>
          </div>

          <div>
              <span className="text-xs text-surface-400 block mb-2 px-1">Error Reason</span>
              <div className="p-3 bg-red-50 text-red-700 text-sm font-medium rounded-xl border border-red-100">
                {entry.error_reason}
              </div>
          </div>

          <div>
            <span className="text-xs text-surface-400 block mb-2 px-1">Original Payload</span>
            <pre className="p-4 bg-surface-900 text-brand-400 text-xs font-mono rounded-xl overflow-x-auto max-h-[300px]">
              {JSON.stringify(entry.payload, null, 2)}
            </pre>
          </div>
        </div>

        <div className="mt-8 pt-6 border-t border-surface-100 flex justify-end gap-3">
           <button onClick={onClose} className="btn-secondary">Close</button>
        </div>
      </motion.div>
    </div>
  )
}
