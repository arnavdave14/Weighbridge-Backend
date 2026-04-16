import { useState, useEffect } from 'react'
import { X, RefreshCw, Paperclip, ExternalLink, Activity, Info, Mail, MessageSquare } from 'lucide-react'
import api from '../../services/api'
import { format } from 'date-fns'

interface ModalProps {
  logId: string
  onClose: () => void
  onRetried: () => void
}

export default function DocumentDetailModal({ logId, onClose, onRetried }: ModalProps) {
  const [log, setLog] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [retrying, setRetrying] = useState(false)

  useEffect(() => {
    fetchLog()
  }, [logId])

  async function fetchLog() {
    setLoading(true)
    try {
      const res = await api.get(`/documents/${logId}`)
      setLog(res.data)
    } catch (err) {
      console.error('Failed to fetch log details', err)
    } finally {
      setLoading(false)
    }
  }

  async function handleRetry() {
    setRetrying(true)
    try {
      await api.post(`/documents/${logId}/retry`)
      alert('Document retried successfully')
      fetchLog()
      onRetried()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Retry failed')
    } finally {
      setRetrying(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
          <div>
            <h2 className="text-lg font-bold text-slate-800">Document Delivery Details</h2>
            <p className="text-xs text-slate-500 font-mono mt-1">ID: {logId}</p>
          </div>
          <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-200/50">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {loading ? (
            <div className="flex items-center justify-center p-12">
              <RefreshCw className="w-8 h-8 text-brand-500 animate-spin" />
            </div>
          ) : !log ? (
            <div className="text-center p-8 text-red-500">Log not found</div>
          ) : (
            <>
              {/* Context header */}
              <div className="flex items-center justify-between p-4 bg-slate-50 rounded-xl border border-slate-200">
                <div className="flex items-center gap-4">
                  <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                    log.status === 'SUCCESS' ? 'bg-green-100 text-green-600' : 
                    log.status === 'FAILED' ? 'bg-red-100 text-red-600' : 
                    'bg-yellow-100 text-yellow-600'
                  }`}>
                    <Activity className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-slate-800">{log.document_name}</h3>
                    <p className="text-sm text-slate-500 capitalize">{log.company_name} • {log.document_type}</p>
                  </div>
                </div>
                {log.status === 'FAILED' && (
                  <button
                    onClick={handleRetry}
                    disabled={retrying}
                    className="flex items-center gap-2 px-4 py-2 bg-slate-800 text-white rounded-lg text-sm font-medium hover:bg-slate-700 disabled:opacity-50"
                  >
                    <RefreshCw className={`w-4 h-4 ${retrying ? 'animate-spin' : ''}`} />
                    Retry Delivery
                  </button>
                )}
              </div>

              {/* Delivery Details */}
              <div className="grid grid-cols-2 gap-4">
                <div className="border border-slate-100 rounded-xl p-4">
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Delivery Information</h4>
                  <div className="space-y-3">
                    <div>
                      <p className="text-xs text-slate-500 flex items-center gap-1"><Mail className="w-3 h-3"/> Target Email</p>
                      <p className="text-sm font-medium text-slate-800">{log.email_used || '-'}</p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500 flex items-center gap-1"><MessageSquare className="w-3 h-3"/> Target WhatsApp</p>
                      <p className="text-sm font-medium text-slate-800">{log.whatsapp_channel || '-'}</p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500">Provider Strategy</p>
                      <p className="text-sm font-medium text-slate-800 uppercase">
                        {log.delivery_channel} via {log.provider_type} SMTP
                      </p>
                    </div>
                  </div>
                </div>

                <div className="border border-slate-100 rounded-xl p-4">
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Attempt Details</h4>
                  <div className="space-y-3">
                    <div>
                      <p className="text-xs text-slate-500">Status</p>
                      <span className={`inline-flex items-center px-2 py-0.5 mt-1 rounded-full text-xs font-bold tracking-wider ${
                        log.status === 'SUCCESS' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                      }`}>
                        {log.status}
                      </span>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500">Time / Latency</p>
                      <p className="text-sm font-medium text-slate-800">
                        {format(new Date(log.created_at), 'PP pp')} <br/>
                        <span className="text-slate-500 font-normal">{(log.latency || 0).toFixed(2)}s</span>
                      </p>
                    </div>
                    {log.retry_count > 0 && (
                      <div>
                        <p className="text-xs text-slate-500">Retries</p>
                        <p className="text-sm font-medium text-amber-600">{log.retry_count} times</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Error Box */}
              {log.error_message && (
                <div className="bg-red-50 border border-red-100 rounded-xl p-4">
                  <h4 className="text-xs font-bold text-red-800 mb-1 flex items-center gap-1">
                    <Info className="w-4 h-4"/> Error Details
                  </h4>
                  <pre className="text-xs text-red-600 whitespace-pre-wrap font-mono mt-2 overflow-x-auto">
                    {log.error_message}
                  </pre>
                </div>
              )}

              {/* Metadata */}
              {log.metadata && Object.keys(log.metadata).length > 0 && (
                <div>
                  <h4 className="text-sm font-bold text-slate-800 mb-3 border-b border-slate-100 pb-2">Extracted Metadata</h4>
                  <div className="grid grid-cols-2 gap-y-2 gap-x-4 bg-slate-50 p-4 rounded-xl border border-slate-200">
                    {Object.entries(log.metadata).map(([key, val]: any) => (
                      <div key={key}>
                        <span className="text-xs text-slate-500 capitalize">{key.replace('_', ' ')}: </span>
                        <span className="text-sm font-medium text-slate-800">{String(val)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Attachments */}
              {log.attachments && log.attachments.length > 0 && (
                <div>
                  <h4 className="text-sm font-bold text-slate-800 mb-3 border-b border-slate-100 pb-2 flex items-center gap-2">
                    <Paperclip className="w-4 h-4" /> Attachments
                  </h4>
                  <div className="space-y-2">
                    {log.attachments.map((att: any, i: number) => (
                      <a 
                        key={i} 
                        href={att.file_url} 
                        target="_blank" 
                        rel="noreferrer"
                        className="flex items-center justify-between p-3 bg-slate-50 border border-slate-200 rounded-lg hover:border-brand-300 hover:bg-brand-50 transition-colors group"
                      >
                        <span className="text-sm font-medium text-slate-700 group-hover:text-brand-700">{att.file_name}</span>
                        <ExternalLink className="w-4 h-4 text-slate-400 group-hover:text-brand-500" />
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
