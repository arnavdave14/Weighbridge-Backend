import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Scale, Mail, Lock, AlertCircle, Eye, EyeOff, ArrowLeft, CheckCircle } from 'lucide-react'
import { useAuthStore } from '../store/useStore'
import api from '../services/api'
import { useToast } from '../context/ToastContext'

export default function Login() {
  const [step, setStep] = useState(0) // 0: Credentials, 1: OTP
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [otp, setOtp] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const { login } = useAuthStore()
  const navigate = useNavigate()
  const toast = useToast()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const body = new URLSearchParams({ username: email, password })
      const { data } = await api.post('/auth/login', body, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      
      // Backend now returns { message: "OTP sent to email" }
      setStep(1)
      toast.success(data.message || 'OTP sent to your email!')
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? 'Login failed. Check credentials.'
      setError(msg)
      toast.error(msg)
      console.error('[Login: Auth] Failed:', err)
    } finally {
      setBusy(false)
    }
  }

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const { data } = await api.post('/auth/verify-otp', { email, otp })
      login(data.access_token)
      toast.success('Successfully logged in!')
      navigate('/')
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? 'Verification failed. Invalid or expired OTP.'
      setError(msg)
      toast.error(msg)
      console.error('[Login: Verify] Failed:', err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-surface-900 via-blue-950 to-indigo-950 overflow-hidden relative p-4">
      {/* Animated background blobs */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-brand-500/20 rounded-full blur-3xl animate-blob" />
      <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-indigo-500/20 rounded-full blur-3xl animate-blob animation-delay-2000" />
      <div className="absolute top-1/2 left-1/2 w-64 h-64 bg-purple-500/15 rounded-full blur-3xl animate-blob animation-delay-4000" />

      <motion.div
        initial={{ opacity: 0, y: 24, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
        className="relative w-full max-w-md"
      >
        <div className="bg-white/10 backdrop-blur-2xl border border-white/20 rounded-3xl p-8 shadow-2xl">
          {/* Header */}
          <div className="text-center mb-8">
            <motion.div
              initial={{ scale: 0.8 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.1, type: 'spring', stiffness: 200 }}
              className="inline-flex w-16 h-16 rounded-2xl bg-gradient-to-br from-brand-500 to-indigo-600 items-center justify-center mb-4 shadow-glow"
            >
              <Scale className="w-8 h-8 text-white" />
            </motion.div>
            <h1 className="text-3xl font-bold text-white">Admin Panel</h1>
            <p className="text-white/60 text-sm mt-1">Weighbridge SaaS Control Center</p>
          </div>

          {error && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="mb-5 flex items-center gap-3 px-4 py-3 rounded-xl bg-red-500/20 border border-red-400/30 text-red-300 text-sm"
            >
              <AlertCircle className="w-4 h-4 shrink-0" />
              {error}
            </motion.div>
          )}

          <AnimatePresence mode="wait">
            {step === 0 ? (
              <motion.form
                key="login-form"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                onSubmit={handleSubmit}
                className="space-y-4"
              >
                <div>
                  <label className="block text-xs font-semibold text-white/50 uppercase tracking-wide mb-1.5">Email</label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-brand-400" />
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="admin@weighbridge.com"
                      required
                      className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-white/10 border border-white/20
                                 text-white placeholder-white/40 text-sm focus:outline-none
                                 focus:ring-2 focus:ring-brand-400 focus:border-transparent transition-all"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-white/50 uppercase tracking-wide mb-1.5">Password</label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-brand-400" />
                    <input
                      type={showPw ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      required
                      className="w-full pl-10 pr-10 py-2.5 rounded-xl bg-white/10 border border-white/20
                                 text-white placeholder-white/40 text-sm focus:outline-none
                                 focus:ring-2 focus:ring-brand-400 focus:border-transparent transition-all"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPw(!showPw)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white transition-colors"
                    >
                      {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={busy}
                  className="w-full mt-2 py-3 px-4 rounded-xl font-semibold text-sm text-white
                             bg-gradient-to-r from-brand-600 to-indigo-600
                             hover:from-brand-500 hover:to-indigo-500
                             shadow-lg shadow-brand-900/50 active:scale-[0.98]
                             transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {busy ? 'Authenticating…' : 'Sign In'}
                </button>
                
                <p className="text-center text-white/30 text-xs mt-6">
                  Default: admin@weighbridge.com / Admin123!
                </p>
              </motion.form>
            ) : (
              <motion.form
                key="otp-form"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                onSubmit={handleVerifyOtp}
                className="space-y-4"
              >
                <div className="mb-6 text-center">
                  <div className="inline-flex p-3 rounded-full bg-brand-500/10 mb-2">
                    <CheckCircle className="w-6 h-6 text-brand-400" />
                  </div>
                  <h2 className="text-xl font-semibold text-white">Check your email</h2>
                  <p className="text-white/60 text-sm mt-1">We've sent a 6-digit code to {email}</p>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-white/50 uppercase tracking-wide mb-1.5">Verification Code</label>
                  <input
                    type="text"
                    maxLength={6}
                    value={otp}
                    onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                    placeholder="123456"
                    required
                    className="w-full px-4 py-3 rounded-xl bg-white/10 border border-white/20
                               text-center text-2xl font-bold tracking-[0.5em] text-white placeholder-white/20
                               focus:outline-none focus:ring-2 focus:ring-brand-400 focus:border-transparent transition-all"
                  />
                </div>

                <button
                  type="submit"
                  disabled={busy || otp.length !== 6}
                  className="w-full mt-2 py-3 px-4 rounded-xl font-semibold text-sm text-white
                             bg-gradient-to-r from-brand-600 to-indigo-600
                             hover:from-brand-500 hover:to-indigo-500
                             shadow-lg shadow-brand-900/50 active:scale-[0.98]
                             transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {busy ? 'Verifying…' : 'Verify & Access'}
                </button>

                <button
                  type="button"
                  onClick={() => setStep(0)}
                  className="w-full flex items-center justify-center gap-2 text-white/40 hover:text-white text-sm transition-colors py-2"
                >
                  <ArrowLeft className="w-4 h-4" />
                  Back to login
                </button>
              </motion.form>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  )
}
