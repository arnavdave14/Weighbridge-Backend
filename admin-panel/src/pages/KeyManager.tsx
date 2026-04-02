import { useState, useEffect, useMemo, type FormEvent, useCallback, memo, useRef } from 'react'
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
  email?: string; phone?: string; mobile_number?: string; whatsapp_number?: string
  address?: string; labels?: string[]
  bill_header_1?: string; bill_header_2?: string; bill_header_3?: string; bill_footer?: string
  logo_url?: string; signup_image_url?: string
}

const statusInfo = {
  active: { cls: 'badge-active', icon: CheckCircle2 },
  expired: { cls: 'badge-expired', icon: XCircle },
  revoked: { cls: 'badge-revoked', icon: Ban },
}

// --- Sub-components ---

function StatusBadge({ status }: { status: string }) {
  const s = statusInfo[status as keyof typeof statusInfo] ?? statusInfo.expired
  return (
    <span className={s.cls}>
      <s.icon className="w-3 h-3" />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  )
}

const KeyRow = memo(({ item, onCopy, onExtend, onRevoke, copiedId }: { 
  item: Key; 
  onCopy: (text: string, id: string) => void;
  onExtend: (id: string, current: string) => void;
  onRevoke: (id: string) => void;
  copiedId: string | null;
}) => {
  const isExpired = new Date(item.expiry_date) < new Date()
  
  return (
    <tr className="hover:bg-surface-50/50 transition-colors">
      <td>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-indigo-600 flex items-center justify-center text-white text-xs font-bold shrink-0">
            {item.company_name.substring(0, 2).toUpperCase()}
          </div>
          <div>
            <p className="font-semibold text-surface-900 text-[13px]">{item.company_name}</p>
            {item.email && <p className="text-[11px] text-surface-400">{item.email}</p>}
          </div>
        </div>
      </td>
      <td>
        <div className="flex items-center gap-2">
          <code className="text-[11px] font-mono text-brand-700 bg-brand-50 px-2 py-0.5 rounded">
            {item.token.substring(0, 14)}…
          </code>
          <button onClick={() => onCopy(item.token, item.id)} className="text-surface-300 hover:text-brand-500 transition-colors">
            {copiedId === item.id ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
        </div>
      </td>
      <td><StatusBadge status={item.status} /></td>
      <td>
        <div className="text-[12px]">
          <p className={`font-medium ${isExpired ? 'text-red-600' : 'text-surface-700'}`}>
            {format(new Date(item.expiry_date), 'dd MMM yyyy')}
          </p>
          <p className="text-surface-400">
            {isExpired ? 'Expired' : `Expires ${formatDistanceToNow(new Date(item.expiry_date), { addSuffix: true })}`}
          </p>
        </div>
      </td>
      <td className="text-[12px] text-surface-400">
        {format(new Date(item.created_at), 'dd MMM yyyy')}
      </td>
      <td className="text-right">
        <div className="flex items-center justify-end gap-2">
          <button onClick={() => onExtend(item.id, item.expiry_date)}
            className="text-[11px] font-medium text-brand-600 hover:text-brand-700 hover:underline flex items-center gap-1">
            <Clock className="w-3 h-3" /> Extend
          </button>
          {item.status !== 'revoked' && (
            <button onClick={() => onRevoke(item.id)}
              className="text-[11px] font-medium text-red-500 hover:text-red-600 hover:underline flex items-center gap-1">
              <Trash2 className="w-3 h-3" /> Revoke
            </button>
          )}
        </div>
      </td>
    </tr>
  )
})

const GeneratedKeysModal = memo(({ keys, onCopy, copiedId, onClose }: { 
  keys: string[]; 
  onCopy: (text: string, id: string) => void;
  copiedId: string | null;
  onClose: () => void;
}) => (
  <AnimatePresence>
    {keys.length > 0 && (
      <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
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
            {keys.map((k, i) => (
              <div key={i} className="flex items-center gap-3 bg-surface-50 border border-surface-200 rounded-xl px-4 py-3">
                <code className="flex-1 font-mono text-sm text-brand-700 font-bold tracking-wider">{k}</code>
                <button onClick={() => onCopy(k, `modal-${i}`)} className="text-surface-400 hover:text-brand-600 transition-colors">
                  {copiedId === `modal-${i}` ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
            ))}
          </div>
          <button onClick={onClose} className="btn-primary w-full mt-6 justify-center">
            I've Saved the Keys
          </button>
        </motion.div>
      </div>
    )}
  </AnimatePresence>
))

const ImageUpload = ({ label, value, target, onChange }: { label: string; value: string; target: 'logo' | 'signup'; onChange: (val: string) => void }) => {
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const endpoint = target === 'logo' ? '/admin/upload/logo' : '/admin/upload/signup'
      const { data } = await api.post(endpoint, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      onChange(data.url)
    } catch (err) {
      console.error('Upload failed:', err)
      alert('Upload failed. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="space-y-2">
      <label className="form-label text-brand-600 font-bold">{label}</label>
      <div className="flex items-center gap-4">
        {value ? (
          <div className="relative w-16 h-16 rounded-xl border border-surface-200 overflow-hidden bg-surface-50 shrink-0 group">
            <img src={value} alt="Preview" className="w-full h-full object-contain" />
            <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
              <button 
                type="button" 
                onClick={() => onChange('')} 
                className="p-1 rounded-full bg-white/20 hover:bg-white/40 text-white"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          </div>
        ) : (
          <div className="w-16 h-16 rounded-xl border-2 border-dashed border-surface-200 flex items-center justify-center text-surface-300 shrink-0">
            <Plus className="w-5 h-5" />
          </div>
        )}
        
        <div className="flex-1">
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileChange} 
            className="hidden" 
            accept="image/*" 
          />
          <div className="flex items-center gap-2">
            <button 
              type="button" 
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="btn-secondary py-1.5 px-3 text-xs flex items-center gap-2"
            >
              {uploading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plus className="w-3 h-3" />}
              {uploading ? 'Uploading...' : (value ? 'Change Image' : 'Select Image')}
            </button>
            {value && (
              <span className="text-[10px] text-surface-400 font-mono truncate max-w-[150px]">
                {value.split('/').pop()}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

const CreateKeyDrawer = memo(({ isOpen, onClose, apps, onSuccess }: { 
  isOpen: boolean; 
  onClose: () => void; 
  apps: App[];
  onSuccess: (rawKeys: string[]) => void;
}) => {
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    app_id: '', company_name: '', expiry_date: format(new Date(new Date().setFullYear(new Date().getFullYear() + 1)), 'yyyy-MM-dd'), count: 1, email: '',
    phone: '', mobile_number: '', whatsapp_number: '', address: '', labels: '',
    bill_header_1: '', bill_header_2: '', bill_header_3: '', bill_footer: '',
    logo_url: '', signup_image_url: '',
  })

  useEffect(() => {
    if (!isOpen) setForm({
      app_id: '', company_name: '', expiry_date: format(new Date(new Date().setFullYear(new Date().getFullYear() + 1)), 'yyyy-MM-dd'), count: 1, email: '',
      phone: '', mobile_number: '', whatsapp_number: '', address: '', labels: '',
      bill_header_1: '', bill_header_2: '', bill_header_3: '', bill_footer: '',
      logo_url: '', signup_image_url: '',
    })
  }, [isOpen])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const payload = {
        ...form,
        expiry_date: new Date(form.expiry_date).toISOString(),
        labels: form.labels ? form.labels.split(',').map((l: string) => l.trim()).filter(Boolean) : [],
      }
      const { data } = await api.post('/apps/keys', payload)
      onSuccess(data.map((d: any) => d.raw_activation_key))
      onClose()
    } catch (e: any) {
      console.error(e)
      alert(e.response?.data?.detail || 'Generation failed')
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
            className="fixed inset-y-0 right-0 z-50 w-full max-w-xl glass border-l border-white/20 flex flex-col"
          >
            <div className="flex items-center justify-between px-6 py-5 border-b border-white/30">
              <h2 className="text-lg font-bold text-surface-900">Generate Activation Key</h2>
              <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-surface-100 text-surface-500"><X className="w-4 h-4" /></button>
            </div>
            <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-6">
              {/* App Selection */}
              <div className="bg-brand-50/50 p-4 rounded-2xl border border-brand-100">
                <label className="form-label text-brand-700">Application *</label>
                <select required value={form.app_id} onChange={(e) => setForm({ ...form, app_id: e.target.value })} className="form-input bg-white">
                  <option value="">Select application…</option>
                  {apps.map((a) => <option key={a.id} value={a.id}>{a.app_name} ({a.app_id})</option>)}
                </select>
              </div>

              <div className="space-y-4">
                <p className="text-xs font-bold text-surface-400 uppercase tracking-widest pl-1">Company Identity</p>
                <div className="grid grid-cols-2 gap-4">
                  <div className="col-span-2">
                    <label className="form-label">Company Name *</label>
                    <input required value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })}
                      placeholder="e.g. Bharat Steel Ltd" className="form-input font-bold" />
                  </div>
                  <ImageUpload 
                    label="Company Logo" 
                    value={form.logo_url} 
                    target="logo"
                    onChange={(url) => setForm(f => ({ ...f, logo_url: url }))} 
                  />
                  <ImageUpload 
                    label="Sign-Up Image" 
                    value={form.signup_image_url} 
                    target="signup"
                    onChange={(url) => setForm(f => ({ ...f, signup_image_url: url }))} 
                  />
                </div>
              </div>

              <div className="space-y-4 pt-2">
                <p className="text-xs font-bold text-surface-400 uppercase tracking-widest pl-1">Contact Details</p>
                <div className="grid grid-cols-2 gap-4">
                  <div className="col-span-2">
                    <label className="form-label">Email Address</label>
                    <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="contact@company.com" className="form-input" />
                  </div>
                  <div><label className="form-label">Mobile Number</label><input value={form.mobile_number} onChange={(e) => setForm({ ...form, mobile_number: e.target.value })} placeholder="+91 98XXX XXXX" className="form-input" /></div>
                  <div><label className="form-label">WhatsApp Number</label><input value={form.whatsapp_number} onChange={(e) => setForm({ ...form, whatsapp_number: e.target.value })} placeholder="+91 98XXX XXXX" className="form-input" /></div>
                  <div className="col-span-2"><label className="form-label">Office Address</label><textarea rows={2} value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} placeholder="Full company address..." className="form-input resize-none" /></div>
                </div>
              </div>

              <div className="space-y-4 pt-2">
                <p className="text-xs font-bold text-surface-400 uppercase tracking-widest pl-1">Configuration & Billing</p>
                <div className="space-y-3 bg-surface-50 p-4 rounded-2xl border border-surface-200">
                  <div className="grid grid-cols-3 gap-3">
                    <div className="col-span-3"><label className="form-label">Custom Labels (comma-separated)</label><input value={form.labels} onChange={(e) => setForm({ ...form, labels: e.target.value })} placeholder="Vehicle, Material, Party..." className="form-input" /></div>
                    <div className="col-span-1"><label className="form-label">Header 1</label><input value={form.bill_header_1} onChange={(e) => setForm({ ...form, bill_header_1: e.target.value })} className="form-input" /></div>
                    <div className="col-span-1"><label className="form-label">Header 2</label><input value={form.bill_header_2} onChange={(e) => setForm({ ...form, bill_header_2: e.target.value })} className="form-input" /></div>
                    <div className="col-span-1"><label className="form-label">Header 3</label><input value={form.bill_header_3} onChange={(e) => setForm({ ...form, bill_header_3: e.target.value })} className="form-input" /></div>
                    <div className="col-span-3"><label className="form-label">Bill Footer</label><input value={form.bill_footer} onChange={(e) => setForm({ ...form, bill_footer: e.target.value })} placeholder="Terms and conditions..." className="form-input" /></div>
                  </div>
                </div>
              </div>

              <div className="space-y-4 pt-2">
                <p className="text-xs font-bold text-surface-400 uppercase tracking-widest pl-1">License Settings</p>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="form-label">Expiry Date *</label>
                    <input 
                      type="date" 
                      required 
                      value={form.expiry_date} 
                      onChange={(e) => setForm({ ...form, expiry_date: e.target.value })} 
                      className="form-input" 
                    />
                  </div>
                  <div><label className="form-label">Key Count</label><input type="number" min={1} max={50} value={form.count} onChange={(e) => setForm({ ...form, count: parseInt(e.target.value) })} className="form-input" /></div>
                </div>
              </div>

              <div className="pt-4 flex gap-3 sticky bottom-0 bg-white/90 backdrop-blur-sm pb-2">
                <button type="button" onClick={onClose} className="btn-secondary flex-1">Cancel</button>
                <button type="submit" disabled={saving} className="btn-primary flex-1 justify-center">
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <KeyRound className="w-4 h-4" />}
                  {saving ? 'Generating…' : 'Generate Keys'}
                </button>
              </div>
            </form>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
})

const ExtendKeyModal = memo(({ keyId, currentExpiry, onClose, onConfirm }: { 
  keyId: string | null; 
  currentExpiry: string;
  onClose: () => void; 
  onConfirm: (date: string) => void;
}) => {
  const [newDate, setNewDate] = useState('')
  
  useEffect(() => {
    if (currentExpiry) {
      setNewDate(format(new Date(currentExpiry), 'yyyy-MM-dd'))
    }
  }, [currentExpiry])

  return (
    <AnimatePresence>
      {keyId && (
        <div className="fixed inset-0 z-50 bg-black/30 backdrop-blur-sm flex items-center justify-center p-4">
          <motion.div initial={{ scale: 0.95 }} animate={{ scale: 1 }} exit={{ scale: 0.95 }}
            className="glass rounded-2xl p-6 max-w-sm w-full border border-white/40 shadow-xl">
            <div className="flex items-center gap-3 mb-5"><CalendarClock className="w-5 h-5 text-brand-600" /><h3 className="font-bold text-surface-900">Modify Expiry Date</h3></div>
            <label className="form-label">New Expiry Date</label>
            <input 
              type="date" 
              value={newDate} 
              onChange={(e) => setNewDate(e.target.value)} 
              className="form-input mb-4" 
            />
            <div className="flex gap-3">
              <button onClick={onClose} className="btn-secondary flex-1">Cancel</button>
              <button onClick={() => onConfirm(new Date(newDate).toISOString())} className="btn-primary flex-1 justify-center">Update Date</button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
})

// --- Main Page ---

export default function KeyManager() {
  const [apps, setApps] = useState<App[]>([])
  const [allKeys, setAllKeys] = useState<Key[]>([])
  const [selectedAppId, setSelectedAppId] = useState<string>('')
  const [loadingKeys, setLoadingKeys] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [extendKey, setExtendKey] = useState<{id: string, expiry: string} | null>(null)
  const [generatedRawKeys, setGeneratedRawKeys] = useState<string[]>([])

  const fetchAllKeys = useCallback(async () => {
    setLoadingKeys(true)
    try {
      const { data } = await api.get('/apps/keys/all')
      setAllKeys(data)
    } finally {
      setLoadingKeys(false)
    }
  }, [])

  useEffect(() => {
    api.get('/apps').then((r) => setApps(r.data))
    fetchAllKeys()
  }, [fetchAllKeys])

  const filteredKeys = useMemo(() => {
    return selectedAppId ? allKeys.filter((k) => k.app_id === selectedAppId) : allKeys
  }, [allKeys, selectedAppId])

  const copyToClipboard = useCallback((text: string, id: string) => {
    navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }, [])

  const handleRevoke = useCallback(async (keyId: string) => {
    if (!confirm('Revoke this license?')) return
    await api.delete(`/apps/keys/${keyId}/revoke`)
    fetchAllKeys()
  }, [fetchAllKeys])

  const handleUpdateExpiry = useCallback(async (isoDate: string) => {
    if (!extendKey) return
    await api.put(`/apps/keys/${extendKey.id}`, { expiry_date: isoDate })
    setExtendKey(null)
    fetchAllKeys()
  }, [extendKey, fetchAllKeys])

  const handleCreateSuccess = useCallback((keys: string[]) => {
    setGeneratedRawKeys(keys)
    fetchAllKeys()
  }, [fetchAllKeys])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div><h1 className="page-title">License Keys</h1><p className="page-subtitle">Manage company licenses and configurations</p></div>
        <button onClick={() => setShowCreate(true)} className="btn-primary"><Plus className="w-4 h-4" /> Generate Key</button>
      </div>

      <GeneratedKeysModal keys={generatedRawKeys} onCopy={copyToClipboard} copiedId={copiedId} onClose={() => setGeneratedRawKeys([])} />
      <CreateKeyDrawer isOpen={showCreate} onClose={() => setShowCreate(false)} apps={apps} onSuccess={handleCreateSuccess} />
      <ExtendKeyModal 
        keyId={extendKey?.id || null} 
        currentExpiry={extendKey?.expiry || ''} 
        onClose={() => setExtendKey(null)} 
        onConfirm={handleUpdateExpiry} 
      />

      <div className="glass rounded-xl px-5 py-3 flex items-center gap-4 border border-white/50">
        <span className="text-sm font-medium text-surface-600">Filter:</span>
        <select 
          aria-label="Filter licenses by application"
          value={selectedAppId} 
          onChange={(e) => setSelectedAppId(e.target.value)} 
          className="form-input max-w-xs"
        >
          <option value="">All Applications</option>
          {apps.map((a) => <option key={a.id} value={a.id}>{a.app_name}</option>)}
        </select>
        <span className="ml-auto text-xs text-surface-400">{filteredKeys.length} licenses</span>
      </div>

      <div className="glass rounded-2xl border border-white/50 overflow-hidden">
        {loadingKeys ? (
          <div className="flex items-center justify-center py-20 text-surface-400"><Loader2 className="w-7 h-7 animate-spin" /></div>
        ) : filteredKeys.length === 0 ? (
          <div className="text-center py-20 text-surface-400"><KeyRound className="w-12 h-12 mx-auto mb-3 opacity-20" /><p>No keys found.</p></div>
        ) : (
          <table className="data-table">
            <thead><tr><th>Company</th><th>Token</th><th>Status</th><th>Expiry</th><th>Issued</th><th className="text-right">Actions</th></tr></thead>
            <tbody>
              {filteredKeys.map((key) => (
                <KeyRow 
                  key={key.id} 
                  item={key} 
                  onCopy={copyToClipboard} 
                  onExtend={(id, expiry) => setExtendKey({ id, expiry })} 
                  onRevoke={handleRevoke} 
                  copiedId={copiedId} 
                />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
