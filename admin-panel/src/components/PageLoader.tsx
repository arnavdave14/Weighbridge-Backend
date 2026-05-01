export default function PageLoader() {
  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-surface-50">
      {/* Glowing backdrop blob */}
      <div className="absolute w-96 h-96 rounded-full bg-brand-300/20 blur-3xl animate-pulse" />

      {/* Card */}
      <div className="relative flex flex-col items-center gap-6 glass rounded-3xl px-14 py-12 shadow-2xl">
        {/* Spinner ring */}
        <div className="relative flex items-center justify-center w-20 h-20">
          {/* Outer rotating ring */}
          <svg
            className="absolute inset-0 w-full h-full animate-spin"
            viewBox="0 0 80 80"
            fill="none"
          >
            <circle
              cx="40"
              cy="40"
              r="34"
              stroke="url(#spinnerGrad)"
              strokeWidth="6"
              strokeLinecap="round"
              strokeDasharray="140 80"
            />
            <defs>
              <linearGradient id="spinnerGrad" x1="0" y1="0" x2="80" y2="80" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stopColor="#6366f1" />
                <stop offset="100%" stopColor="#0ea5e9" />
              </linearGradient>
            </defs>
          </svg>

          {/* Inner brand icon */}
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-brand-200">
            <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
            </svg>
          </div>
        </div>

        {/* Label */}
        <div className="flex flex-col items-center gap-1.5">
          <span className="text-sm font-semibold text-surface-700 tracking-wide">Loading page…</span>
          {/* Bouncing dots */}
          <div className="flex items-center gap-1.5 mt-1">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-brand-500"
                style={{ animation: `bounce 1.2s ease-in-out ${i * 0.2}s infinite` }}
              />
            ))}
          </div>
        </div>
      </div>

      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
          40%            { transform: translateY(-6px); opacity: 1; }
        }
      `}</style>
    </div>
  )
}
