import { motion } from 'motion/react';
import {
  AlertTriangle,
  CheckCircle2,
  AlertOctagon,
  Flame,
  ShieldCheck,
} from 'lucide-react';
import { Card, Badge } from '../common';

export function FlagsList({ flags = [] }) {
  if (!flags || flags.length === 0) {
    return (
      <Card
        title="Automated Anomaly & Fraud Flags"
        subtitle="Zero anomalies detected"
        icon={ShieldCheck}
        iconBg="rgba(16, 185, 129, 0.12)"
        iconColor="var(--risk-low)"
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flags-clean"
        >
          <CheckCircle2 size={24} className="flags-clean__icon" />
          <div className="flags-clean__text">
            <strong>Clean Screening Profile</strong>
            <p>No high-risk fraud markers or heuristic anomalies triggered across any module.</p>
          </div>
        </motion.div>
      </Card>
    );
  }

  const getFlagSeverity = (flag) => {
    const text = (typeof flag === 'string' ? flag : flag.message || flag.name || '').toLowerCase();
    if (text.includes('tamper') || text.includes('fake') || text.includes('fail') || text.includes('mismatch')) {
      return 'high';
    }
    if (text.includes('warn') || text.includes('expired') || text.includes('missing') || text.includes('low')) {
      return 'medium';
    }
    return 'info';
  };

  return (
    <Card
      title="Automated Risk & Anomaly Flags"
      subtitle={`${flags.length} potential risk indicator${flags.length > 1 ? 's' : ''} detected`}
      icon={AlertTriangle}
      iconBg="rgba(244, 63, 94, 0.12)"
      iconColor="var(--risk-high)"
      action={<Badge label={`${flags.length} ACTIVE FLAGS`} variant="high" />}
    >
      <div className="flags-list">
        {flags.map((flag, idx) => {
          const text = typeof flag === 'string' ? flag : flag.message || flag.name || JSON.stringify(flag);
          const severity = getFlagSeverity(flag);
          const Icon = severity === 'high' ? Flame : AlertTriangle;

          return (
            <motion.div
              key={idx}
              initial={{ opacity: 0, x: -15 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.4, delay: idx * 0.08, ease: [0.16, 1, 0.3, 1] }}
              whileHover={{ x: 6, scale: 1.01 }}
              className={`flag-item flag-item--${severity}`}
            >
              <div className="flag-item__icon-wrap">
                <Icon size={16} className="flag-item__icon" />
              </div>
              <div className="flag-item__content">
                <div className="flag-item__text">{text}</div>
                <div className="flag-item__severity">Severity Level: {severity.toUpperCase()}</div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </Card>
  );
}
