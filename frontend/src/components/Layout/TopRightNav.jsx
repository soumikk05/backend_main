import React, { useState, useRef, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import {
  Globe,
  ChevronDown,
  FileSearch,
  CheckCircle,
  ShieldAlert,
  UserCheck,
  Activity,
  X,
  Menu,
} from 'lucide-react';
import { useLanguage } from '../../hooks/useLanguage';
import { useAuth } from '../../hooks/useAuth';
import './TopRightNav.css';

const languageOptions = [
  { code: 'en', label: 'English', native: 'English' },
  { code: 'hi', label: 'Hindi', native: 'हिन्दी — Hindi' },
  { code: 'bn', label: 'Bengali', native: 'বাংলা — Bengali' },
  { code: 'te', label: 'Telugu', native: 'తెలుగు — Telugu' },
  { code: 'mr', label: 'Marathi', native: 'मराठी — Marathi' },
  { code: 'ta', label: 'Tamil', native: 'தமிழ் — Tamil' },
  { code: 'gu', label: 'Gujarati', native: 'ગુજરાતી — Gujarati' },
  { code: 'ur', label: 'Urdu', native: 'اردو — Urdu' },
  { code: 'kn', label: 'Kannada', native: 'ಕನ್ನಡ — Kannada' },
  { code: 'ml', label: 'Malayalam', native: 'മലയാളം — Malayalam' },
  { code: 'pa', label: 'Punjabi', native: 'ਪੰਜਾਬੀ — Punjabi' },
  { code: 'as', label: 'Assamese', native: 'অসমীয়া — Assamese' },
  { code: 'or', label: 'Odia', native: 'ଓଡ଼ିଆ — Odia' },
  { code: 'mai', label: 'Maithili', native: 'मैथिली — Maithili' },
  { code: 'sa', label: 'Sanskrit', native: 'संस्कृत — Sanskrit' },
  { code: 'ne', label: 'Nepali', native: 'नेपाली — Nepali' },
  { code: 'kok', label: 'Konkani', native: 'कोंकणी — Konkani' },
  { code: 'sd', label: 'Sindhi', native: 'सिन्धी — Sindhi' },
  { code: 'doi', label: 'Dogri', native: 'डोगरी — Dogri' },
  { code: 'ks', label: 'Kashmiri', native: 'कश्मीरी — Kashmiri' },
  { code: 'mni', label: 'Manipuri', native: 'मणिपुरी — Manipuri' },
];

export function TopRightNav() {
  const { user, logout } = useAuth();
  const { language, setLanguage, t } = useLanguage();
  const [servicesOpen, setServicesOpen] = useState(false);
  const [langOpen, setLangOpen] = useState(false);
  const [aboutModalOpen, setAboutModalOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const servicesRef = useRef(null);
  const langRef = useRef(null);
  const navigate = useNavigate();
  const location = useLocation();

  // Close dropdowns on outside click
  useEffect(() => {
    const handleOutsideClick = (e) => {
      if (servicesRef.current && !servicesRef.current.contains(e.target)) {
        setServicesOpen(false);
      }
      if (langRef.current && !langRef.current.contains(e.target)) {
        setLangOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

  const currentLangObj = languageOptions.find((l) => l.code === language) || languageOptions[0];

  const handleServiceClick = (serviceId) => {
    setServicesOpen(false);
    setMobileMenuOpen(false);
    if (!user) {
      navigate('/login');
      return;
    }
    if (serviceId === 'ocr') {
      navigate('/ocr');
    } else if (serviceId === 'validation') {
      navigate('/validation');
    } else if (serviceId === 'tampering') {
      navigate('/tampering');
    } else if (serviceId === 'face') {
      navigate('/face');
    } else if (serviceId === 'risk' || serviceId === 'pipeline') {
      navigate('/pipeline');
    } else {
      navigate('/');
    }
  };

  const handleHomeClick = () => {
    if (location.pathname === '/') {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      navigate('/');
    }
    setMobileMenuOpen(false);
  };

  return (
    <>
      <nav className="top-right-nav" aria-label="Top Secondary Navigation">
        {/* Mobile Toggle Button */}
        <button
          type="button"
          className="top-right-nav__mobile-toggle"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label="Toggle navigation menu"
        >
          {mobileMenuOpen ? <X size={18} /> : <Menu size={18} />}
        </button>

        {/* Desktop / Collapsible Nav List */}
        <div className={`top-right-nav__menu ${mobileMenuOpen ? 'top-right-nav__menu--open' : ''}`}>
          {/* 1. HOME */}
          <button
            type="button"
            className={`top-right-nav__item ${location.pathname === '/' ? 'top-right-nav__item--active' : ''}`}
            onClick={handleHomeClick}
          >
            {t('nav_home', 'HOME')}
          </button>

          {/* 2. ABOUT US */}
          <button
            type="button"
            className="top-right-nav__item"
            onClick={() => {
              setAboutModalOpen(true);
              setMobileMenuOpen(false);
            }}
          >
            {t('nav_about', 'ABOUT US')}
          </button>

          {/* 3. SERVICES DROPDOWN */}
          <div className="top-right-nav__dropdown-wrapper" ref={servicesRef}>
            <button
              type="button"
              className={`top-right-nav__item top-right-nav__dropdown-btn ${servicesOpen ? 'top-right-nav__item--active' : ''}`}
              onClick={() => {
                setServicesOpen(!servicesOpen);
                setLangOpen(false);
              }}
              aria-haspopup="true"
              aria-expanded={servicesOpen}
            >
              <span>{t('nav_services', 'SERVICES')}</span>
              <ChevronDown
                size={13}
                className={`top-right-nav__chevron ${servicesOpen ? 'top-right-nav__chevron--rotated' : ''}`}
              />
            </button>

            <AnimatePresence>
              {servicesOpen && (
                <motion.div
                  initial={{ opacity: 0, y: 6, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 6, scale: 0.98 }}
                  transition={{ duration: 0.15 }}
                  className="top-right-nav__dropdown top-right-nav__dropdown--services"
                >
                  <button
                    type="button"
                    className="top-right-nav__dropdown-item"
                    onClick={() => handleServiceClick('ocr')}
                  >
                    <FileSearch size={14} className="top-right-nav__dropdown-icon" />
                    <span>{t('service_ocr', 'OCR Extraction')}</span>
                  </button>

                  <button
                    type="button"
                    className="top-right-nav__dropdown-item"
                    onClick={() => handleServiceClick('validation')}
                  >
                    <CheckCircle size={14} className="top-right-nav__dropdown-icon" />
                    <span>{t('service_validation', 'Document Validation')}</span>
                  </button>

                  <button
                    type="button"
                    className="top-right-nav__dropdown-item"
                    onClick={() => handleServiceClick('tampering')}
                  >
                    <ShieldAlert size={14} className="top-right-nav__dropdown-icon" />
                    <span>{t('service_tampering', 'Tampering Detection')}</span>
                  </button>

                  <button
                    type="button"
                    className="top-right-nav__dropdown-item"
                    onClick={() => handleServiceClick('face')}
                  >
                    <UserCheck size={14} className="top-right-nav__dropdown-icon" />
                    <span>{t('service_face', 'Face Verification')}</span>
                  </button>

                  <button
                    type="button"
                    className="top-right-nav__dropdown-item"
                    onClick={() => handleServiceClick('risk')}
                  >
                    <Activity size={14} className="top-right-nav__dropdown-icon" />
                    <span>{t('service_risk', 'Risk Assessment')}</span>
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* 4. LOGIN / AUTH SESSION */}
          {user ? (
            <div className="top-right-nav__auth-group">
              <span className="top-right-nav__officer-badge">
                <span className="top-right-nav__officer-dot" />
                {user.role ? user.role.toUpperCase() : 'OFFICER'}
              </span>
              <button
                type="button"
                className="top-right-nav__item top-right-nav__logout-btn"
                onClick={() => {
                  logout();
                  navigate('/');
                }}
                title="Logout session"
              >
                LOGOUT
              </button>
            </div>
          ) : (
            <Link
              to="/login"
              className="top-right-nav__item top-right-nav__login-btn"
              onClick={() => setMobileMenuOpen(false)}
            >
              {t('nav_login', 'LOGIN')}
            </Link>
          )}

          {/* 5. 🌐 LANGUAGE DROPDOWN */}
          <div className="top-right-nav__dropdown-wrapper" ref={langRef}>
            <button
              type="button"
              className={`top-right-nav__item top-right-nav__lang-btn ${langOpen ? 'top-right-nav__item--active' : ''}`}
              onClick={() => {
                setLangOpen(!langOpen);
                setServicesOpen(false);
              }}
              aria-haspopup="true"
              aria-expanded={langOpen}
              title="Select Portal Language"
            >
              <Globe size={14} className="top-right-nav__globe-icon" />
              <span className="top-right-nav__lang-name">
                {currentLangObj.label.toUpperCase()}
              </span>
              <ChevronDown
                size={13}
                className={`top-right-nav__chevron ${langOpen ? 'top-right-nav__chevron--rotated' : ''}`}
              />
            </button>

            <AnimatePresence>
              {langOpen && (
                <motion.div
                  initial={{ opacity: 0, y: 6, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 6, scale: 0.98 }}
                  transition={{ duration: 0.15 }}
                  className="top-right-nav__dropdown top-right-nav__dropdown--lang"
                >
                  <div className="top-right-nav__lang-header">
                    <Globe size={12} />
                    <span>{language === 'hi' ? 'भाषा चुनें' : 'Select Language'}</span>
                  </div>
                  <div className="top-right-nav__lang-scroll">
                    {languageOptions.map((lang) => (
                      <button
                        key={lang.code}
                        type="button"
                        className={`top-right-nav__lang-item ${language === lang.code ? 'top-right-nav__lang-item--selected' : ''}`}
                        onClick={() => {
                          setLanguage(lang.code);
                          setLangOpen(false);
                          setMobileMenuOpen(false);
                        }}
                      >
                        <span className="top-right-nav__lang-native">{lang.native}</span>
                        {language === lang.code && (
                          <span className="top-right-nav__lang-check">✓</span>
                        )}
                      </button>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </nav>

      {/* About Us (Cloud Commandoes) Modal */}
      <AnimatePresence>
        {aboutModalOpen && (
          <div className="top-right-nav__modal-overlay" onClick={() => setAboutModalOpen(false)}>
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="top-right-nav__modal"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="top-right-nav__modal-header">
                <div>
                  <h3 className="top-right-nav__modal-title">{t('about_modal_title', 'About Cloud Commandoes')}</h3>
                  <div className="top-right-nav__modal-subtitle">{t('about_modal_team', 'Team Cloud Commandoes')}</div>
                </div>
                <button
                  type="button"
                  className="top-right-nav__modal-close"
                  onClick={() => setAboutModalOpen(false)}
                  aria-label="Close modal"
                >
                  <X size={18} />
                </button>
              </div>

              <div className="top-right-nav__modal-body">
                <div className="top-right-nav__modal-lead">
                  <h4>Securing Identity. Protecting Borders. Empowering Intelligence.</h4>
                  <p>
                    Cloud Commandoes is a technology-driven team focused on building intelligent solutions for modern security challenges. Our mission is to combine Artificial Intelligence, Computer Vision, OCR, and secure data processing to help security personnel identify fraudulent documents and identity threats faster and more accurately.
                  </p>
                </div>

                <div className="top-right-nav__modal-section">
                  <h5>Who We Are</h5>
                  <p>
                    Cloud Commandoes is a team of passionate developers, engineers, and innovators working at the intersection of Artificial Intelligence and National Security.
                  </p>
                  <p>
                    Our flagship solution, the AI-Based Fake Identity & Document Screening System, is designed to assist authorities in screening passports, visas, national identity cards, driving licenses, permits, and other identity documents.
                  </p>
                  <p>
                    <em>We believe that technology should not replace human judgment — it should strengthen it.</em>
                  </p>
                </div>

                <div className="top-right-nav__modal-grid">
                  <div className="top-right-nav__modal-pillar">
                    <h6>MISSION</h6>
                    <p>
                      To build intelligent, reliable, and secure technology that strengthens identity verification and protects national borders from document fraud and identity-based threats.
                    </p>
                  </div>
                  <div className="top-right-nav__modal-pillar">
                    <h6>VISION</h6>
                    <p>
                      A future where every identity document can be verified within seconds, every suspicious alteration can be detected intelligently, and security personnel have the technology they need to make faster and safer decisions.
                    </p>
                  </div>
                </div>
              </div>

              <div className="top-right-nav__modal-footer">
                <button
                  type="button"
                  className="top-right-nav__modal-btn"
                  onClick={() => setAboutModalOpen(false)}
                >
                  {t('about_modal_close', 'Close')}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
}
