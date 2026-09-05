import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { historyApi } from '../../api/history.api';
import { apiClient } from '../../api/client';
import { AlertTriangle, Search, Plus, Trash2, ShieldOff, Trash } from 'lucide-react';
import { Spinner, Badge } from '../common';

export const AdminPage = () => {
  const [blacklist, setBlacklist] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [newDocNum, setNewDocNum] = useState('');
  const [newReason, setNewReason] = useState('');
  const [search, setSearch] = useState('');
  const [isPurging, setIsPurging] = useState(false);

  const fetchBlacklist = () => {
    setLoading(true);
    historyApi.getBlacklist()
      .then(data => {
        setBlacklist(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchBlacklist();
  }, []);

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!newDocNum) return;
    setIsSubmitting(true);
    try {
      await historyApi.addToBlacklist({
        document_number: newDocNum,
        reason: newReason || 'MANUAL_FLAG',
        severity: 'high',
        status: 'active'
      });
      setNewDocNum('');
      setNewReason('');
      fetchBlacklist();
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRemove = async (docNum) => {
    if (!window.confirm(`Deactivate blacklist entry for ${docNum}?`)) return;
    try {
      await historyApi.removeFromBlacklist(docNum);
      fetchBlacklist();
    } catch (err) {
      console.error(err);
    }
  };

  const handlePurge = async () => {
    if (!window.confirm("This will permanently remove all expired evidence artifacts. Proceed?")) return;
    setIsPurging(true);
    try {
      const res = await apiClient.post('/api/privacy/purge');
      alert(`Purge complete. Removed ${res.data.removed_files} files.`);
    } catch (err) {
      console.error(err);
      alert("Purge failed.");
    } finally {
      setIsPurging(false);
    }
  };

  const filtered = blacklist.filter(b =>
    b.document_number.toLowerCase().includes(search.toLowerCase()) ||
    b.reason?.toLowerCase().includes(search.toLowerCase())
  );

  const inputStyle = {
    width: '100%',
    padding: '0.375rem 0.625rem',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--input-border)',
    background: 'var(--input-bg)',
    color: 'var(--text-primary)',
    fontSize: '0.8125rem',
    outline: 'none',
    fontFamily: 'var(--font-body)',
    transition: 'border-color var(--duration-fast) ease',
  };

  return (
    <div
      style={{
        padding: '1rem 1.25rem 2rem',
        minHeight: 'calc(100vh - 60px)',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '1rem',
          paddingBottom: '0.75rem',
          borderBottom: '1px solid var(--border-subtle)',
        }}
      >
        <div>
          <h1
            style={{
              fontSize: '1rem',
              fontWeight: 700,
              color: 'var(--text-primary)',
              letterSpacing: '-0.01em',
            }}
          >
            Document Blacklist
          </h1>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.125rem' }}>
            Manage flagged document numbers
          </p>
        </div>

        <button
          onClick={handlePurge}
          disabled={isPurging}
          className="btn btn--danger"
          style={{ fontSize: '0.6875rem' }}
        >
          {isPurging ? <Spinner size="sm" /> : <Trash size={13} />}
          Data Purge
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Add form */}
        <div className="col-span-1">
          <div
            style={{
              background: 'var(--surface)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              padding: '1rem',
              position: 'sticky',
              top: '3.5rem',
            }}
          >
            <h2
              style={{
                fontSize: '0.8125rem',
                fontWeight: 700,
                color: 'var(--text-primary)',
                marginBottom: '0.75rem',
              }}
            >
              Add to Blacklist
            </h2>

            <form onSubmit={handleAdd} style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
              <div>
                <label
                  style={{
                    display: 'block',
                    fontSize: '0.625rem',
                    fontWeight: 600,
                    color: 'var(--text-secondary)',
                    marginBottom: '0.25rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.03em',
                  }}
                >
                  Document Number
                </label>
                <input
                  type="text"
                  value={newDocNum}
                  onChange={e => setNewDocNum(e.target.value)}
                  style={inputStyle}
                  placeholder="e.g. A1234567"
                  required
                />
              </div>

              <div>
                <label
                  style={{
                    display: 'block',
                    fontSize: '0.625rem',
                    fontWeight: 600,
                    color: 'var(--text-secondary)',
                    marginBottom: '0.25rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.03em',
                  }}
                >
                  Reason
                </label>
                <input
                  type="text"
                  value={newReason}
                  onChange={e => setNewReason(e.target.value)}
                  style={inputStyle}
                  placeholder="Known forgery, stolen, etc."
                />
              </div>

              <button
                type="submit"
                disabled={isSubmitting || !newDocNum}
                className="btn btn--primary"
                style={{ width: '100%', fontSize: '0.75rem' }}
              >
                {isSubmitting ? <Spinner size="sm" /> : <Plus size={14} />}
                Add Entry
              </button>
            </form>
          </div>
        </div>

        {/* List */}
        <div className="col-span-2">
          <div
            style={{
              background: 'var(--surface)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              overflow: 'hidden',
            }}
          >
            {/* Search bar */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '0.5rem 0.75rem',
                borderBottom: '1px solid var(--border-subtle)',
              }}
            >
              <span
                style={{
                  fontSize: '0.8125rem',
                  fontWeight: 700,
                  color: 'var(--text-primary)',
                }}
              >
                Active Entries
              </span>
              <div style={{ position: 'relative' }}>
                <Search
                  size={12}
                  style={{
                    position: 'absolute',
                    left: '0.5rem',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    color: 'var(--text-muted)',
                  }}
                />
                <input
                  type="text"
                  placeholder="Search…"
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  style={{
                    ...inputStyle,
                    width: '180px',
                    paddingLeft: '1.75rem',
                    fontSize: '0.6875rem',
                  }}
                />
              </div>
            </div>

            {loading ? (
              <div style={{ padding: '2rem', display: 'flex', justifyContent: 'center' }}>
                <Spinner size="md" />
              </div>
            ) : filtered.length === 0 ? (
              <div
                style={{
                  padding: '2rem',
                  textAlign: 'center',
                  color: 'var(--text-muted)',
                  fontSize: '0.8125rem',
                }}
              >
                No matching entries.
              </div>
            ) : (
              <div>
                <AnimatePresence>
                  {filtered.map((item, idx) => (
                    <motion.div
                      key={item.document_number}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ delay: idx * 0.03 }}
                      whileHover={{ backgroundColor: 'var(--surface-hover)' }}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        padding: '0.5rem 0.75rem',
                        borderBottom: '1px solid var(--border-subtle)',
                        opacity: item.status !== 'active' ? 0.5 : 1,
                        transition: 'background var(--duration-fast) ease',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
                        {item.status === 'active'
                          ? <AlertTriangle size={14} style={{ color: 'var(--risk-high)' }} />
                          : <ShieldOff size={14} style={{ color: 'var(--text-muted)' }} />
                        }
                        <div>
                          <div
                            style={{
                              fontFamily: 'var(--font-mono)',
                              fontSize: '0.75rem',
                              fontWeight: 700,
                              color: 'var(--text-primary)',
                            }}
                          >
                            {item.document_number}
                          </div>
                          <div
                            style={{
                              fontSize: '0.625rem',
                              color: 'var(--text-muted)',
                              marginTop: '1px',
                            }}
                          >
                            {item.reason || 'No reason'}
                          </div>
                        </div>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span
                          style={{
                            fontSize: '0.625rem',
                            color: 'var(--text-muted)',
                            fontFamily: 'var(--font-mono)',
                          }}
                        >
                          {new Date(item.added_at).toLocaleDateString()}
                        </span>
                        <Badge
                          label={item.status}
                          variant={item.status === 'active' ? 'high' : 'neutral'}
                        />
                        {item.status === 'active' && (
                          <motion.button
                            whileHover={{ scale: 1.1 }}
                            whileTap={{ scale: 0.9 }}
                            onClick={() => handleRemove(item.document_number)}
                            style={{
                              padding: '0.25rem',
                              borderRadius: 'var(--radius-sm)',
                              border: 'none',
                              background: 'none',
                              cursor: 'pointer',
                              color: 'var(--text-muted)',
                              transition: 'color var(--duration-fast) ease',
                            }}
                            title="Deactivate"
                          >
                            <Trash2 size={13} />
                          </motion.button>
                        )}
                      </div>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
