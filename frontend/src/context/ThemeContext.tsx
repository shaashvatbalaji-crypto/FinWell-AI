import React, { createContext, useContext, useState, useEffect } from 'react';

type ThemeMode = 'dark' | 'light';

interface ThemeContextType {
  mode: ThemeMode;
  toggleMode: () => void;
  accentColor: string;
  setAccentColor: (color: string) => void;
  reducedMotion: boolean;
  setReducedMotion: (val: boolean) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [mode, setMode] = useState<ThemeMode>('dark');
  const [accentColor, setAccentColor] = useState<string>('#4263FF');
  const [reducedMotion, setReducedMotion] = useState<boolean>(false);

  useEffect(() => {
    // Keep dark class on html root for modern fintech aesthetics
    document.documentElement.classList.add('dark');
  }, []);

  const toggleMode = () => {
    // In FinWell AI, dark mode is the signature aesthetic inspired by NeuroBank
    // Light mode can be toggled if requested, or toggles subtle high-contrast accents
    setMode((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  return (
    <ThemeContext.Provider
      value={{
        mode,
        toggleMode,
        accentColor,
        setAccentColor,
        reducedMotion,
        setReducedMotion,
      }}
    >
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
