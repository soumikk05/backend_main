import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'motion/react';
import { ShieldCheck, AlertTriangle } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { authApi } from '../../api/auth.api';

export const LoginPage = () => {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin');
  const [role, setRole] = useState('admin');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const data = await authApi.login(username, password, role);
      login(data.access_token, data.role);
      window.scrollTo(0, 0);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || 'Authentication failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-120px)] flex">
      {/* Left: Brand panel — deep navy, takes 40% */}
      <div
        className="hidden lg:flex flex-col justify-between p-10"
        style={{
          width: '40%',
          background: 'var(--bg-secondary)',
          color: 'var(--text-primary)',
          borderRight: '1px solid var(--border-subtle)'
        }}
      >
        <div>
          <div className="flex items-center gap-2.5 mb-10">
            <ShieldCheck size={20} style={{ color: 'var(--accent)' }} />
            <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
              AUTHENTRA
            </span>
          </div>

          <h1
            style={{
              fontSize: '1.75rem',
              fontWeight: 700,
              lineHeight: 1.25,
              letterSpacing: '-0.02em',
              marginBottom: '1rem',
              maxWidth: '320px',
            }}
          >
            Identity Document Screening & Fraud Detection
          </h1>

          <p
            style={{
              fontSize: '0.875rem',
              lineHeight: 1.65,
              color: 'var(--text-secondary)',
              maxWidth: '300px',
            }}
          >
            Multi-modal analysis combining OCR extraction, MRZ checksum validation,
            error-level forensics, and biometric face matching.
          </p>
        </div>

        {/* Technical capabilities — not generic marketing cards */}
        <div
          style={{
            borderTop: '1px solid var(--border-subtle)',
            paddingTop: '1.25rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.625rem',
          }}
        >
          {[
            'OCR — Neural text extraction',
            'MRZ — ICAO 9303 checksum validation',
            'ELA — Error level tampering forensics',
            'Face — 512-dim biometric matching',
          ].map((item, i) => (
            <div
              key={i}
              style={{
                fontSize: '0.75rem',
                fontFamily: 'var(--font-mono)',
                color: 'var(--text-muted)',
                letterSpacing: '0.01em',
              }}
            >
              {item}
            </div>
          ))}
        </div>
      </div>

      {/* Right: Login form — takes remaining space */}
      <div
        className="flex-1 flex items-center justify-center p-6"
        style={{ 
          background: 'var(--bg-tertiary)',
        }}
      >
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          style={{ width: '100%', maxWidth: '360px' }}
        >
          {/* Mobile brand */}
          <div className="lg:hidden flex items-center gap-2 mb-6">
            <ShieldCheck size={18} style={{ color: 'var(--accent)' }} />
            <span style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              AUTHENTRA
            </span>
          </div>

          <h2
            style={{
              fontSize: '1.35rem',
              fontWeight: 800,
              color: 'var(--text-primary)',
              marginBottom: '0.2rem',
              letterSpacing: '0.04em',
              textTransform: 'uppercase',
            }}
          >
            SECURE ACCESS
          </h2>
          <div
            style={{
              fontSize: '0.75rem',
              fontWeight: 700,
              color: '#E5A93C',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              marginBottom: '0.5rem',
            }}
          >
            Authorized Personnel Only
          </div>
          <p
            style={{
              fontSize: '0.8125rem',
              color: 'var(--text-muted)',
              marginBottom: '1.5rem',
              lineHeight: 1.45,
            }}
          >
            Access to identity screening and verification capabilities is restricted to authorized users.
          </p>

          {error && (
            <motion.div
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              style={{
                marginBottom: '1rem',
                padding: '0.625rem 0.75rem',
                borderRadius: 'var(--radius-md)',
                background: 'var(--risk-high-bg)',
                color: 'var(--risk-high)',
                border: '1px solid var(--risk-high)',
                fontSize: '0.8125rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
              }}
            >
              <AlertTriangle size={14} />
              <span>{error}</span>
            </motion.div>
          )}

          <form onSubmit={handleLogin}>
            <div style={{ marginBottom: '0.875rem' }}>
              <label
                style={{
                  display: 'block',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  color: 'var(--text-secondary)',
                  marginBottom: '0.375rem',
                }}
              >
                Employee / Officer ID
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                style={{
                  width: '100%',
                  padding: '0.5rem 0.75rem',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--input-border)',
                  background: 'var(--input-bg)',
                  color: 'var(--text-primary)',
                  fontSize: '0.875rem',
                  outline: 'none',
                  transition: 'border-color var(--duration-fast) ease',
                  fontFamily: 'var(--font-body)',
                }}
                onFocus={(e) => (e.target.style.borderColor = 'var(--border-focus)')}
                onBlur={(e) => (e.target.style.borderColor = 'var(--input-border)')}
              />
            </div>

            <div style={{ marginBottom: '0.875rem' }}>
              <label
                style={{
                  display: 'block',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  color: 'var(--text-secondary)',
                  marginBottom: '0.375rem',
                }}
              >
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                style={{
                  width: '100%',
                  padding: '0.5rem 0.75rem',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--input-border)',
                  background: 'var(--input-bg)',
                  color: 'var(--text-primary)',
                  fontSize: '0.875rem',
                  outline: 'none',
                  transition: 'border-color var(--duration-fast) ease',
                  fontFamily: 'var(--font-body)',
                }}
                onFocus={(e) => (e.target.style.borderColor = 'var(--border-focus)')}
                onBlur={(e) => (e.target.style.borderColor = 'var(--input-border)')}
              />
            </div>

            <div style={{ marginBottom: '1.25rem' }}>
              <label
                style={{
                  display: 'block',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  color: 'var(--text-secondary)',
                  marginBottom: '0.375rem',
                }}
              >
                Access Role
              </label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.5rem 0.75rem',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--input-border)',
                  background: 'var(--input-bg)',
                  color: 'var(--text-primary)',
                  fontSize: '0.875rem',
                  outline: 'none',
                  appearance: 'none',
                  cursor: 'pointer',
                  fontFamily: 'var(--font-body)',
                }}
              >
                <option value="officer">Officer</option>
                <option value="supervisor">Supervisor</option>
                <option value="admin">Administrator</option>
                <option value="auditor">Auditor</option>
              </select>
            </div>

            <motion.button
              type="submit"
              disabled={loading}
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
              className="btn btn--primary btn--lg"
              style={{
                width: '100%',
                background: '#0B1E36',
                border: '1px solid rgba(229, 169, 60, 0.4)',
                color: '#FFFFFF',
                fontWeight: 700,
                letterSpacing: '0.06em',
              }}
            >
              {loading ? 'AUTHENTICATING…' : 'AUTHENTICATE'}
            </motion.button>
          </form>

          <div
            style={{
              marginTop: '1.25rem',
              padding: '0.75rem',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px dashed var(--border-subtle)',
              fontSize: '0.75rem',
            }}
          >
            <div style={{ fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
              Quick Credentials (Click to Auto-Fill):
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
              <button
                type="button"
                onClick={() => {
                  setUsername('admin');
                  setPassword('admin');
                  setRole('admin');
                }}
                style={{
                  background: 'rgba(229, 169, 60, 0.12)',
                  border: '1px solid rgba(229, 169, 60, 0.4)',
                  color: '#e5a93c',
                  padding: '4px 10px',
                  borderRadius: '4px',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Admin (admin / admin)
              </button>
              <button
                type="button"
                onClick={() => {
                  setUsername('user');
                  setPassword('password');
                  setRole('officer');
                }}
                style={{
                  background: 'rgba(255, 255, 255, 0.06)',
                  border: '1px solid var(--border-subtle)',
                  color: 'var(--text-secondary)',
                  padding: '4px 10px',
                  borderRadius: '4px',
                  fontSize: '0.75rem',
                  cursor: 'pointer',
                }}
              >
                Officer (user / password)
              </button>
            </div>
          </div>

          <p
            style={{
              textAlign: 'center',
              fontSize: '0.6875rem',
              color: 'var(--text-muted)',
              marginTop: '1.25rem',
              lineHeight: 1.4,
              borderTop: '1px solid var(--border-subtle)',
              paddingTop: '0.75rem',
            }}
          >
            All access attempts may be recorded for security and audit purposes.
          </p>
        </motion.div>
      </div>
    </div>
  );
};
