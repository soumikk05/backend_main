import { Routes, Route, useLocation } from 'react-router-dom';
import { motion } from 'motion/react';
import { Header } from './components/Layout/Header';
import { Sidebar } from './components/Layout/Sidebar';
import { Footer } from './components/Layout/Footer';
import { Home } from './components/Home/Home';
import { LoginPage } from './components/Auth/LoginPage';
import { RequireAuth } from './components/Auth/RequireAuth';
import { HistoryPage } from './components/History/HistoryPage';
import { AdminPage } from './components/Admin/AdminPage';
import { DashboardRoute } from './components/Dashboard/DashboardRoute';

import { ScreeningModularWorkspace } from './components/Modules/ScreeningModularWorkspace';

import { useAuth } from './hooks/useAuth';
import { useEffect, useState } from 'react';
import './App.css';

function App() {
  const { user } = useAuth();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Scroll to top on route change
  useEffect(() => {
    window.scrollTo(0, 0);
    setSidebarOpen(false);
  }, [location.pathname]);

  const isLoginPage = location.pathname === '/login';
  const isHomePage = location.pathname === '/';
  const showShell = Boolean(user && !isLoginPage);

  return (
    <div className="gov-portal-root">
      {/* Official india.gov.in Header only for internal admin/history views, omitted on Home & Login */}
      {!isHomePage && !isLoginPage && (
        <Header onMenuToggle={() => setSidebarOpen(!sidebarOpen)} />
      )}

      {/* Main Portal Shell */}
      <div className="app-shell">
        {/* Navigation Drawer */}
        {showShell && (
          <Sidebar
            isOpen={sidebarOpen}
            onClose={() => setSidebarOpen(false)}
          />
        )}

        {/* Content Viewport */}
        <div className="app-main" id="main-content">
          <motion.div
            className="app-content"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
          >
            <Routes>
              {/* Public Routes */}
              <Route path="/login" element={<LoginPage />} />
              <Route path="/" element={<Home />} />

              {/* Dedicated Screening Module Routes */}
              <Route path="/pipeline" element={
                <RequireAuth allowedRoles={['officer', 'supervisor', 'admin', 'auditor']}>
                  <ScreeningModularWorkspace defaultModule="pipeline" />
                </RequireAuth>
              } />

              <Route path="/ocr" element={
                <RequireAuth allowedRoles={['officer', 'supervisor', 'admin', 'auditor']}>
                  <ScreeningModularWorkspace defaultModule="ocr" />
                </RequireAuth>
              } />

              <Route path="/validation" element={
                <RequireAuth allowedRoles={['officer', 'supervisor', 'admin', 'auditor']}>
                  <ScreeningModularWorkspace defaultModule="validation" />
                </RequireAuth>
              } />

              <Route path="/tampering" element={
                <RequireAuth allowedRoles={['officer', 'supervisor', 'admin', 'auditor']}>
                  <ScreeningModularWorkspace defaultModule="tampering" />
                </RequireAuth>
              } />

              <Route path="/face" element={
                <RequireAuth allowedRoles={['officer', 'supervisor', 'admin', 'auditor']}>
                  <ScreeningModularWorkspace defaultModule="face" />
                </RequireAuth>
              } />

              <Route path="/history" element={
                <RequireAuth allowedRoles={['officer', 'supervisor', 'admin', 'auditor']}>
                  <HistoryPage />
                </RequireAuth>
              } />

              <Route path="/dashboard/:id" element={
                <RequireAuth allowedRoles={['officer', 'supervisor', 'admin', 'auditor']}>
                  <DashboardRoute />
                </RequireAuth>
              } />

              <Route path="/admin" element={
                <RequireAuth allowedRoles={['admin', 'supervisor']}>
                  <AdminPage />
                </RequireAuth>
              } />
            </Routes>
          </motion.div>
        </div>
      </div>

      {/* Official Government Footer */}
      <Footer />
    </div>
  );
}

export default App;
