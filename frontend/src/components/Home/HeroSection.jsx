import React, { useState } from 'react';
import { motion } from 'motion/react';
import { StateEmblem } from '../common/StateEmblem';
import { TopRightNav } from '../Layout/TopRightNav';
import { AnnouncementTicker } from '../common/AnnouncementTicker';
import { useLanguage } from '../../hooks/useLanguage';
import './HeroSection.css';

export function HeroSection() {
  const { language, t } = useLanguage();
  const isHindi = language === 'hi';

  const genuineMetrics = [
    {
      value: '54,807',
      labelHi: 'प्रशिक्षित डेटासेट',
      labelEn: 'Trained Dataset Images',
    },
    {
      value: '30,090',
      labelHi: 'छेड़छाड़ की गई पहचानें',
      labelEn: 'Tampered Forgeries Identified',
    },
    {
      value: '24,717',
      labelHi: 'वास्तविक दस्तावेज़',
      labelEn: 'Genuine Verified Documents',
    },
    {
      value: '9',
      labelHi: 'दस्तावेज़ श्रेणियां',
      labelEn: 'Document Classes',
    },
  ];

  return (
    <section className="gov-hero-wrapper" aria-label="Portal Introduction">
      {/* 1. India Gate National Security Hero Backdrop */}
      <div className="gov-hero">
        <div className="gov-hero__overlay" />

        {/* TOP RIGHT NAVIGATION BAR */}
        <TopRightNav />

        <div className="gov-container gov-hero__content">
          {/* Centered Golden Ashoka Lion Capital */}
          <div className="gov-hero__emblem-wrap">
            <StateEmblem size={56} color="#E5A93C" />
          </div>

          {/* Project Title (AUTHENTRA) & National Security Slogan */}
          <div className="gov-hero__branding">
            <h1 className="gov-hero__title">
              {isHindi
                ? 'ऑथेंट्रा — राष्ट्रीय पहचान एवं दस्तावेज़ सत्यापन पोर्टल'
                : 'AUTHENTRA — National Identity & Document Screening Portal'}
            </h1>
            <div className="gov-hero__slogan">
              {isHindi ? (
                <>
                  सशक्त और सुरक्षित भारत के लिए <span className="gov-hero__slogan-gold">सुरक्षित पहचान</span>
                </>
              ) : (
                <>
                  Safer Identities for a <span className="gov-hero__slogan-gold">Stronger, Safer India</span>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 2. Continuous Announcement Ticker */}
      <AnnouncementTicker />

      {/* 3. Dr. A.P.J. Abdul Kalam Speech Card */}
      <div className="gov-container gov-quote-container">
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="gov-quote-card"
        >
          <div className="gov-quote-card__avatar-wrap">
            <img
              src="/kalam.png"
              alt="Dr. A.P.J. Abdul Kalam"
              className="gov-quote-card__avatar"
              onError={(e) => {
                e.target.style.display = 'none';
              }}
            />
          </div>

          <div className="gov-quote-card__content">
            <blockquote className="gov-quote-card__quote">
              {isHindi
                ? '‘प्रौद्योगिकी को आर्थिक विकास और राष्ट्रीय सुरक्षा के लिए प्रेरक शक्ति बनना होगा।’'
                : '‘Technology has to be the driving force for economical development and national security.’'}
            </blockquote>
            <div className="gov-quote-card__author">
              <span className="gov-quote-card__name">
                {isHindi
                  ? '— डॉ. ए.पी.जे. अब्दुल कलाम, टेक्नोलॉजी विज़न 2020'
                  : '— Dr. A.P.J. Abdul Kalam, Technology Vision 2020'}
              </span>
            </div>
          </div>
        </motion.div>
      </div>

      {/* 4. Official Portal Statistics Bar */}
      <div className="gov-stats-bar">
        <div className="gov-container gov-stats-bar__inner">
          {genuineMetrics.map((item, index) => (
            <motion.div
              key={item.labelEn}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: index * 0.08 }}
              className="gov-stats-card"
            >
              <div className="gov-stats-card__value">{item.value}</div>
              <div className="gov-stats-card__label">
                {isHindi ? item.labelHi : item.labelEn}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
