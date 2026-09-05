import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  FileText,
  Camera,
  ScanFace,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
} from 'lucide-react';
import { UploadZone } from './UploadZone';
import { Spinner } from '../common';

export function UploadPage({ onAnalyze, loading, status, error }) {
  const [docFile, setDocFile] = useState(null);
  const [selfieFile, setSelfieFile] = useState(null);

  const handleSubmit = () => {
    if (!docFile) return;
    onAnalyze(docFile, selfieFile);
  };

  return (
    <div className="upload-page">
      {/* Processing overlay */}
      <AnimatePresence>
        {loading && (
          <motion.div
            key="loader"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="loading-overlay"
          >
            <Spinner size="lg" />
            <div className="loading-overlay__text">
              {status || 'Processing document…'}
            </div>
            <div className="loading-overlay__sub">
              Executing multimodal pipeline: Neural OCR, Doc Validation, ELA/CNN Tampering, Biometrics & Risk Engine.
            </div>
            <div className="loading-overlay__steps">
              {[
                { icon: FileText, label: 'Neural OCR' },
                { icon: CheckCircle2, label: 'Doc Validation' },
                { icon: AlertTriangle, label: 'Tampering / ELA' },
                ...(selfieFile ? [{ icon: ScanFace, label: 'Face Biometrics' }] : []),
                { icon: CheckCircle2, label: 'Risk Score Engine' },
              ].map((step, i) => {
                const Icon = step.icon;
                return (
                  <motion.div
                    key={step.label}
                    className="loading-overlay__step"
                    animate={{ opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 1.5, repeat: Infinity, delay: i * 0.25 }}
                  >
                    <Icon size={13} />
                    <span>{step.label}</span>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Page heading */}
      <div className="upload-page__header">
        <h1 className="upload-page__title">Document Screening</h1>
        <p className="upload-page__desc">
          Upload an identity document for automated verification. The system performs
          OCR extraction, MRZ checksum validation, error-level analysis, and optional
          biometric face matching.
        </p>
      </div>

      {/* Error */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            className="error-banner"
          >
            <AlertTriangle size={15} />
            <span>{error}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Upload grid — asymmetric: document is primary */}
      <div className="upload-page__grid">
        <div className="upload-page__grid-item upload-page__grid-item--primary">
          <div className="upload-page__section-label">
            <FileText size={14} />
            <span>Identity Document</span>
            <span className="upload-page__required-tag">Required</span>
          </div>
          <UploadZone
            label="Drop document image"
            hint="Passport, visa, national ID — PNG, JPG, BMP"
            icon={FileText}
            file={docFile}
            onFileChange={setDocFile}
          />
        </div>

        <div className="upload-page__grid-item">
          <div className="upload-page__section-label">
            <Camera size={14} />
            <span>Live Selfie</span>
            <span className="upload-page__optional-tag">Optional</span>
          </div>
          <UploadZone
            label="Drop selfie for face match"
            hint="Compares live photo against document portrait"
            icon={ScanFace}
            file={selfieFile}
            onFileChange={setSelfieFile}
          />
        </div>
      </div>

      {/* Supported types — flat list, not cards */}
      <div className="upload-page__supported">
        <span className="upload-page__supported-label">Supported:</span>
        {['Passport', 'Visa Stamp', 'National ID', 'Driver License'].map((t) => (
          <span key={t} className="upload-page__supported-item">{t}</span>
        ))}
      </div>

      {/* Action */}
      <div className="upload-page__actions">
        <motion.button
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.99 }}
          className="btn btn--primary btn--lg"
          disabled={!docFile || loading}
          onClick={handleSubmit}
        >
          {loading ? (
            <>
              <Spinner size="sm" />
              <span>Analyzing…</span>
            </>
          ) : (
            <>
              <span>Run Analysis</span>
              <ArrowRight size={16} />
            </>
          )}
        </motion.button>
      </div>
    </div>
  );
}
