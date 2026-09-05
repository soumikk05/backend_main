import React, { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { historyApi } from '../../api/history.api';
import { Badge, Spinner } from '../common';
import { ChevronRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const HistoryPage = () => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    historyApi.getHistory().then(data => {
      setHistory(data.items || data || []);
      setLoading(false);
    }).catch(err => {
      console.error(err);
      setLoading(false);
    });
  }, []);

  return (
    <div
      style={{
        padding: '1rem 1.25rem 2rem',
        minHeight: 'calc(100vh - 60px)',
      }}
    >
      {/* Page header */}
      <div style={{ marginBottom: '0.75rem', paddingBottom: '0.75rem', borderBottom: '1px solid var(--border-subtle)' }}>
        <h1
          style={{
            fontSize: '1rem',
            fontWeight: 700,
            color: 'var(--text-primary)',
            letterSpacing: '-0.01em',
          }}
        >
          Screening History
        </h1>
        <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.125rem' }}>
          Past document verification results
        </p>
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '2rem 0' }}>
          <Spinner size="md" />
        </div>
      ) : history.length === 0 ? (
        <div
          style={{
            padding: '1.5rem',
            textAlign: 'center',
            color: 'var(--text-muted)',
            fontSize: '0.8125rem',
            background: 'var(--bg-tertiary)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          No screening records found.
        </div>
      ) : (
        <div
          style={{
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            overflow: 'hidden',
          }}
        >
          {/* Table header */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1.5fr 120px 80px 28px',
              gap: '0.5rem',
              padding: '0.5rem 0.75rem',
              background: 'var(--bg-tertiary)',
              borderBottom: '1px solid var(--border-subtle)',
              fontSize: '0.5625rem',
              fontWeight: 700,
              color: 'var(--text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
            }}
          >
            <span>ID</span>
            <span>Document</span>
            <span>Date</span>
            <span>Risk</span>
            <span></span>
          </div>

          {/* Rows */}
          {history.map((record, idx) => (
            <motion.div
              key={record.id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: idx * 0.03 }}
              onClick={() => navigate(`/dashboard/${record.id}`)}
              whileHover={{ backgroundColor: 'var(--surface-hover)' }}
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1.5fr 120px 80px 28px',
                gap: '0.5rem',
                padding: '0.5rem 0.75rem',
                alignItems: 'center',
                cursor: 'pointer',
                borderBottom: idx < history.length - 1 ? '1px solid var(--border-subtle)' : 'none',
                background: 'var(--surface)',
                transition: 'background var(--duration-fast) ease',
              }}
            >
              <span
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.6875rem',
                  color: 'var(--text-secondary)',
                }}
              >
                {record.id.slice(0, 8)}…
              </span>

              <span
                style={{
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  color: 'var(--text-primary)',
                }}
              >
                {record.document_type || 'Unknown'} — {record.document_number || 'N/A'}
              </span>

              <span
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.6875rem',
                  color: 'var(--text-muted)',
                }}
              >
                {new Date(record.created_at).toLocaleDateString()}
              </span>

              <Badge
                label={record.risk_label}
                variant={record.risk_label?.toLowerCase() || 'neutral'}
              />

              <ChevronRight
                size={13}
                style={{ color: 'var(--text-muted)' }}
              />
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
};
