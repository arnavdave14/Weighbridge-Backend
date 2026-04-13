import { useState, useEffect, useMemo, type FormEvent, useCallback, memo, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useSearchParams } from 'react-router-dom'
import { 
  Plus, Copy, Check, Trash2, KeyRound, Loader2, Filter, 
  Clock, RefreshCw, Layers, X, Calendar
} from 'lucide-react'
import api from '../services/api'
import { format } from 'date-fns'
import { useToast } from '../context/ToastContext'

interface App { id: string; app_id: string; app_name: string }

interface CustomLabel {
  name: string
  type: 'text' | 'alphanumeric' | 'alphabetical' | 'numeric' | 'date'
  required: boolean
  regex?: string
}

interface Key {
  id: string; app_id: string; status: string; token: string
  current_version?: number
  expiry_date: string; created_at: string; company_name: string
  email?: string; phone?: string; mobile_number?: string; whatsapp_number?: string
  address?: string; labels?: CustomLabel[]
  bill_header_1?: string; bill_header_2?: string; bill_header_3?: string; bill_footer?: string
  logo_url?: string; signup_image_url?: string
}

// --- Sub-components ---

const KeyRow = memo(({ item, appName, onCopy, onExtend, onRevoke, onRotate, copiedId }: {
  item: Key;
  appName: string;
  onCopy: (text: string, id: string) => void;
  onExtend: (id: string, expiry: string) => void;
  onRevoke: (id: string) => void;
  onRotate: (id: string) => void;
  copiedId: string | null;
}) => {
  return (
    <tr className="hover:bg-surface-50/50 transition-colors">
      <td className="py-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-brand-50 flex items-center justify-center text-brand-600 font-bold text-xs ring-1 ring-brand-100">
            {item.company_name.charAt(0).toUpperCase()}
          </div>
          <div>
            <div className="text-sm font-bold text-surface-900">{item.company_name}</div>
            <div className="text-[10px] text-surface-500 flex items-center gap-1"><Layers className="w-3 h-3" /> {appName}</div>
          </div>
        </div>
      </td>
      <td>
        <div className="flex items-center gap-2 group">
          <code className="text-xs font-mono text-surface-600 bg-surface-100 px-2 py-0.5 rounded-md max-w-[120px] truncate">
            {item.token.substring(0, 14)}…
          </code>
          <button onClick={() => onCopy(item.token, item.id)} className="opacity-0 group-hover:opacity-100 transition-opacity p-1 text-surface-400 hover:text-brand-600">
            {copiedId === item.id ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
        </div>
      </td>
      <td>
        <div className="flex items-center gap-2">
          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
            item.status === 'ACTIVE' ? 'bg-emerald-100 text-emerald-700' : 
            item.status === 'EXPIRING_SOON' ? 'bg-amber-100 text-amber-700' :
            item.status === 'EXPIRED' ? 'bg-orange-100 text-orange-700' : 'bg-red-100 text-red-700'
          }`}>
            {item.status.replace('_', ' ')}
          </span>
          {item.current_version !== undefined && (
             <span className="px-1.5 py-0.5 bg-surface-100 text-surface-600 text-[9px] font-mono rounded border border-surface-200">
                v{item.current_version}
             </span>
          )}
        </div>
      </td>
      <td>
        <div className="text-xs text-surface-600 font-medium">{format(new Date(item.expiry_date), 'MMM dd, yyyy')}</div>
      </td>
      <td>
        <div className="text-xs text-surface-400">{format(new Date(item.created_at), 'MMM dd, yyyy')}</div>
      </td>
      <td className="text-right">
        <div className="flex items-center justify-end gap-3 pr-2">
          <button onClick={() => onExtend(item.id, item.expiry_date)}
            className="text-[11px] font-medium text-brand-600 hover:text-brand-700 hover:underline flex items-center gap-1">
            <Clock className="w-3 h-3" /> Extend
          </button>
          {item.status !== 'REVOKED' && (
            <button onClick={() => {
              if (window.confirm("Rotate machine token? Old token will stop working in 1 hour.")) {
                onRotate(item.id)
              }
            }}
              className="text-[11px] font-medium text-surface-500 hover:text-brand-600 hover:underline flex items-center gap-1">
              <RefreshCw className="w-3 h-3" /> Rotate
            </button>
          )}
          {item.status !== 'REVOKED' && item.status !== 'EXPIRED' && (
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

const ImageUpload = ({ label, value, target, appId, onChange }: { label: string; value: string; target: 'logo' | 'signup'; appId: string; onChange: (val: string) => void }) => {
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const toast = useToast()

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (!appId) {
      toast.error('You have to first select the application.')
      return
    }

    setUploading(true)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const endpoint = target === 'logo' ? '/upload/logo' : '/upload/signup'
      const { data } = await api.post(endpoint, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      onChange(data.url)
      toast.success(`${label} uploaded successfully!`)
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Upload failed. Please try again.')
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
              <button type="button" onClick={() => onChange('')} className="p-1 rounded-full bg-white/20 hover:bg-white/40 text-white"><X className="w-3 h-3" /></button>
            </div>
          </div>
        ) : (
          <div className="w-16 h-16 rounded-xl border-2 border-dashed border-surface-200 flex items-center justify-center text-surface-300 shrink-0">
            <Plus className="w-5 h-5" />
          </div>
        )}
        <div className="flex-1">
          <input type="file" ref={fileInputRef} onChange={handleFileChange} className="hidden" accept="image/*" />
          <button type="button" onClick={() => fileInputRef.current?.click()} disabled={uploading} className="btn-secondary py-1.5 px-3 text-xs flex items-center gap-2">
            {uploading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plus className="w-3 h-3" />}
            {uploading ? 'Uploading...' : (value ? 'Change Image' : 'Select Image')}
          </button>
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
  const toast = useToast()
  const [saving, setSaving] = useState(false)
  const [lastSubmitted, setLastSubmitted] = useState<string | null>(null)
  
  const initialForm = {
    app_id: '', company_name: '', expiry_date: format(new Date(new Date().setFullYear(new Date().getFullYear() + 1)), 'yyyy-MM-dd'), count: 1, email: '',
    phone: '', mobile_number: '', whatsapp_number: '', address: '', labels: [] as CustomLabel[],
    bill_header_1: '', bill_header_2: '', bill_header_3: '', bill_footer: '',
    logo_url: '', signup_image_url: '',
    notification_type: 'both' as 'whatsapp' | 'email' | 'both',
  }
  const [form, setForm] = useState(initialForm)

  const isDuplicate = useMemo(() => {
    if (!lastSubmitted) return false;
    const current = JSON.stringify({
      app_id: form.app_id,
      company: form.company_name,
      email: form.email,
      whatsapp: form.whatsapp_number
    });
    return current === lastSubmitted;
  }, [form.app_id, form.company_name, form.email, form.whatsapp_number, lastSubmitted]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!form.app_id) { toast.error('You have to first select the application.'); return }
    setSaving(true)
    try {
      const payload = { ...form, expiry_date: new Date(form.expiry_date).toISOString() }
      const { data } = await api.post('/apps/keys', payload)
      
      // Store successful submission data for duplicate prevention
      setLastSubmitted(JSON.stringify({
        app_id: form.app_id,
        company: form.company_name,
        email: form.email,
        whatsapp: form.whatsapp_number
      }))

      onSuccess(data.map((d: any) => d.raw_activation_key))
      toast.success(`Successfully generated ${form.count} activation key(s)!`)
      onClose()
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Generation failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} className="fixed inset-0 z-40 bg-black/30" />
          <motion.div initial={{ x: '100%', opacity: 0.5 }} animate={{ x: 0, opacity: 1 }} exit={{ x: '100%', opacity: 0.5 }} transition={{ type: 'tween', ease: 'easeOut', duration: 0.25 }} className="fixed inset-y-0 right-0 z-50 w-full max-w-xl glass border-l border-white/20 flex flex-col">
            <div className="flex items-center justify-between px-6 py-5 border-b border-white/30">
              <h2 className="text-lg font-bold text-surface-900">Generate Activation Key</h2>
              <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-surface-100 text-surface-500"><X className="w-4 h-4" /></button>
            </div>
            <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-6">
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
                  <div className="col-span-2"><label className="form-label">Company Name *</label><input required value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })} className="form-input font-bold" /></div>
                  <ImageUpload label="Company Logo" value={form.logo_url} target="logo" appId={form.app_id} onChange={(url) => setForm(f => ({ ...f, logo_url: url }))} />
                  <ImageUpload label="Sign-Up Image" value={form.signup_image_url} target="signup" appId={form.app_id} onChange={(url) => setForm(f => ({ ...f, signup_image_url: url }))} />
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
                <div className="space-y-4 bg-surface-50 p-4 rounded-2xl border border-surface-200">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-[11px] font-bold text-surface-400 uppercase tracking-wider">Custom Fields / Labels</label>
                      <button 
                        type="button" 
                        onClick={() => setForm(f => ({ ...f, labels: [...f.labels, { name: '', type: 'text', required: false, regex: '' }] }))}
                        className="text-[10px] font-bold text-brand-600 hover:text-brand-700 flex items-center gap-1 group"
                      >
                        <Plus className="w-3 h-3 group-hover:scale-110 transition-transform" /> Add Field
                      </button>
                    </div>

                    <div className="space-y-4">
                      {form.labels.length === 0 && (
                        <div className="text-[10px] text-surface-400 text-center py-2 border border-dashed border-surface-200 rounded-lg">
                          No custom fields added.
                        </div>
                      )}
                      {form.labels.map((field, idx) => (
                        <div key={idx} className="space-y-2 animate-in slide-in-from-right-2 duration-200">
                          <div className="flex items-center gap-2 group">
                            <input 
                              required
                              value={field.name}
                              onChange={(e) => {
                                const newList = [...form.labels];
                                newList[idx].name = e.target.value;
                                setForm({ ...form, labels: newList });
                              }}
                              placeholder="Field Name"
                              className="form-input text-xs py-1.5 flex-1"
                            />
                            <select 
                              value={field.type}
                              onChange={(e) => {
                                const newList = [...form.labels];
                                newList[idx].type = e.target.value as any;
                                setForm({ ...form, labels: newList });
                              }}
                              className="form-input text-[10px] py-1.5 w-24 bg-white"
                            >
                              <option value="text">Text</option>
                              <option value="alphanumeric">Alphanumeric</option>
                              <option value="alphabetical">Letters</option>
                              <option value="numeric">Numbers</option>
                              <option value="date">Date</option>
                            </select>
                            <label className="flex items-center gap-1.5 cursor-pointer px-2 py-1.5 rounded-lg hover:bg-surface-100 transition-colors">
                              <input 
                                type="checkbox"
                                checked={field.required}
                                onChange={(e) => {
                                  const newList = [...form.labels];
                                  newList[idx].required = e.target.checked;
                                  setForm({ ...form, labels: newList });
                                }}
                                className="w-3 h-3 accent-brand-500 rounded"
                              />
                              <span className="text-[9px] font-bold text-surface-501 uppercase tracking-tighter">Req</span>
                            </label>
                            <button 
                              type="button"
                              onClick={() => setForm(f => ({ ...f, labels: f.labels.filter((_, i) => i !== idx) }))}
                              className="p-1.5 text-surface-300 hover:text-red-500 transition-colors"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                          <div className="pl-1">
                            <input 
                              value={field.regex || ''}
                              onChange={(e) => {
                                const newList = [...form.labels];
                                newList[idx].regex = e.target.value;
                                setForm({ ...form, labels: newList });
                              }}
                              placeholder="Custom Regex Override (Optional)"
                              className="w-full text-[9px] bg-transparent border-b border-surface-200 focus:border-brand-300 py-0.5 text-surface-400 placeholder:text-surface-300 outline-none font-mono"
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-3 pt-2 border-t border-surface-200">
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
                  <div className="col-span-2">
                    <label className="form-label">Notification Channel</label>
                    <div className="flex gap-2">
                      {['both', 'whatsapp', 'email'].map((type) => (
                        <button
                          key={type}
                          type="button"
                          onClick={() => setForm({ ...form, notification_type: type as any })}
                          className={`flex-1 py-2 px-3 rounded-xl text-xs font-bold capitalize transition-all border ${
                            form.notification_type === type 
                              ? 'bg-brand-600 border-brand-600 text-white shadow-lg shadow-brand-200' 
                              : 'bg-white border-surface-200 text-surface-600 hover:border-brand-200'
                          }`}
                        >
                          {type}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
              <div className="pt-4 flex gap-3 sticky bottom-0 backdrop-blur-sm pb-2">
                <button type="button" onClick={onClose} className="btn-secondary flex-1">Cancel</button>
                <button type="submit" disabled={saving || isDuplicate} className={`btn-primary flex-1 justify-center ${isDuplicate ? 'opacity-50 cursor-not-allowed grayscale' : ''}`}>
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <KeyRound className="w-4 h-4" />}
                  {saving ? 'Generating…' : isDuplicate ? 'Already Generated' : 'Generate Keys'}
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
  useEffect(() => { if (currentExpiry) setNewDate(format(new Date(currentExpiry), 'yyyy-MM-dd')) }, [currentExpiry])
  return (
    <AnimatePresence>
      {keyId && (
        <div className="fixed inset-0 z-50 bg-black/30 backdrop-blur-sm flex items-center justify-center p-4">
          <motion.div initial={{ scale: 0.95 }} animate={{ scale: 1 }} exit={{ scale: 0.95 }} className="glass rounded-2xl p-6 max-w-sm w-full border border-white/40 shadow-xl">
            <div className="flex items-center gap-3 mb-5"><Clock className="w-5 h-5 text-brand-600" /><h3 className="font-bold text-surface-900">Modify Expiry Date</h3></div>
            <input type="date" value={newDate} onChange={(e) => setNewDate(e.target.value)} className="form-input mb-4" />
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
  const [searchParams, setSearchParams] = useSearchParams()
  const [apps, setApps] = useState<App[]>([])
  const [allKeys, setAllKeys] = useState<Key[]>([])
  const [selectedAppId, setSelectedAppId] = useState<string>(searchParams.get('appId') || '')
  const [loadingKeys, setLoadingKeys] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [extendKey, setExtendKey] = useState<{ id: string, expiry: string } | null>(null)
  const [generatedRawKeys, setGeneratedRawKeys] = useState<string[]>([])
  const [sortOrder, setSortOrder] = useState<'latest' | 'oldest' | 'custom'>('latest')
  const [dateRange, setDateRange] = useState({ start: '', end: '' })
  const toast = useToast()

  const fetchAllKeys = useCallback(async () => {
    setLoadingKeys(true)
    try {
      const { data } = await api.get('/apps/keys/all')
      setAllKeys(data)
    } catch (err) {
      toast.error('Could not load license keys.')
    } finally {
      setLoadingKeys(false)
    }
  }, [toast])

  useEffect(() => {
    api.get('/apps').then((r) => setApps(r.data))
    fetchAllKeys()
  }, [fetchAllKeys])

  const filteredAndSortedKeys = useMemo(() => {
    let result = selectedAppId ? allKeys.filter((k) => k.app_id === selectedAppId) : [...allKeys]

    if (sortOrder === 'custom' && dateRange.start && dateRange.end) {
      const start = new Date(dateRange.start)
      const end = new Date(dateRange.end)
      start.setHours(0, 0, 0, 0)
      end.setHours(23, 59, 59, 999)
      
      result = result.filter(key => {
        const date = new Date(key.created_at)
        return date >= start && date <= end
      })
    }

    result.sort((a, b) => {
      const d1 = new Date(a.created_at).getTime()
      const d2 = new Date(b.created_at).getTime()
      return sortOrder === 'oldest' ? d1 - d2 : d2 - d1
    })
    return result
  }, [allKeys, selectedAppId, sortOrder, dateRange])

  const copyToClipboard = useCallback((text: string, id: string) => {
    navigator.clipboard.writeText(text)
    setCopiedId(id)
    toast.success('Key copied to clipboard!')
    setTimeout(() => setCopiedId(null), 2000)
  }, [toast])

  const handleRevoke = useCallback(async (id: string) => {
    try {
      if (window.confirm("Are you sure you want to revoke this license? Hardware will stop syncing immediately.")) {
        await api.delete(`/apps/keys/${id}/revoke`)
        toast.success('License revoked.')
        fetchAllKeys()
      }
    } catch (err) {
      toast.error('Could not revoke license.')
    }
  }, [fetchAllKeys, toast])

  const handleRotateToken = useCallback(async (id: string) => {
    try {
        await api.patch(`/apps/keys/${id}/rotate-token`)
        toast.success('Token rotated! Grace period of 1 hour started.')
        fetchAllKeys()
    } catch (err) {
        toast.error('Could not rotate token.')
    }
  }, [fetchAllKeys, toast])

  const handleUpdateExpiry = useCallback(async (isoDate: string) => {
    if (!extendKey) return
    try {
      await api.patch(`/apps/keys/${extendKey.id}`, { expiry_date: isoDate })
      toast.success('Expiry date updated.')
      setExtendKey(null)
      fetchAllKeys()
    } catch (err) {
      toast.error('Could not update expiry date.')
    }
  }, [extendKey, fetchAllKeys, toast])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div><h1 className="page-title">License Keys</h1><p className="page-subtitle">Manage company licenses and configurations</p></div>
        <button onClick={() => setShowCreate(true)} className="btn-primary"><Plus className="w-4 h-4" /> Generate Key</button>
      </div>

      <GeneratedKeysModal keys={generatedRawKeys} onCopy={copyToClipboard} copiedId={copiedId} onClose={() => setGeneratedRawKeys([])} />
      <CreateKeyDrawer isOpen={showCreate} onClose={() => setShowCreate(false)} apps={apps} onSuccess={(keys) => { setGeneratedRawKeys(keys); fetchAllKeys(); }} />
      <ExtendKeyModal keyId={extendKey?.id || null} currentExpiry={extendKey?.expiry || ''} onClose={() => setExtendKey(null)} onConfirm={handleUpdateExpiry} />

      <div className="flex flex-wrap items-center gap-4 glass p-4 rounded-xl border border-white/50">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-surface-400" />
          <select value={selectedAppId} onChange={(e) => { setSelectedAppId(e.target.value); setSearchParams(e.target.value ? { appId: e.target.value } : {}) }} className="form-input max-w-xs py-1.5 text-sm">
            <option value="">All Applications</option>
            {apps.map((a) => <option key={a.id} value={a.id}>{a.app_name}</option>)}
          </select>
        </div>

        <div className="flex items-center gap-2 border-l border-surface-200 pl-4">
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

        <span className="ml-auto text-xs text-surface-400">{filteredAndSortedKeys.length} licenses</span>
      </div>

      {sortOrder === 'custom' && (
        <motion.div 
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="glass p-4 rounded-xl border border-white/40 flex flex-wrap items-center gap-4 mt-2"
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

      <div className="glass rounded-2xl border border-white/50 overflow-hidden">
        {loadingKeys ? (
          <div className="flex items-center justify-center py-20 text-surface-400"><Loader2 className="w-7 h-7 animate-spin" /></div>
        ) : (
          <table className="data-table">
            <thead><tr><th>Company / App</th><th>Token</th><th>Status</th><th>Expiry</th><th>Issued</th><th className="text-right">Actions</th></tr></thead>
            <tbody>
              {filteredAndSortedKeys.map((key: Key) => (
                <KeyRow
                  key={key.id}
                  item={key}
                  appName={apps.find(a => a.id === key.app_id)?.app_name || 'Unknown App'}
                  onCopy={copyToClipboard}
                  onExtend={(id, expiry) => setExtendKey({ id, expiry })}
                  onRevoke={handleRevoke}
                  onRotate={handleRotateToken}
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
