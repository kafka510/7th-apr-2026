import { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';

export type Theme = 'light' | 'dark';

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

const THEME_STORAGE_KEY = 'peak-energy-theme';

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => {
    // Check localStorage first
    const savedTheme = localStorage.getItem(THEME_STORAGE_KEY) as Theme;
    if (savedTheme === 'light' || savedTheme === 'dark') {
      return savedTheme;
    }
    
    // Check system preference
    if (typeof window !== 'undefined' && window.matchMedia) {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      return prefersDark ? 'dark' : 'light';
    }
    
    // Default to dark (current app default)
    return 'dark';
  });

  useEffect(() => {
    // Apply theme to document
    const root = document.documentElement;
    const body = document.body;
    const reactRoot = document.getElementById('react-root');
    const contentArea = document.querySelector('.content-area') as HTMLElement;
    
    // Set background colors for body and root elements
    const bgColor = theme === 'dark' ? '#1a2233' : '#f8fbff';
    const textColor = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';
    
    body.style.backgroundColor = bgColor;
    body.style.color = textColor;
    body.style.transition = 'background-color 0.3s ease, color 0.3s ease';
    
    if (reactRoot) {
      reactRoot.style.backgroundColor = bgColor;
      reactRoot.style.transition = 'background-color 0.3s ease';
    }
    
    // Apply theme to content-area (from base.html)
    if (contentArea) {
      contentArea.style.backgroundColor = bgColor;
      contentArea.style.color = textColor;
      contentArea.style.transition = 'background-color 0.3s ease, color 0.3s ease';
    }
    
    if (theme === 'dark') {
      root.setAttribute('data-theme', 'dark');
      body.setAttribute('data-theme', 'dark');
    } else {
      root.setAttribute('data-theme', 'light');
      body.setAttribute('data-theme', 'light');
    }
    
    // Also set class for compatibility
    root.classList.toggle('dark', theme === 'dark');
    root.classList.toggle('light', theme === 'light');
    
    // Save to localStorage
    localStorage.setItem(THEME_STORAGE_KEY, theme);
    
    // Dispatch custom event for Django templates to sync
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('theme-changed', { detail: { theme } }));
      
      // Send postMessage to all iframes (for cross-iframe theme sync)
      try {
        const iframes = document.querySelectorAll('iframe');
        iframes.forEach((iframe) => {
          try {
            iframe.contentWindow?.postMessage(
              { type: 'theme-changed', theme },
              '*'
            );
          } catch {
            // Ignore cross-origin errors
          }
        });
      } catch {
        // Ignore errors
      }
      
      // Also notify parent window if we're in an iframe
      if (window.parent !== window) {
        try {
          window.parent.postMessage(
            { type: 'theme-changed', theme, source: 'iframe' },
            '*'
          );
        } catch {
          // Ignore cross-origin errors
        }
      }
    }
  }, [theme]);

  // Listen for theme changes from parent window (when in iframe) and storage events
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      // Accept messages from same origin or trusted sources
      // Only process if theme is different to avoid unnecessary updates
      if (event.data && event.data.type === 'theme-changed' && event.data.theme) {
        const newTheme = event.data.theme as Theme;
        if ((newTheme === 'light' || newTheme === 'dark') && newTheme !== theme) {
          setThemeState(newTheme);
        }
      }
    };

    const handleStorage = (e: StorageEvent) => {
      if (e.key === THEME_STORAGE_KEY && e.newValue) {
        const newTheme = e.newValue as Theme;
        if ((newTheme === 'light' || newTheme === 'dark') && newTheme !== theme) {
          setThemeState(newTheme);
        }
      }
    };

    window.addEventListener('message', handleMessage);
    window.addEventListener('storage', handleStorage);

    return () => {
      window.removeEventListener('message', handleMessage);
      window.removeEventListener('storage', handleStorage);
    };
  }, [theme]); // Include theme in dependencies to check for changes

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme);
  };

  const toggleTheme = () => {
    setThemeState((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}


