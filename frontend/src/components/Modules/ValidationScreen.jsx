import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import {
  CheckCircle2,
  XCircle,
  AlertOctagon,
  ShieldCheck,
  Code2,
  FileText,
  RotateCcw,
  Sparkles,
  ArrowRight,
  AlertTriangle,
  FileCheck,
  ListChecks,
} from 'lucide-react';
import { screeningApi } from '../../api/screening.api';
import { ModuleHeader } from './ModuleHeader';
import { RawJsonViewer } from './RawJsonViewer';
import { Card, Badge, CheckItem, Skeleton, ProgressBar } from '../common';
import { UploadZone } from '../Upload/UploadZone';

const SAMPLE_PASSPORT_JSON = {
  document_type: "PASSPORT",
  fields: {
    document_number: "P12345678",
    name: "SAMPLE CITIZEN",
    surname: "CITIZEN",
    given_names: "SAMPLE",
    nationality: "USA",
    country: "USA",
    dob: "1990-05-15",
    expiry_date: "2030-05-15",
    sex: "M",
    raw_mrz_text: "P<USACITIZEN<<SAMPLE<<<<<<<<<<<<<<<<<<<<<<<\nP123456782USA9005156M3005154<<<<<<<<<<<<<<06"
  },
  confidence: {
    document_number: 0.95,
    name: 0.92,
    nationality: 0.98,
    dob: 0.94,
    expiry_date: 0.96
  }
};

const SAMPLE_EXPIRED_JSON = {
  document_type: "PASSPORT",
  fields: {
    document_number: "A87654321",
    name: "EXPIRED USER",
    nationality: "IND",
    dob: "1985-01-01",
    expiry_date: "2020-01-01", // Expired
    sex: "F"
  },
  confidence: {
    document_number: 0.9,
    expiry_date: 0.88
  }
};

export function ValidationScreen() {
  const location = useLocation();
  const [activeTab, setActiveTab] = useState('json'); // 'json' or 'doc'
  const [jsonText, setJsonText] = useState(
    JSON.stringify(location.state?.initialExtraction || SAMPLE_PASSPORT_JSON, null, 2)
  );
  const [quickDocFile, setQuickDocFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  // If navigated with state from OCR module, auto populate and run
  useEffect(() => {
    if (location.state?.initialExtraction) {
      const data = location.state.initialExtraction;
      setJsonText(JSON.stringify(data, null, 2));
      runValidationDirect(data);
    }
  }, [location.state]);

  const runValidationDirect = async (payload) => {
    setLoading(true);
    setError(null);
    try {
      const res = await screeningApi.checkValidation(payload);
      setResult(res);
    } catch (err) {
      console.error(err);
      setError(
        err.response?.data?.detail ||
          err.message ||
          'Validation failed. Please verify the JSON input schema.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleValidateJson = () => {
    try {
      const parsed = JSON.parse(jsonText);
      runValidationDirect(parsed);
    } catch (err) {
      setError(`Invalid JSON syntax: ${err.message}`);
    }
  };

  const handleQuickExtractAndValidate = async () => {
    if (!quickDocFile) return;
    setLoading(true);
    setError(null);
    try {
      const ocrData = await screeningApi.extractOcr(quickDocFile);
      setJsonText(JSON.stringify(ocrData, null, 2));
      const valData = await screeningApi.checkValidation(ocrData);
      setResult(valData);
    } catch (err) {
      console.error(err);
      setError(
        err.response?.data?.detail ||
          err.message ||
          'OCR extraction or validation failed.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setResult(null);
    setError(null);
  };

  // Result metrics
  const isValid = result?.valid ?? false;
  const checks = result?.checks || [];
  const passCount = result?.pass_count ?? checks.filter((c) => c.passed).length;
  const failCount = result?.fail_count ?? checks.filter((c) => !c.passed).length;
  const passedRules = result?.passed_rules || [];
  const failedRules = result?.failed_rules || [];
  const warnings = result?.warnings || [];

  return (
    <div className="space-y-6">
      <ModuleHeader
        badge="MODULE 03"
        title="Document Rule Validation"
        subtitle="Rule-based logical validation engine for ICAO checksums, expiration dates, and formatting rules."
        icon={CheckCircle2}
        endpoint="POST /api/validation/check"
        actions={
          result && (
            <motion.button
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={handleReset}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 font-mono text-xs transition-colors"
            >
              <RotateCcw size={14} />
              <span>Modify Input</span>
            </motion.button>
          )
        }
      />

      {/* Error display */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 font-mono text-sm flex items-start gap-3"
        >
          <AlertTriangle size={18} className="text-rose-400 shrink-0 mt-0.5" />
          <div className="flex-1">
            <div className="font-semibold text-rose-400">Validation Error</div>
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
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card icon={ShieldCheck} title={<Skeleton width="200px" height="18px" />} subtitle={<Skeleton width="160px" height="13px" />}>
              <div className="py-4 flex flex-col items-center gap-3">
                <Skeleton variant="text" width="120px" height="36px" />
                <Skeleton variant="text" width="200px" height="12px" />
              </div>
            </Card>

            <Card title={<Skeleton width="180px" height="18px" />} subtitle={<Skeleton width="240px" height="13px" />} className="md:col-span-2">
              <div className="grid grid-cols-2 gap-4 mt-2">
                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/10">
                  <Skeleton variant="text" width="80px" />
                  <Skeleton variant="text" width="50px" height="28px" style={{ marginTop: '8px' }} />
                </div>
                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/10">
                  <Skeleton variant="text" width="80px" />
                  <Skeleton variant="text" width="50px" height="28px" style={{ marginTop: '8px' }} />
                </div>
              </div>
            </Card>
          </div>

          <Card title={<Skeleton width="220px" height="18px" />} subtitle={<Skeleton width="200px" height="13px" />}>
            <div className="space-y-2 mt-2">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-white/[0.01] border border-white/5">
                  <Skeleton variant="circular" width="28px" height="28px" />
                  <div style={{ flex: 1 }}>
                    <Skeleton variant="text" width={`${50 + i * 8}%`} />
                    <Skeleton variant="text" width={`${30 + i * 10}%`} />
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </motion.div>
      )}

      {/* Input Mode Selector & Editor (If no result or user editing) */}
      {!result && !loading && (
        <div className="space-y-6">
          {/* Mode Tabs */}
          <div className="flex items-center gap-2 p-1 rounded-xl bg-black/40 border border-white/10 w-fit">
            <button
              onClick={() => setActiveTab('json')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-mono text-xs transition-all ${
                activeTab === 'json'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-bold shadow-[0_0_15px_rgba(6,182,212,0.2)]'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Code2 size={14} />
              <span>OCR JSON Payload</span>
            </button>
            <button
              onClick={() => setActiveTab('doc')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-mono text-xs transition-all ${
                activeTab === 'doc'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-bold shadow-[0_0_15px_rgba(6,182,212,0.2)]'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <FileText size={14} />
              <span>Quick Upload & Validate</span>
            </button>
          </div>

          {activeTab === 'json' ? (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <span className="font-mono text-xs text-slate-400">
                  Input JSON with <code className="text-cyan-400">document_type</code> and <code className="text-cyan-400">fields</code>:
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setJsonText(JSON.stringify(SAMPLE_PASSPORT_JSON, null, 2))}
                    className="px-2.5 py-1 text-xs font-mono rounded bg-white/5 hover:bg-white/10 text-cyan-300 border border-white/10 transition-colors"
                  >
                    Load Valid Sample
                  </button>
                  <button
                    onClick={() => setJsonText(JSON.stringify(SAMPLE_EXPIRED_JSON, null, 2))}
                    className="px-2.5 py-1 text-xs font-mono rounded bg-white/5 hover:bg-white/10 text-rose-300 border border-white/10 transition-colors"
                  >
                    Load Expired Sample
                  </button>
                </div>
              </div>

              <div className="relative rounded-xl border border-white/10 bg-[#030712]/90 p-4">
                <textarea
                  rows={14}
                  value={jsonText}
                  onChange={(e) => setJsonText(e.target.value)}
                  className="w-full bg-transparent font-mono text-xs text-cyan-200 focus:outline-none leading-relaxed resize-y"
                  placeholder='{ "document_type": "PASSPORT", "fields": { ... } }'
                  spellCheck="false"
                />
              </div>

              <div className="flex justify-end">
                <motion.button
                  whileHover={{ scale: 1.02, boxShadow: '0 0 25px rgba(6, 182, 212, 0.4)' }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleValidateJson}
                  className="flex items-center gap-3 px-6 py-3 rounded-xl font-mono text-sm font-bold tracking-wider uppercase bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-lg cursor-pointer"
                >
                  <span>Execute Validation Engine</span>
                  <ArrowRight size={16} />
                </motion.button>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              <UploadZone
                label="Upload document to extract OCR & validate automatically"
                hint="Passes OCR results directly into the validation rules"
                icon={FileText}
                file={quickDocFile}
                onFileChange={setQuickDocFile}
              />

              <div className="flex justify-end">
                <motion.button
                  whileHover={{ scale: 1.02, boxShadow: '0 0 25px rgba(6, 182, 212, 0.4)' }}
                  whileTap={{ scale: 0.98 }}
                  disabled={!quickDocFile || loading}
                  onClick={handleQuickExtractAndValidate}
                  className={`flex items-center gap-3 px-6 py-3 rounded-xl font-mono text-sm font-bold tracking-wider uppercase transition-all ${
                    quickDocFile
                      ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-lg cursor-pointer'
                      : 'bg-white/5 border border-white/10 text-slate-500 cursor-not-allowed'
                  }`}
                >
                  <span>Extract & Validate</span>
                  <ArrowRight size={16} />
                </motion.button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Validation Results Display */}
      {result && !loading && (
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="space-y-6"
        >
          {/* Top Overall Status Card */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card
              title="Overall Validation Result"
              subtitle={result.document_type ? `Target Doc: ${result.document_type}` : 'Logical Rule Engine'}
              icon={ShieldCheck}
              action={
                <Badge
                  label={isValid ? 'VALID' : 'INVALID'}
                  variant={isValid ? 'pass' : 'high'}
                  icon={isValid ? CheckCircle2 : XCircle}
                />
              }
              className="md:col-span-1"
            >
              <div className="py-4 text-center">
                <div
                  className={`text-4xl font-mono font-bold tracking-wider ${
                    isValid ? 'text-emerald-400' : 'text-rose-400'
                  }`}
                >
                  {isValid ? 'PASSED' : 'FAILED'}
                </div>
                <p className="text-xs font-mono text-slate-400 mt-2">
                  {isValid
                    ? 'All structural, checksum, and date integrity checks satisfied.'
                    : 'One or more mandatory logical validation rules failed.'}
                </p>
              </div>
            </Card>

            <Card
              title="Rule Check Summary"
              subtitle="Breakdown of rule passes and failures"
              icon={ListChecks}
              className="md:col-span-2"
            >
              <div className="grid grid-cols-2 gap-4 mt-2">
                <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                  <div className="text-xs font-mono text-emerald-400 uppercase">Checks Passed</div>
                  <div className="text-3xl font-mono font-bold text-emerald-300 mt-1">
                    {passCount}
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20">
                  <div className="text-xs font-mono text-rose-400 uppercase">Checks Failed</div>
                  <div className="text-3xl font-mono font-bold text-rose-300 mt-1">
                    {failCount}
                  </div>
                </div>
              </div>
            </Card>
          </div>

          {/* Detailed Check List */}
          <Card
            title="Individual Validation Rules"
            subtitle={`${checks.length} rule assertions evaluated`}
            icon={FileCheck}
          >
            <div className="space-y-2 mt-2">
              {checks.length > 0 ? (
                checks.map((c, idx) => (
                  <CheckItem
                    key={idx}
                    name={c.check_name || c.name || `Check #${idx + 1}`}
                    passed={c.passed ?? c.valid ?? false}
                    reason={c.reason || c.message || (c.passed ? 'Rule satisfied' : 'Rule failed')}
                    delay={idx * 0.05}
                  />
                ))
              ) : (
                <div className="text-xs font-mono text-slate-400 p-4 text-center">
                  No individual check details returned.
                </div>
              )}
            </div>
          </Card>

          {/* Warnings list if any */}
          {warnings.length > 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30"
            >
              <div className="flex items-center gap-2 font-mono text-xs text-amber-400 font-bold mb-2">
                <AlertTriangle size={15} />
                <span>NON-BLOCKING WARNINGS:</span>
              </div>
              <ul className="space-y-1 font-mono text-xs text-amber-200/90 pl-5 list-disc">
                {warnings.map((w, idx) => (
                  <li key={idx}>{w}</li>
                ))}
              </ul>
            </motion.div>
          )}

          {/* Raw JSON Debug */}
          <RawJsonViewer data={result} title="Validation Check Response JSON" />
        </motion.div>
      )}
    </div>
  );
}
