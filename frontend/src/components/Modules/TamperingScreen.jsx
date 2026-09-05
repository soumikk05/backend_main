import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Scan,
  AlertTriangle,
  Cpu,
  Layers,
  Eye,
  ShieldCheck,
  ShieldAlert,
  Flame,
  RotateCcw,
  Sparkles,
  ArrowRight,
  Fingerprint,
  Info,
  Binary,
} from 'lucide-react';
import { screeningApi } from '../../api/screening.api';
import { ModuleHeader } from './ModuleHeader';
import { RawJsonViewer } from './RawJsonViewer';
import { UploadZone } from '../Upload/UploadZone';
import { Card, Badge, ProgressBar, Skeleton, CheckItem } from '../common';
import { scoreToHex } from '../../utils/helpers';

export function TamperingScreen() {
  const [docFile, setDocFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tamperingResult, setTamperingResult] = useState(null);
  const [cnnResult, setCnnResult] = useState(null);

  const handleAnalyze = async () => {
    if (!docFile) return;
    setLoading(true);
    setError(null);

    try {
      // Run both classical forensic tampering analysis and deep CNN forgery scoring in parallel
      const [tamperingData, cnnData] = await Promise.allSettled([
        screeningApi.analyzeTampering(docFile),
        screeningApi.cnnScore(docFile),
      ]);

      if (tamperingData.status === 'fulfilled') {
        setTamperingResult(tamperingData.value);
      } else {
        throw tamperingData.reason;
      }

      if (cnnData.status === 'fulfilled') {
        setCnnResult(cnnData.value);
      }
    } catch (err) {
      console.error(err);
      setError(
        err.response?.data?.detail ||
          err.message ||
          'Tampering analysis failed. Please verify document format.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setDocFile(null);
    setTamperingResult(null);
    setCnnResult(null);
    setError(null);
  };

  const tamperingScore = tamperingResult?.tampering_score ?? 0;
  const isTampered = tamperingScore > 40;
  const checks = tamperingResult?.checks || [];
  const detectors = tamperingResult?.detectors || {};
  const heatmap = tamperingResult?.heatmap;

  const color = scoreToHex(tamperingScore);

  return (
    <div className="space-y-6">
      <ModuleHeader
        badge="MODULE 04"
        title="Tampering & Forgery Analysis"
        subtitle="Multi-signal forensic matrix: Error Level Analysis (ELA) + EXIF anomaly + ORB copy-move + Stamp + Deep CNN classification."
        icon={Scan}
        endpoint="POST /api/tampering/analyze & /cnn-score"
        actions={
          tamperingResult && (
            <motion.button
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={handleReset}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 font-mono text-xs transition-colors"
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
            <div className="font-semibold text-rose-400">Forensic Analysis Error</div>
            <div className="text-xs text-rose-200/80 mt-1">{error}</div>
          </div>
        </motion.div>
      )}

      {/* Loading Skeleton */}
      {loading && (
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card icon={Scan} title={<Skeleton width="180px" height="18px" />} subtitle={<Skeleton width="240px" height="13px" />}>
              <div className="py-2 flex flex-col items-center gap-3">
                <Skeleton variant="text" width="120px" height="48px" />
                <Skeleton variant="rounded" width="100%" height="8px" />
                <Skeleton variant="text" width="200px" height="12px" />
              </div>
            </Card>

            <Card title={<Skeleton width="260px" height="18px" />} subtitle={<Skeleton width="280px" height="13px" />} className="lg:col-span-2">
              <div className="space-y-4 mt-2">
                <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/10 flex items-center justify-between">
                  <div>
                    <Skeleton variant="text" width="140px" />
                    <Skeleton variant="text" width="80px" height="28px" style={{ marginTop: '4px' }} />
                  </div>
                  <Skeleton variant="rounded" width="160px" height="28px" />
                </div>
                <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/10">
                  <Skeleton variant="text" width="120px" />
                  <Skeleton variant="text" width="90%" style={{ marginTop: '8px' }} />
                </div>
              </div>
            </Card>
          </div>

          <Card title={<Skeleton width="200px" height="18px" />} subtitle={<Skeleton width="260px" height="13px" />}>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-2">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div key={i} className="p-3.5 rounded-xl bg-white/[0.02] border border-white/10">
                  <Skeleton variant="text" width="60%" />
                  <Skeleton variant="text" width="70px" height="24px" style={{ marginTop: '8px' }} />
                  <Skeleton variant="text" width="50%" style={{ marginTop: '8px' }} />
                </div>
              ))}
            </div>
          </Card>
        </motion.div>
      )}

      {/* Upload Form */}
      {!tamperingResult && !loading && (
        <div className="space-y-6">
          <UploadZone
            label="Upload Document Image for Forgery Screening"
            hint="Supports JPG, PNG, TIFF, BMP (Analyzes raw pixel compression & metadata)"
            icon={Scan}
            file={docFile}
            onFileChange={setDocFile}
          />

          <div className="flex justify-end">
            <motion.button
              whileHover={{ scale: 1.02, boxShadow: '0 0 25px rgba(6, 182, 212, 0.4)' }}
              whileTap={{ scale: 0.98 }}
              disabled={!docFile || loading}
              onClick={handleAnalyze}
              className={`flex items-center gap-3 px-6 py-3 rounded-xl font-mono text-sm font-bold tracking-wider uppercase transition-all ${
                docFile
                  ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-lg cursor-pointer'
                  : 'bg-white/5 border border-white/10 text-slate-500 cursor-not-allowed'
              }`}
            >
              <span>Analyze Tampering</span>
              <ArrowRight size={16} />
            </motion.button>
          </div>
        </div>
      )}

      {/* Results View */}
      {tamperingResult && !loading && (
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="space-y-6"
        >
          {/* Top Score Banner */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card
              title="Tampering Risk Index"
              subtitle="Composite multi-signal anomaly index"
              icon={Scan}
              action={
                <Badge
                  label={isTampered ? 'SUSPICIOUS / TAMPERED' : 'AUTHENTIC PIXELS'}
                  variant={isTampered ? 'high' : 'pass'}
                  icon={isTampered ? ShieldAlert : ShieldCheck}
                />
              }
              glowColor={color}
              className="lg:col-span-1"
            >
              <div className="py-2 text-center">
                <div className="text-5xl font-mono font-bold" style={{ color }}>
                  {tamperingScore.toFixed(1)}
                  <span className="text-sm text-slate-500 font-normal"> /100</span>
                </div>
                <div className="mt-4">
                  <ProgressBar value={tamperingScore} color={color} height={8} />
                </div>
                <p className="text-xs font-mono text-slate-400 mt-3">
                  {isTampered
                    ? 'High probability of digital tampering or localized text splicing detected.'
                    : 'Image compression matrices and sensor noise profiles appear natural.'}
                </p>
              </div>
            </Card>

            {/* Deep CNN Forgery Card */}
            <Card
              title="Convolutional Neural Forgery Model"
              subtitle="Deep spatial anomaly & patch classification"
              icon={Cpu}
              className="lg:col-span-2"
            >
              {cnnResult ? (
                <div className="space-y-4 mt-2">
                  <div className="flex items-center justify-between p-3.5 rounded-xl bg-white/[0.02] border border-white/10">
                    <div>
                      <div className="text-xs font-mono text-slate-400">CNN FORGERY PROBABILITY</div>
                      <div
                        className="text-2xl font-mono font-bold mt-0.5"
                        style={{ color: scoreToHex(cnnResult.cnn_score) }}
                      >
                        {cnnResult.cnn_score.toFixed(1)}%
                      </div>
                    </div>
                    <Badge
                      label={cnnResult.triggered ? 'ANOMALY DETECTED' : 'CLEAN SPATIAL MATRIX'}
                      variant={cnnResult.triggered ? 'high' : 'pass'}
                    />
                  </div>

                  <div className="p-3.5 rounded-xl bg-black/40 border border-white/5 font-mono text-xs text-slate-300">
                    <div className="text-slate-400 mb-1 flex items-center gap-1.5">
                      <Info size={12} className="text-cyan-400" />
                      <span>Model Inference Detail:</span>
                    </div>
                    <div>{cnnResult.detail || 'Spatial convolution completed without patch anomalies.'}</div>
                  </div>
                </div>
              ) : (
                <div className="text-xs font-mono text-slate-400 p-4 text-center">
                  CNN model not loaded or bypassed.
                </div>
              )}
            </Card>
          </div>

          {/* Detector Signals Grid */}
          <Card
            title="Forensic Detector Signals"
            subtitle="Individual algorithmic detector readings"
            icon={Layers}
          >
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-2">
              {Object.keys(detectors).length > 0 ? (
                Object.entries(detectors).map(([key, val]) => {
                  const detVal = typeof val === 'number' ? val.toFixed(1) : String(val);
                  const isHigh = typeof val === 'number' && val > 40;
                  return (
                    <div
                      key={key}
                      className="p-3.5 rounded-xl bg-white/[0.02] border border-white/10 flex flex-col justify-between"
                    >
                      <div className="flex items-center justify-between text-xs font-mono text-slate-400">
                        <span className="capitalize">{key.replace(/_/g, ' ')}</span>
                        <Binary size={13} className="text-cyan-400" />
                      </div>
                      <div className="my-2">
                        <div
                          className={`text-xl font-mono font-bold ${
                            isHigh ? 'text-rose-400' : 'text-emerald-400'
                          }`}
                        >
                          {typeof val === 'number' ? `${detVal}%` : detVal}
                        </div>
                      </div>
                      <div className="text-[10px] font-mono text-slate-500">
                        {isHigh ? 'Triggered alert threshold' : 'Nominal range'}
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="col-span-3 text-xs font-mono text-slate-400 p-4 text-center">
                  Signal details processed in aggregated score.
                </div>
              )}
            </div>
          </Card>

          {/* Tampering Checks Breakdown */}
          {checks.length > 0 && (
            <Card
              title="Forensic Check Details"
              subtitle={`${checks.length} checks performed`}
              icon={Fingerprint}
            >
              <div className="space-y-2 mt-2">
                {checks.map((chk, idx) => (
                  <CheckItem
                    key={idx}
                    name={chk.name}
                    passed={!chk.triggered}
                    reason={`${chk.detail} (Score: ${chk.score?.toFixed(1)}%)`}
                    delay={idx * 0.05}
                  />
                ))}
              </div>
            </Card>
          )}

          {/* Raw JSON Debug */}
          <RawJsonViewer
            data={{ tampering: tamperingResult, cnn: cnnResult }}
            title="Tampering Analysis & CNN Response JSON"
          />
        </motion.div>
      )}
    </div>
  );
}
