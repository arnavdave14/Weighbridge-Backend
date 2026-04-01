import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, AppWindow, X, Loader2, ChevronRight } from 'lucide-react'
import api from '../services/api'
import { format } from 'date-fns'

interface App {
  id: string
  app_id: string
  app_name: string
  description?: string
  created_at: string
}

const COLORS = [
  'from-blue-500 to-indigo-600',
  'from-violet-500 to-purple-600',
  'from-emerald-500 to-teal-600',
  'from-orange-500 to-amber-600',
  'from-pink-500 to-rose-600',
]

export default function AppsManager() {
  const [apps, setApps] = useState<App[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ app_name: '', description: '' })
  const [saving, setSaving] = useState(false)
  const nameRef = useRef<HTMLInputElement>(null)

  const fetchApps = async () => {
    try {
      const { data } = await api.get('/apps')
      setApps(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchApps() }, [])
  useEffect(() => { if (showCreate) nameRef.current?.focus() }, [showCreate])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      await api.post('/apps', form)
      setShowCreate(false)
      setForm({ app_name: '', description: '' })
      fetchApps()
    } catch (e) {
      console.error(e)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Applications</h1>
          <p className="page-subtitle">Manage your software products. Each app can have multiple company licenses.</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary">
          <Plus className="w-4 h-4" /> New Application
        </button>
      </div>

      {/* Create drawer */}
      <AnimatePresence>
        {showCreate && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowCreate(false)}
              className="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm"
            />
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', stiffness: 300, damping: 35 }}
              className="fixed inset-y-0 right-0 z-50 w-full max-w-md glass shadow-2xl border-l border-white/40 flex flex-col"
            >
              <div className="flex items-center justify-between px-6 py-5 border-b border-white/30">
                <h2 className="text-lg font-bold text-surface-900">New Application</h2>
                <button onClick={() => setShowCreate(false)} className="p-1.5 rounded-lg hover:bg-surface-100 text-surface-500">
                  <X className="w-4 h-4" />
                </button>
              </div>

              <form onSubmit={handleCreate} className="flex-1 p-6 space-y-4 overflow-y-auto">
                <div>
                  <label className="form-label">Application Name *</label>
                  <input ref={nameRef} required value={form.app_name}
                    onChange={(e) => setForm({ ...form, app_name: e.target.value })}
                    placeholder="e.g. Weighbridge Pro" className="form-input" />
                </div>
                <div>
                  <label className="form-label">Description</label>
                  <textarea rows={3} value={form.description}
                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                    placeholder="Optional short description…"
                    className="form-input resize-none" />
                </div>

                <div className="pt-4 flex gap-3">
                  <button type="button" onClick={() => setShowCreate(false)} className="btn-secondary flex-1">Cancel</button>
                  <button type="submit" disabled={saving} className="btn-primary flex-1">
                    {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                    {saving ? 'Creating…' : 'Create App'}
                  </button>
                </div>
              </form>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* App Cards */}
      {loading ? (
        <div className="flex items-center justify-center py-24 text-surface-400">
          <Loader2 className="w-8 h-8 animate-spin" />
        </div>
      ) : apps.length === 0 ? (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          className="text-center py-24 text-surface-400"
        >
          <AppWindow className="w-14 h-14 mx-auto mb-3 opacity-30" />
          <p className="font-medium">No applications yet.</p>
          <p className="text-sm">Click <strong>New Application</strong> to create your first product.</p>
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {apps.map((app, i) => (
            <motion.div
              key={app.id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.07 }}
              className="glass rounded-2xl border border-white/50 overflow-hidden hover:shadow-xl transition-all duration-300 hover:-translate-y-1 group"
            >
              {/* Card top gradient bar */}
              <div className={`h-1.5 bg-gradient-to-r ${COLORS[i % COLORS.length]}`} />

              <div className="p-5">
                <div className="flex items-start gap-4">
                  <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${COLORS[i % COLORS.length]} flex items-center justify-center shrink-0 shadow-md text-white text-lg font-bold`}>
                    {app.app_name.substring(0, 2).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-bold text-surface-900 truncate">{app.app_name}</h3>
                    {app.description && (
                      <p className="text-xs text-surface-500 mt-0.5 truncate">{app.description}</p>
                    )}
                    <code className="text-[10px] text-brand-600 font-mono bg-brand-50 px-1.5 py-0.5 rounded mt-1.5 inline-block">
                      {app.app_id}
                    </code>
                  </div>
                </div>

                <div className="flex items-center justify-between mt-4 pt-4 border-t border-surface-100">
                  <span className="text-xs text-surface-400">
                    Created {format(new Date(app.created_at), 'MMM d, yyyy')}
                  </span>
                  <button
                    onClick={() => { /* navigate to keys for this app */ }}
                    className="text-xs font-medium text-brand-600 hover:text-brand-700 flex items-center gap-1 group-hover:underline"
                  >
                    View Licenses <ChevronRight className="w-3 h-3" />
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}
