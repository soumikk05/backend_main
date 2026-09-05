import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  ShieldCheck,
  FileText,
  ScanFace,
  RotateCcw,
  AlertTriangle,
  Activity,
  Zap,
  Sparkles,
  ArrowRight,
  Layers,
  Lock,
} from 'lucide-react';
import { screeningApi } from '../../api/screening.api';
import { ModuleHeader } from './ModuleHeader';
import { RawJsonViewer } from './RawJsonViewer';
import { UploadZone } from '../Upload/UploadZone';
import { LivenessCaptureCard } from './LivenessCaptureCard/LivenessCaptureCard';
import { Card, Badge, ProgressBar, Skeleton, CheckItem } from '../common';
import { RiskGauge } from '../Dashboard/RiskGauge';
import { OcrResults } from '../Dashboard/OcrResults';
import { ValidationPanel } from '../Dashboard/ValidationPanel';
import { TamperingPanel } from '../Dashboard/TamperingPanel';
import { FacePanel } from '../Dashboard/FacePanel';
import { FlagsList } from '../Dashboard/FlagsList';
import { AuditPanel, TimelinePanel } from '../Dashboard/OperationsPanels';
import { scoreToHex } from '../../utils/helpers';
import { AnimatedCounter } from '../common/AnimatedBg';

export function PipelineScreen() {
  const [docFile, setDocFile] = useState(null);
  const [selfieFile, setSelfieFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('');
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const handleAssess = async () => {
    if (!docFile) return;
    setLoading(true);
    setError(null);
    setStatus('Executing full multimodal forensic pipeline...');

    try {
      const data = await screeningApi.assessRisk(docFile, selfieFile);
      setResult(data);
    } catch (err) {
      console.error(err);
      setError(
        err.response?.data?.detail ||
          err.message ||
          'Pipeline execution failed. Please verify the document and backend connectivity.'
      );
    } finally {
      setLoading(false);
      setStatus('');
    }
  };

  const handleReset = () => {
    setDocFile(null);
    setSelfieFile(null);
    setResult(null);
    setError(null);
  };

  // Result parsing
  const risk_score = result?.risk_score ?? result?.risk_summary?.risk_score ?? 0;
  const risk_label = result?.risk_label ?? result?.risk_summary?.risk_label ?? 'LOW';
  const flags = result?.flags ?? result?.risk_summary?.flags ?? [];
  const ocr = result?.module_outputs?.ocr || result?.ocr || result?.modules?.ocr || {};
  const validation = result?.module_outputs?.validation || result?.modules?.validation;
  const tampering = result?.module_outputs?.tampering || result?.modules?.tampering;
  const face = result?.module_outputs?.face || result?.modules?.face;
  const timeline = result?.timeline || {};
  const audit = result?.audit || {};
  const decision = result?.decision;
  const reasons = result?.reasons || [];

  const component_scores = result?.component_scores || {
    validation: validation?.overall_valid ? 100 : 0,
    tampering: tampering?.tampering_score || 0,
    face: face?.match ? 100 : 0,
  };

  return (
    <div className="space-y-6">
      <ModuleHeader
        badge="PRIMARY PIPELINE"
        title="Full Risk Assessment Pipeline"
        subtitle="End-to-end multimodal screening: Neural OCR + Rules + ELA/CNN Tampering + DeepFace Biometrics."
        icon={ShieldCheck}
        endpoint="POST /api/risk/assess"
        actions={
          result && (
            <motion.button
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={handleReset}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/30 text-cyan-400 font-mono text-xs transition-colors"
            >
              <RotateCcw size={14} />
              <span>New Scan</span>
            </motion.button>
          )
        }
      />

      {/* Error state */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 font-mono text-sm flex items-start gap-3"
        >
          <AlertTriangle size={18} className="text-rose-400 shrink-0 mt-0.5" />
          <div className="flex-1">
            <div className="font-semibold text-rose-400">Execution Error</div>
            <div className="text-xs text-rose-200/80 mt-1">{error}</div>
          </div>
          <button
            onClick={() => setError(null)}
            className="text-xs text-rose-400 hover:text-rose-200 underline"
          >
            Dismiss
          </button>
        </motion.div>
      )}

      {/* Loading Skeleton */}
      {loading && (
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-8"
        >
          {/* Top Score Row Skeleton */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="lg:col-span-1">
              <div className="flex flex-col items-center py-6 gap-4">
                <Skeleton variant="circular" width="140px" height="140px" />
                <Skeleton variant="text" width="100px" height="20px" />
                <Skeleton variant="text" width="60px" height="14px" />
              </div>
            </Card>

            <Card
              title={<Skeleton width="240px" height="20px" />}
              subtitle={<Skeleton width="300px" height="14px" />}
              icon={Layers}
              className="lg:col-span-2"
            >
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="p-4 rounded-xl bg-white/[0.02] border border-white/10">
                    <Skeleton variant="text" width="60%" />
                    <Skeleton variant="text" width="80px" height="28px" style={{ marginTop: '12px' }} />
                    <Skeleton variant="rounded" width="100%" height="6px" style={{ marginTop: '12px' }} />
                  </div>
                ))}
              </div>
            </Card>
          </div>

          {/* Module Panels Skeleton */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            {[1, 2, 3, 4].map((i) => (
              <Card key={i} title={<Skeleton width="200px" height="18px" />} subtitle={<Skeleton width="260px" height="13px" />}>
                <div className="space-y-3 mt-3">
                  {[1, 2, 3].map((j) => (
                    <div key={j} className="p-3 rounded-lg bg-white/[0.01] border border-white/5">
                      <Skeleton variant="text" width={`${40 + j * 15}%`} />
                      <Skeleton variant="text" width={`${60 + j * 5}%`} />
                    </div>
                  ))}
                </div>
              </Card>
            ))}
          </div>

          {/* Status text */}
          <div className="text-center">
            <p className="text-xs text-slate-400 font-mono animate-pulse">
              {status || 'Executing full multimodal forensic pipeline...'}
            </p>
          </div>
        </motion.div>
      )}

      {/* Upload Zone Form (Shown if no result yet or user wants to re-scan) */}
      {!result && !loading && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <UploadZone
              label="Document Image (Required)"
              hint="Passport, Visa, National ID, DL (JPG/PNG)"
              icon={FileText}
              file={docFile}
              onFileChange={setDocFile}
            />

            <LivenessCaptureCard
              onVerified={(verifiedBlob) => {
                setSelfieFile(verifiedBlob);
              }}
              onResetVerified={() => {
                setSelfieFile(null);
              }}
            />
          </div>

          <div className="flex justify-end">
            <motion.button
              whileHover={{ scale: 1.02, boxShadow: '0 0 25px rgba(6, 182, 212, 0.4)' }}
              whileTap={{ scale: 0.98 }}
              disabled={!docFile || loading}
              onClick={handleAssess}
              className={`flex items-center gap-3 px-6 py-3.5 rounded-xl font-mono text-sm font-bold tracking-wider uppercase transition-all ${
                docFile
                  ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-lg cursor-pointer'
                  : 'bg-white/5 border border-white/10 text-slate-500 cursor-not-allowed'
              }`}
            >
              <span>Run Pipeline Assessment</span>
              <ArrowRight size={16} />
            </motion.button>
          </div>
        </div>
      )}

      {/* Results View */}
      {result && !loading && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="space-y-8"
        >
          {/* Top Score Row */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Risk Gauge */}
            <Card className="lg:col-span-1" glowColor={scoreToHex(risk_score)}>
              <RiskGauge score={risk_score} label={risk_label} />
              {decision && (
                <div className="mt-4 pt-4 border-t border-white/10 text-center">
                  <span className="text-[10px] font-mono uppercase text-slate-400">
                    AUTOMATED DECISION
                  </span>
                  <div className="font-mono text-sm font-bold mt-0.5 text-cyan-300">
                    {typeof decision === 'object' ? JSON.stringify(decision) : String(decision)}
                  </div>
                </div>
              )}
            </Card>

            {/* Component Breakdown */}
            <Card
              title="Component Risk Contribution"
              subtitle="Weighted multimodal confidence distribution"
              icon={Layers}
              className="lg:col-span-2"
            >
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-2">
                {[
                  {
                    key: 'validation',
                    label: 'MRZ / Format',
                    val: component_scores.validation ?? 0,
                    icon: ShieldCheck,
                  },
                  {
                    key: 'tampering',
                    label: 'Tampering / ELA',
                    val: component_scores.tampering ?? 0,
                    icon: Zap,
                  },
                  {
                    key: 'face',
                    label: 'Face Biometrics',
                    val: component_scores.face ?? 0,
                    icon: Sparkles,
                  },
                ].map(({ key, label, val, icon: ScoreIcon }) => {
                  const color = scoreToHex(val);
                  return (
                    <div
                      key={key}
                      className="p-4 rounded-xl bg-white/[0.02] border border-white/10 flex flex-col justify-between"
                    >
                      <div className="flex items-center justify-between text-xs font-mono text-slate-400">
                        <span>{label}</span>
                        <ScoreIcon size={14} style={{ color }} />
                      </div>
                      <div className="my-3">
                        <div className="text-2xl font-mono font-bold" style={{ color }}>
                          <AnimatedCounter value={val} duration={1.2} />
                          <span className="text-xs text-slate-500 font-normal"> /100</span>
                        </div>
                      </div>
                      <ProgressBar value={val} color={color} height={6} />
                    </div>
                  );
                })}
              </div>

              {reasons.length > 0 && (
                <div className="mt-4 pt-4 border-t border-white/10">
                  <span className="text-xs font-mono text-slate-400">PRIMARY RISK FACTORS:</span>
                  <div className="mt-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300/90 font-mono text-xs flex items-center gap-2">
                    <span className="text-amber-400">›</span>
                    <span>
                      Detected {reasons.length} risk flag{reasons.length > 1 ? 's' : ''}. Check the Automated Risk & Anomaly Flags section below for detailed info.
                    </span>
                  </div>
                </div>
              )}
            </Card>
          </div>

          {/* Flags Banner if any */}
          {flags.length > 0 && <FlagsList flags={flags} />}

          {/* Module Deep-Dive Panels */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <OcrResults ocr={ocr} />
            <ValidationPanel validation={validation} />
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <TamperingPanel tampering={tampering} />
            <FacePanel face={face} />
          </div>

          {/* Operations & Audit Trails */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <AuditPanel audit={audit} />
            <TimelinePanel timeline={timeline} />
          </div>

          {/* Raw JSON Debug Viewer */}
          <RawJsonViewer data={result} title="Pipeline Full Assessment Response JSON" />
        </motion.div>
      )}
    </div>
  );
}
