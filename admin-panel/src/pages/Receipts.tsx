/**
 * Receipts.tsx — Admin Data Viewer for Weighbridge Receipts
 *
 * Features:
 *  - Filterable, paginated table reading from /admin/receipts
 *  - Cascading dropdowns: App → Key (Customer) → Machine
 *  - Date range, sync status filter, search box
 *  - Sortable columns (date, gross weight)
 *  - Click-row → receipt detail slide-over panel
 *  - Loading skeletons, empty state, error handling
 *  - Framer Motion animations matching existing pages
 */

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ClipboardList, Search, Filter, RefreshCw, ChevronLeft, ChevronRight,
  CheckCircle2, Clock, X, ArrowUpDown, ChevronDown,
  Truck, Scale, Building2, AppWindow, Cpu, Calendar, Users
} from 'lucide-react'
import api from '../services/api'
import { format } from 'date-fns'
import { useToast } from '../context/ToastContext'

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

interface AppOption { id: string; app_id: string; app_name: string }
interface KeyOption  { id: string; token: string; company_name: string; status: string }
interface MachineOption { machine_id: string; name?: string }

interface Receipt {
  id: number
  local_id: number
  machine_id: string
  date_time: string
  
  // New Flexible Schema
  payload_json?: {
    data: Record<string, any>
  }
  image_urls?: string[]
  
  // Legacy fields (kept for backward compatibility during transition)
  gross_weight: number
  tare_weight: number
  net_weight: number
  rate?: number
  truck_no?: string
  custom_data: Record<string, any>
  
  is_synced: boolean
  sync_attempts: number
  last_error?: string
  whatsapp_status: string
  created_at: string
  app_name?: string
  app_id_str?: string
  company_name?: string
  key_status?: string
  user_id?: string
  employee_name?: string
  employee_username?: string
}

interface PaginatedResponse {
  total: number
  page: number
  limit: number
  pages: number
  items: Receipt[]
}

type SortField = 'created_at' | 'date_time' | 'gross_weight' | 'tare_weight'
type SortDir   = 'asc' | 'desc'

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────

function SyncBadge({ synced }: { synced: boolean }) {
  return synced ? (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-100">
      <CheckCircle2 className="w-3 h-3" /> Synced
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-100">
      <Clock className="w-3 h-3" /> Pending
    </span>
  )
}

function SkeletonRow() {
  return (
    <tr className="animate-pulse">
      {Array.from({ length: 8 }).map((_, i) => (
        <td key={i} className="px-4 py-3.5 border-t border-surface-100">
          <div className="h-4 bg-surface-100 rounded w-3/4" />
        </td>
      ))}
    </tr>
  )
}

// ─────────────────────────────────────────────
// Main component
// ─────────────────────────────────────────────

export default function Receipts() {
  const toast = useToast()

  // ── Filter state ──
  const [selectedApp, setSelectedApp]         = useState('')
  const [selectedKey, setSelectedKey]         = useState('')
  const [selectedMachine, setSelectedMachine] = useState('')
  const [dateFrom, setDateFrom]               = useState('')
  const [dateTo, setDateTo]                   = useState('')
  const [isSynced, setIsSynced]               = useState<'' | 'true' | 'false'>('')
  const [search, setSearch]                   = useState('')
  const [sortBy, setSortBy]                   = useState<SortField>('created_at')
  const [sortDir, setSortDir]                 = useState<SortDir>('desc')

  // ── Pagination ──
  const [page, setPage]   = useState(1)
  const [limit, setLimit] = useState(50)

  // ── Data ──
  const [data, setData]       = useState<PaginatedResponse | null>(null)
  const [loading, setLoading] = useState(true)

  // ── Dropdown options ──
  const [apps, setApps]       = useState<AppOption[]>([])
  const [keys, setKeys]       = useState<KeyOption[]>([])
  const [machines, setMachines] = useState<MachineOption[]>([])

  // ── Detail panel ──
  const [selectedReceipt, setSelectedReceipt] = useState<Receipt | null>(null)

  // ── Load App list once ──
  useEffect(() => {
    api.get('/apps').then(r => setApps(r.data)).catch(() => {})
  }, [])

  // ── Cascade: when App changes, load Keys ──
  useEffect(() => {
    setSelectedKey('')
    setSelectedMachine('')
    setKeys([])
    setMachines([])
    if (!selectedApp) return
    api.get(`/apps/${selectedApp}/keys`).then(r => setKeys(r.data)).catch(() => {})
  }, [selectedApp])

  // ── Cascade: when Key changes, load Machines ──
  useEffect(() => {
    setSelectedMachine('')
    setMachines([])
    if (!selectedKey) return
    const key = keys.find(k => k.id === selectedKey)
    if (!key) return
    api.get(`/keys/${selectedKey}/machines`).then(r => setMachines(r.data)).catch(() => {})
  }, [selectedKey, keys])

  // ── Fetch receipts ──
  const fetchReceipts = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, any> = { page, limit, sort_by: sortBy, sort_dir: sortDir }
      if (search)         params.search = search
      if (isSynced !== '') params.is_synced = isSynced
      if (dateFrom)       params.date_from = dateFrom
      if (dateTo)         params.date_to = dateTo
      if (selectedMachine) params.machine_id = selectedMachine

      // Pick the most specific endpoint
      let url = '/receipts'
      if (selectedKey)    url = `/keys/${selectedKey}/receipts`
      else if (selectedApp) url = `/apps/${selectedApp}/receipts`

      const { data: res } = await api.get(url, { params })
      setData(res)
    } catch (err: any) {
      console.error('[Receipts: Fetch]', err)
      toast.error(err.response?.data?.detail || 'Failed to load receipts.')
    } finally {
      setLoading(false)
    }
  }, [page, limit, sortBy, sortDir, search, isSynced, dateFrom, dateTo, selectedMachine, selectedApp, selectedKey, toast])

  useEffect(() => { fetchReceipts() }, [fetchReceipts])

  // ── Reset to page 1 on any filter change ──
  const resetAndFetch = () => { setPage(1) }
  useEffect(() => { resetAndFetch() }, [selectedApp, selectedKey, selectedMachine, isSynced, dateFrom, dateTo, search])

  // ── Sort toggle ──
  const toggleSort = (field: SortField) => {
    if (sortBy === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortBy(field); setSortDir('desc') }
  }

  const SortIcon = ({ field }: { field: SortField }) =>
    sortBy === field
      ? <ArrowUpDown className="w-3 h-3 text-brand-600" />
      : <ArrowUpDown className="w-3 h-3 text-surface-300" />

  return (
    <div className="space-y-6">
      {/* ── Header ── */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col md:flex-row md:items-center justify-between gap-4"
      >
        <div>
          <h1 className="page-title flex items-center gap-2">
            <ClipboardList className="w-7 h-7 text-brand-600" />
            Receipts
          </h1>
          <p className="page-subtitle">Weightment records across all applications and machines</p>
        </div>
        <div className="flex items-center gap-2">
          {data && (
            <span className="text-xs font-semibold text-surface-500 glass px-3 py-1.5 rounded-full border border-white/40">
              {data.total.toLocaleString()} total records
            </span>
          )}
          <button
            onClick={fetchReceipts}
            id="receipts-refresh-btn"
            className="p-2 glass rounded-xl border border-white/40 text-brand-600 hover:bg-white/50 transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </motion.div>

      {/* ── Filter Panel ── */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        className="glass rounded-2xl border border-white/50 p-4"
      >
        <div className="flex items-center gap-2 mb-3 text-xs font-bold text-surface-500 uppercase tracking-wider">
          <Filter className="w-3.5 h-3.5" /> Filters
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">

          {/* App */}
          <div className="relative">
            <AppWindow className="absolute left-3 top-2.5 w-3.5 h-3.5 text-surface-400 pointer-events-none" />
            <select
              id="filter-app"
              value={selectedApp}
              onChange={e => setSelectedApp(e.target.value)}
              className="form-input pl-8 pr-6 appearance-none text-xs cursor-pointer"
            >
              <option value="">All Apps</option>
              {apps.map(a => <option key={a.id} value={a.id}>{a.app_name}</option>)}
            </select>
            <ChevronDown className="absolute right-2 top-2.5 w-3 h-3 text-surface-400 pointer-events-none" />
          </div>

          {/* Customer (Key) */}
          <div className="relative">
            <Building2 className="absolute left-3 top-2.5 w-3.5 h-3.5 text-surface-400 pointer-events-none" />
            <select
              id="filter-key"
              value={selectedKey}
              onChange={e => setSelectedKey(e.target.value)}
              disabled={!selectedApp}
              className="form-input pl-8 pr-6 appearance-none text-xs cursor-pointer disabled:opacity-40"
            >
              <option value="">All Customers</option>
              {keys.map(k => <option key={k.id} value={k.id}>{k.company_name}</option>)}
            </select>
            <ChevronDown className="absolute right-2 top-2.5 w-3 h-3 text-surface-400 pointer-events-none" />
          </div>

          {/* Machine */}
          <div className="relative">
            <Cpu className="absolute left-3 top-2.5 w-3.5 h-3.5 text-surface-400 pointer-events-none" />
            <select
              id="filter-machine"
              value={selectedMachine}
              onChange={e => setSelectedMachine(e.target.value)}
              disabled={!selectedKey}
              className="form-input pl-8 pr-6 appearance-none text-xs cursor-pointer disabled:opacity-40"
            >
              <option value="">All Machines</option>
              {machines.map(m => (
                <option key={m.machine_id} value={m.machine_id}>
                  {m.name || m.machine_id}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-2 top-2.5 w-3 h-3 text-surface-400 pointer-events-none" />
          </div>

          {/* Date From */}
          <div className="relative">
            <Calendar className="absolute left-3 top-2.5 w-3.5 h-3.5 text-surface-400 pointer-events-none" />
            <input
              id="filter-date-from"
              type="datetime-local"
              value={dateFrom}
              onChange={e => setDateFrom(e.target.value)}
              className="form-input pl-8 text-xs"
              placeholder="Date from"
            />
          </div>

          {/* Date To */}
          <div className="relative">
            <Calendar className="absolute left-3 top-2.5 w-3.5 h-3.5 text-surface-400 pointer-events-none" />
            <input
              id="filter-date-to"
              type="datetime-local"
              value={dateTo}
              onChange={e => setDateTo(e.target.value)}
              className="form-input pl-8 text-xs"
              placeholder="Date to"
            />
          </div>

          {/* Sync Status */}
          <div className="relative">
            <select
              id="filter-sync-status"
              value={isSynced}
              onChange={e => setIsSynced(e.target.value as any)}
              className="form-input appearance-none text-xs cursor-pointer"
            >
              <option value="">All Status</option>
              <option value="true">Synced</option>
              <option value="false">Pending</option>
            </select>
            <ChevronDown className="absolute right-2 top-2.5 w-3 h-3 text-surface-400 pointer-events-none" />
          </div>

          {/* Search — full width bottom row */}
          <div className="col-span-2 md:col-span-3 lg:col-span-4 relative">
            <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-surface-400 pointer-events-none" />
            <input
              id="search-receipts"
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search truck number, vehicle, operator..."
              className="form-input pl-8 text-xs"
            />
            {search && (
              <button
                onClick={() => setSearch('')}
                className="absolute right-2 top-2 p-0.5 rounded text-surface-400 hover:text-surface-700"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Page size */}
          <div className="relative">
            <select
              id="filter-page-size"
              value={limit}
              onChange={e => { setLimit(Number(e.target.value)); setPage(1) }}
              className="form-input appearance-none text-xs cursor-pointer"
            >
              <option value={25}>25 / page</option>
              <option value={50}>50 / page</option>
              <option value={100}>100 / page</option>
              <option value={200}>200 / page</option>
            </select>
            <ChevronDown className="absolute right-2 top-2.5 w-3 h-3 text-surface-400 pointer-events-none" />
          </div>

          {/* Clear filters */}
          <button
            id="clear-filters-btn"
            onClick={() => {
              setSelectedApp(''); setSelectedKey(''); setSelectedMachine('')
              setDateFrom(''); setDateTo(''); setIsSynced(''); setSearch(''); setPage(1)
            }}
            className="btn-secondary text-xs px-3 py-2"
          >
            <X className="w-3.5 h-3.5" /> Clear All
          </button>
        </div>
      </motion.div>

      {/* ── Data Table ── */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="glass rounded-2xl border border-white/50 overflow-hidden shadow-sm"
      >
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th className="w-[1px] text-center">#</th>
                <th className="w-[160px] whitespace-nowrap">
                  <button onClick={() => toggleSort('date_time')} className="flex items-center gap-1 hover:text-surface-700">
                    Date <SortIcon field="date_time" />
                  </button>
                </th>
                <th className="w-[140px] whitespace-nowrap">
                  <div className="flex items-center gap-1">
                    <Truck className="w-3.5 h-3.5" /> Truck No
                  </div>
                </th>
                <th className="w-[150px] whitespace-nowrap">
                  <button onClick={() => toggleSort('gross_weight')} className="flex items-center gap-1 hover:text-surface-700">
                    Net Weight (kg) <SortIcon field="gross_weight" />
                  </button>
                </th>
                <th className="w-[140px] whitespace-nowrap"><div className="flex items-center gap-1"><AppWindow className="w-3.5 h-3.5" /> App</div></th>
                <th className="w-[180px] whitespace-nowrap"><div className="flex items-center gap-1"><Building2 className="w-3.5 h-3.5" /> Customer</div></th>
                <th className="w-[120px] whitespace-nowrap"><div className="flex items-center gap-1"><Cpu className="w-3.5 h-3.5" /> Machine</div></th>
                <th className="w-[140px] whitespace-nowrap"><div className="flex items-center gap-1"><Users className="w-3.5 h-3.5" /> Operator</div></th>
                <th className="w-[80px] text-center">Sync</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-100">
              {loading ? (
                Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} />)
              ) : !data || data.items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-16 text-surface-400">
                    <Scale className="w-10 h-10 opacity-10 mx-auto mb-3" />
                    <p className="text-sm font-medium">No receipts found</p>
                    <p className="text-xs mt-1">Adjust filters or sync more data from field machines.</p>
                  </td>
                </tr>
              ) : (
                data.items.map((r, idx) => (
                  <tr
                    key={r.id}
                    id={`receipt-row-${r.id}`}
                    onClick={() => setSelectedReceipt(r)}
                    className="hover:bg-white/30 transition-colors cursor-pointer"
                  >
                    <td className="text-xs text-surface-400 font-mono text-center">
                      {((page - 1) * limit) + idx + 1}
                    </td>
                    <td className="whitespace-nowrap">
                      <span className="text-xs text-surface-600 font-mono tabular-nums">
                        {format(new Date(r.date_time), 'dd MMM yy, HH:mm')}
                      </span>
                    </td>
                    <td className="whitespace-nowrap">
                      <span className="text-sm font-bold text-surface-800 font-mono tracking-tight uppercase">
                        {(r.payload_json?.data?.truck_no || r.truck_no) || <span className="text-surface-300 text-xs italic font-normal">—</span>}
                      </span>
                    </td>
                    <td className="whitespace-nowrap">
                      {(() => {
                        const payloadData = r.payload_json?.data || {}
                        const gross = payloadData.gross ?? r.gross_weight
                        const tare = payloadData.tare ?? r.tare_weight
                        const net = payloadData.net ?? r.net_weight
                        return (
                          <div className="flex flex-col">
                            <span className="text-sm font-bold text-brand-700 font-mono tabular-nums">
                              {(Number(net) || 0).toLocaleString()} kg
                            </span>
                            <span className="text-[10px] text-surface-400 font-mono tabular-nums">
                              G:{gross} / T:{tare}
                            </span>
                          </div>
                        )
                      })()}
                    </td>
                    <td>
                      {r.app_name
                        ? <span className="text-[10px] bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-full border border-indigo-100 font-bold uppercase tracking-wider">{r.app_name}</span>
                        : <span className="text-surface-300 text-xs">—</span>
                      }
                    </td>
                    <td>
                      <span className="text-xs font-semibold text-surface-700 truncate block max-w-[160px]" title={r.company_name}>
                        {r.company_name || <span className="text-surface-300 italic font-normal">Unknown</span>}
                      </span>
                    </td>
                    <td>
                      <span className="text-[11px] font-mono text-surface-500 truncate block max-w-[100px]" title={r.machine_id}>
                        {r.machine_id}
                      </span>
                    </td>
                    <td>
                      <span className="text-xs font-medium text-surface-700 truncate block max-w-[120px]" title={r.employee_name}>
                        {r.employee_name || <span className="text-surface-300 italic font-normal">None</span>}
                      </span>
                    </td>
                    <td className="text-center"><SyncBadge synced={r.is_synced} /></td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* ── Pagination Bar ── */}
        {data && data.total > 0 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-surface-100 bg-surface-50/40">
            <span className="text-xs text-surface-500">
              Showing {((page - 1) * limit) + 1}–{Math.min(page * limit, data.total)} of{' '}
              <strong>{data.total.toLocaleString()}</strong> receipts
            </span>
            <div className="flex items-center gap-2">
              <button
                id="pagination-prev"
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-1.5 rounded-lg hover:bg-surface-100 disabled:opacity-30 disabled:cursor-not-allowed text-surface-600"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-xs text-surface-600 font-medium px-2">
                Page {page} / {data.pages}
              </span>
              <button
                id="pagination-next"
                onClick={() => setPage(p => Math.min(data.pages, p + 1))}
                disabled={page >= data.pages}
                className="p-1.5 rounded-lg hover:bg-surface-100 disabled:opacity-30 disabled:cursor-not-allowed text-surface-600"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </motion.div>

      {/* ── Receipt Detail Slide-Over ── */}
      <AnimatePresence>
        {selectedReceipt && (
          <ReceiptDetailPanel
            receipt={selectedReceipt}
            onClose={() => setSelectedReceipt(null)}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

// ─────────────────────────────────────────────
// Receipt Detail Panel
// ─────────────────────────────────────────────

function ReceiptDetailPanel({ receipt, onClose }: { receipt: Receipt; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-end">
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        onClick={onClose}
        className="absolute inset-0 bg-black/30 backdrop-blur-sm"
      />

      {/* Panel */}
      <motion.div
        initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }}
        transition={{ type: 'spring', damping: 28, stiffness: 300 }}
        className="relative w-full max-w-md h-full glass border-l border-white/50 shadow-2xl overflow-y-auto"
      >
        {/* Header */}
        <div className="sticky top-0 glass border-b border-white/30 px-6 py-4 flex items-center justify-between z-10">
          <div>
            <h2 className="text-base font-bold text-surface-900">Receipt #{receipt.id}</h2>
            <p className="text-xs text-surface-500 mt-0.5">Local ID: {receipt.local_id}</p>
          </div>
          <button
            onClick={onClose}
            id="receipt-detail-close"
            className="p-2 rounded-xl hover:bg-surface-100 text-surface-500"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-6 space-y-5">
          {/* Core weights */}
          {(() => {
            const data = receipt.payload_json?.data || {}
            const gross = data.gross ?? receipt.gross_weight
            const tare = data.tare ?? receipt.tare_weight
            const net = data.net ?? receipt.net_weight
            
            return (
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: 'Gross', value: `${gross} kg`, color: 'text-surface-700' },
                  { label: 'Tare', value: `${tare} kg`, color: 'text-surface-700' },
                  { label: 'Net', value: `${net} kg`, color: 'text-brand-700 font-bold' },
                ].map(({ label, value, color }) => (
                  <div key={label} className="bg-surface-50 rounded-xl p-3 border border-surface-100 text-center">
                    <p className="text-[10px] text-surface-400 mb-1">{label}</p>
                    <p className={`text-sm ${color}`}>{value}</p>
                  </div>
                ))}
              </div>
            )
          })()}

          {/* Metadata grid */}
          <div className="space-y-2">
            {[
              { icon: Truck, label: 'Date & Time', value: format(new Date(receipt.date_time), 'dd MMM yyyy, HH:mm:ss') },
              { icon: Cpu, label: 'Machine', value: receipt.machine_id },
              { icon: Building2, label: 'Customer', value: receipt.company_name || '—' },
              { icon: Users, label: 'Operator', value: receipt.employee_name ? `${receipt.employee_name} (@${receipt.employee_username})` : '—' },
              { icon: AppWindow, label: 'Application', value: receipt.app_name || '—' },
            ].map(({ icon: Icon, label, value }) => (
              <div key={label} className="flex items-center gap-3 p-3 rounded-xl bg-surface-50 border border-surface-100">
                <Icon className="w-4 h-4 text-brand-500 shrink-0" />
                <div className="min-w-0">
                  <p className="text-[10px] text-surface-400">{label}</p>
                  <p className="text-xs font-semibold text-surface-800 truncate">{value}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Dynamic Data Content */}
          <div>
            <p className="text-xs font-bold text-surface-600 uppercase tracking-wide mb-2">Weightment Data</p>
            <div className="grid grid-cols-1 gap-2">
              {(() => {
                const data = receipt.payload_json?.data || receipt.custom_data || {}
                const entries = Object.entries(data).filter(([k]) => !['gross', 'tare', 'net', 'rate', 'remarks'].includes(k.toLowerCase()))
                
                if (entries.length === 0) return <p className="text-xs text-surface-400 italic">No additional fields</p>

                return entries.map(([key, val]) => (
                  <div key={key} className="flex items-center justify-between p-3 rounded-xl bg-surface-50 border border-surface-100">
                    <span className="text-[10px] text-surface-500 font-bold capitalize">{key.replace(/_/g, ' ')}</span>
                    <span className="text-xs font-semibold text-surface-800">{String(val)}</span>
                  </div>
                ))
              })()}
            </div>
          </div>

          {/* Images Section */}
          {(receipt.image_urls && receipt.image_urls.length > 0) && (
            <div>
              <p className="text-xs font-bold text-surface-600 uppercase tracking-wide mb-2">Images ({receipt.image_urls.length})</p>
              <div className="grid grid-cols-2 gap-2">
                {receipt.image_urls.map((url, idx) => (
                  <div key={idx} className="aspect-square rounded-xl border border-surface-100 overflow-hidden bg-surface-50 relative group">
                    <img src={url} alt={`Receipt ${idx}`} className="w-full h-full object-cover" />
                    <a 
                      href={url} 
                      target="_blank" 
                      rel="noreferrer"
                      className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-white text-[10px] font-bold"
                    >
                      View Full
                    </a>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Sync status */}
          <div className="p-4 rounded-xl border border-surface-100 bg-surface-50 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-surface-500 font-semibold">Sync Status</span>
              <SyncBadge synced={receipt.is_synced} />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-surface-400">Attempts</span>
              <span className="text-xs font-mono">{receipt.sync_attempts}</span>
            </div>
            {receipt.last_error && (
              <div className="p-2 bg-red-50 rounded-lg border border-red-100 text-[10px] text-red-700 font-mono break-all">
                {receipt.last_error}
              </div>
            )}
          </div>
        </div>
      </motion.div>
    </div>
  )
}
