import { motion } from 'motion/react';
import { ShieldCheck, ShieldAlert, AlertTriangle } from 'lucide-react';
import { Badge } from '../common';
import { scoreToHex } from '../../utils/helpers';
import { AnimatedCounter } from '../common/AnimatedBg';

const RADIUS = 68;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export function RiskGauge({ score = 0, label = 'LOW' }) {
  const pct = Math.min(100, Math.max(0, score)) / 100;
  const targetOffset = CIRCUMFERENCE * (1 - pct);
  const color = scoreToHex(score);

  const getStatusIcon = () => {
    if (score <= 30) return ShieldCheck;
    if (score <= 65) return AlertTriangle;
    return ShieldAlert;
  };

  const StatusIcon = getStatusIcon();

  const glowColor = score <= 30
    ? 'rgba(16, 185, 129, 0.35)'
    : score <= 65
      ? 'rgba(245, 158, 11, 0.35)'
      : 'rgba(244, 63, 94, 0.35)';

  return (
    <div className="risk-gauge">
      <div
        className="risk-gauge__svg-wrap"
        style={{ '--gauge-glow': glowColor }}
      >
        <svg className="risk-gauge__svg" viewBox="0 0 200 200">
          {/* Background track */}
          <circle
            className="risk-gauge__track"
            cx="100"
            cy="100"
            r={RADIUS}
          />
          {/* Motion Animated Fill Circle */}
          <motion.circle
            className="risk-gauge__fill"
            cx="100"
            cy="100"
            r={RADIUS}
            stroke={color}
            strokeDasharray={CIRCUMFERENCE}
            initial={{ strokeDashoffset: CIRCUMFERENCE }}
            animate={{ strokeDashoffset: targetOffset }}
            transition={{ duration: 1.6, ease: [0.16, 1, 0.3, 1] }}
          />
        </svg>

        <div className="risk-gauge__center">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', stiffness: 400, damping: 15, delay: 0.3 }}
            className="risk-gauge__status-icon"
            style={{ color }}
          >
            <StatusIcon size={24} />
          </motion.div>

          <div className="risk-gauge__score" style={{ color }}>
            <AnimatedCounter value={score} duration={1.6} />
          </div>
          <div className="risk-gauge__of">RISK INDEX / 100</div>
        </div>
      </div>

      <div className="risk-gauge__label">
        <Badge
          label={`STATUS: ${label}`}
          variant={label.toLowerCase()}
          icon={StatusIcon}
        />
      </div>
    </div>
  );
}
