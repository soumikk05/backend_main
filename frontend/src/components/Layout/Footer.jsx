import React from 'react';
import { StateEmblem } from '../Common/StateEmblem';
import { useLanguage } from '../../hooks/useLanguage';
import './Footer.css';

export function Footer() {
  const { language } = useLanguage();
  const isHindi = language === 'hi';

  return (
    <footer className="gov-footer" role="contentinfo">
      {/* Tricolor divider */}
      <div className="gov-tricolor-stripe" aria-hidden="true">
        <div className="gov-tricolor-stripe__saffron" />
        <div className="gov-tricolor-stripe__white" />
        <div className="gov-tricolor-stripe__green" />
      </div>

      <div className="gov-footer__main">
        <div className="gov-container gov-footer__inner">
          <div className="gov-footer__brand">
            <StateEmblem size={40} color="#CBD5E1" />
            <div className="gov-footer__brand-text">
              <div className="gov-footer__title">
                {isHindi
                  ? 'ऑथेंट्रा — राष्ट्रीय पहचान एवं दस्तावेज़ सत्यापन पोर्टल'
                  : 'AUTHENTRA — National Identity & Document Screening Portal'}
              </div>
              <div className="gov-footer__subtitle">
                {isHindi
                  ? 'राष्ट्रीय पहचान एवं दस्तावेज़ स्क्रीनिंग प्रणाली (AUTHENTRA)'
                  : 'National Identity & Document Screening System (AUTHENTRA)'}
              </div>
            </div>
          </div>

          <div className="gov-footer__links">
            <a href="#main-content">
              {isHindi ? 'वेबसाइट नीतियां' : 'Website Policies'}
            </a>
            <span className="gov-footer__divider">·</span>
            <a href="#main-content">
              {isHindi ? 'सहायता' : 'Help'}
            </a>
            <span className="gov-footer__divider">·</span>
            <a href="#main-content">
              {isHindi ? 'प्रतिक्रिया' : 'Feedback'}
            </a>
            <span className="gov-footer__divider">·</span>
            <a href="#main-content">
              {isHindi ? 'सुरक्षा दिशानिर्देश' : 'Security Audit'}
            </a>
          </div>
        </div>
      </div>

      <div className="gov-footer__bottom">
        <div className="gov-container gov-footer__bottom-inner">
          <p>
            {isHindi ? (
              <>
                पोर्टल का डिज़ाइन, विकास एवं प्रबंधन <strong>क्लाउड कमांडोज़</strong> द्वारा किया गया है — एसआरएम इंस्टीट्यूट ऑफ साइंस एंड टेक्नोलॉजी, रामापुरम, चेन्नई, भारत के छात्र।
              </>
            ) : (
              <>
                Portal designed, developed, and maintained by <strong>CLOUD COMMANDOS</strong>, students from SRM Institute of Science and Technology, Ramapuram, Chennai, India.
              </>
            )}
          </p>
          <div className="gov-footer__audit-tag">
            <span>TLS 1.3 Certified</span>
            <span>·</span>
            <span>STQC Cyber Compliant</span>
            <span>·</span>
            <span>Version 2.0.4-NIC</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
