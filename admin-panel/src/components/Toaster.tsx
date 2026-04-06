import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle2, XCircle, AlertTriangle, Info, X } from 'lucide-react'
import { useToast } from '../context/ToastContext'

const toastTypes = {
  success: { icon: CheckCircle2, cls: 'bg-emerald-50 border-emerald-100 text-emerald-800', iconCls: 'text-emerald-500' },
  error: { icon: XCircle, cls: 'bg-rose-50 border-rose-100 text-rose-800', iconCls: 'text-rose-500' },
  warning: { icon: AlertTriangle, cls: 'bg-amber-50 border-amber-100 text-amber-800', iconCls: 'text-amber-500' },
  info: { icon: Info, cls: 'bg-blue-50 border-blue-100 text-blue-800', iconCls: 'text-blue-500' },
}

export function Toaster() {
  const { toasts, remove } = useToast()

  return (
    <div className="fixed top-6 right-6 z-[9999] flex flex-col gap-3 w-full max-w-sm pointer-events-none">
      <AnimatePresence>
        {toasts.map((toast) => {
          const cfg = toastTypes[toast.type]
          return (
            <motion.div
              key={toast.id}
              layout
              initial={{ opacity: 0, x: 20, scale: 0.95 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95, transition: { duration: 0.2 } }}
              className={`pointer-events-auto flex items-start gap-3 p-4 rounded-2xl border shadow-xl backdrop-blur-md ${cfg.cls}`}
            >
              <cfg.icon className={`w-5 h-5 shrink-0 ${cfg.iconCls}`} />
              <div className="flex-1 min-w-0 pr-6">
                <p className="text-sm font-semibold leading-tight">{toast.message}</p>
              </div>
              <button
                onClick={() => remove(toast.id)}
                className="absolute top-4 right-4 text-surface-400 hover:text-surface-900 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}
