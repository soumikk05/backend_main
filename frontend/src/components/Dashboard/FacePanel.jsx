import { motion } from 'motion/react';
import {
  ScanFace,
  UserCheck,
  UserX,
  Sparkles,
  Percent,
  Layers,
  ShieldCheck,
  Info,
} from 'lucide-react';
import { Card, Badge, ProgressBar } from '../common';

export function FacePanel({ face }) {
  if (!face) {
    return (
      <Card
        title="Biometric Face Verification"
        subtitle="Optional live selfie comparison"
        icon={ScanFace}
      >
        <div className="empty-state">
          <Info size={16} className="empty-state__icon" />
          <span>No selfie provided during upload. Facial matching was bypassed.</span>
        </div>
      </Card>
    );
  }

  const match = Boolean(face.matched ?? face.match);
  const similarity_score = face.similarity ?? face.similarity_score ?? face.confidence;
  const face_detected_doc = Boolean(face.face_detected_document ?? face.face_detected_doc ?? true);
  const face_detected_selfie = Boolean(face.face_detected_selfie ?? true);
  const details = face.details || {};

  const simPct =
    similarity_score !== undefined
      ? Math.round(similarity_score * 100)
      : Math.round(confidence * 100);

  const getSimColor = (val) => {
    if (val >= 70) return 'var(--risk-low)';
    if (val >= 45) return 'var(--risk-medium)';
    return 'var(--risk-high)';
  };

  const simColor = getSimColor(simPct);

  return (
    <Card
      title="Biometric Face Verification"
      subtitle="Face comparison between document and selfie"
      icon={ScanFace}
      action={
        <Badge
          label={match ? 'FACE MATCH CONFIRMED' : 'FACE MISMATCH'}
          variant={match ? 'pass' : 'high'}
          icon={match ? UserCheck : UserX}
        />
      }
    >
      {/* Similarity Score */}
      <div className="module-metric">
        <div className="module-metric__header">
          <span className="module-metric__label">Similarity Score</span>
          <span className="module-metric__value" style={{ color: simColor }}>
            {simPct}%
          </span>
        </div>
        <ProgressBar value={simPct} color={simColor} />
      </div>

      {/* Face Status Grid */}
      <div className="face-grid">
        <motion.div
          whileHover={{ scale: 1.02 }}
          className="face-status-card"
        >
          <div className="face-status-card__header">
            <ScanFace size={15} className="face-status-card__icon" />
            <span>Document Portrait</span>
          </div>
          <div className="face-status-card__badge">
            <Badge
              label={face_detected_doc ? 'Detected & Extracted' : 'Missing Face'}
              variant={face_detected_doc ? 'pass' : 'high'}
            />
          </div>
        </motion.div>

        <motion.div
          whileHover={{ scale: 1.02 }}
          className="face-status-card"
        >
          <div className="face-status-card__header">
            <ScanFace size={15} className="face-status-card__icon" />
            <span>Selfie</span>
          </div>
          <div className="face-status-card__badge">
            <Badge
              label={face_detected_selfie ? 'Detected & Extracted' : 'Missing Face'}
              variant={face_detected_selfie ? 'pass' : 'high'}
            />
          </div>
        </motion.div>
      </div>

      {/* Model Spec Note */}
      <div className="face-spec-footer">
        <Sparkles size={13} className="face-spec-footer__icon" />
        <span>Facenet512 · Distance Threshold: 0.30 · MTCNN Alignment</span>
      </div>
    </Card>
  );
}
