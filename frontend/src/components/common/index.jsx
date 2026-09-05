import { motion } from 'motion/react';
import './common.css';

export { AnimatedText } from './AnimatedBg';
export { CyberText } from './CyberText';

/**
 * Skeleton loading placeholder
 */
export function Skeleton({ variant = 'text', width = '100%', height = '16px', className = '', style = {} }) {
  const getRadius = () => {
    if (variant === 'circular') return '9999px';
    if (variant === 'rounded') return '8px';
    return '4px';
  };

  return (
    <div
      className={`skeleton animate-pulse ${className}`}
      style={{
        width,
        height: variant === 'circular' ? (width || height) : height,
        borderRadius: getRadius(),
        backgroundColor: 'rgba(255, 255, 255, 0.08)',
        display: 'inline-block',
        ...style,
      }}
    />
  );
}

/**
 * Clean professional Card with Motion hover animations
 */
export function Card({
  title,
  subtitle,
  icon: Icon,
  iconBg,
  iconColor,
  action,
  children,
  className = '',
  delay = 0,
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay, ease: [0.16, 1, 0.3, 1] }}
      whileHover={{
        y: -4,
        boxShadow: 'var(--card-shadow-hover)',
      }}
      className={`card ${className}`}
    >
      {(title || Icon || action) && (
        <div className="card__header">
          {Icon && (
            <motion.div
              whileHover={{ rotate: 5, scale: 1.1 }}
              transition={{ type: 'spring', stiffness: 400, damping: 15 }}
              className="card__icon"
              style={{
                background: iconBg || 'var(--accent-light)',
                color: iconColor || 'var(--accent)',
              }}
            >
              <Icon size={22} />
            </motion.div>
          )}
          <div style={{ flex: 1 }}>
            {title && <h3 className="card__title">{title}</h3>}
            {subtitle && <p className="card__subtitle">{subtitle}</p>}
          </div>
          {action && <div className="card__action">{action}</div>}
        </div>
      )}
      <div className="card__body">{children}</div>
    </motion.div>
  );
}

/**
 * Clean Badge
 */
export function Badge({ label, variant = 'neutral', icon: Icon, className = '' }) {
  const getVariantClass = () => {
    switch (variant.toLowerCase()) {
      case 'low':
      case 'pass':
      case 'verified':
        return 'badge--low';
      case 'medium':
      case 'warning':
      case 'suspicious':
        return 'badge--medium';
      case 'high':
      case 'fail':
      case 'fraud':
        return 'badge--high';
      case 'info':
        return 'badge--info';
      default:
        return 'badge--neutral';
    }
  };

  return (
    <motion.span
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      whileHover={{ scale: 1.05 }}
      transition={{ type: 'spring', stiffness: 500, damping: 20 }}
      className={`badge ${getVariantClass()} ${className}`}
    >
      {Icon && <Icon size={12} className="badge__icon" />}
      {label}
    </motion.span>
  );
}

/**
 * Clean Progress Bar
 */
export function ProgressBar({ value = 0, max = 100, color, showLabel = false, height = 8 }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));

  return (
    <div className="progress-container">
      <div className="progress" style={{ height: `${height}px` }}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
          className="progress__fill"
          style={{
            background: color || 'var(--accent)',
          }}
        />
      </div>
      {showLabel && (
        <div className="progress__label">
          <span>{Math.round(pct)}%</span>
        </div>
      )}
    </div>
  );
}

/**
 * Clean Spinner
 */
export function Spinner({ size = 'md', color = 'var(--accent)' }) {
  const sizeMap = { sm: 20, md: 36, lg: 60 };
  const dim = sizeMap[size] || 36;

  return (
    <div className={`spinner spinner--${size}`} style={{ width: dim, height: dim }}>
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
        className="spinner__ring"
        style={{ width: dim, height: dim, borderTopColor: color }}
      />
    </div>
  );
}

/**
 * Check Item with Motion animation
 */
export function CheckItem({ name, passed = true, reason, icon: CustomIcon, delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, delay, ease: [0.16, 1, 0.3, 1] }}
      whileHover={{ x: 4, backgroundColor: 'var(--surface-hover)' }}
      className={`check-item ${passed ? 'check-item--passed' : 'check-item--failed'}`}
    >
      <motion.div
        whileHover={{ scale: 1.15 }}
        transition={{ type: 'spring', stiffness: 400 }}
        className={`check-item__icon check-item__icon--${passed ? 'pass' : 'fail'}`}
      >
        {CustomIcon ? (
          <CustomIcon size={14} />
        ) : passed ? (
          <span>✓</span>
        ) : (
          <span>✕</span>
        )}
      </motion.div>
      <div className="check-item__content">
        <div className="check-item__name">{name}</div>
        {reason && <div className="check-item__reason">{reason}</div>}
      </div>
    </motion.div>
  );
}

/**
 * Stat Pill
 */
export function StatPill({ label, value, color, icon: Icon }) {
  return (
    <motion.div
      whileHover={{ y: -2, scale: 1.02 }}
      transition={{ type: 'spring', stiffness: 400, damping: 17 }}
      className="stat-pill"
    >
      {Icon && <Icon size={14} style={{ color: color || 'var(--text-muted)' }} />}
      <span className="stat-pill__label">{label}:</span>
      <span className="stat-pill__value" style={{ color: color || 'var(--text-primary)' }}>
        {value}
      </span>
    </motion.div>
  );
}
