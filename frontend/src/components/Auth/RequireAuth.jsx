import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

export const RequireAuth = ({ children, allowedRoles }) => {
  const { user } = useAuth();
  const location = useLocation();

  if (!user) {
    // Redirect them to the /login page, but save the current location they were trying to go to
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    // User role is not authorized for this route
    return (
      <div className="min-h-screen flex items-center justify-center font-mono" style={{ color: 'var(--risk-high)' }}>
        <h1>403 - FORBIDDEN (Insufficient Clearance)</h1>
      </div>
    );
  }

  return children;
};
