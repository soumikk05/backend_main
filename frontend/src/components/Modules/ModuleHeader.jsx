import { motion } from 'motion/react';
import { CyberText } from '../common';

export function ModuleHeader({
  badge = "MODULE",
  title,
  subtitle,
  icon: Icon,
  endpoint,
  actions
}) {
  return (
    <div
      className="mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5"
      style={{ borderBottom: '1px solid var(--border-subtle)' }}
    >
      <div className="flex items-start gap-4">
        {Icon && (
          <motion.div
            whileHover={{ scale: 1.05, rotate: 5 }}
            className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0"
            style={{
              background: 'rgba(229, 169, 60, 0.12)',
              border: '1px solid rgba(229, 169, 60, 0.35)',
              color: 'var(--accent)',
            }}
          >
            <Icon size={24} />
          </motion.div>
        )}

        <div>
          <div className="flex items-center gap-2 mb-1">
            <span
              className="px-2 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider"
              style={{
                background: 'rgba(229, 169, 60, 0.12)',
                border: '1px solid rgba(229, 169, 60, 0.35)',
                color: '#d97706',
                fontWeight: 700,
              }}
            >
              {badge}
            </span>
            {endpoint && (
              <span
                className="px-2 py-0.5 rounded text-[10px] font-mono"
                style={{
                  background: 'var(--surface-hover)',
                  border: '1px solid var(--border-subtle)',
                  color: 'var(--text-muted)',
                }}
              >
                {endpoint}
              </span>
            )}
          </div>
          <h1
            className="text-xl md:text-2xl font-bold font-mono tracking-wide"
            style={{ color: 'var(--text-primary)' }}
          >
            <CyberText text={title} />
          </h1>
          {subtitle && (
            <p className="text-xs md:text-sm mt-0.5" style={{ color: 'var(--text-secondary)' }}>
              {subtitle}
            </p>
          )}
        </div>
      </div>

      {actions && (
        <div className="flex items-center gap-2 shrink-0">
          {actions}
        </div>
      )}
    </div>
  );
}
