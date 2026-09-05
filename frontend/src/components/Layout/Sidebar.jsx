import { motion } from 'motion/react';
import {
  ShieldCheck,
  FileText,
  FileSearch,
  CheckCircle,
  ShieldAlert,
  UserCheck,
  Clock,
  Shield,
  Trash,
  LogOut,
  User,
} from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import './Sidebar.css';

const navSections = [
  {
    label: 'Screening Modules',
    items: [
      { path: '/', label: 'Document Screening (Portal)', icon: FileText, roles: null },
      { path: '/pipeline', label: 'Full Risk Assessment', icon: ShieldCheck, roles: ['officer', 'supervisor', 'admin', 'auditor'] },
      { path: '/ocr', label: 'Neural OCR Extraction', icon: FileSearch, roles: ['officer', 'supervisor', 'admin', 'auditor'] },
      { path: '/validation', label: 'Document Validation', icon: CheckCircle, roles: ['officer', 'supervisor', 'admin', 'auditor'] },
      { path: '/tampering', label: 'Tampering Forensics', icon: ShieldAlert, roles: ['officer', 'supervisor', 'admin', 'auditor'] },
      { path: '/face', label: 'Face Verification', icon: UserCheck, roles: ['officer', 'supervisor', 'admin', 'auditor'] },
    ],
  },
  {
    label: 'Records',
    items: [
      {
        path: '/history',
        label: 'Screening History',
        icon: Clock,
        roles: ['officer', 'supervisor', 'admin', 'auditor'],
      },
    ],
  },
  {
    label: 'Administration',
    items: [
      {
        path: '/admin',
        label: 'Document Blacklist',
        icon: Shield,
        roles: ['admin', 'supervisor'],
      },
    ],
  },
];

export function Sidebar({ isOpen, onClose }) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path) => location.pathname === path;

  if (!user) return null;

  const roleInitial = (user.role || 'U')[0].toUpperCase();

  return (
    <>
      {/* Mobile overlay */}
      <div
        className={`sidebar-overlay ${isOpen ? 'sidebar-overlay--visible' : ''}`}
        onClick={onClose}
      />

      <aside className={`sidebar ${isOpen ? 'sidebar--open' : ''}`}>
        {/* Tricolor stripe */}
        <div className="sidebar__stripe" />

        {/* Brand */}
        <Link to="/" className="sidebar__brand" onClick={onClose}>
          <div className="sidebar__logo-wrap">
            <ShieldCheck size={16} />
          </div>
          <div className="sidebar__brand-text">
            <div className="sidebar__title">AUTHENTRA</div>
            <div className="sidebar__subtitle">Screening Portal</div>
          </div>
        </Link>

        {/* Navigation */}
        <nav className="sidebar__nav">
          {navSections.map((section) => {
            // Filter items by role
            const visibleItems = section.items.filter(
              (item) => !item.roles || item.roles.includes(user.role)
            );
            if (visibleItems.length === 0) return null;

            return (
              <div key={section.label} className="sidebar__section">
                <div className="sidebar__section-label">{section.label}</div>
                {visibleItems.map((item) => {
                  const Icon = item.icon;
                  const active = isActive(item.path);

                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      className={`sidebar__link ${active ? 'sidebar__link--active' : ''}`}
                      onClick={onClose}
                    >
                      <span className="sidebar__link-icon">
                        <Icon size={16} />
                      </span>
                      <span>{item.label}</span>
                    </Link>
                  );
                })}
              </div>
            );
          })}
        </nav>

        {/* User profile / session at bottom */}
        <div className="sidebar__footer">
          <div className="sidebar__user">
            <div className="sidebar__user-avatar">
              {roleInitial}
            </div>
            <div className="sidebar__user-info">
              <div className="sidebar__user-role">{user.username || 'Officer'}</div>
              <div className="sidebar__user-status">Active Session</div>
            </div>
            <button
              type="button"
              className="sidebar__logout-btn"
              onClick={handleLogout}
              title="Logout"
            >
              <LogOut size={13} />
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
