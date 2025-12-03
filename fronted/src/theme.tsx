import React, { createContext, useContext, useState, ReactNode } from 'react';

interface Theme {
  name: string;
  primary: string;
  primaryHover: string;
  badge: string;
  iconBg: string;
  textHover: string;
  ring: string;
  bgSoft: string;
  text: string;
  border: string;
}

const defaultTheme: Theme = {
  name: 'default',
  primary: 'bg-blue-500',
  primaryHover: 'hover:bg-blue-600',
  badge: 'bg-blue-100 text-blue-800',
  iconBg: 'bg-blue-500',
  textHover: 'hover:text-blue-600',
  ring: 'focus:ring-2 focus:ring-blue-500 focus:border-transparent',
  bgSoft: 'bg-gray-50',
  text: 'text-gray-700',
  border: 'border-gray-300'
};

const ThemeContext = createContext<{
  theme: Theme;
  setTheme: (theme: Theme) => void;
}>({
  theme: defaultTheme,
  setTheme: () => {}
});

export const ThemeProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [theme, setTheme] = useState<Theme>(defaultTheme);

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
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