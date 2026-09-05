import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Dashboard } from './Dashboard';
import { operationsApi } from '../../api/operations.api';

export const DashboardRoute = () => {
  const { id } = useParams();
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch the hydration payload for this specific screening ID
    operationsApi.getDashboard(id).then(data => {
      setResult(data);
      setLoading(false);
    }).catch(err => {
      console.error(err);
      setLoading(false);
    });
  }, [id]);

  if (loading) {
    return <div className="pt-12 min-h-screen text-center" style={{ color: 'var(--accent)' }}>Loading Dashboard...</div>;
  }

  if (!result) {
    return <div className="pt-12 min-h-screen text-center" style={{ color: 'var(--risk-high)' }}>Failed to load Dashboard data.</div>;
  }

  return (
    <div className="min-h-screen">
      <Dashboard result={result} onBack={() => window.history.back()} />
    </div>
  );
};
