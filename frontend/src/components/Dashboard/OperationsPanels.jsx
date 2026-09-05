import { motion } from 'motion/react';
import { Card } from '../common';
import { Clock, Shield, Database, Activity } from 'lucide-react';

export const AuditPanel = ({ audit }) => {
  if (!audit || !audit.audit_hash) return null;

  return (
    <div id="audit" className="scroll-mt-24">
      <Card
        icon={Database}
        title="Blockchain Audit Trail"
        subtitle="Tamper-Evident Cryptographic Ledger"
      >
        <div className="space-y-3 font-mono text-sm mt-3">
          <div
            className="flex justify-between pb-2"
            style={{ borderBottom: '1px solid var(--border-subtle)' }}
          >
            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Timestamp</span>
            <span style={{ color: 'var(--accent)', fontWeight: 700, fontSize: '0.8125rem' }}>
              {new Date(audit.timestamp).toLocaleString()}
            </span>
          </div>
          <div
            className="flex justify-between pb-2"
            style={{ borderBottom: '1px solid var(--border-subtle)' }}
          >
            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Inspecting Officer</span>
            <span style={{ color: 'var(--accent)', fontWeight: 700, fontSize: '0.8125rem' }}>
              {audit.officer || 'SYSTEM_AUTO'}
            </span>
          </div>
          <div
            className="flex flex-col gap-1 pb-2"
            style={{ borderBottom: '1px solid var(--border-subtle)' }}
          >
            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Previous Hash Link</span>
            <span
              className="text-xs break-all p-2 rounded"
              style={{
                color: 'var(--risk-high)',
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-subtle)',
                fontFamily: 'var(--font-mono)',
                fontSize: '0.6875rem',
              }}
            >
              {audit.previous_hash || 'GENESIS_BLOCK'}
            </span>
          </div>
          <div className="flex flex-col gap-1">
            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Current Cryptographic Signature</span>
            <span
              className="text-xs break-all p-2 rounded"
              style={{
                color: 'var(--risk-low)',
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-subtle)',
                fontFamily: 'var(--font-mono)',
                fontSize: '0.6875rem',
              }}
            >
              {audit.audit_hash}
            </span>
          </div>
        </div>
      </Card>
    </div>
  );
};

export const TimelinePanel = ({ timeline }) => {
  if (!timeline || Object.keys(timeline).length === 0) return null;

  return (
    <div id="timeline" className="scroll-mt-24">
      <Card
        icon={Activity}
        title="Processing Metrics"
        subtitle="Micro-service Execution Times"
      >
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3">
          {Object.entries(timeline).map(([stage, ms], idx) => (
            <motion.div
              key={stage}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: idx * 0.1 }}
              whileHover={{ scale: 1.03 }}
              className="p-3 flex flex-col justify-center items-center gap-1.5 relative overflow-hidden group"
              style={{
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                transition: 'border-color var(--duration-fast) ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'var(--accent)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--border-subtle)';
              }}
            >
              <div
                className="absolute bottom-0 left-0 h-0.5"
                style={{
                  width: `${Math.min(100, (ms / 2000) * 100)}%`,
                  background: `linear-gradient(90deg, transparent, var(--accent))`,
                  opacity: 0.6,
                }}
              />
              <span
                className="text-xs font-mono uppercase tracking-wider"
                style={{ color: 'var(--text-muted)', fontSize: '0.625rem' }}
              >
                {stage}
              </span>
              <span className="font-bold font-mono" style={{ color: 'var(--text-primary)', fontSize: '1.25rem' }}>
                {ms}{' '}
                <span style={{ color: 'var(--accent)', fontSize: '0.625rem' }}>ms</span>
              </span>
            </motion.div>
          ))}
        </div>
      </Card>
    </div>
  );
};
