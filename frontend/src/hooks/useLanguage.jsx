import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { translations, languageList } from '../i18n/translations';

const LanguageContext = createContext(null);

export const LanguageProvider = ({ children }) => {
  const [language, setLanguageState] = useState(() => {
    return localStorage.getItem('portal_language') || 'en';
  });

  const setLanguage = useCallback((langCode) => {
    if (translations[langCode]) {
      setLanguageState(langCode);
      localStorage.setItem('portal_language', langCode);
    }
  }, []);

  const t = useCallback((key, fallback = '') => {
    const langDict = translations[language] || translations.en;
    if (langDict && langDict[key]) {
      return langDict[key];
    }
    const defaultDict = translations.en;
    return defaultDict[key] || fallback || key;
  }, [language]);

  const selectedLangObj = languageList.find((l) => l.code === language) || languageList[0];

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t, languageList, selectedLangObj }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
};
