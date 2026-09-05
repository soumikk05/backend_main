import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  Calendar,
  Accessibility,
  Languages,
  Sun,
  Moon,
  Shield,
  FileCheck,
  Clock,
  LogOut,
  Menu,
  Lock,
} from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { useTheme } from '../../hooks/useTheme';
import { StateEmblem } from '../Common/StateEmblem';
import './Header.css';

export function Header({ onMenuToggle }) {
  const { user, logout } = useAuth();
  const { theme, toggleTheme, fontSize, setFontSize } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();

  // Interactive menu states
  const [showCalendar, setShowCalendar] = useState(false);
  const [showAccessibility, setShowAccessibility] = useState(false);
  const [language, setLanguage] = useState('en'); // 'en' | 'hi'

  const [currentDateTime, setCurrentDateTime] = useState('');
  const [currentDateFormatted, setCurrentDateFormatted] = useState('');
  const [currentTimeFormatted, setCurrentTimeFormatted] = useState('');

  const calendarRef = useRef(null);
  const accessibilityRef = useRef(null);

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const dateStr = now.toLocaleDateString(language === 'hi' ? 'hi-IN' : 'en-IN', {
        weekday: 'short',
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      });
      const timeStr = now.toLocaleTimeString('en-IN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true,
      });
      setCurrentDateFormatted(dateStr);
      setCurrentTimeFormatted(timeStr);
      setCurrentDateTime(`${dateStr} | ${timeStr} IST`);
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, [language]);

  // Close popovers on click outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (calendarRef.current && !calendarRef.current.contains(e.target)) {
        setShowCalendar(false);
      }
      if (accessibilityRef.current && !accessibilityRef.current.contains(e.target)) {
        setShowAccessibility(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  const toggleLanguage = () => {
    setLanguage((prev) => (prev === 'en' ? 'hi' : 'en'));
  };

  return (
    <header className="gov-header" role="banner">
      {/* 1. Tricolor Top Stripe */}
      <div className="gov-tricolor-stripe" aria-hidden="true">
        <div className="gov-tricolor-stripe__saffron" />
        <div className="gov-tricolor-stripe__white" />
        <div className="gov-tricolor-stripe__green" />
      </div>

      {/* 2. Top Utility & Accessibility Bar with Exact User Layout */}
      <div className="gov-topbar">
        <div className="gov-container gov-topbar__inner">
          {/* Left: Government of India */}
          <div className="gov-topbar__left">
            {language === 'hi' ? (
              <span className="gov-topbar__title-hi">भारत सरकार</span>
            ) : (
              <span className="gov-topbar__title-en">GOVERNMENT OF INDIA</span>
            )}
          </div>

          {/* Right: Interactive Navigation Bar matching user image */}
          <div className="gov-topbar__right">
            {/* Skip to Main Content */}
            <a href="#main-content" className="gov-topbar__item gov-topbar__skip-link">
              {language === 'hi' ? 'मुख्य सामग्री पर जाएं' : 'Skip to main content'}
            </a>

            <span className="gov-topbar__divider">|</span>

            {/* Calendar Icon Button with Interactive Popup */}
            <div className="gov-topbar__popover-wrapper" ref={calendarRef}>
              <button
                type="button"
                className={`gov-topbar__icon-btn ${showCalendar ? 'gov-topbar__icon-btn--active' : ''}`}
                onClick={() => {
                  setShowCalendar(!showCalendar);
                  setShowAccessibility(false);
                }}
                title={language === 'hi' ? 'दिनांक एवं समय' : 'Official Date & Time (IST)'}
                aria-label="View Official Time"
              >
                <Calendar size={15} />
              </button>

              <AnimatePresence>
                {showCalendar && (
                  <motion.div
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 5 }}
                    className="gov-popover"
                  >
                    <div className="gov-popover__header">
                      <Calendar size={13} />
                      <span>{language === 'hi' ? 'भारतीय मानक समय (IST)' : 'Indian Standard Time'}</span>
                    </div>
                    <div className="gov-popover__body">
                      <div className="gov-popover__clock-time">{currentTimeFormatted}</div>
                      <div className="gov-popover__clock-date">{currentDateFormatted}</div>
                      <div className="gov-popover__tz-tag">UTC +05:30 · National Physical Laboratory</div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <span className="gov-topbar__divider">|</span>

            {/* Accessibility Icon (Universal Person) with interactive Controls */}
            <div className="gov-topbar__popover-wrapper" ref={accessibilityRef}>
              <button
                type="button"
                className={`gov-topbar__icon-btn ${showAccessibility ? 'gov-topbar__icon-btn--active' : ''}`}
                onClick={() => {
                  setShowAccessibility(!showAccessibility);
                  setShowCalendar(false);
                }}
                title={language === 'hi' ? 'सुलभता विकल्प' : 'Accessibility Options'}
                aria-label="Accessibility Settings"
              >
                <Accessibility size={15} />
              </button>

              <AnimatePresence>
                {showAccessibility && (
                  <motion.div
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 5 }}
                    className="gov-popover gov-popover--wide"
                  >
                    <div className="gov-popover__header">
                      <Accessibility size={13} />
                      <span>{language === 'hi' ? 'सुलभता सेटिंग्स' : 'Accessibility Controls'}</span>
                    </div>
                    <div className="gov-popover__body">
                      {/* Font size */}
                      <div className="gov-popover__row">
                        <span className="gov-popover__label">
                          {language === 'hi' ? 'पाठ का आकार:' : 'Text Size:'}
                        </span>
                        <div className="gov-topbar__sizer">
                          <button
                            type="button"
                            className={`gov-topbar__size-btn ${fontSize === 'small' ? 'gov-topbar__size-btn--active' : ''}`}
                            onClick={() => setFontSize('small')}
                          >
                            A-
                          </button>
                          <button
                            type="button"
                            className={`gov-topbar__size-btn ${fontSize === 'normal' ? 'gov-topbar__size-btn--active' : ''}`}
                            onClick={() => setFontSize('normal')}
                          >
                            A
                          </button>
                          <button
                            type="button"
                            className={`gov-topbar__size-btn ${fontSize === 'large' ? 'gov-topbar__size-btn--active' : ''}`}
                            onClick={() => setFontSize('large')}
                          >
                            A+
                          </button>
                        </div>
                      </div>

                      {/* Theme toggle */}
                      <div className="gov-popover__row">
                        <span className="gov-popover__label">
                          {language === 'hi' ? 'कंट्रास्ट दृश्य:' : 'Contrast Theme:'}
                        </span>
                        <button
                          type="button"
                          onClick={toggleTheme}
                          className="gov-popover__toggle-btn"
                        >
                          {theme === 'dark' ? <Sun size={13} /> : <Moon size={13} />}
                          <span>{theme === 'dark' ? 'सामान्य' : 'उच्च कंट्रास्ट'}</span>
                        </button>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <span className="gov-topbar__divider">|</span>

            {/* Language Switcher 'अ A' */}
            <button
              type="button"
              className="gov-topbar__lang-btn"
              onClick={toggleLanguage}
              title={language === 'en' ? 'Switch to Hindi (हिन्दी में देखें)' : 'Switch to English'}
              aria-label="Toggle language"
            >
              <span className="gov-topbar__lang-icon">अ A</span>
              <span className="gov-topbar__lang-label">
                {language === 'en' ? 'हिन्दी' : 'English'}
              </span>
            </button>

            <span className="gov-topbar__divider">|</span>

            {/* Indian Flag Strip */}
            <div className="gov-topbar__flag-strip" title="Republic of India">
              <div className="gov-topbar__flag-band gov-topbar__flag-band--saffron" />
              <div className="gov-topbar__flag-band gov-topbar__flag-band--white" />
              <div className="gov-topbar__flag-band gov-topbar__flag-band--green" />
            </div>
          </div>
        </div>
      </div>


      {/* 4. Primary Government Navigation Bar (Navy Blue) */}
      <nav className="gov-navbar" aria-label="Main Navigation">
        <div className="gov-container gov-navbar__inner">
          {/* Mobile Menu Toggle */}
          {onMenuToggle && (
            <button
              type="button"
              className="gov-navbar__mobile-toggle"
              onClick={onMenuToggle}
              aria-label="Open Navigation Drawer"
            >
              <Menu size={18} />
              <span>{language === 'hi' ? 'मेनू' : 'Menu'}</span>
            </button>
          )}

          {/* Primary Nav Links */}
          <div className="gov-navbar__links">
            <Link
              to="/"
              className={`gov-navbar__link ${isActive('/') ? 'gov-navbar__link--active' : ''}`}
            >
              <FileCheck size={16} />
              <span>{language === 'hi' ? 'दस्तावेज़ सत्यापन' : 'Screening'}</span>
            </Link>

            {user && (
              <Link
                to="/history"
                className={`gov-navbar__link ${isActive('/history') ? 'gov-navbar__link--active' : ''}`}
              >
                <Clock size={16} />
                <span>{language === 'hi' ? 'जांच इतिहास' : 'Case Records'}</span>
              </Link>
            )}

            {user && ['admin', 'supervisor'].includes(user.role) && (
              <Link
                to="/admin"
                className={`gov-navbar__link ${isActive('/admin') ? 'gov-navbar__link--active' : ''}`}
              >
                <Shield size={16} />
                <span>{language === 'hi' ? 'प्रतिबंधित सूची' : 'Blacklist Registry'}</span>
              </Link>
            )}
          </div>

          {/* Nav Right: Pipeline Status + Logout */}
          <div className="gov-navbar__right">
            <div className="gov-navbar__pipeline-status" title="Dual-Stream V2 Neural Model Online">
              <span className="gov-navbar__status-dot" />
              <span className="gov-navbar__status-label">DUAL-STREAM V2 AI ONLINE</span>
            </div>

            {user ? (
              <button
                type="button"
                onClick={handleLogout}
                className="gov-navbar__logout-btn"
                title="Log out of secure session"
              >
                <LogOut size={14} />
                <span>{language === 'hi' ? 'लॉगआउट' : 'Logout'}</span>
              </button>
            ) : (
              <Link to="/login" className="gov-navbar__login-link">
                {language === 'hi' ? 'लॉग इन' : 'Login'}
              </Link>
            )}
          </div>
        </div>
      </nav>
    </header>
  );
}
