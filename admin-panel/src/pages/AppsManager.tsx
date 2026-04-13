import { useState, useEffect, useRef, type FormEvent, useCallback, memo, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { Plus, AppWindow, X, Loader2, ChevronRight, Trash2, Filter, Calendar, KeyRound, RefreshCw, Mail, ShieldCheck, AlertCircle, Info } from 'lucide-react'
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
  
  // SMTP Fields
  smtp_enabled: boolean
  smtp_host?: string
  smtp_port?: number
  smtp_user?: string
  from_email?: string
  from_name?: string
  smtp_status: 'VALID' | 'INVALID' | 'UNTESTED'
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
    description: '',
    smtp_enabled: false,
    smtp_host: 'smtp.gmail.com',
    smtp_port: 587,
    smtp_user: '',
    smtp_password: '',
    from_email: '',
    from_name: ''
  })
  const [testingSmtp, setTestingSmtp] = useState(false)
  const [smtpStatus, setSmtpStatus] = useState<'VALID' | 'INVALID' | 'UNTESTED'>('UNTESTED')
  const [saving, setSaving] = useState(false)
  const nameRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (isOpen) {
      if (initialData) {
        setForm({
          app_name: initialData.app_name,
          description: initialData.description || '',
          smtp_enabled: initialData.smtp_enabled || false,
          smtp_host: initialData.smtp_host || 'smtp.gmail.com',
          smtp_port: initialData.smtp_port || 587,
          smtp_user: initialData.smtp_user || '',
          smtp_password: '', // Password is write-only
          from_email: initialData.from_email || '',
          from_name: initialData.from_name || ''
        })
        setSmtpStatus(initialData.smtp_status)
      } else {
        setForm({
          app_name: '',
          description: '',
          smtp_enabled: false,
          smtp_host: 'smtp.gmail.com',
          smtp_port: 587,
          smtp_user: '',
          smtp_password: '',
          from_email: '',
          from_name: ''
        })
        setSmtpStatus('UNTESTED')
      }
      setTimeout(() => nameRef.current?.focus(), 100)
    } else {
      setForm({
        app_name: '',
        description: '',
        smtp_enabled: false,
        smtp_host: 'smtp.gmail.com',
        smtp_port: 587,
        smtp_user: '',
        smtp_password: '',
        from_email: '',
        from_name: ''
      })
    }
  }, [isOpen, initialData])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      // Create a clean payload (don't send empty password strings if not changing)
      const payload: any = { ...form }
      if (!payload.smtp_password) delete payload.smtp_password

      if (initialData) {
        await api.patch(`/apps/${initialData.id}`, payload)
        toast.success(`Application "${form.app_name}" updated!`)
      } else {
        await api.post('/apps', payload)
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

  const handleTestSmtp = async () => {
    if (!initialData) {
        toast.warning("Please save the application first before testing SMTP.")
        return
    }
    setTestingSmtp(true)
    try {
        const { data } = await api.post(`/apps/${initialData.id}/test-smtp`)
        if (data.status === 'success') {
            toast.success("SMTP Configuration is VALID!")
            setSmtpStatus('VALID')
        } else {
            toast.error(data.reason || "SMTP connection failed.")
            setSmtpStatus('INVALID')
        }
    } catch (err: any) {
        toast.error(err.response?.data?.detail || "Test failed. Ensure configuration is saved.")
        setSmtpStatus('INVALID')
    } finally {
        setTestingSmtp(false)
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

              {/* --- SMTP Configuration Section --- */}
              <div className="pt-4 border-t border-white/20">
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                        <Mail className="w-4 h-4 text-brand-600" />
                        <h3 className="text-sm font-bold text-surface-900">SMTP Settings</h3>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" checked={form.smtp_enabled}
                            onChange={(e) => setForm({ ...form, smtp_enabled: e.target.checked })}
                            className="sr-only peer" />
                        <div className="w-9 h-5 bg-surface-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-brand-600"></div>
                        <span className="ml-2 text-xs font-medium text-surface-600">{form.smtp_enabled ? 'Enabled' : 'Disabled'}</span>
                    </label>
                </div>

                {form.smtp_enabled && (
                    <motion.div 
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="space-y-3 bg-brand-50/50 p-4 rounded-xl border border-brand-100"
                    >
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-[10px] uppercase tracking-wider font-bold text-brand-600 flex items-center gap-1">
                                {smtpStatus === 'VALID' && <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />}
                                {smtpStatus === 'INVALID' && <AlertCircle className="w-3.5 h-3.5 text-red-500" />}
                                {smtpStatus === 'UNTESTED' && <Info className="w-3.5 h-3.5 text-surface-400" />}
                                Status: <span className={
                                    smtpStatus === 'VALID' ? 'text-emerald-600' :
                                    smtpStatus === 'INVALID' ? 'text-red-600' : 'text-surface-500'
                                }>{smtpStatus}</span>
                            </span>
                            {initialData && (
                                <button
                                    type="button"
                                    onClick={handleTestSmtp}
                                    disabled={testingSmtp}
                                    className="text-[10px] font-bold bg-white px-2 py-1 rounded-lg border border-brand-200 text-brand-600 hover:bg-brand-600 hover:text-white transition-colors flex items-center gap-1"
                                >
                                    {testingSmtp ? <Loader2 className="w-2.5 h-2.5 animate-spin" /> : <RefreshCw className="w-2.5 h-2.5" />}
                                    Test SMTP
                                </button>
                            )}
                        </div>

                        <div className="grid grid-cols-3 gap-3">
                            <div className="col-span-2">
                                <label className="text-[10px] font-bold text-surface-500 uppercase ml-1">SMTP Host</label>
                                <input value={form.smtp_host} onChange={(e) => setForm({...form, smtp_host: e.target.value})}
                                    placeholder="smtp.gmail.com" className="form-input text-xs py-1.5" />
                            </div>
                            <div>
                                <label className="text-[10px] font-bold text-surface-500 uppercase ml-1">Port</label>
                                <input type="number" value={form.smtp_port} onChange={(e) => setForm({...form, smtp_port: parseInt(e.target.value)})}
                                    placeholder="587" className="form-input text-xs py-1.5" />
                            </div>
                        </div>

                        <div>
                            <label className="text-[10px] font-bold text-surface-500 uppercase ml-1">SMTP User / Email</label>
                            <input value={form.smtp_user} onChange={(e) => setForm({...form, smtp_user: e.target.value})}
                                placeholder="user@gmail.com" className="form-input text-xs py-1.5" />
                        </div>

                        <div>
                            <label className="text-[10px] font-bold text-surface-500 uppercase ml-1">Password</label>
                            <input type="password" value={form.smtp_password} onChange={(e) => setForm({...form, smtp_password: e.target.value})}
                                placeholder={initialData ? "••••••••" : "SMTP Password"} className="form-input text-xs py-1.5" />
                            <p className="text-[9px] text-surface-400 mt-1 italic leading-tight">
                                {initialData ? "Leave blank to keep existing password." : "Password will be encrypted at rest."}
                            </p>
                        </div>

                        <div className="grid grid-cols-2 gap-3 pt-1">
                            <div>
                                <label className="text-[10px] font-bold text-surface-500 uppercase ml-1">Sender Email</label>
                                <input value={form.from_email} onChange={(e) => setForm({...form, from_email: e.target.value})}
                                    placeholder="support@company.com" className="form-input text-xs py-1.5" />
                            </div>
                            <div>
                                <label className="text-[10px] font-bold text-surface-500 uppercase ml-1">Sender Name</label>
                                <input value={form.from_name} onChange={(e) => setForm({...form, from_name: e.target.value})}
                                    placeholder="Company Name" className="form-input text-xs py-1.5" />
                            </div>
                        </div>
                    </motion.div>
                )}
              </div>

              <div className="pt-4 flex gap-3">
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
  const [sortOrder, setSortOrder] = useState<'latest' | 'oldest' | 'custom'>('latest')
  const [dateRange, setDateRange] = useState({ start: '', end: '' })

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
