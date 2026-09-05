import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import {
  FileText,
  User,
  Calendar,
  Globe,
  Hash,
  Fingerprint,
  RotateCcw,
  AlertTriangle,
  ArrowRight,
  Sparkles,
  Tag,
  Check,
  Copy,
  Cpu,
} from 'lucide-react';
import { screeningApi } from '../../api/screening.api';
import { ModuleHeader } from './ModuleHeader';
import { RawJsonViewer } from './RawJsonViewer';
import { UploadZone } from '../Upload/UploadZone';
import { Card, Badge, Skeleton } from '../common';

const getFieldText = (val) => {
  if (val === null || val === undefined) return null;
  if (typeof val === 'object') {
    if (val.value !== undefined && val.value !== null) return String(val.value);
    return JSON.stringify(val);
  }
  return String(val);
};

export function OcrScreen() {
  const navigate = useNavigate();
  const [docFile, setDocFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [copiedField, setCopiedField] = useState(null);

  const handleExtract = async () => {
    if (!docFile) return;
    setLoading(true);
    setError(null);

    try {
      const data = await screeningApi.extractOcr(docFile);
      setResult(data);
    } catch (err) {
      console.error(err);
      setError(
        err.response?.data?.detail ||
          err.message ||
          'OCR Extraction failed. Please verify document resolution and format.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setDocFile(null);
    setResult(null);
    setError(null);
  };

  const handleSendToValidation = () => {
    if (!result) return;
    navigate('/validation', { state: { initialExtraction: result } });
  };

  const handleCopy = (val, key) => {
    if (!val) return;
    navigator.clipboard.writeText(typeof val === 'object' ? JSON.stringify(val) : String(val));
    setCopiedField(key);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const fields = result?.fields || {};
  const confidence = result?.confidence || {};
  const docType = result?.document_type || 'UNKNOWN';
  const engine = result?.engine || 'PassportEye / EasyOCR';
  const rawMrz = result?.raw_mrz || fields?.raw_mrz || fields?.raw_mrz_text;

  const normalizedFieldList = [
    { key: 'document_type', label: 'Document Type', value: docType, icon: Tag },
    {
      key: 'document_number',
      label: 'Document Number',
      value: getFieldText(fields.document_number) || getFieldText(fields.doc_number) || getFieldText(fields.passport_number),
      icon: Hash,
    },
    {
      key: 'name',
      label: 'Holder Name',
      value: getFieldText(fields.name) || getFieldText(fields.full_name) || `${getFieldText(fields.given_names) || ''} ${getFieldText(fields.surname) || ''}`.trim(),
      icon: User,
    },
    {
      key: 'nationality',
      label: 'Nationality / Country',
      value: getFieldText(fields.nationality) || getFieldText(fields.country) || getFieldText(fields.state),
      icon: Globe,
    },
    {
      key: 'dob',
      label: 'Date of Birth',
      value: getFieldText(fields.dob) || getFieldText(fields.date_of_birth),
      icon: Calendar,
    },
    {
      key: 'issue_date',
      label: 'Date of Issue',
      value: getFieldText(fields.issue_date),
      icon: Calendar,
    },
    {
      key: 'expiry_date',
      label: 'Expiration Date',
      value: getFieldText(fields.expiry_date) || getFieldText(fields.expiration_date),
      icon: Calendar,
    },
    {
      key: 'sex',
      label: 'Sex / Gender',
      value: getFieldText(fields.sex) || getFieldText(fields.gender),
      icon: User,
    },
    {
      key: 'personal_number',
      label: 'Personal ID No',
      value: getFieldText(fields.personal_number) || getFieldText(fields.national_id),
      icon: Fingerprint,
    },
  ].filter((f) => f.value && f.value !== '');

  // Catch other non-standard fields returned by OCR
  const otherFields = Object.entries(fields).filter(
    ([k]) =>
      ![
        'document_type',
        'document_number',
        'doc_number',
        'passport_number',
        'name',
        'full_name',
        'given_names',
        'surname',
        'nationality',
        'country',
        'state',
        'dob',
        'date_of_birth',
        'expiry_date',
        'expiration_date',
        'issue_date',
        'sex',
        'gender',
        'personal_number',
        'national_id',
        'raw_mrz',
        'raw_mrz_text',
        'raw_text_lines',
      ].includes(k)
  );

  return (
    <div className="space-y-6">
      <ModuleHeader
        badge="MODULE 02"
        title="OCR Extraction Engine"
        subtitle="Specialized dual-mode extractor for MRZ machine-readable zones and visual document fields."
        icon={FileText}
        endpoint="POST /api/ocr/extract"
        actions={
          result && (
            <div className="flex items-center gap-2">
              <motion.button
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                onClick={handleSendToValidation}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-emerald-400 font-mono text-xs transition-colors"
              >
                <span>Validate Extraction</span>
                <ArrowRight size={14} />
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                onClick={handleReset}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 font-mono text-xs transition-colors"
              >
                <RotateCcw size={14} />
                <span>Reset</span>
              </motion.button>
            </div>
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
            <div className="font-semibold text-rose-400">OCR Extraction Error</div>
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
          <div className="p-4 rounded-xl bg-black/40 border border-white/10 flex items-center justify-between">
            <Skeleton width="180px" height="24px" />
            <Skeleton width="120px" height="24px" />
          </div>

          <Card
            title={<Skeleton width="220px" height="20px" />}
            subtitle={<Skeleton width="280px" height="14px" />}
            icon={FileText}
          >
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-2">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div key={i} className="p-3.5 rounded-xl bg-white/[0.02] border border-white/10 flex flex-col justify-between" style={{ height: '90px' }}>
                  <Skeleton variant="text" width="40%" />
                  <Skeleton variant="text" width="70%" />
                </div>
              ))}
            </div>
            
            <div className="mt-6 pt-4 border-t border-white/10">
               <Skeleton variant="text" width="200px" />
               <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mt-3">
                 {[1, 2, 3].map((i) => (
                   <div key={i} className="p-3 rounded-lg bg-white/[0.01] border border-white/5">
                     <Skeleton variant="text" width="50%" />
                     <Skeleton variant="text" width="80%" />
                   </div>
                 ))}
               </div>
            </div>
          </Card>
        </motion.div>
      )}

      {/* Upload Zone */}
      {!result && !loading && (
        <div className="space-y-6">
          <UploadZone
            label="Upload Document for OCR Extraction"
            hint="Supports Passports, National IDs, Driver Licenses, and Visas (JPG, PNG)"
            icon={FileText}
            file={docFile}
            onFileChange={setDocFile}
          />

          <div className="flex justify-end">
            <motion.button
              whileHover={{ scale: 1.02, boxShadow: '0 0 25px rgba(6, 182, 212, 0.4)' }}
              whileTap={{ scale: 0.98 }}
              disabled={!docFile || loading}
              onClick={handleExtract}
              className={`flex items-center gap-3 px-6 py-3 rounded-xl font-mono text-sm font-bold tracking-wider uppercase transition-all ${
                docFile
                  ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-lg cursor-pointer'
                  : 'bg-white/5 border border-white/10 text-slate-500 cursor-not-allowed'
              }`}
            >
              <span>Extract Fields</span>
              <ArrowRight size={16} />
            </motion.button>
          </div>
        </div>
      )}

      {/* Extracted Fields Display */}
      {result && !loading && (
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="space-y-6"
        >
          {/* Header Metadata Bar */}
          <div className="p-4 rounded-xl bg-black/40 border border-white/10 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <span className="text-xs font-mono text-slate-400">DETECTED TYPE:</span>
              <Badge label={docType} variant="info" />
            </div>

            <div className="flex items-center gap-3">
              <span className="text-xs font-mono text-slate-400">OCR ENGINE:</span>
              <div className="flex items-center gap-1.5 text-xs font-mono text-cyan-400">
                <Cpu size={14} />
                <span>{engine}</span>
              </div>
            </div>
          </div>

          {/* Key Fields Grid */}
          <Card
            title="Structured Identity Payload"
            subtitle={`${normalizedFieldList.length} normalized fields identified`}
            icon={FileText}
          >
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-2">
              {normalizedFieldList.map((item) => {
                const Icon = item.icon;
                const confVal = confidence[item.key];
                const confPct = typeof confVal === 'number' ? Math.round(confVal * 100) : null;
                const isCopied = copiedField === item.key;

                return (
                  <motion.div
                    key={item.key}
                    whileHover={{ y: -2 }}
                    className="p-3.5 rounded-xl bg-white/[0.02] border border-white/10 hover:border-cyan-500/30 transition-all flex flex-col justify-between"
                  >
                    <div className="flex items-center justify-between text-xs font-mono text-slate-400 mb-2">
                      <div className="flex items-center gap-1.5">
                        <Icon size={13} className="text-cyan-400" />
                        <span>{item.label}</span>
                      </div>
                      {confPct !== null && (
                        <span
                          className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${
                            confPct >= 80
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                              : confPct >= 50
                              ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                              : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                          }`}
                        >
                          {confPct}% conf
                        </span>
                      )}
                    </div>

                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-sm font-bold text-white truncate select-all">
                        {String(item.value)}
                      </span>
                      <button
                        onClick={() => handleCopy(item.value, item.key)}
                        className="text-slate-500 hover:text-cyan-400 p-1 transition-colors shrink-0"
                        title="Copy field value"
                      >
                        {isCopied ? (
                          <Check size={13} className="text-emerald-400" />
                        ) : (
                          <Copy size={13} />
                        )}
                      </button>
                    </div>
                  </motion.div>
                );
              })}
            </div>

            {/* Other Dynamic Fields if any */}
            {otherFields.length > 0 && (
              <div className="mt-6 pt-4 border-t border-white/10">
                <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">
                  Additional Extracted Attributes
                </span>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mt-3">
                  {otherFields.map(([k, v]) => (
                    <div
                      key={k}
                      className="p-3 rounded-lg bg-white/[0.01] border border-white/5 font-mono text-xs"
                    >
                      <div className="text-slate-400 capitalize">{k.replace(/_/g, ' ')}:</div>
                      <div className="text-cyan-200 mt-0.5 break-all font-semibold">
                        {getFieldText(v)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Card>

          {/* Raw MRZ Section if present */}
          {rawMrz && (
            <Card
              title="Machine Readable Zone (MRZ)"
              subtitle="ICAO 9303 Conforming Lines"
              icon={Fingerprint}
            >
              <div className="p-4 rounded-xl bg-black/70 border border-white/10 font-mono text-xs text-emerald-400 tracking-widest leading-loose overflow-x-auto whitespace-pre">
                {Array.isArray(rawMrz) ? rawMrz.join('\n') : String(rawMrz)}
              </div>
            </Card>
          )}

          {/* Bottom Next Step Callout */}
          <div className="p-5 rounded-xl bg-cyan-500/5 border border-cyan-500/20 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div>
              <div className="font-mono text-sm font-bold text-white flex items-center gap-2">
                <Sparkles size={16} className="text-cyan-400" />
                <span>Ready for Logical & Checksum Validation?</span>
              </div>
              <p className="text-xs text-slate-400 mt-1 font-mono">
                Send this extracted identity payload directly to the Document Validation engine to verify MRZ checksums and date rules.
              </p>
            </div>
            <motion.button
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={handleSendToValidation}
              className="px-4 py-2 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-mono text-xs font-bold uppercase tracking-wider flex items-center gap-2 shadow-[0_0_20px_rgba(16,185,129,0.3)] shrink-0"
            >
              <span>Validate This Data</span>
              <ArrowRight size={14} />
            </motion.button>
          </div>

          {/* Raw JSON Debug */}
          <RawJsonViewer data={result} title="OCR Extraction Response JSON" />
        </motion.div>
      )}
    </div>
  );
}
