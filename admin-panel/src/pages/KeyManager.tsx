import { useState, useEffect, useMemo, type FormEvent, useCallback, memo, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useSearchParams } from 'react-router-dom'
import { 
  Plus, Copy, Check, Trash2, KeyRound, Loader2, Filter, 
  Clock, RefreshCw, Layers, X, Calendar, Settings, ShieldCheck,
  ChevronRight, ChevronLeft, Wifi, CircleDot, CheckCircle2, XCircle
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

  // Communication Settings
  smtp_enabled: boolean;
  smtp_host?: string;
  smtp_port?: number;
  smtp_user?: string;
  from_email?: string;
  from_name?: string;
  smtp_status: 'VALID' | 'INVALID' | 'UNTESTED';
  whatsapp_sender_channel?: string;

  // Verification Status
  whatsapp_verified?: boolean;
  email_verified?: boolean;
  whatsapp_verified_at?: string | null;
  email_verified_at?: string | null;

  // Server / LAN Connection Config
  server_ip?: string;
  port?: number;
  connection_status?: 'PENDING' | 'ACTIVE' | 'OFFLINE';
  last_heartbeat_at?: string | null;
}

// --- Sub-components ---
const ConnectionResultView = ({ result, port }: { result: any, port: number }) => {
  if (!result) return null;
  return (
    <div className="bg-white p-4 rounded-xl border border-surface-200 mt-3 text-xs space-y-3 w-full col-span-2">
      <div className="flex justify-between items-center">
        <span className="text-surface-500 font-bold uppercase text-[9px]">IP Reachability</span>
        <span className={result.ip_status === 'Reachable' ? 'text-emerald-600 font-bold' : 'text-red-500 font-bold'}>{result.ip_status === 'Reachable' ? '✅ Reachable' : '❌ Not Reachable'}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-surface-500 font-bold uppercase text-[9px]">Port ({port})</span>
        <span className={result.port_status === 'Open' ? 'text-emerald-600 font-bold' : 'text-red-500 font-bold'}>{result.port_status === 'Open' ? '✅ Open' : '❌ Closed'}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-surface-500 font-bold uppercase text-[9px]">Service Health</span>
        <span className={result.service_status === 'Running' ? 'text-emerald-600 font-bold' : 'text-red-500 font-bold'}>{result.service_status === 'Running' ? '✅ Running' : '❌ Not Running'}</span>
      </div>
      <div className="mt-2 pt-3 border-t border-surface-100 text-[10px] text-surface-600 font-medium">
        {result.message}
      </div>
    </div>
  )
}


const KeyRow = memo(({ item, appName, onCopy, onExtend, onRevoke, onRotate, onSettings, copiedId }: {
  item: Key;
  appName: string;
  onCopy: (text: string, id: string) => void;
  onExtend: (id: string, expiry: string) => void;
  onRevoke: (id: string) => void;
  onRotate: (id: string) => void;
  onSettings: (item: Key) => void;
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
          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
            item.connection_status === 'ACTIVE' ? 'bg-blue-100 text-blue-700' : 
            item.connection_status === 'OFFLINE' ? 'bg-red-100 text-red-700' : 'bg-surface-200 text-surface-600'
          }`}>
            {item.connection_status || 'PENDING'}
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
          <button onClick={() => onSettings(item)}
            className="text-[11px] font-medium text-surface-500 hover:text-brand-600 hover:underline flex items-center gap-1">
            <Settings className="w-3 h-3" /> Settings
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

// --- Verification Status Badge ---
type VerifyStatus = 'idle' | 'testing' | 'success' | 'failed'

const VerifyBadge = ({ status, verifiedAt }: { status: VerifyStatus | boolean | undefined, verifiedAt?: string | null }) => {
  if (status === true || status === 'success') return (
    <span className="flex items-center gap-1 text-[10px] font-bold text-emerald-600">
      <CheckCircle2 className="w-3 h-3" /> Verified{verifiedAt ? ` · ${format(new Date(verifiedAt), 'MMM d')}` : ''}
    </span>
  )
  if (status === false || status === 'failed') return (
    <span className="flex items-center gap-1 text-[10px] font-bold text-red-500">
      <XCircle className="w-3 h-3" /> Failed
    </span>
  )
  if (status === 'testing') return (
    <span className="flex items-center gap-1 text-[10px] font-bold text-amber-500">
      <Loader2 className="w-3 h-3 animate-spin" /> Testing…
    </span>
  )
  return (
    <span className="flex items-center gap-1 text-[10px] font-bold text-surface-400">
      <CircleDot className="w-3 h-3" /> Not Tested
    </span>
  )
}

// --- Wizard Step Indicator ---
const StepIndicator = ({ current, total, labels }: { current: number, total: number, labels: string[] }) => (
  <div className="flex items-center gap-0 mb-6">
    {labels.map((label, i) => {
      const step = i + 1
      const done = current > step
      const active = current === step
      return (
        <div key={i} className="flex items-center flex-1 last:flex-none">
          <div className="flex flex-col items-center gap-1">
            <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-all ${
              done ? 'bg-brand-600 border-brand-600 text-white' :
              active ? 'bg-white border-brand-600 text-brand-600' :
              'bg-white border-surface-200 text-surface-400'
            }`}>
              {done ? <Check className="w-3.5 h-3.5" /> : step}
            </div>
            <span className={`text-[9px] font-bold uppercase tracking-wider whitespace-nowrap ${
              active ? 'text-brand-600' : done ? 'text-surface-500' : 'text-surface-300'
            }`}>{label}</span>
          </div>
          {i < total - 1 && (
            <div className={`flex-1 h-0.5 mx-1 mb-4 transition-all ${ done ? 'bg-brand-400' : 'bg-surface-200'}`} />
          )}
        </div>
      )
    })}
  </div>
)

// --- CreateKeyDrawer (4-Step Wizard) ---
const CreateKeyDrawer = memo(({ isOpen, onClose, apps, onSuccess }: {
  isOpen: boolean;
  onClose: () => void;
  apps: App[];
  onSuccess: (rawKeys: string[]) => void;
}) => {
  const toast = useToast()
  const [step, setStep] = useState(1)
  const [saving, setSaving] = useState(false)
  const [lastSubmitted, setLastSubmitted] = useState<string | null>(null)

  // WA test state
  const [waTestStatus, setWaTestStatus] = useState<VerifyStatus>('idle')
  const [waTestPhone, setWaTestPhone] = useState('')
  // SMTP test state
  const [smtpTestStatus, setSmtpTestStatus] = useState<VerifyStatus>('idle')
  const [smtpTestEmail, setSmtpTestEmail] = useState('')

  // LAN/Server test state
  const [testingConnection, setTestingConnection] = useState(false)
  const [testResult, setTestResult] = useState<any>(null)
  const [ipDetected, setIpDetected] = useState(false)
  const [runningPort, setRunningPort] = useState<number | null>(null)

  useEffect(() => {
    if (isOpen) {
      api.get('/settings/detect-ip').then(r => setRunningPort(r.data.port)).catch(() => {})
    }
  }, [isOpen])

  const isValidIP = (ip: string) => {
    if (!ip) return false
    if (ip.toLowerCase() === 'localhost') return true
    const ipv4Regex = /^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.){3}(25[0-5]|(2[0-4]|1\d|[1-9]|)\d)$/
    return ipv4Regex.test(ip)
  }

  const initialForm = {
    app_id: '', company_name: '',
    expiry_date: format(new Date(new Date().setFullYear(new Date().getFullYear() + 1)), 'yyyy-MM-dd'),
    count: 1, mobile_number: '', address: '',
    labels: [] as CustomLabel[],
    bill_header_1: '', bill_header_2: '', bill_header_3: '', bill_footer: '',
    logo_url: '', signup_image_url: '',
    notification_type: 'both' as 'whatsapp' | 'email' | 'both',
    smtp_enabled: false,
    SMTP_HOST: 'smtp.gmail.com', SMTP_PORT: 587,
    SMTP_USER: 'ticketemailsender01@gmail.com', SMTP_PASS: 'quzknqtlseeeeqdw',
    EMAILS_FROM_EMAIL: 'ticketemailsender01@gmail.com', EMAILS_FROM_NAME: 'Weighment',
    whatsapp_sender_channel: '919893224689:5',
    server_ip: '',
    port: 8000 as number | undefined
  }
  const [form, setForm] = useState(initialForm)

  const handleDetectIP = async () => {
    try {
      const { data } = await api.get('/settings/detect-ip')
      setForm(f => ({ ...f, server_ip: data.server_ip, port: data.port }))
      setIpDetected(true)
      setTimeout(() => setIpDetected(false), 3000)
      toast.success('Local Server IP detected!')
    } catch (err: any) {
      toast.error('Could not detect server IP automatically.')
    }
  }

  const handleTestConnection = async () => {
    const { server_ip, port } = form
    if (!isValidIP(server_ip)) {
      toast.error('Invalid IP address format.')
      return
    }

    setTestingConnection(true)
    setTestResult(null)
    try {
      const { data } = await api.get(`/settings/test-connection?ip=${server_ip}&port=${port}`)
      setTestResult(data)
    } catch (err: any) {
      toast.error('Failed to perform connection test.')
    } finally {
      setTestingConnection(false)
    }
  }

  const copyServerURL = (ip: string, port: number) => {
    const url = `http://${ip}:${port}`
    navigator.clipboard.writeText(url)
    toast.success('Server URL copied to clipboard!')
  }

  const resetAll = () => {
    setStep(1); setForm(initialForm)
    setWaTestStatus('idle'); setWaTestPhone('')
    setSmtpTestStatus('idle'); setSmtpTestEmail('')
    setLastSubmitted(null)
  }

  const handleClose = () => { resetAll(); onClose() }

  const isDuplicate = useMemo(() => {
    if (!lastSubmitted) return false
    return JSON.stringify({ app_id: form.app_id, company: form.company_name }) === lastSubmitted
  }, [form.app_id, form.company_name, lastSubmitted])

  // Step 3: Test WhatsApp (stateless — no key exists yet)
  const handleTestWA = async () => {
    if (!form.whatsapp_sender_channel || !waTestPhone) {
      toast.error('Enter both the Sender Channel and a Test Phone Number.')
      return
    }
    setWaTestStatus('testing')
    try {
      const { data } = await api.post('/apps/comms/test-whatsapp', {
        whatsapp_sender_channel: form.whatsapp_sender_channel,
        test_receiver_phone: waTestPhone
      })
      setWaTestStatus(data.status === 'success' ? 'success' : 'failed')
      if (data.status === 'success') toast.success(data.message)
      else toast.error(data.reason || 'WhatsApp test failed.')
    } catch (err: any) {
      setWaTestStatus('failed')
      toast.error(err.response?.data?.detail || 'WhatsApp test failed.')
    }
  }

  // Step 3: Test SMTP (stateless)
  const handleTestSMTP = async () => {
    if (!smtpTestEmail) { toast.error('Enter a test receiver email.'); return }
    setSmtpTestStatus('testing')
    try {
      const { data } = await api.post('/apps/comms/test-smtp', {
        smtp_host: form.SMTP_HOST, smtp_port: form.SMTP_PORT,
        smtp_user: form.SMTP_USER, smtp_password: form.SMTP_PASS,
        from_email: form.EMAILS_FROM_EMAIL, from_name: form.EMAILS_FROM_NAME,
        test_receiver_email: smtpTestEmail
      })
      setSmtpTestStatus(data.status === 'success' ? 'success' : 'failed')
      if (data.status === 'success') toast.success(data.message)
      else toast.error(data.reason || 'SMTP test failed.')
    } catch (err: any) {
      setSmtpTestStatus('failed')
      toast.error(err.response?.data?.detail || 'SMTP test failed.')
    }
  }

  const handleSubmit = async () => {
    if (!form.app_id) { toast.error('Select an application first.'); return }
    if (!isValidIP(form.server_ip)) { toast.error('Valid Server IP (IPv4 or localhost) is required.'); return }
    if (!form.port || form.port < 1024 || form.port > 65535) { toast.error('Server Port must be between 1024 and 65535.'); return }

    setSaving(true)
    try {
      const payload = { ...form, expiry_date: new Date(form.expiry_date).toISOString() }
      if (!payload.SMTP_PASS) delete (payload as any).SMTP_PASS
      const { data } = await api.post('/apps/keys', payload)
      setLastSubmitted(JSON.stringify({ app_id: form.app_id, company: form.company_name }))
      onSuccess(data.map((d: any) => d.raw_activation_key))
      toast.success(`Successfully generated ${form.count} activation key(s)!`)
      handleClose()
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Generation failed')
    } finally {
      setSaving(false)
    }
  }

  const STEPS = ['Identity', 'Config', 'Comms', 'Generate']

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={handleClose} className="fixed inset-0 z-40 bg-black/30" />
          <motion.div initial={{ x: '100%', opacity: 0.5 }} animate={{ x: 0, opacity: 1 }} exit={{ x: '100%', opacity: 0.5 }} transition={{ type: 'tween', ease: 'easeOut', duration: 0.25 }} className="fixed inset-y-0 right-0 z-50 w-full max-w-xl glass border-l border-white/20 flex flex-col">
            {/* Header */}
            <div className="px-6 pt-5 pb-4 border-b border-white/30">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold text-surface-900">Generate Activation Key</h2>
                <button onClick={handleClose} className="p-1.5 rounded-lg hover:bg-surface-100 text-surface-500"><X className="w-4 h-4" /></button>
              </div>
              <StepIndicator current={step} total={4} labels={STEPS} />
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto p-6">
              <AnimatePresence mode="wait">

                {/* ── Step 1: Company Identity ── */}
                {step === 1 && (
                  <motion.div key="s1" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="space-y-5">
                    <div className="bg-brand-50/50 p-4 rounded-2xl border border-brand-100">
                      <label className="form-label text-brand-700">Application *</label>
                      <select required value={form.app_id} onChange={(e) => setForm({ ...form, app_id: e.target.value })} className="form-input bg-white">
                        <option value="">Select application…</option>
                        {apps.map((a) => <option key={a.id} value={a.id}>{a.app_name} ({a.app_id})</option>)}
                      </select>
                    </div>
                    <div>
                      <h3 className="text-[10px] font-bold text-surface-400 uppercase tracking-[0.2em] pl-1 mb-2">Company Identity</h3>
                      <div className="h-px bg-surface-100 w-full mb-4" />
                      <div className="grid grid-cols-2 gap-4">
                        <div className="col-span-2">
                          <label className="text-[10px] font-bold text-surface-500 uppercase ml-1">Company Name *</label>
                          <input required value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })} className="form-input font-bold" />
                        </div>
                        <ImageUpload label="Company Logo" value={form.logo_url} target="logo" appId={form.app_id} onChange={(url) => setForm(f => ({ ...f, logo_url: url }))} />
                        <ImageUpload label="Sign-Up Image" value={form.signup_image_url} target="signup" appId={form.app_id} onChange={(url) => setForm(f => ({ ...f, signup_image_url: url }))} />
                      </div>
                    </div>
                    <div>
                      <h3 className="text-[10px] font-bold text-surface-400 uppercase tracking-[0.2em] pl-1 mb-2">Contact Details</h3>
                      <div className="h-px bg-surface-100 w-full mb-4" />
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="text-[10px] font-bold text-surface-500 uppercase ml-1">Mobile Number</label>
                          <input value={form.mobile_number} onChange={(e) => setForm({ ...form, mobile_number: e.target.value })} placeholder="91XXXXXXXXXX" className="form-input" />
                        </div>
                        <div className="col-span-2">
                          <label className="text-[10px] font-bold text-surface-500 uppercase ml-1">Office Address</label>
                          <textarea rows={2} value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} placeholder="Full company address..." className="form-input resize-none" />
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* ── Step 2: Software Config ── */}
                {step === 2 && (
                  <motion.div key="s2" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="space-y-5">
                    <div>
                      <h3 className="text-[10px] font-bold text-surface-400 uppercase tracking-[0.2em] pl-1 mb-2">Custom Fields / Labels</h3>
                      <div className="h-px bg-surface-100 w-full mb-3" />
                      <div className="space-y-3">
                        <div className="flex justify-end">
                          <button type="button" onClick={() => setForm(f => ({ ...f, labels: [...f.labels, { name: '', type: 'text', required: false }] }))} className="text-[10px] font-bold text-brand-600 hover:text-brand-700 flex items-center gap-1">
                            <Plus className="w-3 h-3" /> Add Field
                          </button>
                        </div>
                        {form.labels.length === 0 && (
                          <div className="text-[10px] text-surface-400 text-center py-4 border-2 border-dashed border-surface-200 rounded-xl">No custom fields added.</div>
                        )}
                        {form.labels.map((field, idx) => (
                          <div key={idx} className="flex items-center gap-2">
                            <input required value={field.name} onChange={(e) => { const l = [...form.labels]; l[idx].name = e.target.value; setForm({ ...form, labels: l }) }} placeholder="Field Name" className="form-input text-xs py-1.5 flex-1" />
                            <select value={field.type} onChange={(e) => { const l = [...form.labels]; l[idx].type = e.target.value as any; setForm({ ...form, labels: l }) }} className="form-input text-[10px] py-1.5 w-24 bg-white">
                              <option value="text">Text</option>
                              <option value="alphanumeric">Alphanumeric</option>
                              <option value="alphabetical">Letters</option>
                              <option value="numeric">Numbers</option>
                              <option value="date">Date</option>
                            </select>
                            <label className="flex items-center gap-1 cursor-pointer text-[9px] font-bold text-surface-500 uppercase">
                              <input type="checkbox" checked={field.required} onChange={(e) => { const l = [...form.labels]; l[idx].required = e.target.checked; setForm({ ...form, labels: l }) }} className="w-3 h-3 accent-brand-500" /> Req
                            </label>
                            <button type="button" onClick={() => setForm(f => ({ ...f, labels: f.labels.filter((_, i) => i !== idx) }))} className="p-1.5 text-surface-300 hover:text-red-500"><Trash2 className="w-3.5 h-3.5" /></button>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div>
                      <h3 className="text-[10px] font-bold text-surface-400 uppercase tracking-[0.2em] pl-1 mb-2">Bill Layout</h3>
                      <div className="h-px bg-surface-100 w-full mb-3" />
                      <div className="grid grid-cols-2 gap-3">
                        <div><label className="text-[10px] font-bold text-surface-500 uppercase ml-1">Header 1</label><input value={form.bill_header_1} onChange={(e) => setForm({ ...form, bill_header_1: e.target.value })} className="form-input" /></div>
                        <div><label className="text-[10px] font-bold text-surface-500 uppercase ml-1">Header 2</label><input value={form.bill_header_2} onChange={(e) => setForm({ ...form, bill_header_2: e.target.value })} className="form-input" /></div>
                        <div><label className="text-[10px] font-bold text-surface-500 uppercase ml-1">Header 3</label><input value={form.bill_header_3} onChange={(e) => setForm({ ...form, bill_header_3: e.target.value })} className="form-input" /></div>
                        <div className="col-span-2"><label className="text-[10px] font-bold text-surface-500 uppercase ml-1">Bill Footer</label><input value={form.bill_footer} onChange={(e) => setForm({ ...form, bill_footer: e.target.value })} placeholder="Terms and conditions..." className="form-input" /></div>
                      </div>
                    </div>
                    <div>
                      <h3 className="text-[10px] font-bold text-surface-400 uppercase tracking-[0.2em] pl-1 mb-2">License Details</h3>
                      <div className="h-px bg-surface-100 w-full mb-3" />
                      <div className="grid grid-cols-2 gap-4">
                        <div><label className="text-[10px] font-bold text-surface-500 uppercase ml-1">Expiry Date *</label><input type="date" required value={form.expiry_date} onChange={(e) => setForm({ ...form, expiry_date: e.target.value })} className="form-input" /></div>
                        <div><label className="text-[10px] font-bold text-surface-500 uppercase ml-1">Key Count</label><input type="number" min={1} max={50} value={form.count} onChange={(e) => setForm({ ...form, count: parseInt(e.target.value) })} className="form-input" /></div>
                      </div>
                    </div>
                    <div>
                      <div className="flex items-center justify-between pl-1 mb-2">
                        <h3 className="text-[10px] font-bold text-surface-400 uppercase tracking-[0.2em]">LAN / Server Configuration</h3>
                      </div>
                      <div className="h-px bg-surface-100 w-full mb-3" />
                      <div className="bg-blue-50/50 border border-blue-200 rounded-lg p-3 flex gap-2">
                        <span className="text-blue-500 text-lg leading-none">ℹ️</span>
                        <p className="text-[10px] text-blue-700 font-medium">This configuration is for future deployment. The service will not be reachable until the client software is installed and running.</p>
                      </div>
                      <div className="bg-brand-50/30 p-4 rounded-2xl border border-brand-100 space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <div className="flex items-center justify-between mb-1">
                               <label className="text-[10px] font-bold text-surface-500 uppercase ml-1">Server IP (LAN)</label>
                               <div className="flex items-center gap-2">
                                  {ipDetected && <span className="text-[9px] font-bold text-emerald-600 flex items-center gap-0.5"><Check className="w-2.5 h-2.5" /> detected</span>}
                                  <button type="button" onClick={handleDetectIP} className="text-[9px] font-bold text-brand-600 hover:underline">Auto-Detect</button>
                               </div>
                            </div>
                            <input value={form.server_ip} onChange={(e) => setForm({ ...form, server_ip: e.target.value })} placeholder="192.168.1.XX" className="form-input text-sm" />
                          </div>
                          <div>
                            <label className="text-[10px] font-bold text-surface-500 uppercase ml-1 block mb-1">Server Port</label>
                            <input type="number" min={1024} max={65535} value={form.port} onChange={(e) => setForm({ ...form, port: parseInt(e.target.value) || undefined })} className="form-input text-sm" />
                          </div>
                        </div>
                        {runningPort && form.port !== runningPort && (
                           <div className="bg-amber-50 border border-amber-200 rounded-lg p-2.5 flex items-start gap-2 mt-4">
                              <RefreshCw className="w-3.5 h-3.5 text-amber-600 mt-0.5" />
                              <p className="text-[10px] text-amber-700 font-medium leading-relaxed">
                                 Setting the port to <strong>{form.port}</strong> requires a manual server restart for the new configuration to take effect.
                              </p>
                           </div>
                        )}
                        <div className="flex items-center justify-between pt-1 border-t border-brand-100/50 mt-4">
                          <div className="flex items-center gap-3">
                            <button type="button" onClick={() => copyServerURL(form.server_ip, form.port || 8000)} className="text-[10px] font-bold text-brand-600 flex items-center gap-1 hover:text-brand-700">
                               <Copy className="w-3 h-3" /> Copy URL
                            </button>
                            <button type="button" onClick={handleTestConnection} disabled={testingConnection || !form.port} className="text-[10px] font-bold text-brand-600 flex items-center gap-1 hover:text-brand-700">
                               {testingConnection ? <Loader2 className="w-3 h-3 animate-spin" /> : <Wifi className="w-3 h-3" />}
                               Test Connection
                            </button>
                          </div>
                        </div>
                        <ConnectionResultView result={testResult} port={form.port || 8000} />
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* ── Step 3: Communication Setup + Test ── */}
                {step === 3 && (
                  <motion.div key="s3" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="space-y-6">

                    {/* WhatsApp */}
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <h3 className="text-[10px] font-bold text-surface-600 uppercase tracking-[0.2em] pl-1">WhatsApp Sender</h3>
                        <VerifyBadge status={waTestStatus} />
                      </div>
                      <div className="h-px bg-surface-100 w-full" />
                      <div className="bg-surface-50 p-4 rounded-2xl border border-surface-200 space-y-3">
                        <div>
                          <label className="text-[10px] font-bold text-surface-500 uppercase ml-1">Sender Channel ID</label>
                          <input
                            value={form.whatsapp_sender_channel}
                            onChange={(e) => { setForm({ ...form, whatsapp_sender_channel: e.target.value }); setWaTestStatus('idle') }}
                            placeholder="91XXXXXXXXXX:ID"
                            className={`form-input mt-1 ${ form.whatsapp_sender_channel && !form.whatsapp_sender_channel.includes(':') ? 'border-amber-400' : '' }`}
                          />
                          {form.whatsapp_sender_channel && !form.whatsapp_sender_channel.includes(':') && (
                            <p className="text-[9px] text-amber-600 mt-1 font-bold">Required format: number:id (missing ":")</p>
                          )}
                        </div>
                        <div>
                          <label className="text-[10px] font-bold text-surface-500 uppercase ml-1">Test Receiver Phone <span className="text-surface-300 normal-case font-normal">(your number)</span></label>
                          <div className="flex gap-2 mt-1">
                            <input value={waTestPhone} onChange={(e) => setWaTestPhone(e.target.value)} placeholder="91XXXXXXXXXX" className="form-input flex-1" />
                            <button type="button" onClick={handleTestWA} disabled={waTestStatus === 'testing'} className="btn-secondary px-3 text-[10px] font-bold whitespace-nowrap flex items-center gap-1.5">
                              {waTestStatus === 'testing' ? <Loader2 className="w-3 h-3 animate-spin" /> : <Wifi className="w-3 h-3" />}
                              Test WhatsApp Connection
                            </button>
                          </div>
                        </div>
                        <p className="text-[9px] text-surface-400 italic">This will send a test message to your number to verify the channel. Click 'Next' to continue without testing.</p>
                      </div>
                    </div>

                    {/* Email SMTP */}
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <h3 className="text-[10px] font-bold text-surface-600 uppercase tracking-[0.2em] pl-1">Email (SMTP)</h3>
                          <label className="relative inline-flex items-center cursor-pointer">
                            <input type="checkbox" checked={form.smtp_enabled} onChange={(e) => setForm({ ...form, smtp_enabled: e.target.checked })} className="sr-only peer" />
                            <div className="w-8 h-4 bg-surface-200 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-brand-600 shadow-inner"></div>
                            <span className="ml-2 text-[10px] font-bold text-surface-500 uppercase">Enable</span>
                          </label>
                        </div>
                        {form.smtp_enabled && <VerifyBadge status={smtpTestStatus} />}
                      </div>
                      <div className="h-px bg-surface-100 w-full" />

                      {form.smtp_enabled && (
                        <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="bg-surface-50 p-4 rounded-2xl border border-surface-200 space-y-3 overflow-hidden">
                          <div className="grid grid-cols-3 gap-3">
                            <div className="col-span-2"><label className="text-[10px] font-bold text-surface-400 uppercase">SMTP Host</label><input value={form.SMTP_HOST} onChange={(e) => { setForm({ ...form, SMTP_HOST: e.target.value }); setSmtpTestStatus('idle') }} className="form-input text-sm" /></div>
                            <div><label className="text-[10px] font-bold text-surface-400 uppercase">Port</label><input type="number" value={form.SMTP_PORT} onChange={(e) => setForm({ ...form, SMTP_PORT: parseInt(e.target.value) })} className="form-input text-sm" /></div>
                          </div>
                          <div className="grid grid-cols-2 gap-3">
                            <div><label className="text-[10px] font-bold text-surface-400 uppercase">SMTP User</label><input value={form.SMTP_USER} onChange={(e) => setForm({ ...form, SMTP_USER: e.target.value })} placeholder="user@domain.com" className="form-input text-sm" /></div>
                            <div><label className="text-[10px] font-bold text-surface-400 uppercase">SMTP Pass <span className="text-red-500">*</span></label><input type="password" required={form.smtp_enabled} value={form.SMTP_PASS} onChange={(e) => { setForm({ ...form, SMTP_PASS: e.target.value }); setSmtpTestStatus('idle') }} className={`form-input text-sm ${form.smtp_enabled && !form.SMTP_PASS ? 'border-red-200' : ''}`} /></div>
                          </div>
                          <div className="grid grid-cols-2 gap-3">
                            <div><label className="text-[10px] font-bold text-surface-400 uppercase">From Email</label><input value={form.EMAILS_FROM_EMAIL} onChange={(e) => setForm({ ...form, EMAILS_FROM_EMAIL: e.target.value })} placeholder="noreply@domain.com" className="form-input text-sm" /></div>
                            <div><label className="text-[10px] font-bold text-surface-400 uppercase">From Name</label><input value={form.EMAILS_FROM_NAME} onChange={(e) => setForm({ ...form, EMAILS_FROM_NAME: e.target.value })} placeholder="Billing Dept" className="form-input text-sm" /></div>
                          </div>
                          <div>
                            <label className="text-[10px] font-bold text-surface-500 uppercase ml-1">Test Receiver Email <span className="text-surface-300 normal-case font-normal">(your email)</span></label>
                            <div className="flex gap-2 mt-1">
                              <input value={smtpTestEmail} onChange={(e) => setSmtpTestEmail(e.target.value)} placeholder="admin@yourcompany.com" className="form-input flex-1 text-sm" />
                              <button type="button" onClick={handleTestSMTP} disabled={smtpTestStatus === 'testing'} className="btn-secondary px-3 text-[10px] font-bold whitespace-nowrap flex items-center gap-1.5">
                                {smtpTestStatus === 'testing' ? <Loader2 className="w-3 h-3 animate-spin" /> : <ShieldCheck className="w-3 h-3" />}
                                Test Email Connection
                              </button>
                            </div>
                          </div>
                          <p className="text-[9px] text-surface-400 italic">This will send a test message to your email to verify configuration. Click 'Next' to continue without testing.</p>
                        </motion.div>
                      )}

                      {/* Notification channel selector */}
                      <div className="mt-2">
                        <label className="text-[10px] font-bold text-surface-500 uppercase ml-1 block mb-2">Notification Channels to Enable</label>
                        <div className="flex gap-2">
                          {['both', 'whatsapp', 'email'].map((type) => (
                            <button key={type} type="button" onClick={() => setForm({ ...form, notification_type: type as any })}
                              className={`flex-1 py-1.5 px-3 rounded-lg text-[10px] font-bold capitalize transition-all border ${ form.notification_type === type ? 'bg-brand-600 border-brand-600 text-white' : 'bg-white border-surface-200 text-surface-600'}`}>
                              {type}
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* ── Step 4: Review & Generate ── */}
                {step === 4 && (
                  <motion.div key="s4" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="space-y-4">
                    <div className="bg-brand-50/50 p-5 rounded-2xl border border-brand-100 space-y-3">
                      <h3 className="text-sm font-bold text-surface-900">Review Configuration</h3>
                      <div className="space-y-2 text-xs">
                        <div className="flex justify-between"><span className="text-surface-500">Company</span><span className="font-bold text-surface-800">{form.company_name || '—'}</span></div>
                        <div className="flex justify-between"><span className="text-surface-500">Application</span><span className="font-bold text-surface-800">{apps.find(a => a.id === form.app_id)?.app_name || '—'}</span></div>
                        <div className="flex justify-between"><span className="text-surface-500">Expiry</span><span className="font-bold text-surface-800">{form.expiry_date}</span></div>
                        <div className="flex justify-between"><span className="text-surface-500">Keys to Generate</span><span className="font-bold text-surface-800">{form.count}</span></div>
                        <div className="flex justify-between"><span className="text-surface-500">Custom Fields</span><span className="font-bold text-surface-800">{form.labels.length} fields</span></div>
                        <div className="h-px bg-brand-100" />
                        <div className="flex justify-between items-center">
                          <span className="text-surface-500">WhatsApp Channel</span>
                          <span className="flex items-center gap-2">
                            <span className="font-mono text-surface-800">{form.whatsapp_sender_channel || <span className="text-surface-400 italic">Not set</span>}</span>
                            <VerifyBadge status={waTestStatus} />
                          </span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-surface-500">SMTP Config</span>
                          <span className="flex items-center gap-2">
                            <span className="font-bold text-surface-800">{form.smtp_enabled ? 'Enabled' : 'Disabled'}</span>
                            {form.smtp_enabled && <VerifyBadge status={smtpTestStatus} />}
                          </span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-surface-500">Notifications</span>
                          <span className="font-bold text-surface-800 capitalize">{form.notification_type}</span>
                        </div>
                        <div className="h-px bg-brand-100" />
                        <div className="flex justify-between">
                          <span className="text-surface-500">Server Address</span>
                          <span className="font-mono text-xs font-bold text-brand-700">http://{form.server_ip || '—'}:{form.port}</span>
                        </div>
                      </div>
                    </div>

                    <div className="bg-amber-50 border border-amber-200 rounded-xl p-3">
                      <p className="text-[10px] text-amber-700 font-bold">⚠️ The raw activation key will be shown ONE TIME after generation. Make sure to save it immediately.</p>
                    </div>
                  </motion.div>
                )}

              </AnimatePresence>
            </div>

            {/* Footer Navigation */}
            <div className="px-6 py-4 border-t border-white/30 flex gap-3">
              {step > 1 ? (
                <button type="button" onClick={() => setStep(s => s - 1)} className="btn-secondary flex items-center gap-2">
                  <ChevronLeft className="w-4 h-4" /> Back
                </button>
              ) : (
                <button type="button" onClick={handleClose} className="btn-secondary">Cancel</button>
              )}
              {step < 4 ? (
                <button type="button"
                  onClick={() => {
                    if (step === 1 && (!form.app_id || !form.company_name)) {
                      toast.error('Application and Company Name are required.')
                      return
                    }
                    setStep(s => s + 1)
                  }}
                  className="btn-primary flex-1 justify-center flex items-center gap-2">
                  Next <ChevronRight className="w-4 h-4" />
                </button>
              ) : (
                <button type="button" onClick={handleSubmit} disabled={saving || isDuplicate}
                  className={`btn-primary flex-1 justify-center flex items-center gap-2 ${ isDuplicate ? 'opacity-50 cursor-not-allowed grayscale' : '' }`}>
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <KeyRound className="w-4 h-4" />}
                  {saving ? 'Generating…' : isDuplicate ? 'Already Generated' : 'Generate License Keys'}
                </button>
              )}
            </div>
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

const KeySettingsDrawer = memo(({ isOpen, onClose, keyItem, onSuccess }: {
  isOpen: boolean;
  onClose: () => void;
  keyItem: Key | null;
  onSuccess: () => void;
}) => {
  const toast = useToast()
  const [saving, setSaving] = useState(false)
  const [testingSmtp, setTestingSmtp] = useState(false)
  const [testingWhatsapp, setTestingWhatsapp] = useState(false)
  const [form, setForm] = useState<any>(null)

  // Live verification state (overrides what came from DB after a test in this session)
  const [waStatus, setWaStatus] = useState<VerifyStatus | undefined>(undefined)
  const [emailStatus, setEmailStatus] = useState<VerifyStatus | undefined>(undefined)
  // Test receiver fields
  const [waTestPhone, setWaTestPhone] = useState('')
  const [smtpTestEmail, setSmtpTestEmail] = useState('')

  // LAN/Server test state
  const [testingConnection, setTestingConnection] = useState(false)
  const [testResult, setTestResult] = useState<any>(null)
  const [ipDetected, setIpDetected] = useState(false)
  const [runningPort, setRunningPort] = useState<number | null>(null)

  const isValidIP = (ip: string) => {
    if (!ip) return false
    if (ip.toLowerCase() === 'localhost') return true
    const ipv4Regex = /^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.){3}(25[0-5]|(2[0-4]|1\d|[1-9]|)\d)$/
    return ipv4Regex.test(ip)
  }

  const handleTestConnection = async () => {
    const { server_ip, port } = form
    if (!isValidIP(server_ip)) {
      toast.error('Invalid IP address format.')
      return
    }

    setTestingConnection(true)
    setTestResult(null)
    try {
      const { data } = await api.get(`/settings/test-connection?ip=${server_ip}&port=${port}`)
      setTestResult(data)
    } catch (err: any) {
      toast.error('Failed to perform connection test.')
    } finally {
      setTestingConnection(false)
    }
  }

  const copyServerURL = (ip: string, port: number) => {
    const url = `http://${ip}:${port}`
    navigator.clipboard.writeText(url)
    toast.success('Server URL copied to clipboard!')
  }

  useEffect(() => {
    if (isOpen) {
      api.get('/settings/detect-ip').then(r => setRunningPort(r.data.port)).catch(() => {})
    }
  }, [isOpen])

  useEffect(() => {
    if (isOpen && keyItem) {
      setForm({
        // Branding & Identity
        company_name: keyItem.company_name || '',
        logo_url: keyItem.logo_url || '',
        signup_image_url: keyItem.signup_image_url || '',
        
        // Contact Details
        email: keyItem.email || '',
        mobile_number: keyItem.mobile_number || '',
        address: keyItem.address || '',
        
        // Software Config / Labels
        labels: keyItem.labels ? [...keyItem.labels] : [],
        
        // Bill Layout
        bill_header_1: keyItem.bill_header_1 || '',
        bill_header_2: keyItem.bill_header_2 || '',
        bill_header_3: keyItem.bill_header_3 || '',
        bill_footer: keyItem.bill_footer || '',

        // Communication Settings
        smtp_enabled: keyItem.smtp_enabled,
        SMTP_HOST: (keyItem as any).smtp_host || 'smtp.gmail.com',
        SMTP_PORT: (keyItem as any).smtp_port || 587,
        SMTP_USER: (keyItem as any).smtp_user || '',
        SMTP_PASS: '',
        EMAILS_FROM_EMAIL: (keyItem as any).from_email || '',
        EMAILS_FROM_NAME: (keyItem as any).from_name || '',
        whatsapp_sender_channel: keyItem.whatsapp_sender_channel || '',
        server_ip: keyItem.server_ip || '',
        port: keyItem.port || 8000,
        notification_type: 'both' // Default for session
      })
      // Seed status from DB values
      setWaStatus(keyItem.whatsapp_verified ? 'success' : keyItem.whatsapp_verified === false && keyItem.whatsapp_sender_channel ? 'failed' : undefined)
      setEmailStatus(keyItem.email_verified ? 'success' : keyItem.email_verified === false && keyItem.smtp_enabled ? 'failed' : undefined)
      setWaTestPhone('')
      setSmtpTestEmail('')
    }
  }, [isOpen, keyItem])

  const handleTestSmtp = async () => {
    if (!keyItem) return
    setTestingSmtp(true)
    setEmailStatus('testing')
    try {
      const { data } = await api.post(`/apps/keys/${keyItem.id}/test-smtp`, {
        test_receiver_email: smtpTestEmail || undefined
      })
      if (data.status === 'success') {
        setEmailStatus('success')
        toast.success(data.message || 'Email configuration is VALID!')
      } else {
        setEmailStatus('failed')
        toast.error(data.reason || 'SMTP connection failed.')
      }
    } catch (err: any) {
      setEmailStatus('failed')
      toast.error(err.response?.data?.detail || 'SMTP test failed.')
    } finally {
      setTestingSmtp(false)
    }
  }

  const handleTestWhatsapp = async () => {
    if (!keyItem) return
    setTestingWhatsapp(true)
    setWaStatus('testing')
    try {
      const { data } = await api.post(`/apps/keys/${keyItem.id}/test-whatsapp`, {
        test_receiver_phone: waTestPhone || undefined
      })
      if (data.status === 'success') {
        setWaStatus('success')
        toast.success(data.message || 'WhatsApp channel is VALID!')
      } else {
        setWaStatus('failed')
        toast.error(data.reason || 'WhatsApp test failed.')
      }
    } catch (err: any) {
      setWaStatus('failed')
      toast.error(err.response?.data?.detail || 'Test failed.')
    } finally {
      setTestingWhatsapp(false)
    }
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!keyItem) return
    if (!isValidIP(form.server_ip)) { toast.error('Valid Server IP (IPv4 or localhost) is required.'); return }
    if (!form.port || form.port < 1024 || form.port > 65535) { toast.error('Server Port must be between 1024 and 65535.'); return }

    setSaving(true)
    try {
      const payload = { ...form }
      if (!payload.SMTP_PASS) delete payload.SMTP_PASS
      await api.patch(`/apps/keys/${keyItem.id}`, payload)
      toast.success('Settings updated successfully!')
      onSuccess()
      onClose()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Update failed')
    } finally {
      setSaving(false)
    }
  }

  if (!form) return null

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} className="fixed inset-0 z-40 bg-black/30" />
          <motion.div initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }} className="fixed inset-y-0 right-0 z-50 w-full max-w-xl glass border-l border-white/20 flex flex-col">
            <div className="flex items-center justify-between px-6 py-5 border-b border-white/30">
              <div>
                <h2 className="text-lg font-bold text-surface-900">License Settings</h2>
                <p className="text-[10px] text-surface-400 mt-0.5">{keyItem?.company_name} · v{keyItem?.current_version || 1}</p>
              </div>
              <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-surface-100 text-surface-500"><X className="w-4 h-4" /></button>
            </div>
            <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-8">

              {/* ── Section 1: Identity & Branding ── */}
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <CircleDot className="w-4 h-4 text-brand-600" />
                  <h3 className="text-sm font-bold text-surface-800">Identity & Branding</h3>
                </div>
                <div className="bg-surface-50/50 p-5 rounded-2xl border border-surface-200/60 space-y-5">
                  <div>
                    <label className="text-[10px] font-bold text-surface-500 uppercase ml-1">Company Name</label>
                    <input 
                      value={form.company_name} 
                      onChange={(e) => setForm({ ...form, company_name: e.target.value })} 
                      className="form-input mt-1 font-bold" 
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <ImageUpload label="Company Logo" value={form.logo_url} target="logo" appId={keyItem?.app_id || ''} onChange={(url: string) => setForm((f: any) => ({ ...f, logo_url: url }))} />
                    <ImageUpload label="Sign-Up Image" value={form.signup_image_url} target="signup" appId={keyItem?.app_id || ''} onChange={(url: string) => setForm((f: any) => ({ ...f, signup_image_url: url }))} />
                  </div>
                </div>
              </div>

              {/* ── Section 2: Contact Details ── */}
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <CircleDot className="w-4 h-4 text-brand-600" />
                  <h3 className="text-sm font-bold text-surface-800">Contact Info</h3>
                </div>
                <div className="bg-surface-50/50 p-5 rounded-2xl border border-surface-200/60 space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-[10px] font-bold text-surface-500 uppercase ml-1">Email <span className="normal-case font-normal text-surface-400">(for receipts)</span></label>
                      <input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="customer@email.com" className="form-input mt-1" />
                    </div>
                    <div>
                      <label className="text-[10px] font-bold text-surface-500 uppercase ml-1">Mobile Number</label>
                      <input value={form.mobile_number} onChange={(e) => setForm({ ...form, mobile_number: e.target.value })} placeholder="91XXXXXXXXXX" className="form-input mt-1" />
                    </div>
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-surface-500 uppercase ml-1">Office Address</label>
                    <textarea rows={2} value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} className="form-input mt-1 resize-none" />
                  </div>
                </div>
              </div>

              {/* ── Section 3: Custom Fields (Labels) ── */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CircleDot className="w-4 h-4 text-brand-600" />
                    <h3 className="text-sm font-bold text-surface-800">Custom Fields (Labels)</h3>
                  </div>
                  <button type="button" onClick={() => setForm((f: any) => ({ ...f, labels: [...f.labels, { name: '', type: 'text', required: false }] }))} className="text-[10px] font-bold text-brand-600 flex items-center gap-1">
                    <Plus className="w-3 h-3" /> Add Field
                  </button>
                </div>
                <div className="bg-surface-50/50 p-5 rounded-2xl border border-surface-200/60 space-y-3">
                  {form.labels.length === 0 && (
                    <div className="text-[11px] text-surface-400 text-center py-6 border-2 border-dashed border-surface-200 rounded-xl">No custom labels configured.</div>
                  )}
                  {form.labels.map((field: CustomLabel, idx: number) => (
                    <div key={idx} className="flex items-center gap-2">
                      <input required value={field.name} onChange={(e) => { const l = [...form.labels]; l[idx].name = e.target.value; setForm({ ...form, labels: l }) }} placeholder="Field Name" className="form-input text-xs py-1.5 flex-1" />
                      <select value={field.type} onChange={(e) => { const l = [...form.labels]; l[idx].type = e.target.value as any; setForm({ ...form, labels: l }) }} className="form-input text-[10px] py-1.5 w-24 bg-white">
                        <option value="text">Text</option>
                        <option value="alphanumeric">Alphanumeric</option>
                        <option value="alphabetical">Letters</option>
                        <option value="numeric">Numbers</option>
                        <option value="date">Date</option>
                      </select>
                      <label className="flex items-center gap-1 cursor-pointer text-[9px] font-bold text-surface-500 uppercase">
                        <input type="checkbox" checked={field.required} onChange={(e) => { const l = [...form.labels]; l[idx].required = e.target.checked; setForm({ ...form, labels: l }) }} className="w-3 h-3 accent-brand-500" /> Req
                      </label>
                      <button type="button" onClick={() => setForm((f: any) => ({ ...f, labels: f.labels.filter((_: any, i: number) => i !== idx) }))} className="p-1.5 text-surface-300 hover:text-red-500"><Trash2 className="w-3.5 h-3.5" /></button>
                    </div>
                  ))}
                  <p className="text-[9px] text-surface-400 italic">Changing fields will increment the schema version for connected devices.</p>
                </div>
              </div>

              {/* ── Section 4: Bill Layout ── */}
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <CircleDot className="w-4 h-4 text-brand-600" />
                  <h3 className="text-sm font-bold text-surface-800">Bill Layout</h3>
                </div>
                <div className="bg-surface-50/50 p-5 rounded-2xl border border-surface-200/60 space-y-4">
                  <div className="grid grid-cols-1 gap-3">
                    <div><label className="text-[10px] font-bold text-surface-500 uppercase ml-1">Header 1</label><input value={form.bill_header_1} onChange={(e) => setForm({ ...form, bill_header_1: e.target.value })} className="form-input mt-1" /></div>
                    <div><label className="text-[10px] font-bold text-surface-500 uppercase ml-1">Header 2</label><input value={form.bill_header_2} onChange={(e) => setForm({ ...form, bill_header_2: e.target.value })} className="form-input mt-1" /></div>
                    <div><label className="text-[10px] font-bold text-surface-500 uppercase ml-1">Header 3</label><input value={form.bill_header_3} onChange={(e) => setForm({ ...form, bill_header_3: e.target.value })} className="form-input mt-1" /></div>
                    <div><label className="text-[10px] font-bold text-surface-500 uppercase ml-1">Bill Footer</label><input value={form.bill_footer} onChange={(e) => setForm({ ...form, bill_footer: e.target.value })} className="form-input mt-1" /></div>
                  </div>
                </div>
              </div>

              {/* ── Section 5: Communication Config ── */}
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <CircleDot className="w-4 h-4 text-brand-600" />
                  <h3 className="text-sm font-bold text-surface-800">Communication Config</h3>
                </div>
                
                {/* WhatsApp */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <p className="text-[10px] font-bold text-surface-500 uppercase tracking-widest ml-1">WhatsApp Config</p>
                    <VerifyBadge status={waStatus} verifiedAt={keyItem?.whatsapp_verified_at} />
                  </div>
                  <div className="bg-surface-50 p-4 rounded-2xl border border-surface-200 space-y-3">
                    <div>
                      <label className="text-[10px] font-bold text-surface-500 uppercase">Sender Channel ID</label>
                      <input
                        value={form.whatsapp_sender_channel}
                        onChange={(e) => { setForm({ ...form, whatsapp_sender_channel: e.target.value }); setWaStatus(undefined) }}
                        placeholder="91XXXXXXXXXX:ID"
                        className="form-input mt-1"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-bold text-surface-500 uppercase">Test Receiver Phone <span className="text-surface-300 normal-case font-normal">(your number)</span></label>
                      <div className="flex gap-2 mt-1">
                        <input value={waTestPhone} onChange={(e) => setWaTestPhone(e.target.value)} placeholder="91XXXXXXXXXX" className="form-input flex-1 text-sm" />
                        <button type="button" onClick={handleTestWhatsapp} disabled={testingWhatsapp} className="btn-secondary px-3 text-[10px] font-bold uppercase tracking-wider whitespace-nowrap flex items-center gap-1.5">
                          {testingWhatsapp ? <Loader2 className="w-3 h-3 animate-spin" /> : <Wifi className="w-3 h-3" />}
                          Test WA
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Email SMTP */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <p className="text-[10px] font-bold text-surface-500 uppercase tracking-widest ml-1">Email (SMTP)</p>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" checked={form.smtp_enabled}
                          onChange={(e) => { setForm({ ...form, smtp_enabled: e.target.checked }); setEmailStatus(undefined) }}
                          className="sr-only peer" />
                        <div className="w-8 h-4 bg-surface-200 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:bg-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-brand-600"></div>
                      </label>
                    </div>
                    {form.smtp_enabled && <VerifyBadge status={emailStatus} verifiedAt={keyItem?.email_verified_at} />}
                  </div>

                  {form.smtp_enabled && (
                    <div className="bg-surface-50 p-4 rounded-2xl border border-surface-200 space-y-4">
                      <div className="grid grid-cols-3 gap-3">
                        <div className="col-span-2">
                          <label className="text-[10px] font-bold text-surface-400 uppercase">SMTP Host</label>
                          <input value={form.SMTP_HOST} onChange={(e) => { setForm({ ...form, SMTP_HOST: e.target.value }); setEmailStatus(undefined) }} className="form-input text-sm" />
                        </div>
                        <div>
                          <label className="text-[10px] font-bold text-surface-400 uppercase">Port</label>
                          <input type="number" value={form.SMTP_PORT} onChange={(e) => setForm({ ...form, SMTP_PORT: parseInt(e.target.value) })} className="form-input text-sm" />
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="text-[10px] font-bold text-surface-400 uppercase">SMTP User</label>
                          <input value={form.SMTP_USER} onChange={(e) => { setForm({ ...form, SMTP_USER: e.target.value }); setEmailStatus(undefined) }} className="form-input text-sm" />
                        </div>
                        <div>
                          <label className="text-[10px] font-bold text-surface-400 uppercase">
                            SMTP Pass {form.smtp_enabled && <span className="text-red-500">*</span>}
                          </label>
                          <input type="password" required={form.smtp_enabled} value={form.SMTP_PASS}
                            onChange={(e) => { setForm({ ...form, SMTP_PASS: e.target.value }); setEmailStatus(undefined) }}
                            className={`form-input text-sm ${form.smtp_enabled && !form.SMTP_PASS ? 'border-red-200' : ''}`}
                            placeholder="Required to save"
                          />
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="text-[10px] font-bold text-surface-400 uppercase">From Email</label>
                          <input value={form.EMAILS_FROM_EMAIL} onChange={(e) => setForm({ ...form, EMAILS_FROM_EMAIL: e.target.value })} className="form-input text-sm" />
                        </div>
                        <div>
                          <label className="text-[10px] font-bold text-surface-400 uppercase">From Name</label>
                          <input value={form.EMAILS_FROM_NAME} onChange={(e) => setForm({ ...form, EMAILS_FROM_NAME: e.target.value })} className="form-input text-sm" />
                        </div>
                      </div>
                      <div>
                        <label className="text-[10px] font-bold text-surface-500 uppercase">Test Receiver Email <span className="text-surface-300 normal-case font-normal">(your email)</span></label>
                        <div className="flex gap-2 mt-1">
                          <input value={smtpTestEmail} onChange={(e) => setSmtpTestEmail(e.target.value)} placeholder="admin@domain.com" className="form-input text-sm flex-1" />
                          <button type="button" onClick={handleTestSmtp} disabled={testingSmtp} className="btn-secondary px-3 text-[10px] font-bold flex items-center gap-1.5 whitespace-nowrap">
                            {testingSmtp ? <Loader2 className="w-3 h-3 animate-spin" /> : <ShieldCheck className="w-3 h-3" />}
                            Test SMTP
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* LAN / Server Configuration */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <CircleDot className="w-4 h-4 text-brand-600" />
                    <h3 className="text-sm font-bold text-surface-800">LAN / Server Configuration</h3>
                  </div>
                  <div className="bg-brand-50/20 p-5 rounded-2xl border border-brand-100/50 space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="flex items-center justify-between mb-1">
                           <label className="text-[10px] font-bold text-surface-500 uppercase ml-1">Server IP (LAN)</label>
                           <div className="flex items-center gap-2">
                              {ipDetected && <span className="text-[9px] font-bold text-emerald-600 flex items-center gap-0.5"><Check className="w-2.5 h-2.5" /> detected</span>}
                              <button type="button" onClick={async () => {
                                try {
                                  const { data } = await api.get('/settings/detect-ip')
                                  setForm((f: any) => ({ ...f, server_ip: data.server_ip }))
                                  setIpDetected(true)
                                  setTimeout(() => setIpDetected(false), 3000)
                                  toast.success('Local Server IP detected!')
                                } catch {
                                  toast.error('Could not detect server IP.')
                                }
                              }} className="text-[9px] font-bold text-brand-600 hover:underline">Auto-Detect</button>
                           </div>
                        </div>
                        <input value={form.server_ip} onChange={(e) => setForm({ ...form, server_ip: e.target.value })} className="form-input text-sm" />
                      </div>
                      <div>
                        <label className="text-[10px] font-bold text-surface-500 uppercase ml-1 block mb-1">Server Port</label>
                        <input type="number" min={1024} max={65535} value={form.port} onChange={(e) => setForm({ ...form, port: parseInt(e.target.value) || 8000 })} className="form-input text-sm" />
                      </div>
                    </div>
                    {runningPort && form.port !== runningPort && (
                       <div className="bg-amber-50 border border-amber-200 rounded-lg p-2.5 flex items-start gap-2">
                          <RefreshCw className="w-3.5 h-3.5 text-amber-600 mt-0.5" />
                          <p className="text-[10px] text-amber-700 font-medium leading-relaxed">
                             Changing the port to <strong>{form.port}</strong> requires a manual server restart for the new configuration to take effect.
                          </p>
                       </div>
                    )}
                    <div className="flex items-center justify-between pt-1 border-t border-brand-100/50">
                        <div className="flex items-center gap-3">
                           <button type="button" onClick={() => copyServerURL(form.server_ip, form.port || 8000)} className="text-[10px] font-bold text-brand-600 flex items-center gap-1 hover:text-brand-700">
                              <Copy className="w-3 h-3" /> Copy URL
                           </button>
                           <button type="button" onClick={handleTestConnection} disabled={testingConnection || !form.port} className="text-[10px] font-bold text-brand-600 flex items-center gap-1 hover:text-brand-700">
                              {testingConnection ? <Loader2 className="w-3 h-3 animate-spin" /> : <Wifi className="w-3 h-3" />}
                              Test Connection
                           </button>
                        </div>
                        <ConnectionResultView result={testResult} port={form.port || 8000} />
                    </div>
                  </div>
                </div>
              </div>

              <div className="pt-6 flex gap-3 sticky bottom-0 bg-white/80 backdrop-blur-md pb-2">
                <button type="button" onClick={onClose} className="btn-secondary flex-1">Cancel</button>
                <button type="submit" disabled={saving} className="btn-primary flex-1 justify-center">
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Save Everything'}
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

export default function KeyManager() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [apps, setApps] = useState<App[]>([])
  const [allKeys, setAllKeys] = useState<Key[]>([])
  const [selectedAppId, setSelectedAppId] = useState<string>(searchParams.get('appId') || '')
  const [loadingKeys, setLoadingKeys] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [extendKey, setExtendKey] = useState<{ id: string, expiry: string } | null>(null)
  const [settingsKey, setSettingsKey] = useState<Key | null>(null)
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
      <KeySettingsDrawer isOpen={!!settingsKey} keyItem={settingsKey} onClose={() => setSettingsKey(null)} onSuccess={fetchAllKeys} />

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
                  onSettings={(item) => setSettingsKey(item)}
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
