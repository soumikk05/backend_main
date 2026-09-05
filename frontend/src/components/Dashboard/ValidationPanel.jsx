import { motion } from 'motion/react';
import {
  CheckCircle2,
  XCircle,
  AlertOctagon,
  ShieldCheck,
  Fingerprint,
} from 'lucide-react';
import { Card, Badge, CheckItem, ProgressBar } from '../common';
import { scoreToHex } from '../../utils/helpers';

export function ValidationPanel({ validation }) {
  if (!validation) {
    return (
      <Card title="Structural & MRZ Validation" subtitle="No validation data" icon={ShieldCheck}>
        <div className="empty-state">Validation module did not return results.</div>
      </Card>
    );
  }

  const score = Math.round(validation.consistency_score ?? validation.score ?? (validation.overall_valid ? 100 : 0));
  const isPassed = Boolean(validation.overall_valid ?? validation.valid ?? (validation.status === 'PASS'));
  const checks = validation.checks ?? [];
  const color = scoreToHex(score);

  return (
    <Card
      title="MRZ & Structural Validation"
      subtitle="Checksums, Expiration & Document Integrity"
      icon={ShieldCheck}
      action={
        <Badge
          label={isPassed ? 'VALID STRUCTURE' : 'VALIDATION FAILED'}
          variant={isPassed ? 'pass' : 'high'}
          icon={isPassed ? CheckCircle2 : XCircle}
        />
      }
    >
      {/* Score and Bar */}
      <div className="module-metric">
        <div className="module-metric__header">
          <span className="module-metric__label">Validation Integrity Score</span>
          <span className="module-metric__value" style={{ color }}>
            {score}/100
          </span>
        </div>
        <ProgressBar value={score} color={color} />
      </div>

      {/* Check details */}
      <div className="checks-list">
        {checks.length > 0 ? (
          checks.map((c, idx) => (
            <CheckItem
              key={idx}
              name={c.check_name || c.name || `Check #${idx + 1}`}
              passed={c.passed ?? c.valid ?? false}
              reason={c.reason || c.message}
              icon={c.passed ? CheckCircle2 : AlertOctagon}
              delay={idx * 0.06}
            />
          ))
        ) : (
          <div className="check-item-empty">
            <CheckItem
              name="MRZ Checksum Algorithm"
              passed={mrz_valid}
              reason={mrz_valid ? 'All check digits match computed hash' : 'Checksum mismatch or unreadable MRZ'}
              icon={Fingerprint}
            />
          </div>
        )}
      </div>
    </Card>
  );
}
