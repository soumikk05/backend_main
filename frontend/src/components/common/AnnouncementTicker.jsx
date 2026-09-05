import React from 'react';
import { AlertTriangle, ShieldCheck } from 'lucide-react';
import { useLanguage } from '../../hooks/useLanguage';
import './AnnouncementTicker.css';

const announcementsEn = [
  'SECURITY ALERT: Verify all identity documents through authorized screening channels before approval.',
  'DOCUMENT VERIFICATION: Passport, Visa, National ID, Driving License and Permit documents can be screened through AUTHENTRA.',
  'FRAUD ALERT: Suspicious alterations to photographs, dates, document numbers and visa stamps may indicate document tampering.',
  'AI SCREENING: AUTHENTRA combines OCR, document validation, tampering detection and face verification to assist authorized personnel.',
  'NATIONAL SECURITY: Strengthening identity verification through intelligent document screening and AI-assisted risk assessment.',
  'IDENTITY ALERT: Multiple identities, impersonation and inconsistent document information may require additional verification.',
  'DOCUMENT VALIDATION: Always verify document validity, expiry dates and extracted information before completing the screening process.',
  'SECURITY & PRIVACY: Sensitive identity information should only be accessed and processed by authorized personnel.',
  'AI-POWERED SCREENING: Analyze identity documents within seconds and identify potential risk indicators for further review.',
  '🇮🇳 SECURE INDIA: Technology-driven identity verification for safer borders and stronger national security.',
];

const announcementsHi = [
  'सुरक्षा चेतावनी: अनुमोदन से पहले सभी पहचान दस्तावेज़ों को केवल अधिकृत चैनलों के माध्यम से सत्यापित करें।',
  'दस्तावेज़ सत्यापन: पासपोर्ट, वीज़ा, राष्ट्रीय पहचान पत्र, ड्राइविंग लाइसेंस और परमिट दस्तावेज़ ऑथेंट्रा के माध्यम से जांचे जा सकते हैं।',
  'धोखाधड़ी चेतावनी: तस्वीरों, तारीखों, दस्तावेज़ संख्याओं और वीज़ा टिकटों में संदिग्ध बदलाव दस्तावेज़ से छेड़छाड़ का संकेत हो सकते हैं।',
  'एआई स्क्रीनिंग: अधिकृत कर्मियों की सहायता के लिए ऑथेंट्रा ओसीआर, दस्तावेज़ सत्यापन, छेड़छाड़ का पता लगाने और चेहरा मिलान को जोड़ता है।',
  'राष्ट्रीय सुरक्षा: बुद्धिमान दस्तावेज़ स्क्रीनिंग और एआई-सहायता प्राप्त जोखिम मूल्यांकन के माध्यम से पहचान सत्यापन को मजबूत करना।',
  'पहचान चेतावनी: एकाधिक पहचानें, प्रतिरूपण और असंगत दस्तावेज़ जानकारी के लिए अतिरिक्त सत्यापन की आवश्यकता हो सकती है।',
  'दस्तावेज़ सत्यापन: स्क्रीनिंग प्रक्रिया पूरी करने से पहले हमेशा दस्तावेज़ की वैधता, समाप्ति तिथि और निकाली गई जानकारी सत्यापित करें।',
  'सुरक्षा एवं गोपनीयता: संवेदनशील पहचान जानकारी तक केवल अधिकृत कर्मियों द्वारा ही पहुँचा और संसाधित किया जाना चाहिए।',
  'एआई संचालित स्क्रीनिंग: सेकंडों में पहचान दस्तावेज़ों का विश्लेषण करें और आगे की समीक्षा के लिए संभावित जोखिम संकेतकों की पहचान करें।',
  '🇮🇳 सुरक्षित भारत: सुरक्षित सीमाओं और मजबूत राष्ट्रीय सुरक्षा के लिए प्रौद्योगिकी-संचालित पहचान सत्यापन।',
];

export function AnnouncementTicker() {
  const { language } = useLanguage();
  const isHindi = language === 'hi';
  const announcements = isHindi ? announcementsHi : announcementsEn;

  return (
    <div className="gov-ticker" role="region" aria-label="Official Security Announcements">
      <div className="gov-ticker__badge" aria-hidden="true">
        <AlertTriangle size={13} className="gov-ticker__badge-icon" />
        <span>{isHindi ? 'सुरक्षा अलर्ट' : 'SECURITY ALERTS'}</span>
      </div>

      <div className="gov-ticker__track-wrapper">
        <div className="gov-ticker__track">
          {/* Primary loop list */}
          <div className="gov-ticker__items">
            {announcements.map((text, idx) => (
              <span key={`p-${idx}`} className="gov-ticker__item">
                <span className="gov-ticker__dot">•</span>
                {text}
              </span>
            ))}
          </div>

          {/* Duplicated list for seamless infinite marquee loop */}
          <div className="gov-ticker__items" aria-hidden="true">
            {announcements.map((text, idx) => (
              <span key={`d-${idx}`} className="gov-ticker__item">
                <span className="gov-ticker__dot">•</span>
                {text}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
