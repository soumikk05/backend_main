import { motion } from 'motion/react';
import {
  CheckCircle2,
  AlertTriangle,
  Lock,
  RotateCcw,
  Sparkles,
  ShieldCheck,
  ShieldAlert,
} from 'lucide-react';

export function VerificationResult({
  state,
  errorMessage,
  attempts,
  maxAttempts = 3,
  verifiedFrameUrl,
  onRetry,
  onReset,
}) {
  if (state === 'PASSED') {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="result-box result-box--passed p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex flex-col sm:flex-row items-center gap-4"
      >
        {verifiedFrameUrl ? (
          <div className="relative w-24 h-24 rounded-lg overflow-hidden border-2 border-emerald-400/50 shrink-0 shadow-[0_0_15px_rgba(16,185,129,0.3)]">
            <img
              src={verifiedFrameUrl}
              alt="Verified frontal frame"
              className="w-full h-full object-cover"
            />
            <div className="absolute bottom-0 inset-x-0 bg-black/70 text-[9px] font-mono text-emerald-300 text-center py-0.5">
              VERIFIED
            </div>
          </div>
        ) : (
          <div className="w-16 h-16 rounded-full bg-emerald-500/20 border border-emerald-400 flex items-center justify-center text-emerald-400 shrink-0">
            <CheckCircle2 size={32} />
          </div>
        )}

        <div className="flex-1 text-center sm:text-left">
          <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 font-bold mb-1">
            <ShieldCheck size={12} />
            <span>Active Liveness Confirmed</span>
          </div>
          <div className="text-sm font-bold font-mono text-white">
            Backend Verified Frontal Frame
          </div>
          <p className="text-xs font-mono text-slate-300 mt-1">
            Motion challenge verified. Frontal frame unlocked for 1:1 facial biometric matching.
          </p>
        </div>

        {onReset && (
          <button
            onClick={onReset}
            className="text-xs font-mono text-slate-400 hover:text-cyan-400 transition-colors p-1.5"
            title="Recapture selfie"
          >
            <RotateCcw size={14} />
          </button>
        )}
      </motion.div>
    );
  }

  if (state === 'FAILED') {
    const remaining = maxAttempts - attempts;

    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="result-box result-box--failed p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex flex-col items-center text-center gap-3"
      >
        <div className="w-12 h-12 rounded-full bg-rose-500/20 border border-rose-400/40 flex items-center justify-center text-rose-400">
          <AlertTriangle size={24} />
        </div>

        <div>
          <div className="text-xs font-mono uppercase tracking-wider text-rose-400 font-bold">
            Motion Verification Failed
          </div>
          <div className="text-sm font-mono text-rose-200 mt-1">
            {errorMessage || 'The requested challenge motion was not detected.'}
          </div>
          <div className="text-xs font-mono text-slate-400 mt-1">
            Remaining attempts: <span className="text-amber-400 font-bold">{remaining}</span> / {maxAttempts}
          </div>
        </div>

        <motion.button
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          onClick={onRetry}
          className="mt-1 flex items-center gap-2 px-4 py-2 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 text-rose-200 font-mono text-xs font-bold uppercase transition-all cursor-pointer"
        >
          <RotateCcw size={14} />
          <span>Try Next Challenge</span>
        </motion.button>
      </motion.div>
    );
  }

  if (state === 'LOCKED_OUT') {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="result-box result-box--locked p-5 rounded-xl bg-red-950/40 border border-red-500/40 flex flex-col items-center text-center gap-3"
      >
        <div className="w-12 h-12 rounded-full bg-red-500/20 border border-red-400 flex items-center justify-center text-red-400 shadow-[0_0_20px_rgba(239,68,68,0.4)]">
          <Lock size={24} />
        </div>

        <div>
          <div className="text-xs font-mono uppercase tracking-widest text-red-400 font-bold">
            Maximum Attempts Exceeded (3/3)
          </div>
          <div className="text-sm font-mono text-white font-bold mt-1">
            Session Locked for Security
          </div>
          <p className="text-xs font-mono text-slate-300 mt-1 max-w-sm">
            Multiple challenge failures detected. To prevent automated replay attacks, camera verification is locked. Please contact identity assistance.
          </p>
        </div>

        {onReset && (
          <button
            onClick={onReset}
            className="text-xs font-mono text-slate-400 hover:text-slate-200 underline mt-2 transition-colors"
          >
            Reset Session (Admin / Demo)
          </button>
        )}
      </motion.div>
    );
  }

  return null;
}
