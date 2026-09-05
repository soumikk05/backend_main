import { motion, AnimatePresence } from 'motion/react';
import {
  Camera,
  Video,
  AlertTriangle,
  RotateCcw,
  Sparkles,
  ShieldCheck,
  Play,
  Zap,
} from 'lucide-react';
import { useLivenessCapture, LIVENESS_STATES } from './useLivenessCapture';
import { ChallengeInstruction } from './ChallengeInstruction';
import { CaptureProgress } from './CaptureProgress';
import { VerificationResult } from './VerificationResult';
import { Spinner } from '../../common';
import './LivenessCaptureCard.css';

export function LivenessCaptureCard({ onVerified, onResetVerified }) {
  const {
    state,
    challenge,
    attempts,
    maxAttempts,
    errorMessage,
    verifiedFrameUrl,
    captureProgress,
    videoRef,
    setVideoRef,
    canvasRef,
    startVerification,
    captureFrameBurst,
    retry,
    reset,
  } = useLivenessCapture({
    onVerified: (bestFrame, responseData) => {
      if (onVerified) onVerified(bestFrame, responseData);
    },
  });

  const handleFullReset = () => {
    reset();
    if (onResetVerified) onResetVerified();
  };

  const getCardClass = () => {
    switch (state) {
      case LIVENESS_STATES.PASSED:
        return 'liveness-card--passed';
      case LIVENESS_STATES.FAILED:
        return 'liveness-card--failed';
      case LIVENESS_STATES.LOCKED_OUT:
        return 'liveness-card--locked';
      case LIVENESS_STATES.CAMERA_READY:
      case LIVENESS_STATES.CHALLENGE_ISSUED:
      case LIVENESS_STATES.CAPTURING:
      case LIVENESS_STATES.VERIFYING:
        return 'liveness-card--active';
      default:
        return 'liveness-card--idle';
    }
  };

  return (
    <div className={`liveness-card ${getCardClass()}`}>
      <canvas ref={canvasRef} style={{ display: 'none' }} />

      {/* 1. IDLE STATE */}
      {state === LIVENESS_STATES.IDLE && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex flex-col items-center text-center gap-4 py-4"
        >
          <div className="w-16 h-16 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 shadow-[0_0_25px_rgba(6,182,212,0.2)]">
            <Camera size={32} />
          </div>

          <div>
            <div className="font-mono text-sm font-bold text-white tracking-wide">
              2. Live Selfie Image
            </div>
            <p className="text-xs font-mono text-slate-400 mt-1 max-w-xs">
              Interactive active challenge-response verification (blink / smile / turn). No static uploads allowed.
            </p>
          </div>

          <motion.button
            whileHover={{ scale: 1.04, boxShadow: '0 0 25px rgba(6, 182, 212, 0.4)' }}
            whileTap={{ scale: 0.96 }}
            onClick={startVerification}
            className="flex items-center gap-2.5 px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-mono text-xs font-bold uppercase tracking-wider shadow-lg cursor-pointer transition-all"
          >
            <Video size={15} />
            <span>Start Camera Verification</span>
          </motion.button>
        </motion.div>
      )}

      {/* 2. REQUESTING CAMERA STATE */}
      {state === LIVENESS_STATES.REQUESTING_CAMERA && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex flex-col items-center text-center gap-3 py-8"
        >
          <Spinner size="md" />
          <div className="font-mono text-xs text-cyan-400 font-bold uppercase tracking-wider animate-pulse">
            Requesting camera access…
          </div>
          <p className="text-[11px] font-mono text-slate-400">
            Please allow browser camera permissions when prompted.
          </p>
        </motion.div>
      )}

      {/* 3. CAMERA DENIED / ERROR STATE */}
      {state === LIVENESS_STATES.CAMERA_DENIED && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex flex-col items-center text-center gap-3 py-4 max-w-sm"
        >
          <div className="w-12 h-12 rounded-full bg-rose-500/20 border border-rose-500/40 flex items-center justify-center text-rose-400">
            <AlertTriangle size={24} />
          </div>

          <div>
            <div className="font-mono text-xs uppercase tracking-wider text-rose-400 font-bold">
              Camera Access Required
            </div>
            <p className="text-xs font-mono text-rose-200 mt-1">
              {errorMessage || 'Camera access is required for active identity verification.'}
            </p>
          </div>

          <motion.button
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={startVerification}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 text-rose-200 font-mono text-xs font-bold uppercase transition-all cursor-pointer mt-2"
          >
            <RotateCcw size={14} />
            <span>Try Again</span>
          </motion.button>
        </motion.div>
      )}

      {/* 4. LIVE CAMERA STREAM VIEW (CAMERA_READY, CHALLENGE_ISSUED, CAPTURING, VERIFYING) */}
      {[
        LIVENESS_STATES.CAMERA_READY,
        LIVENESS_STATES.CHALLENGE_ISSUED,
        LIVENESS_STATES.CAPTURING,
        LIVENESS_STATES.VERIFYING,
      ].includes(state) && (
        <div className="w-full flex flex-col items-center gap-4">
          <div className="liveness-video-wrap">
            <video
              ref={setVideoRef}
              autoPlay
              playsInline
              muted
              className="liveness-video"
              onLoadedMetadata={(e) => {
                e.target.play().catch(err => console.warn('Video auto-play warning:', err));
              }}
            />

            {/* Cyber HUD Target Overlay */}
            <div className="liveness-hud-overlay">
              <div className="flex items-center justify-between text-[10px] font-mono text-cyan-400 uppercase tracking-widest bg-black/60 px-2 py-0.5 rounded backdrop-blur-sm">
                <span className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                  LIVE FEED
                </span>
                <span>ATTEMPT {attempts + 1}/{maxAttempts}</span>
              </div>

              {/* Target Face Outline */}
              <div className="liveness-hud-target" />

              {/* Scanning Laser Line when Capturing */}
              {state === LIVENESS_STATES.CAPTURING && (
                <div className="liveness-scan-line" />
              )}
            </div>

            {/* Capturing Circular Progress Ring Overlay */}
            {state === LIVENESS_STATES.CAPTURING && (
              <div className="absolute inset-0 bg-black/50 backdrop-blur-xs flex items-center justify-center">
                <CaptureProgress progress={captureProgress} />
              </div>
            )}

            {/* Verifying Spinner Overlay */}
            {state === LIVENESS_STATES.VERIFYING && (
              <div className="absolute inset-0 bg-black/70 backdrop-blur-sm flex flex-col items-center justify-center gap-3 p-4 text-center">
                <Spinner size="md" />
                <div className="font-mono text-xs text-cyan-300 font-bold tracking-wider animate-pulse">
                  Verifying Motion Sequence…
                </div>
                <div className="text-[10px] font-mono text-slate-400">
                  Backend neural temporal analysis in progress
                </div>
              </div>
            )}
          </div>

          {/* Challenge Instruction Banner */}
          {challenge && state !== LIVENESS_STATES.VERIFYING && (
            <ChallengeInstruction challenge={challenge} />
          )}

          {/* Trigger Button to Start Frame Burst */}
          {state === LIVENESS_STATES.CHALLENGE_ISSUED && (
            <motion.button
              whileHover={{ scale: 1.02, boxShadow: '0 0 25px rgba(6, 182, 212, 0.4)' }}
              whileTap={{ scale: 0.98 }}
              onClick={captureFrameBurst}
              className="w-full flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-mono text-xs font-bold uppercase tracking-wider shadow-lg cursor-pointer transition-all"
            >
              <Zap size={15} />
              <span>I'm Ready — Perform Challenge</span>
            </motion.button>
          )}
        </div>
      )}

      {/* 5. PASSED, FAILED, OR LOCKED_OUT RESULTS */}
      {[
        LIVENESS_STATES.PASSED,
        LIVENESS_STATES.FAILED,
        LIVENESS_STATES.LOCKED_OUT,
      ].includes(state) && (
        <VerificationResult
          state={state}
          errorMessage={errorMessage}
          attempts={attempts}
          maxAttempts={maxAttempts}
          verifiedFrameUrl={verifiedFrameUrl}
          onRetry={retry}
          onReset={handleFullReset}
        />
      )}
    </div>
  );
}
