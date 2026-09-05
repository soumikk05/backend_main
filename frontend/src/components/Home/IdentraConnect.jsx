import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  ExternalLink,
  PlayCircle,
  Award,
  Calendar,
  X,
  CheckCircle2,
  Share2,
  ChevronRight,
  Radio,
  FileCheck,
  Flame,
} from 'lucide-react';
import { useLanguage } from '../../hooks/useLanguage';
import './IdentraConnect.css';

export function IdentraConnect() {
  const { language } = useLanguage();
  const isHindi = language === 'hi';

  const [activeTab, setActiveTab] = useState('all');
  const [selectedItem, setSelectedItem] = useState(null);
  const [expandedView, setExpandedView] = useState(false);

  // Interactive Quiz state in modal
  const [quizAnswer, setQuizAnswer] = useState(null);
  const [quizSubmitted, setQuizSubmitted] = useState(false);

  // Video/live stream mock state
  const [isPlaying, setIsPlaying] = useState(false);

  // Contest submission state
  const [entrySubmitted, setEntrySubmitted] = useState(false);

  const initialCards = [
    {
      id: 'bhagat-singh',
      category: 'do',
      tag: isHindi ? 'करें' : 'DO',
      tagColor: '#2563EB',
      image: '/connect_bhagat_singh.jpg',
      title: isHindi
        ? 'शहीद भगत सिंह की जयंती पर विशेष श्रद्धांजलि — राष्ट्रीय देशभक्ति प्रश्नोत्तरी'
        : 'Tribute to Shaheed Bhagat Singh on his Birth Anniversary — National Patriotism Quiz',
      date: isHindi ? '28 सितंबर 2024' : '28th September 2024',
      badgeText: isHindi ? 'प्रमाणपत्र उपलब्ध' : 'Official Certificate',
      description: isHindi
        ? 'शहीद भगत सिंह के जीवन, साहस और मातृभूमि के लिए उनके सर्वोच्च बलिदान को नमन करते हुए इस राष्ट्रीय प्रश्नोत्तरी में भाग लें और गृह मंत्रालय से ई-प्रमाणपत्र प्राप्त करें।'
        : 'Commemorate the extraordinary courage and supreme sacrifice of Shaheed Bhagat Singh. Test your knowledge of India’s freedom movement and earn an official digital certificate.',
      actionType: 'quiz',
      actionLabel: isHindi ? 'भाग लें' : 'Participate Now',
      quizQuestion: {
        question: isHindi
          ? 'शहीद भगत सिंह ने किस संगठन की स्थापना में महत्वपूर्ण भूमिका निभाई थी?'
          : 'Which revolutionary patriotic organisation was co-founded by Shaheed Bhagat Singh in 1928?',
        options: [
          isHindi ? 'हिंदुस्तान सोशलिस्ट रिपब्लिकन एसोसिएशन (HSRA)' : 'Hindustan Socialist Republican Association (HSRA)',
          isHindi ? 'ग़दर पार्टी' : 'Ghadar Party',
          isHindi ? 'आज़ाद हिन्द फ़ौज' : 'Indian National Army (INA)',
          isHindi ? 'अभिनव भारत सोसाइटी' : 'Abhinav Bharat Society',
        ],
        correctIndex: 0,
      },
    },
    {
      id: 'mann-ki-baat',
      category: 'discuss',
      tag: isHindi ? 'चर्चा' : 'DISCUSS',
      tagColor: '#059669',
      image: '/connect_mann_ki_baat.jpg',
      title: isHindi
        ? 'प्रधानमंत्री नरेंद्र मोदी के साथ ‘मन की बात’ का 113वां एपिसोड देखें एवं साझा करें'
        : 'Tune in to 113th Episode of Mann Ki Baat by Prime Minister Narendra Modi',
      date: isHindi ? '25 अगस्त 2024 | प्रातः 11:00 बजे' : '25th August 2024 | 11:00 AM IST',
      badgeText: isHindi ? 'लाइव प्रसारण' : 'Live Broadcast',
      description: isHindi
        ? 'आकाशवाणी एवं दूरदर्शन पर माननीय प्रधानमंत्री के प्रेरक संबोधन को सुनें। राष्ट्र निर्माण, युवा नवाचार, तथा डिजिटल सुरक्षा पर अपने विचार और सुझाव साझा करें।'
        : 'Tune in to the inspiring national broadcast with the Hon’ble Prime Minister. Discuss community initiatives, youth innovations, and technological advancements empowering our nation.',
      actionType: 'stream',
      actionLabel: isHindi ? 'लाइव देखें' : 'Watch LIVE',
      streamDetails: {
        channel: 'All India Radio & Doordarshan News',
        duration: '32 mins broadcast',
        highlights: [
          isHindi ? 'युवा नवप्रवर्तकों एवं रक्षा तकनीक की सराहना' : 'Commendation of youth technological innovators',
          isHindi ? 'साइबर जागरूकता एवं पहचान सुरक्षा पर संदेश' : 'Special message on citizen digital security awareness',
          isHindi ? 'स्थानीय उत्पादों एवं वोकल फॉर लोकल पर बल' : 'Strengthening indigenous innovation & local talent',
        ],
      },
    },
    {
      id: 'aarogya-setu',
      category: 'do',
      tag: isHindi ? 'करें' : 'DO',
      tagColor: '#D97706',
      image: '/connect_aarogya_setu.jpg',
      title: isHindi
        ? 'आरोग्य सेतु 2.0 रील वीडियो मेकिंग प्रतियोगिता — डिजिटल स्वास्थ्य एवं साइबर सुरक्षा'
        : 'Aarogya Setu 2.0 Reel Video Making Competition — Digital Health & Security',
      date: isHindi ? 'अंतिम तिथि: 15 नवंबर 2024' : 'Deadline: 15th November 2024',
      badgeText: isHindi ? 'नकद पुरस्कार एवं प्रशस्ति पत्र' : 'Cash Prizes & Citations',
      description: isHindi
        ? 'डिजिटल स्वास्थ्य सुरक्षा, नागरिक डेटा संरक्षण और साइबर सतर्कता पर अपनी 60-सेकंड की रचनात्मक वीडियो रील बनाएं और आकर्षक नकद पुरस्कार जीतें।'
        : 'Showcase your creativity in a 60-second video reel highlighting citizen cybersecurity awareness, healthcare digital services, and identity protection. Win cash rewards and national recognition.',
      actionType: 'contest',
      actionLabel: isHindi ? 'प्रविष्टि भेजें' : 'Submit Your Reel',
      contestDetails: {
        prizePool: isHindi ? '₹1,50,000 प्रथम पुरस्कार + प्रमाण पत्र' : '₹1,50,000 Top Prize + National Citations',
        eligibility: isHindi ? 'सभी भारतीय नागरिकों एवं छात्रों के लिए खुला' : 'Open to all Indian students & digital creators',
        format: isHindi ? 'MP4 / 9:16 वर्टिकल रील (अधिकतम 60 सेकंड)' : 'MP4 vertical reel format (under 60 seconds)',
      },
    },
  ];

  const extraCards = [
    {
      id: 'cyber-pledge',
      category: 'do',
      tag: isHindi ? 'शपथ' : 'PLEDGE',
      tagColor: '#7C3AED',
      image: '/connect_bhagat_singh.jpg',
      title: isHindi
        ? 'राष्ट्रीय साइबर सुरक्षा शपथ 2024 — डिजिटल रक्षा के प्रति नागरिक प्रतिबद्धता'
        : 'National Cyber Security Citizen Pledge 2024 — Safeguard Your Digital Identity',
      date: isHindi ? 'जारी' : 'Ongoing Initiative',
      badgeText: isHindi ? 'डिजिटल बैज' : 'Digital Badge',
      description: isHindi
        ? 'मजबूत पासवर्ड, दो-कारक प्रमाणीकरण और दस्तावेज़ सुरक्षा अपनाने की औपचारिक शपथ लें और डिजिटल सुरक्षा बैज प्राप्त करें।'
        : 'Take the national citizen security pledge to adopt multi-factor authentication, verify identity documents before sharing, and defend against online identity fraud.',
      actionType: 'quiz',
      actionLabel: isHindi ? 'शपथ लें' : 'Take Citizen Pledge',
      quizQuestion: {
        question: isHindi
          ? 'साइबर सुरक्षा के लिए क्या अनिवार्य है?'
          : 'What is the most secure practice when storing government-issued identity documents?',
        options: [
          isHindi ? 'पासवर्ड-संरक्षित डिजीलॉकर का उपयोग' : 'Encrypted government DigiLocker with multi-factor authentication',
          isHindi ? 'सार्वजनिक क्लाउड ड्राइव में रखना' : 'Unprotected public cloud storage',
          isHindi ? 'सोशल मीडिया चैट पर फोटो भेजना' : 'Sharing raw unmasked images on social messaging',
          isHindi ? 'कागज़ पर पिन लिखकर रखना' : 'Writing passcodes on physical paper copies',
        ],
        correctIndex: 0,
      },
    },
    {
      id: 'ai-challenge',
      category: 'do',
      tag: isHindi ? 'हैकाथॉन' : 'HACKATHON',
      tagColor: '#DC2626',
      image: '/connect_aarogya_setu.jpg',
      title: isHindi
        ? 'आर्टिफिशियल इंटेलिजेंस पहचान सुरक्षा ग्रैंड चैलेंज — क्लाउड कमांडोज़'
        : 'AI Identity Screening & Anti-Spoofing Grand Challenge by Cloud Commandoes',
      date: isHindi ? 'पंजीकरण खुला' : 'Registration Open',
      badgeText: isHindi ? '₹5,00,000 नवाचार अनुदान' : '₹5,00,000 Research Grant',
      description: isHindi
        ? 'भारतीय डेवलपरों और शोधकर्ताओं के लिए उन्नत डीपफेक और दस्तावेज़ जालसाजी पहचान एल्गोरिदम विकसित करने की राष्ट्रीय प्रतियोगिता।'
        : 'National hackathon for developers and researchers to engineer next-generation neural architectures detecting synthetic IDs, morphing attacks, and tampering.',
      actionType: 'contest',
      actionLabel: isHindi ? 'पंजीकरण करें' : 'Register Team',
      contestDetails: {
        prizePool: isHindi ? '₹5,00,000 शोध अनुदान' : '₹5,00,000 Grand Prize & NIC Incubation',
        eligibility: isHindi ? 'कॉलेज के छात्र और स्टार्ट-अप' : 'Engineers, AI researchers & cybersecurity startups',
        format: isHindi ? 'पायथन / पायटॉर्च कोड एवं मॉडल सबमिशन' : 'Python/PyTorch containerized ML model submission',
      },
    },
    {
      id: 'mann-ki-baat-archive',
      category: 'discuss',
      tag: isHindi ? 'चर्चा' : 'DISCUSS',
      tagColor: '#059669',
      image: '/connect_mann_ki_baat.jpg',
      title: isHindi
        ? 'सीमा सुरक्षा एवं प्रौद्योगिकी आधुनिकीकरण पर राष्ट्रीय परिचर्चा'
        : 'National Security & Border Tech Modernization: Citizen Discussion Forum',
      date: isHindi ? 'सक्रिय मंच' : 'Active Discussion Forum',
      badgeText: isHindi ? 'खुला मंच' : 'Public Forum',
      description: isHindi
        ? 'भारतीय सीमाओं और प्रवेश बिंदुओं पर एआई-संचालित पहचान सत्यापन पर अपने विचार, तकनीकी सुझाव और प्रतिक्रियाएं प्रस्तुत करें।'
        : 'Contribute ideas, technological suggestions, and citizen feedback on modernizing document verification and border checkpoint infrastructure.',
      actionType: 'stream',
      actionLabel: isHindi ? 'विचार साझा करें' : 'Join Discussion',
      streamDetails: {
        channel: 'MyGov Open Dialogue Platform',
        duration: 'Over 14,000 citizen contributions',
        highlights: [
          isHindi ? 'स्मार्ट ई-पासपोर्ट तकनीक कार्यान्वयन' : 'Smart chip-embedded e-Passport deployment updates',
          isHindi ? 'एआई आधारित जालसाजी रोकथाम तकनीक' : 'Implementation of AI tampering forensics at airports',
          isHindi ? 'नागरिक गोपनीयता संरक्षण नियम' : 'Ensuring strict compliance with citizen privacy standards',
        ],
      },
    },
  ];

  const allCards = expandedView ? [...initialCards, ...extraCards] : initialCards;

  const filteredCards = allCards.filter((card) => {
    if (activeTab === 'all') return true;
    return card.category === activeTab;
  });

  const openCardModal = (card) => {
    setSelectedItem(card);
    setQuizAnswer(null);
    setQuizSubmitted(false);
    setIsPlaying(false);
    setEntrySubmitted(false);
  };

  const handleQuizSubmit = (e) => {
    e.preventDefault();
    setQuizSubmitted(true);
  };

  const handleContestSubmit = (e) => {
    e.preventDefault();
    setEntrySubmitted(true);
  };

  return (
    <section className="identra-connect" aria-label="National Security & Citizen Engagement Portal">
      <div className="gov-container">
        {/* Section Header with Accent Underline */}
        <div className="identra-connect__header">
          <h2 className="identra-connect__title">
            {isHindi ? 'माईगॉव कनेक्ट' : 'MyGov Connect'}
          </h2>
          <div className="identra-connect__line" />
          <p className="identra-connect__subtitle">
            {isHindi
              ? 'प्रतियोगिताओं में भाग लें, लाइव स्ट्रीम देखें, इत्यादि'
              : 'Participate in quizzes, watch live streams, etc.'}
          </p>

          {/* Interactive Filter Pills */}
          <div className="identra-connect__filters" role="tablist">
            <button
              type="button"
              className={`identra-connect__filter-btn ${activeTab === 'all' ? 'identra-connect__filter-btn--active' : ''}`}
              onClick={() => setActiveTab('all')}
            >
              {isHindi ? 'सभी' : 'All'}
            </button>
            <button
              type="button"
              className={`identra-connect__filter-btn ${activeTab === 'do' ? 'identra-connect__filter-btn--active' : ''}`}
              onClick={() => setActiveTab('do')}
            >
              <Award size={13} />
              {isHindi ? 'गतिविधियां / प्रश्नोत्तरी' : 'Do / Quizzes'}
            </button>
            <button
              type="button"
              className={`identra-connect__filter-btn ${activeTab === 'discuss' ? 'identra-connect__filter-btn--active' : ''}`}
              onClick={() => setActiveTab('discuss')}
            >
              <Radio size={13} />
              {isHindi ? 'चर्चा एवं लाइव' : 'Discuss & Watch'}
            </button>
          </div>
        </div>

        {/* 3-Card Responsive Grid matching User Screenshot */}
        <div className="identra-connect__grid">
          {filteredCards.map((card, idx) => (
            <motion.article
              key={card.id}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, delay: idx * 0.08 }}
              className="identra-connect__card"
              onClick={() => openCardModal(card)}
            >
              {/* Card Image Thumbnail */}
              <div className="identra-connect__img-wrap">
                <img
                  src={card.image}
                  alt={card.title}
                  className="identra-connect__img"
                  loading="lazy"
                />
                <span className="identra-connect__badge-corner">
                  {card.badgeText}
                </span>
              </div>

              {/* Card Body */}
              <div className="identra-connect__body">
                {/* Tag Badge matching user image: blue DO / green DISCUSS */}
                <div className="identra-connect__tag-row">
                  <span
                    className="identra-connect__tag"
                    style={{ backgroundColor: card.tagColor }}
                  >
                    {card.tag}
                  </span>
                  <span className="identra-connect__date">
                    <Calendar size={12} />
                    {card.date}
                  </span>
                </div>

                {/* Card Title */}
                <h3 className="identra-connect__card-title">
                  {card.title}
                </h3>

                {/* Card Excerpt */}
                <p className="identra-connect__card-desc">
                  {card.description}
                </p>

                {/* Interactive Action Button */}
                <div className="identra-connect__card-footer">
                  <button
                    type="button"
                    className="identra-connect__action-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      openCardModal(card);
                    }}
                  >
                    {card.actionType === 'stream' && <PlayCircle size={14} />}
                    {card.actionType === 'quiz' && <Award size={14} />}
                    {card.actionType === 'contest' && <Flame size={14} />}
                    <span>{card.actionLabel}</span>
                    <ChevronRight size={14} className="identra-connect__arrow" />
                  </button>
                </div>
              </div>
            </motion.article>
          ))}
        </div>

        {/* View All Button matching User Screenshot */}
        <div className="identra-connect__footer">
          <button
            type="button"
            className="identra-connect__view-all-btn"
            onClick={() => setExpandedView(!expandedView)}
          >
            <span>
              {expandedView
                ? isHindi
                  ? 'कम देखें'
                  : 'Show Less'
                : isHindi
                  ? 'सभी देखें'
                  : 'View All'}
            </span>
            <ChevronRight
              size={15}
              className={`identra-connect__view-all-icon ${expandedView ? 'identra-connect__view-all-icon--up' : ''}`}
            />
          </button>
        </div>
      </div>

      {/* Interactive Working Modal for Quizzes, Live Streams, and Contests */}
      <AnimatePresence>
        {selectedItem && (
          <div
            className="identra-modal-overlay"
            onClick={() => setSelectedItem(null)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 15 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 15 }}
              className="identra-modal"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Modal Header */}
              <div className="identra-modal__header">
                <div className="identra-modal__header-left">
                  <span
                    className="identra-connect__tag"
                    style={{ backgroundColor: selectedItem.tagColor }}
                  >
                    {selectedItem.tag}
                  </span>
                  <span className="identra-modal__header-badge">
                    {selectedItem.badgeText}
                  </span>
                </div>
                <button
                  type="button"
                  className="identra-modal__close"
                  onClick={() => setSelectedItem(null)}
                  aria-label="Close modal"
                >
                  <X size={18} />
                </button>
              </div>

              {/* Modal Image */}
              <div className="identra-modal__media">
                <img
                  src={selectedItem.image}
                  alt={selectedItem.title}
                  className="identra-modal__img"
                />
              </div>

              {/* Modal Content */}
              <div className="identra-modal__body">
                <h3 className="identra-modal__title">{selectedItem.title}</h3>
                <p className="identra-modal__desc">{selectedItem.description}</p>

                {/* 1. Interactive Quiz Feature */}
                {selectedItem.actionType === 'quiz' && (
                  <div className="identra-modal__interactive-block">
                    <h4 className="identra-modal__block-title">
                      <Award size={16} />
                      {isHindi ? 'त्वरित प्रश्नोत्तरी' : 'Citizen Verification Challenge'}
                    </h4>

                    {!quizSubmitted ? (
                      <form onSubmit={handleQuizSubmit} className="identra-modal__quiz-form">
                        <p className="identra-modal__question">
                          {selectedItem.quizQuestion.question}
                        </p>
                        <div className="identra-modal__options">
                          {selectedItem.quizQuestion.options.map((opt, optIdx) => (
                            <label
                              key={optIdx}
                              className={`identra-modal__option-label ${quizAnswer === optIdx ? 'identra-modal__option-label--selected' : ''}`}
                            >
                              <input
                                type="radio"
                                name="quizOpt"
                                value={optIdx}
                                checked={quizAnswer === optIdx}
                                onChange={() => setQuizAnswer(optIdx)}
                                required
                              />
                              <span>{opt}</span>
                            </label>
                          ))}
                        </div>
                        <button
                          type="submit"
                          disabled={quizAnswer === null}
                          className="identra-modal__submit-btn"
                        >
                          {isHindi ? 'उत्तर जमा करें' : 'Submit Answer'}
                        </button>
                      </form>
                    ) : (
                      <div className="identra-modal__result">
                        <div className="identra-modal__result-badge">
                          <CheckCircle2 size={24} color="#16A34A" />
                          <div>
                            <strong>
                              {quizAnswer === selectedItem.quizQuestion.correctIndex
                                ? isHindi
                                  ? 'शाबाश! सही उत्तर'
                                  : 'Correct Answer!'
                                : isHindi
                                  ? 'धन्यवाद! आपका उत्तर दर्ज कर लिया गया है'
                                  : 'Thank you! Your participation is recorded.'}
                            </strong>
                            <p>
                              {isHindi
                                ? 'राष्ट्रीय पहचान एवं नागरिक सतर्कता अभियान में भाग लेने के लिए धन्यवाद। आपका डिजिटल सहभागिता प्रमाणपत्र तैयार है।'
                                : 'Thank you for supporting national security awareness. An official digital participation badge has been credited.'}
                            </p>
                          </div>
                        </div>
                        <button
                          type="button"
                          className="identra-modal__btn-secondary"
                          onClick={() => setQuizSubmitted(false)}
                        >
                          {isHindi ? 'पुनः प्रयास करें' : 'Try Again'}
                        </button>
                      </div>
                    )}
                  </div>
                )}

                {/* 2. Interactive Broadcast / Stream Feature */}
                {selectedItem.actionType === 'stream' && (
                  <div className="identra-modal__interactive-block">
                    <h4 className="identra-modal__block-title">
                      <Radio size={16} />
                      {isHindi ? 'आधिकारिक प्रसारण केंद्र' : 'Official Media Stream'}
                    </h4>

                    <div className="identra-modal__player">
                      <div className="identra-modal__player-screen">
                        <PlayCircle
                          size={48}
                          className={`identra-modal__play-icon ${isPlaying ? 'identra-modal__play-icon--active' : ''}`}
                          onClick={() => setIsPlaying(!isPlaying)}
                        />
                        <div className="identra-modal__player-overlay">
                          <span className="identra-modal__live-indicator">
                            <span className="identra-modal__live-dot" /> LIVE
                          </span>
                          <span className="identra-modal__player-time">
                            {isPlaying ? '03:42 / 32:00' : '00:00 / 32:00'}
                          </span>
                        </div>
                      </div>

                      <div className="identra-modal__stream-info">
                        <button
                          type="button"
                          className="identra-modal__submit-btn"
                          onClick={() => setIsPlaying(!isPlaying)}
                        >
                          {isPlaying
                            ? isHindi
                              ? 'प्रसारण रोकें'
                              : 'Pause Broadcast'
                            : isHindi
                              ? 'प्रसारण शुरू करें'
                              : 'Tune in to Stream'}
                        </button>
                        <div className="identra-modal__highlights">
                          <strong>{isHindi ? 'मुख्य बिंदु:' : 'Broadcast Highlights:'}</strong>
                          <ul>
                            {selectedItem.streamDetails.highlights.map((h, i) => (
                              <li key={i}>{h}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* 3. Interactive Contest Submission */}
                {selectedItem.actionType === 'contest' && (
                  <div className="identra-modal__interactive-block">
                    <h4 className="identra-modal__block-title">
                      <Flame size={16} />
                      {isHindi ? 'प्रतियोगिता पंजीकरण एवं सबमिशन' : 'Competition Portal'}
                    </h4>

                    {!entrySubmitted ? (
                      <form onSubmit={handleContestSubmit} className="identra-modal__contest-form">
                        <div className="identra-modal__form-row">
                          <div className="identra-modal__form-field">
                            <label>{isHindi ? 'आपका पूरा नाम' : 'Full Name'}</label>
                            <input
                              type="text"
                              placeholder={isHindi ? 'उदा. अमित कुमार' : 'e.g. Vikram Sharma'}
                              required
                            />
                          </div>
                          <div className="identra-modal__form-field">
                            <label>{isHindi ? 'ईमेल आईडी' : 'Official Email'}</label>
                            <input
                              type="email"
                              placeholder="creator@domain.in"
                              required
                            />
                          </div>
                        </div>

                        <div className="identra-modal__form-field">
                          <label>{isHindi ? 'रील वीडियो लिंक (Drive / YouTube / Instagram)' : 'Reel Video Link (Drive / YouTube / Portal)'}</label>
                          <input
                            type="url"
                            placeholder="https://..."
                            required
                          />
                        </div>

                        <div className="identra-modal__guidelines">
                          <span>{selectedItem.contestDetails.prizePool}</span>
                          <span>·</span>
                          <span>{selectedItem.contestDetails.eligibility}</span>
                        </div>

                        <button type="submit" className="identra-modal__submit-btn">
                          {isHindi ? 'प्रविष्टि जमा करें' : 'Submit Entry Now'}
                        </button>
                      </form>
                    ) : (
                      <div className="identra-modal__result">
                        <CheckCircle2 size={24} color="#16A34A" />
                        <div>
                          <strong>{isHindi ? 'प्रविष्टि सफलतापूर्वक प्राप्त हुई!' : 'Entry Submitted Successfully!'}</strong>
                          <p>
                            {isHindi
                              ? 'आपकी प्रविष्टि समीक्षा समिति को प्रेषित कर दी गई है। संदर्भ संख्या: IDN-2024-8849.'
                              : 'Your submission has been cataloged under Reference: IDN-2024-8849. Winners will be announced on the portal.'}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Modal Footer */}
              <div className="identra-modal__footer">
                <button
                  type="button"
                  className="identra-modal__btn-secondary"
                  onClick={() => setSelectedItem(null)}
                >
                  {isHindi ? 'बंद करें' : 'Close'}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </section>
  );
}
