import { useState, useEffect, useRef, type FormEvent, useCallback, memo, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { Plus, AppWindow, X, Loader2, ChevronRight, Trash2, Filter, Calendar, KeyRound, RefreshCw } from 'lucide-react'
import api from '../services/api'
import { format, isWithinInterval, startOfDay, endOfDay } from 'date-fns'
import { useToast } from '../context/ToastContext'

interface App {
  id: string
  app_id: string
  app_name: string
  description?: string
  created_at: string
  keys_count: number
}

const COLORS = [
  'from-blue-500 to-indigo-600',
  'from-violet-500 to-purple-600',
  'from-emerald-500 to-teal-600',
  'from-orange-500 to-amber-600',
  'from-pink-500 to-rose-600',
]

// --- Sub-components ---

const AppCard = memo(({ app, index, onDelete, onEdit }: { 
  app: App; 
  index: number; 
  onDelete: (id: string, name: string) => void;
  onEdit: (app: App) => void;
}) => {
  const navigate = useNavigate()
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.3 }}
      className="glass rounded-2xl border border-white/50 overflow-hidden hover:shadow-xl transition-all duration-300 hover:-translate-y-1 group relative"
    >
      <div className={`h-1.5 bg-gradient-to-r ${COLORS[index % COLORS.length]}`} />
      
      {/* Delete Button */}
      <button
        onClick={(e) => {
          e.stopPropagation()
          onDelete(app.id, app.app_name)
        }}
        className="absolute top-4 right-4 p-2 rounded-xl bg-white/50 text-red-500 opacity-0 group-hover:opacity-100 transition-all hover:bg-red-50 hover:text-red-600 z-10"
        title="Delete Application"
      >
        <Trash2 className="w-4 h-4" />
      </button>

      {/* Edit Button */}
      <button
        onClick={(e) => {
          e.stopPropagation()
          onEdit(app)
        }}
        className="absolute top-4 right-14 p-2 rounded-xl bg-white/50 text-indigo-500 opacity-0 group-hover:opacity-100 transition-all hover:bg-indigo-50 hover:text-indigo-600 z-10"
        title="Edit Application"
      >
        <Plus className="w-4 h-4 rotate-45" /> {/* Using Plus rotated as a pencil/edit icon alternative since Lucide Pencil isn't imported yet, or I can just import it */}
      </button>

      <div className="p-5">
        <div className="flex items-start gap-4">
          <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${COLORS[index % COLORS.length]} flex items-center justify-center shrink-0 shadow-md text-white text-lg font-bold`}>
            {app.app_name.substring(0, 2).toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-bold text-surface-900 truncate pr-8">{app.app_name}</h3>
            {app.description && (
              <p className="text-xs text-surface-500 mt-0.5 truncate">{app.description}</p>
            )}
            <div className="flex items-center gap-2 mt-1.5 flex-wrap">
              <code className="text-[10px] text-brand-600 font-mono bg-brand-50 px-1.5 py-0.5 rounded inline-block">
                {app.app_id}
              </code>
              <span className="text-[10px] font-medium text-violet-600 bg-violet-50 px-1.5 py-0.5 rounded flex items-center gap-1">
                <KeyRound className="w-2.5 h-2.5" />
                {app.keys_count} {app.keys_count === 1 ? 'License' : 'Licenses'}
              </span>
            </div>

          </div>
        </div>
        <div className="flex items-center justify-between mt-4 pt-4 border-t border-surface-100">
          <span className="text-xs text-surface-400">
            Created {format(new Date(app.created_at), 'MMM d, yyyy')}
          </span>
          <button 
            onClick={() => navigate(`/keys?appId=${app.id}`)}
            className="text-xs font-medium text-brand-600 hover:text-brand-700 flex items-center gap-1 group-hover:underline"
          >
            View Licenses <ChevronRight className="w-3 h-3" />
          </button>
        </div>
      </div>
    </motion.div>
  )
})

const AppDrawer = memo(({ isOpen, onClose, onSuccess, initialData }: { 
  isOpen: boolean; 
  onClose: () => void; 
  onSuccess: () => void;
  initialData?: App | null;
}) => {
  const toast = useToast()
  const [form, setForm] = useState({ 
    app_name: '', 
    description: ''
  })
  const [saving, setSaving] = useState(false)
  const nameRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (isOpen) {
      if (initialData) {
        setForm({
          app_name: initialData.app_name,
          description: initialData.description || ''
        })
      } else {
        setForm({
          app_name: '',
          description: ''
        })
      }
      setTimeout(() => nameRef.current?.focus(), 100)
    } else {
      setForm({
        app_name: '',
        description: ''
      })
    }
  }, [isOpen, initialData])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      if (initialData) {
        await api.patch(`/apps/${initialData.id}`, form)
        toast.success(`Application "${form.app_name}" updated!`)
      } else {
        await api.post('/apps', form)
        toast.success(`Application "${form.app_name}" created!`)
      }
      onSuccess()
      onClose()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Operation failed.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-40 bg-black/30"
          />
          <motion.div
            initial={{ x: '100%', opacity: 0.5 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0.5 }}
            transition={{ type: 'tween', ease: 'easeOut', duration: 0.25 }}
            className="fixed inset-y-0 right-0 z-50 w-full max-w-md glass border-l border-white/40 flex flex-col"
          >
            <div className="flex items-center justify-between px-6 py-5 border-b border-white/30">
              <h2 className="text-lg font-bold text-surface-900">
                {initialData ? 'Edit Application' : 'New Application'}
              </h2>
              <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-surface-100 text-surface-500">
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="flex-1 p-6 space-y-4 overflow-y-auto">
              <div>
                <label className="form-label">Application Name *</label>
                <input ref={nameRef} required value={form.app_name}
                  onChange={(e) => setForm({ ...form, app_name: e.target.value })}
                  placeholder="e.g. Weighbridge Pro" className="form-input" />
              </div>
              <div>
                <label className="form-label">Description</label>
                <textarea rows={2} value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="Optional short description…"
                  className="form-input resize-none" />
              </div>
              <div className="pt-4 flex gap-3 border-t border-white/20">
                <button type="button" onClick={onClose} className="btn-secondary flex-1">Cancel</button>
                <button type="submit" disabled={saving} className="btn-primary flex-1">
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : (initialData ? <RefreshCw className="w-4 h-4" /> : <Plus className="w-4 h-4" />)}
                  {saving ? (initialData ? 'Updating…' : 'Creating…') : (initialData ? 'Update App' : 'Create App')}
                </button>
              </div>
            </form>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
})

// --- Main Page ---

export default function AppsManager() {
  const toast = useToast()
  const [apps, setApps] = useState<App[]>([])
  const [loading, setLoading] = useState(true)
  const [showDrawer, setShowDrawer] = useState(false)
  const [editingApp, setEditingApp] = useState<App | null>(null)
  const [sortOrder, setSortOrder] = useState<'latest' | 'oldest' | 'custom'>(
    () => (localStorage.getItem('apps_sortOrder') || 'latest') as 'latest' | 'oldest' | 'custom'
  )
  const [dateRange, setDateRange] = useState(() => {
    try {
      const saved = localStorage.getItem('apps_dateRange')
      if (saved) return JSON.parse(saved)
    } catch (e) {}
    return { start: '', end: '' }
  })

  useEffect(() => {
    localStorage.setItem('apps_sortOrder', sortOrder)
    localStorage.setItem('apps_dateRange', JSON.stringify(dateRange))
  }, [sortOrder, dateRange])

  const fetchApps = useCallback(async () => {
    try {
      const { data } = await api.get('/apps')
      setApps(data)
    } catch (err) {
      console.error('[AppsManager: FetchApps] Failed:', err)
      toast.error('Could not load applications.')
    } finally {
      setLoading(false)
    }
  }, [toast])

  useEffect(() => { fetchApps() }, [fetchApps])

  const handleDelete = async (id: string, name: string) => {
    if (!window.confirm(`Are you sure you want to delete "${name}"? It will be moved to history.`)) return
    try {
      await api.delete(`/apps/${id}`)
      toast.success(`"${name}" deleted successfully.`)
      fetchApps()
    } catch (err) {
      console.error('[AppsManager: Delete] Failed:', err)
      toast.error('Failed to delete application.')
    }
  }

  const filteredAndSortedApps = useMemo(() => {
    let result = [...apps]

    if (sortOrder === 'custom' && dateRange.start && dateRange.end) {
      const start = startOfDay(new Date(dateRange.start))
      const end = endOfDay(new Date(dateRange.end))
      result = result.filter(app => {
        const date = new Date(app.created_at)
        return isWithinInterval(date, { start, end })
      })
    }

    result.sort((a, b) => {
      const d1 = new Date(a.created_at).getTime()
      const d2 = new Date(b.created_at).getTime()
      return sortOrder === 'oldest' ? d1 - d2 : d2 - d1
    })

    return result
  }, [apps, sortOrder, dateRange])

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="page-title">Applications</h1>
          <p className="page-subtitle">Manage your software products. Each app can have multiple company licenses.</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 glass px-3 py-1.5 rounded-xl border border-white/40">
            <Filter className="w-4 h-4 text-surface-400" />
            <select 
              value={sortOrder}
              onChange={(e) => setSortOrder(e.target.value as any)}
              className="bg-transparent text-sm font-medium text-surface-700 outline-none cursor-pointer"
            >
              <option value="latest">Latest First</option>
              <option value="oldest">Oldest First</option>
              <option value="custom">Custom Date</option>
            </select>
          </div>
          <button onClick={() => { setEditingApp(null); setShowDrawer(true); }} className="btn-primary">
            <Plus className="w-4 h-4" /> New App
          </button>
        </div>
      </div>

      {sortOrder === 'custom' && (
        <motion.div 
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="glass p-4 rounded-2xl border border-white/40 flex flex-wrap items-center gap-4"
        >
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-brand-600" />
            <span className="text-sm font-medium text-surface-600">Range:</span>
          </div>
          <input 
            type="date" 
            value={dateRange.start}
            onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
            className="form-input py-1.5 text-sm max-w-[160px]"
          />
          <span className="text-surface-400">to</span>
          <input 
            type="date" 
            value={dateRange.end}
            onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
            className="form-input py-1.5 text-sm max-w-[160px]"
          />
        </motion.div>
      )}

      <AppDrawer 
        isOpen={showDrawer} 
        onClose={() => setShowDrawer(false)} 
        onSuccess={fetchApps} 
        initialData={editingApp}
      />

      {loading ? (
        <div className="flex items-center justify-center py-24 text-surface-400">
          <Loader2 className="w-8 h-8 animate-spin" />
        </div>
      ) : filteredAndSortedApps.length === 0 ? (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          className="text-center py-24 text-surface-400"
        >
          <AppWindow className="w-14 h-14 mx-auto mb-3 opacity-30" />
          <p className="font-medium">No applications found.</p>
          <p className="text-sm">Try adjusting your filters or creating a new application.</p>
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredAndSortedApps.map((app, i) => (
            <AppCard 
              key={app.id} 
              app={app} 
              index={i} 
              onDelete={handleDelete} 
              onEdit={(app) => {
                setEditingApp(app);
                setShowDrawer(true);
              }}
            />
          ))}
        </div>
      )}
    </div>
  )
}
