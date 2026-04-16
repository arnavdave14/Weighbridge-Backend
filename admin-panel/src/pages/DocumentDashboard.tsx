import { useState, useEffect } from 'react'
import { FileText, Search, Filter, AlertTriangle, CheckCircle, Clock } from 'lucide-react'
import api from '../services/api'
import { format } from 'date-fns'
import DocumentDetailModal from '../components/documents/DocumentDetailModal'

export default function DocumentDashboard() {
  const [stats, setStats] = useState<any>(null)
  const [logs, setLogs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  
  // Filters
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  
  // Pagination
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  // Modal
  const [selectedLogId, setSelectedLogId] = useState<string | null>(null)

  useEffect(() => {
    fetchStats()
    fetchLogs()
  }, [page, statusFilter])

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      if (page !== 1) setPage(1)
      else fetchLogs()
    }, 500)
    return () => clearTimeout(timer)
  }, [search])

  async function fetchStats() {
    try {
      const res = await api.get('/documents/stats')
      setStats(res.data)
    } catch (err) {
      console.error('Failed to load doc stats', err)
    }
  }

  async function fetchLogs() {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        limit: '15'
      })
      if (search) params.append('search', search)
      if (statusFilter) params.append('status', statusFilter)

      const res = await api.get(`/documents/logs?${params}`)
      setLogs(res.data.items || [])
      setTotal(res.data.total || 0)
    } catch (err) {
      console.error('Failed to load logs', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
          <FileText className="w-6 h-6 text-brand-600" />
          Document Delivery Monitoring
        </h1>
        <p className="text-slate-500 text-sm mt-1">Track business documents sent via Email and WhatsApp</p>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <p className="text-slate-500 text-sm font-medium mb-1">Total Sent</p>
            <p className="text-2xl font-bold text-slate-800">{stats.total_documents}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <p className="text-slate-500 text-sm font-medium mb-1 flex items-center gap-1">
              <CheckCircle className="w-4 h-4 text-green-500" /> Success Rate
            </p>
            <p className="text-2xl font-bold text-green-600">{stats.success_rate}%</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <p className="text-slate-500 text-sm font-medium mb-1 flex items-center gap-1">
              <AlertTriangle className="w-4 h-4 text-red-500" /> Failed
            </p>
            <p className="text-2xl font-bold text-red-600">{stats.total_failed}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <p className="text-slate-500 text-sm font-medium mb-1 flex items-center gap-1">
              <Clock className="w-4 h-4 text-blue-500" /> Avg Latency
            </p>
            <p className="text-2xl font-bold text-slate-800">{stats.average_latency}s</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-wrap gap-4 items-center">
        <div className="relative flex-1 min-w-[250px]">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search company or targets..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition-all"
          />
        </div>
        
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-400" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 bg-slate-50 border border-slate-200 text-slate-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20"
          >
            <option value="">All Statuses</option>
            <option value="SUCCESS">Success</option>
            <option value="FAILED">Failed</option>
            <option value="PENDING">Pending</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white border text-sm border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 font-medium text-slate-500">Document</th>
                <th className="px-4 py-3 font-medium text-slate-500">Company</th>
                <th className="px-4 py-3 font-medium text-slate-500">Channel (Provider)</th>
                <th className="px-4 py-3 font-medium text-slate-500">Targets</th>
                <th className="px-4 py-3 font-medium text-slate-500">Status</th>
                <th className="px-4 py-3 font-medium text-slate-500 text-right">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading && logs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                    Loading logs...
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                    No documents found
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr 
                    key={log.id} 
                    className="hover:bg-slate-50/50 cursor-pointer transition-colors"
                    onClick={() => setSelectedLogId(log.id)}
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-900">{log.document_name}</div>
                      <div className="text-xs text-slate-500 uppercase">{log.document_type}</div>
                    </td>
                    <td className="px-4 py-3 text-slate-700">{log.company_name}</td>
                    <td className="px-4 py-3">
                      <div className="text-slate-800 capitalize">{log.delivery_channel}</div>
                      <div className="text-xs text-slate-500 uppercase">{log.provider_type}</div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-slate-600 truncate max-w-[150px]" title={log.email_used}>
                        {log.email_used || '-'}
                      </div>
                      <div className="text-slate-600 truncate max-w-[150px]" title={log.whatsapp_channel}>
                        {log.whatsapp_channel || '-'}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wider ${
                        log.status === 'SUCCESS' ? 'bg-green-100 text-green-700' :
                        log.status === 'FAILED' ? 'bg-red-100 text-red-700' :
                        'bg-yellow-100 text-yellow-700'
                      }`}>
                        {log.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-slate-500 whitespace-nowrap">
                      {format(new Date(log.created_at), 'MMM d, HH:mm:ss')}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        {total > 0 && (
          <div className="px-4 py-3 border-t border-slate-200 bg-slate-50 text-right text-xs text-slate-500">
            Showing {logs.length} of {total} documents
          </div>
        )}
      </div>

      {/* Detail Modal */}
      {selectedLogId && (
        <DocumentDetailModal 
          logId={selectedLogId} 
          onClose={() => setSelectedLogId(null)} 
          onRetried={fetchLogs}
        />
      )}
    </div>
  )
}
