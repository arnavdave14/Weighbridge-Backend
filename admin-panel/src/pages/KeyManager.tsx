import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Plus, X, Loader2, KeyRound, CheckCircle2, XCircle, Ban,
  Clock, Copy, Check, Trash2, CalendarClock,
} from 'lucide-react'
import api from '../services/api'
import { format, formatDistanceToNow } from 'date-fns'

interface App { id: string; app_id: string; app_name: string }

interface Key {
  id: string; app_id: string; status: string; token: string
  expiry_date: string; created_at: string; company_name: string
  email?: string; phone?: string; whatsapp_number?: string
  address?: string; labels?: string[]
  bill_header_1?: string; bill_header_2?: string; bill_header_3?: string; bill_footer?: string
}

const statusInfo = {
  active: { cls: 'badge-active', icon: CheckCircle2 },
  expired: { cls: 'badge-expired', icon: XCircle },
  revoked: { cls: 'badge-revoked', icon: Ban },
}

const MONTHS = [1, 3, 6, 12, 24, 36]

function StatusBadge({ status }: { status: string }) {
  const s = statusInfo[status as keyof typeof statusInfo] ?? statusInfo.expired
  return (
    <span className={s.cls}>
      <s.icon className="w-3 h-3" />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  )
}

export default function KeyManager() {
  const [apps, setApps] = useState<App[]>([])
  const [allKeys, setAllKeys] = useState<Key[]>([])
  const [selectedAppId, setSelectedAppId] = useState<string>('')
  const [loadingKeys, setLoadingKeys] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [saving, setSaving] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [extendKeyId, setExtendKeyId] = useState<string | null>(null)
  const [extendMonths, setExtendMonths] = useState(3)
  const [generatedRawKeys, setGeneratedRawKeys] = useState<string[]>([])

  const [form, setForm] = useState({
    app_id: '',
    company_name: '',
    expiry_months: 12,
    count: 1,
    email: '',
    phone: '',
    whatsapp_number: '',
    address: '',
    labels: '',
    bill_header_1: '',
    bill_header_2: '',
    bill_header_3: '',
    bill_footer: '',
  })

  useEffect(() => {
    api.get('/apps').then((r) => setApps(r.data)).catch(console.error)
    fetchAllKeys()
  }, [])

  const fetchAllKeys = async () => {
    setLoadingKeys(true)
    try {
      const { data } = await api.get('/apps/keys/all')
      setAllKeys(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoadingKeys(false)
    }
  }

  const filteredKeys = selectedAppId
    ? allKeys.filter((k) => k.app_id === selectedAppId)
    : allKeys

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const payload = {
        ...form,
        labels: form.labels ? form.labels.split(',').map((l) => l.trim()).filter(Boolean) : [],
        app_id: apps.find((a) => a.id === form.app_id)?.id ?? form.app_id,
      }
      const { data } = await api.post('/apps/keys', payload)
      setGeneratedRawKeys(data.map((d: any) => d.raw_activation_key))
      setShowCreate(false)
      setForm({ ...form, company_name: '', email: '', phone: '', whatsapp_number: '', address: '', labels: '', bill_header_1: '', bill_header_2: '', bill_header_3: '', bill_footer: '' })
      fetchAllKeys()
    } catch (e) {
      console.error(e)
    } finally {
      setSaving(false)
    }
  }

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const handleRevoke = async (keyId: string) => {
    if (!confirm('Revoke this license? This cannot be undone.')) return
    await api.delete(`/apps/keys/${keyId}/revoke`)
    fetchAllKeys()
  }

  const handleExtend = async () => {
    if (!extendKeyId) return
    await api.put(`/apps/keys/${extendKeyId}`, { extend_expiry_months: extendMonths })
    setExtendKeyId(null)
    fetchAllKeys()
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">License Keys</h1>
          <p className="page-subtitle">Each key = one company license with all company configuration</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary">
          <Plus className="w-4 h-4" /> Generate Key
        </button>
      </div>

      {/* Generated Keys Modal */}
      <AnimatePresence>
        {generatedRawKeys.length > 0 && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
              <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }}
                className="glass rounded-2xl p-8 max-w-lg w-full border border-yellow-300/50 shadow-2xl">
                <div className="text-center mb-6">
                  <div className="w-14 h-14 bg-yellow-100 rounded-2xl flex items-center justify-center mx-auto mb-3">
                    <KeyRound className="w-7 h-7 text-yellow-600" />
                  </div>
                  <h2 className="text-xl font-bold text-surface-900">⚠️ Save These Keys Now!</h2>
                  <p className="text-sm text-surface-500 mt-1">Raw keys are shown <strong>only once</strong>. Copy and store them securely.</p>
                </div>
                <div className="space-y-3">
                  {generatedRawKeys.map((k, i) => (
                    <div key={i} className="flex items-center gap-3 bg-surface-50 border border-surface-200 rounded-xl px-4 py-3">
                      <code className="flex-1 font-mono text-sm text-brand-700 font-bold tracking-wider">{k}</code>
                      <button onClick={() => copyToClipboard(k, `modal-${i}`)} className="text-surface-400 hover:text-brand-600 transition-colors">
                        {copiedId === `modal-${i}` ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
                      </button>
                    </div>
                  ))}
                </div>
                <button onClick={() => setGeneratedRawKeys([])} className="btn-primary w-full mt-6 justify-center">
                  I've Saved the Keys
                </button>
              </motion.div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Create Key Drawer */}
      <AnimatePresence>
        {showCreate && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setShowCreate(false)} className="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm" />
            <motion.div
              initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }}
              transition={{ type: 'spring', stiffness: 300, damping: 35 }}
              className="fixed inset-y-0 right-0 z-50 w-full max-w-xl glass shadow-2xl border-l border-white/40 flex flex-col"
            >
              <div className="flex items-center justify-between px-6 py-5 border-b border-white/30">
                <h2 className="text-lg font-bold text-surface-900">Generate Activation Key</h2>
                <button onClick={() => setShowCreate(false)} className="p-1.5 rounded-lg hover:bg-surface-100 text-surface-500"><X className="w-4 h-4" /></button>
              </div>

              <form onSubmit={handleCreate} className="flex-1 overflow-y-auto p-6 space-y-5">
                {/* App Selection */}
                <div>
                  <label className="form-label">Application *</label>
                  <select required value={form.app_id} onChange={(e) => setForm({ ...form, app_id: e.target.value })} className="form-input">
                    <option value="">Select application…</option>
                    {apps.map((a) => <option key={a.id} value={a.id}>{a.app_name} ({a.app_id})</option>)}
                  </select>
                </div>

                <hr className="border-surface-100" />
                <p className="text-xs font-bold text-surface-500 uppercase tracking-widest">Company Details</p>

                <div className="grid grid-cols-2 gap-4">
                  <div className="col-span-2">
                    <label className="form-label">Company Name *</label>
                    <input required value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })}
                      placeholder="e.g. Bharat Steel Ltd" className="form-input" />
                  </div>
                  <div>
                    <label className="form-label">Email</label>
                    <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="contact@company.com" className="form-input" />
                  </div>
                  <div>
                    <label className="form-label">Phone</label>
                    <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="+91 9800000000" className="form-input" />
                  </div>
                  <div>
                    <label className="form-label">WhatsApp</label>
                    <input value={form.whatsapp_number} onChange={(e) => setForm({ ...form, whatsapp_number: e.target.value })} placeholder="+91 9800000000" className="form-input" />
                  </div>
                  <div>
                    <label className="form-label">Address</label>
                    <input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} placeholder="City, State" className="form-input" />
                  </div>
                </div>

                <hr className="border-surface-100" />
                <p className="text-xs font-bold text-surface-500 uppercase tracking-widest">Bill Configuration</p>

                <div className="space-y-3">
                  {(['bill_header_1', 'bill_header_2', 'bill_header_3'] as const).map((f, i) => (
                    <div key={f}>
                      <label className="form-label">Bill Header {i + 1}</label>
                      <input value={form[f]} onChange={(e) => setForm({ ...form, [f]: e.target.value })} placeholder={`Header ${i + 1}`} className="form-input" />
                    </div>
                  ))}
                  <div>
                    <label className="form-label">Bill Footer</label>
                    <input value={form.bill_footer} onChange={(e) => setForm({ ...form, bill_footer: e.target.value })} placeholder="e.g. Thank you for your business!" className="form-input" />
                  </div>
                  <div>
                    <label className="form-label">Labels (comma-separated)</label>
                    <input value={form.labels} onChange={(e) => setForm({ ...form, labels: e.target.value })}
                      placeholder="e.g. Vehicle No, Material, Driver Name" className="form-input" />
                  </div>
                </div>

                <hr className="border-surface-100" />
                <p className="text-xs font-bold text-surface-500 uppercase tracking-widest">License Settings</p>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="form-label">Validity (months)</label>
                    <select value={form.expiry_months} onChange={(e) => setForm({ ...form, expiry_months: parseInt(e.target.value) })} className="form-input">
                      {MONTHS.map((m) => <option key={m} value={m}>{m} month{m > 1 ? 's' : ''}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="form-label">Count (bulk)</label>
                    <input type="number" min={1} max={50} value={form.count} onChange={(e) => setForm({ ...form, count: parseInt(e.target.value) })} className="form-input" />
                  </div>
                </div>

                <div className="pt-2 flex gap-3 sticky bottom-0 bg-white/80 backdrop-blur-sm pb-2">
                  <button type="button" onClick={() => setShowCreate(false)} className="btn-secondary flex-1">Cancel</button>
                  <button type="submit" disabled={saving} className="btn-primary flex-1 justify-center">
                    {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <KeyRound className="w-4 h-4" />}
                    {saving ? 'Generating…' : `Generate ${form.count > 1 ? form.count + ' Keys' : 'Key'}`}
                  </button>
                </div>
              </form>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Extend Modal */}
      <AnimatePresence>
        {extendKeyId && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/30 backdrop-blur-sm flex items-center justify-center p-4">
            <motion.div initial={{ scale: 0.95 }} animate={{ scale: 1 }} exit={{ scale: 0.95 }}
              className="glass rounded-2xl p-6 max-w-sm w-full border border-white/40 shadow-xl">
              <div className="flex items-center gap-3 mb-5">
                <CalendarClock className="w-5 h-5 text-brand-600" />
                <h3 className="font-bold text-surface-900">Modify Expiry</h3>
              </div>
              <label className="form-label">Months to add / remove</label>
              <input type="number" value={extendMonths} onChange={(e) => setExtendMonths(parseInt(e.target.value))}
                placeholder="e.g. 6 to extend, -3 to reduce" className="form-input mb-4" />
              <div className="flex gap-3">
                <button onClick={() => setExtendKeyId(null)} className="btn-secondary flex-1">Cancel</button>
                <button onClick={handleExtend} className="btn-primary flex-1 justify-center">Apply</button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Filter bar */}
      <div className="glass rounded-xl px-5 py-3 flex items-center gap-4 border border-white/50">
        <span className="text-sm font-medium text-surface-600">Filter by App:</span>
        <select value={selectedAppId} onChange={(e) => setSelectedAppId(e.target.value)} className="form-input max-w-xs">
          <option value="">All Applications</option>
          {apps.map((a) => <option key={a.id} value={a.id}>{a.app_name}</option>)}
        </select>
        <span className="ml-auto text-xs text-surface-400">{filteredKeys.length} license{filteredKeys.length !== 1 ? 's' : ''}</span>
      </div>

      {/* Keys Table */}
      <div className="glass rounded-2xl border border-white/50 overflow-hidden">
        {loadingKeys ? (
          <div className="flex items-center justify-center py-20 text-surface-400">
            <Loader2 className="w-7 h-7 animate-spin" />
          </div>
        ) : filteredKeys.length === 0 ? (
          <div className="text-center py-20 text-surface-400">
            <KeyRound className="w-12 h-12 mx-auto mb-3 opacity-20" />
            <p className="font-medium">No license keys yet.</p>
            <p className="text-sm mt-1">Generate keys using the button above.</p>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Company</th>
                <th>Token (truncated)</th>
                <th>Status</th>
                <th>Expiry</th>
                <th>Issued</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredKeys.map((key, i) => {
                const isExpired = new Date(key.expiry_date) < new Date()
                return (
                  <motion.tr key={key.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.04 }}>
                    <td>
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-indigo-600 flex items-center justify-center text-white text-xs font-bold shrink-0">
                          {key.company_name.substring(0, 2).toUpperCase()}
                        </div>
                        <div>
                          <p className="font-semibold text-surface-900 text-[13px]">{key.company_name}</p>
                          {key.email && <p className="text-[11px] text-surface-400">{key.email}</p>}
                        </div>
                      </div>
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        <code className="text-[11px] font-mono text-brand-700 bg-brand-50 px-2 py-0.5 rounded">
                          {key.token.substring(0, 14)}…
                        </code>
                        <button onClick={() => copyToClipboard(key.token, key.id)} className="text-surface-300 hover:text-brand-500 transition-colors">
                          {copiedId === key.id ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                    </td>
                    <td><StatusBadge status={key.status} /></td>
                    <td>
                      <div className="text-[12px]">
                        <p className={`font-medium ${isExpired ? 'text-red-600' : 'text-surface-700'}`}>
                          {format(new Date(key.expiry_date), 'dd MMM yyyy')}
                        </p>
                        <p className="text-surface-400">
                          {isExpired ? 'Expired' : `Expires ${formatDistanceToNow(new Date(key.expiry_date), { addSuffix: true })}`}
                        </p>
                      </div>
                    </td>
                    <td className="text-[12px] text-surface-400">
                      {format(new Date(key.created_at), 'dd MMM yyyy')}
                    </td>
                    <td className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button onClick={() => { setExtendKeyId(key.id); setExtendMonths(3) }}
                          className="text-[11px] font-medium text-brand-600 hover:text-brand-700 hover:underline flex items-center gap-1">
                          <Clock className="w-3 h-3" /> Extend
                        </button>
                        {key.status !== 'revoked' && (
                          <button onClick={() => handleRevoke(key.id)}
                            className="text-[11px] font-medium text-red-500 hover:text-red-600 hover:underline flex items-center gap-1">
                            <Trash2 className="w-3 h-3" /> Revoke
                          </button>
                        )}
                      </div>
                    </td>
                  </motion.tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
