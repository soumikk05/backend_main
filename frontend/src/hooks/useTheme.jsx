import { useState, useEffect, createContext, useContext, useCallback } from 'react';

const ThemeContext = createContext(null);

/*
 * Design tokens for National Portal of India (india.gov.in) Theme
 * 
 * Saffron: #FF9933 / #E65100 (Official National Flag Saffron)
 * White:   #FFFFFF
 * Green:   #138808 / #0E7A3E (Official National Flag Green)
 * Navy:    #1B365D / #0F2C59 (Official Government of India Deep Navy)
 * 
 * Light Mode: High-readability institutional portal palette.
 * Dark Mode / High Contrast: Accessible deep midnight government palette.
 */
const themes = {
  light: {
    '--bg-primary': '#F0F4F8',
    '--bg-secondary': '#FFFFFF',
    '--bg-tertiary': '#E2E8F0',
    '--bg-image': 'none',
    '--surface': '#FFFFFF',
    '--surface-hover': '#F8FAFC',
    '--surface-raised': '#FFFFFF',

    '--header-bg': '#FFFFFF',
    '--header-text': '#1B365D',
    '--header-topbar': '#0B1E36',
    '--header-nav-bg': '#1B365D',
    '--header-nav-text': '#FFFFFF',
    '--header-nav-hover': '#FF9933',

    '--text-primary': '#0F172A',
    '--text-secondary': '#334155',
    '--text-muted': '#64748B',
    '--text-inverse': '#FFFFFF',

    '--border-subtle': '#E2E8F0',
    '--border-default': '#CBD5E1',
    '--border-focus': '#1B365D',

    '--accent': '#1B365D',
    '--accent-alt': '#0F2C59',
    '--accent-saffron': '#FF9933',
    '--accent-saffron-hover': '#E68A00',
    '--accent-green': '#138808',
    '--accent-light': 'rgba(27, 54, 93, 0.08)',
    '--accent-glow': 'rgba(27, 54, 93, 0.15)',

    '--risk-low': '#138808',
    '--risk-low-bg': 'rgba(19, 136, 8, 0.08)',
    '--risk-medium': '#D97706',
    '--risk-medium-bg': 'rgba(217, 119, 6, 0.08)',
    '--risk-high': '#DC2626',
    '--risk-high-bg': 'rgba(220, 38, 38, 0.08)',

    '--success': '#138808',
    '--warning': '#D97706',
    '--error': '#DC2626',
    '--info': '#1B365D',

    '--card-shadow': '0 1px 3px rgba(15, 23, 42, 0.08), 0 1px 2px rgba(15, 23, 42, 0.04)',
    '--card-shadow-hover': '0 4px 12px rgba(27, 54, 93, 0.12)',

    '--footer-bg': '#0B1E36',
    '--footer-text': '#CBD5E1',

    '--input-bg': '#FFFFFF',
    '--input-border': '#CBD5E1',

    '--badge-neutral-bg': '#F1F5F9',
    '--badge-neutral-text': '#334155',
    '--badge-neutral-border': '#CBD5E1',

    '--sidebar-bg': '#FFFFFF',
    '--sidebar-width': '240px',
  },
  dark: {
    '--bg-primary': '#070D18',
    '--bg-secondary': '#0B1626',
    '--bg-tertiary': '#11223A',
    '--bg-image': 'none',
    '--surface': '#0B1626',
    '--surface-hover': '#11223A',
    '--surface-raised': '#162C4A',

    '--header-bg': '#070D18',
    '--header-text': '#F8FAFC',
    '--header-topbar': '#03070E',
    '--header-nav-bg': '#0B1E36',
    '--header-nav-text': '#F8FAFC',
    '--header-nav-hover': '#FF9933',

    '--text-primary': '#F8FAFC',
    '--text-secondary': '#94A3B8',
    '--text-muted': '#64748B',
    '--text-inverse': '#070D18',

    '--border-subtle': '#162C4A',
    '--border-default': '#223E66',
    '--border-focus': '#FF9933',

    '--accent': '#FF9933',
    '--accent-alt': '#FFA742',
    '--accent-saffron': '#FF9933',
    '--accent-saffron-hover': '#FFA742',
    '--accent-green': '#10B981',
    '--accent-light': 'rgba(255, 153, 51, 0.12)',
    '--accent-glow': 'rgba(255, 153, 51, 0.2)',

    '--risk-low': '#10B981',
    '--risk-low-bg': 'rgba(16, 185, 129, 0.12)',
    '--risk-medium': '#F59E0B',
    '--risk-medium-bg': 'rgba(245, 158, 11, 0.12)',
    '--risk-high': '#EF4444',
    '--risk-high-bg': 'rgba(239, 68, 68, 0.12)',

    '--success': '#10B981',
    '--warning': '#F59E0B',
    '--error': '#EF4444',
    '--info': '#38BDF8',

    '--card-shadow': '0 1px 3px rgba(0, 0, 0, 0.4)',
    '--card-shadow-hover': '0 6px 16px rgba(0, 0, 0, 0.6)',

    '--footer-bg': '#03070E',
    '--footer-text': '#94A3B8',

    '--input-bg': '#0B1626',
    '--input-border': '#223E66',

    '--badge-neutral-bg': '#11223A',
    '--badge-neutral-text': '#94A3B8',
    '--badge-neutral-border': '#223E66',

    '--sidebar-bg': '#091322',
    '--sidebar-width': '240px',
  },
};

const fontSizes = {
  small: '14px',
  normal: '15px',
  large: '17px',
};

export const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('gov_theme') || 'light';
  });

  const [fontSize, setFontSizeState] = useState(() => {
    return localStorage.getItem('gov_fontsize') || 'normal';
  });

  // Apply CSS variables to document root whenever theme changes
  useEffect(() => {
    const vars = themes[theme] || themes.light;
    const root = document.documentElement;
    Object.entries(vars).forEach(([key, value]) => {
      root.style.setProperty(key, value);
    });
    root.setAttribute('data-theme', theme);
    localStorage.setItem('gov_theme', theme);
  }, [theme]);

  // Apply font size adjustment to document root
  useEffect(() => {
    const size = fontSizes[fontSize] || fontSizes.normal;
    document.documentElement.style.fontSize = size;
    localStorage.setItem('gov_fontsize', fontSize);
  }, [fontSize]);

  const toggleTheme = useCallback(() => {
    setTheme(prev => (prev === 'light' ? 'dark' : 'light'));
  }, []);

  const setFontSize = useCallback((size) => {
    if (fontSizes[size]) {
      setFontSizeState(size);
    }
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, fontSize, setFontSize }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};
