import { useState, useEffect, useCallback, type FormEvent } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Plus, Users, Loader2, Search, X, Eye, EyeOff,
  UserCheck, UserX, Shield, ChevronDown, Copy, Check, KeyRound
} from 'lucide-react'
import api from '../services/api'
import { format } from 'date-fns'
import { useToast } from '../context/ToastContext'

// ── Types ──────────────────────────────────────────────────────────

interface Key {
  id: string
  token: string
  company_name: string
  status: string
}

interface Employee {
  id: string
  name: string
  username: string
  email: string | null
  key_id: string
  role: string
  is_active: boolean
  created_at: string
}

// ── Create Employee Drawer ─────────────────────────────────────────

function CreateEmployeeDrawer({
  isOpen,
  onClose,
  keys,
  onSuccess,
}: {
  isOpen: boolean
  onClose: () => void
  keys: Key[]
  onSuccess: () => void
}) {
  const toast = useToast()
  const [saving, setSaving] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [form, setForm] = useState(() => {
    try {
      const saved = localStorage.getItem('createEmployeeForm')
      if (saved) return JSON.parse(saved)
    } catch (e) {}
    return {
      name: '',
      username: '',
      email: '',
      password: '',
      key_id: '',
      role: 'operator',
    }
  })

  // Save to localStorage whenever form changes
  useEffect(() => {
    localStorage.setItem('createEmployeeForm', JSON.stringify(form))
  }, [form])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!form.key_id) { toast.error('Please select a company (license key)'); return }
    if (form.password.length < 6) { toast.error('Password must be at least 6 characters'); return }

    setSaving(true)
    try {
      await api.post('/employees', {
        name: form.name,
        username: form.username,
        email: form.email || undefined,
        password: form.password,
        key_id: form.key_id,
        role: form.role,
      })
      toast.success(`Employee '${form.username}' created successfully!`)
      localStorage.removeItem('createEmployeeForm')
      setForm({ name: '', username: '', email: '', password: '', key_id: '', role: 'operator' })
      onSuccess()
      onClose()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to create employee')
    } finally {
      setSaving(false)
    }
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-40 bg-black/30"
          />
          <motion.div
            initial={{ x: '100%', opacity: 0.5 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0.5 }}
            transition={{ type: 'tween', ease: 'easeOut', duration: 0.25 }}
            className="fixed inset-y-0 right-0 z-50 w-full max-w-md glass border-l border-white/20 flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-5 border-b border-white/30">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-600 to-indigo-600 flex items-center justify-center">
                  <Users className="w-4.5 h-4.5 text-white" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-surface-900">Add Employee</h2>
                  <p className="text-[11px] text-surface-500">Create operator or supervisor account</p>
                </div>
              </div>
              <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-surface-100 text-surface-500">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-5">

              {/* Tenant */}
              <div className="bg-brand-50/50 p-4 rounded-2xl border border-brand-100 space-y-3">
                <p className="text-xs font-bold text-brand-700 uppercase tracking-widest">Tenant Assignment</p>
                <div>
                  <label className="form-label">Company (License Key) *</label>
                  <div className="relative">
                    <select
                      required
                      value={form.key_id}
                      onChange={e => setForm({ ...form, key_id: e.target.value })}
                      className="form-input bg-white pr-8 appearance-none"
                    >
                      <option value="">Select company…</option>
                      {keys.map(k => (
                        <option key={k.id} value={k.token}>
                          {k.company_name} ({k.token.substring(0, 12)}…)
                        </option>
                      ))}
                    </select>
                    <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-400 pointer-events-none" />
                  </div>
                  <p className="text-[10px] text-surface-400 mt-1">
                    Employee will only access data for this company
                  </p>
                </div>
              </div>

              {/* Identity */}
              <div className="space-y-4">
                <p className="text-xs font-bold text-surface-400 uppercase tracking-widest pl-1">Employee Identity</p>
                <div>
                  <label className="form-label">Full Name *</label>
                  <input
                    required
                    value={form.name}
                    onChange={e => setForm({ ...form, name: e.target.value })}
                    placeholder="e.g. Ramesh Kumar"
                    className="form-input"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="form-label">Username *</label>
                    <input
                      required
                      value={form.username}
                      onChange={e => setForm({ ...form, username: e.target.value.toLowerCase().trim() })}
                      placeholder="e.g. ramesh01"
                      className="form-input font-mono"
                    />
                  </div>
                  <div>
                    <label className="form-label">Role *</label>
                    <div className="relative">
                      <select
                        value={form.role}
                        onChange={e => setForm({ ...form, role: e.target.value })}
                        className="form-input bg-white appearance-none pr-8"
                      >
                        <option value="operator">Operator</option>
                        <option value="supervisor">Supervisor</option>
                      </select>
                      <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-400 pointer-events-none" />
                    </div>
                  </div>
                </div>
                <div>
                  <label className="form-label">Email Address <span className="text-surface-400 font-normal">(optional, for email login)</span></label>
                  <input
                    type="email"
                    value={form.email}
                    onChange={e => setForm({ ...form, email: e.target.value })}
                    placeholder="e.g. ramesh@company.com"
                    className="form-input"
                  />
                </div>
              </div>

              {/* Password */}
              <div className="space-y-3">
                <p className="text-xs font-bold text-surface-400 uppercase tracking-widest pl-1">Security</p>
                <div>
                  <label className="form-label">Password *</label>
                  <div className="relative">
                    <input
                      required
                      type={showPassword ? 'text' : 'password'}
                      value={form.password}
                      onChange={e => setForm({ ...form, password: e.target.value })}
                      placeholder="Min. 6 characters"
                      className="form-input pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(v => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-surface-400 hover:text-surface-600"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                  <p className="text-[10px] text-surface-400 mt-1">
                    Stored securely using bcrypt. Never shown again after creation.
                  </p>
                </div>
              </div>

              {/* Warning banner */}
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 flex gap-2.5">
                <Shield className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
                <p className="text-[11px] text-amber-700 leading-relaxed">
                  <strong>Copy credentials now.</strong> The password is hashed immediately on save and cannot be retrieved later. Share them with the employee securely.
                </p>
              </div>

              {/* Actions */}
              <div className="flex gap-3 pt-2 sticky bottom-0 backdrop-blur-sm pb-2">
                <button type="button" onClick={onClose} className="btn-secondary flex-1">Cancel</button>
                <button type="submit" disabled={saving} className="btn-primary flex-1 justify-center">
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                  {saving ? 'Creating…' : 'Create Employee'}
                </button>
              </div>
            </form>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

// ── Employee Row ───────────────────────────────────────────────────

function EmployeeRow({
  emp,
  companyName,
  onDeactivate,
  onCopyId,
  copiedId,
}: {
  emp: Employee
  companyName: string
  onDeactivate: (id: string, name: string) => void
  onCopyId: (id: string) => void
  copiedId: string | null
}) {
  return (
    <tr className="hover:bg-surface-50/50 transition-colors">
      {/* Avatar + Name */}
      <td className="py-4">
        <div className="flex items-center gap-3">
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs ring-1 ${
            emp.is_active
              ? 'bg-brand-50 text-brand-600 ring-brand-100'
              : 'bg-surface-100 text-surface-400 ring-surface-200'
          }`}>
            {emp.name.charAt(0).toUpperCase()}
          </div>
          <div>
            <div className="text-sm font-bold text-surface-900">{emp.name}</div>
            <div className="text-[10px] text-surface-500">{companyName}</div>
          </div>
        </div>
      </td>

      {/* Username */}
      <td>
        <code className="text-xs font-mono text-surface-600 bg-surface-100 px-2 py-0.5 rounded-md">
          @{emp.username}
        </code>
      </td>

      {/* Email */}
      <td>
        <span className="text-xs text-surface-500">{emp.email || <span className="italic text-surface-300">—</span>}</span>
      </td>

      {/* Role */}
      <td>
        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
          emp.role === 'supervisor'
            ? 'bg-indigo-100 text-indigo-700'
            : 'bg-surface-100 text-surface-600'
        }`}>
          {emp.role}
        </span>
      </td>

      {/* Status */}
      <td>
        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
          emp.is_active
            ? 'bg-emerald-100 text-emerald-700'
            : 'bg-red-100 text-red-500'
        }`}>
          {emp.is_active ? 'Active' : 'Inactive'}
        </span>
      </td>

      {/* Created */}
      <td>
        <span className="text-xs text-surface-400">
          {format(new Date(emp.created_at), 'MMM dd, yyyy')}
        </span>
      </td>

      {/* Actions */}
      <td className="text-right">
        <div className="flex items-center justify-end gap-3 pr-2">
          <button
            onClick={() => onCopyId(emp.id)}
            title="Copy Employee ID"
            className="text-[11px] font-medium text-surface-400 hover:text-brand-600 flex items-center gap-1"
          >
            {copiedId === emp.id
              ? <Check className="w-3 h-3 text-emerald-500" />
              : <Copy className="w-3 h-3" />}
            ID
          </button>
          {emp.is_active && (
            <button
              onClick={() => onDeactivate(emp.id, emp.name)}
              className="text-[11px] font-medium text-red-500 hover:text-red-600 hover:underline flex items-center gap-1"
            >
              <UserX className="w-3 h-3" /> Deactivate
            </button>
          )}
        </div>
      </td>
    </tr>
  )
}

// ── Main Page ──────────────────────────────────────────────────────

export default function Employees() {
  const toast = useToast()

  const [keys, setKeys] = useState<Key[]>([])
  const [employees, setEmployees] = useState<Employee[]>([])
  const [selectedKeyToken, setSelectedKeyToken] = useState(() => localStorage.getItem('empDashboardKey') || '')
  const [loading, setLoading] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [search, setSearch] = useState(() => localStorage.getItem('empDashboardSearch') || '')
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [includeInactive, setIncludeInactive] = useState(() => localStorage.getItem('empDashboardInactive') === 'true')

  useEffect(() => {
    localStorage.setItem('empDashboardKey', selectedKeyToken)
    localStorage.setItem('empDashboardSearch', search)
    localStorage.setItem('empDashboardInactive', includeInactive.toString())
  }, [selectedKeyToken, search, includeInactive])

  // Load license keys (for tenant selector)
  useEffect(() => {
    api.get('/apps/keys/all')
      .then(r => setKeys(r.data.filter((k: Key) => k.status.toUpperCase() !== 'REVOKED')))
      .catch(() => toast.error('Could not load license keys'))
  }, [])

  // Load employees when tenant changes
  const loadEmployees = useCallback(async (keyToken: string) => {
    if (!keyToken) { setEmployees([]); return }
    setLoading(true)
    try {
      const { data } = await api.get('/employees', {
        params: { key_id: keyToken, include_inactive: includeInactive }
      })
      setEmployees(data)
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Could not load employees')
    } finally {
      setLoading(false)
    }
  }, [includeInactive, toast])

  useEffect(() => {
    loadEmployees(selectedKeyToken)
  }, [selectedKeyToken, loadEmployees])

  const handleDeactivate = useCallback(async (id: string, name: string) => {
    if (!window.confirm(`Deactivate ${name}? Their active sessions will stop working immediately.`)) return
    try {
      await api.patch(`/employees/${id}/deactivate`)
      toast.success(`${name} has been deactivated.`)
      loadEmployees(selectedKeyToken)
    } catch {
      toast.error('Could not deactivate employee.')
    }
  }, [selectedKeyToken, loadEmployees, toast])

  const handleCopyId = useCallback((id: string) => {
    navigator.clipboard.writeText(id)
    setCopiedId(id)
    toast.success('Employee ID copied!')
    setTimeout(() => setCopiedId(null), 2000)
  }, [toast])

  const selectedKey = keys.find(k => k.token === selectedKeyToken)

  const filtered = employees.filter(e => {
    if (!search) return true
    const q = search.toLowerCase()
    return (
      e.name.toLowerCase().includes(q) ||
      e.username.toLowerCase().includes(q) ||
      (e.email?.toLowerCase().includes(q) ?? false)
    )
  })

  const activeCount = employees.filter(e => e.is_active).length
  const inactiveCount = employees.filter(e => !e.is_active).length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Employees</h1>
          <p className="page-subtitle">Manage device operators and supervisors per company</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="btn-primary"
          id="create-employee-btn"
        >
          <Plus className="w-4 h-4" /> Add Employee
        </button>
      </div>

      {/* Create Drawer */}
      <CreateEmployeeDrawer
        isOpen={showCreate}
        onClose={() => setShowCreate(false)}
        keys={keys}
        onSuccess={() => loadEmployees(selectedKeyToken)}
      />

      {/* Tenant Selector + Filters */}
      <div className="glass rounded-xl border border-white/50 p-4 flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2 flex-1 min-w-[220px]">
          <KeyRound className="w-4 h-4 text-surface-400 shrink-0" />
          <div className="relative flex-1">
            <select
              value={selectedKeyToken}
              onChange={e => { setSelectedKeyToken(e.target.value); setSearch('') }}
              className="form-input bg-white text-sm appearance-none pr-8 w-full"
              id="tenant-select"
            >
              <option value="">Select a company…</option>
              {keys.map(k => (
                <option key={k.id} value={k.token}>
                  {k.company_name}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-400 pointer-events-none" />
          </div>
        </div>

        {selectedKeyToken && (
          <>
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-surface-400" />
              <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search name, username…"
                className="form-input pl-8 py-1.5 text-sm w-52"
              />
            </div>

            {/* Include inactive toggle */}
            <label className="flex items-center gap-2 text-sm text-surface-600 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={includeInactive}
                onChange={e => setIncludeInactive(e.target.checked)}
                className="w-3.5 h-3.5 accent-brand-500 rounded"
              />
              Show inactive
            </label>

            {/* Stats */}
            <div className="ml-auto flex items-center gap-3">
              <span className="flex items-center gap-1.5 text-xs text-emerald-600 font-medium">
                <UserCheck className="w-3.5 h-3.5" /> {activeCount} active
              </span>
              {inactiveCount > 0 && (
                <span className="flex items-center gap-1.5 text-xs text-surface-400 font-medium">
                  <UserX className="w-3.5 h-3.5" /> {inactiveCount} inactive
                </span>
              )}
            </div>
          </>
        )}
      </div>

      {/* Table */}
      <div className="glass rounded-2xl border border-white/50 overflow-hidden">
        {!selectedKeyToken ? (
          <div className="flex flex-col items-center justify-center py-20 text-surface-400 gap-3">
            <div className="w-14 h-14 bg-surface-100 rounded-2xl flex items-center justify-center">
              <Users className="w-7 h-7 text-surface-300" />
            </div>
            <p className="text-sm font-medium text-surface-500">Select a company to view its employees</p>
            <p className="text-xs text-surface-400">Employees are scoped per license key / tenant</p>
          </div>
        ) : loading ? (
          <div className="flex items-center justify-center py-20 text-surface-400">
            <Loader2 className="w-7 h-7 animate-spin" />
          </div>
        ) : filtered.length === 0 ? (
          <AnimatePresence mode="wait">
            <motion.div
              key="empty"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col items-center justify-center py-20 gap-3"
            >
              <div className="w-14 h-14 bg-surface-100 rounded-2xl flex items-center justify-center">
                <Users className="w-7 h-7 text-surface-300" />
              </div>
              <p className="text-sm font-medium text-surface-500">
                {search ? 'No employees match your search' : `No employees for ${selectedKey?.company_name}`}
              </p>
              {!search && (
                <button onClick={() => setShowCreate(true)} className="btn-primary text-sm">
                  <Plus className="w-3.5 h-3.5" /> Add First Employee
                </button>
              )}
            </motion.div>
          </AnimatePresence>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Employee</th>
                <th>Username</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Created</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              <AnimatePresence initial={false}>
                {filtered.map(emp => (
                  <EmployeeRow
                    key={emp.id}
                    emp={emp}
                    companyName={selectedKey?.company_name || ''}
                    onDeactivate={handleDeactivate}
                    onCopyId={handleCopyId}
                    copiedId={copiedId}
                  />
                ))}
              </AnimatePresence>
            </tbody>
          </table>
        )}
      </div>

      {/* Credential reminder */}
      {/* shown only when there are employees */}
      {selectedKeyToken && filtered.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex gap-3"
        >
          <Shield className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
          <div className="space-y-0.5">
            <p className="text-xs font-bold text-amber-800">Password Policy Reminder</p>
            <p className="text-[11px] text-amber-700 leading-relaxed">
              Employee passwords are hashed with bcrypt and cannot be retrieved. If an employee forgets their password,
              deactivate their account and create a new one. Login accepts both <strong>username</strong> and <strong>email</strong>.
            </p>
          </div>
        </motion.div>
      )}
    </div>
  )
}
