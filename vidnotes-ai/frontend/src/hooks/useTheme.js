import { useEffect, useState } from 'react';

const STORAGE_KEY = 'vidnotes-theme';

function readSavedTheme() {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'light' ? 'light' : 'dark';
  } catch {
    return 'dark';
  }
}

// `accountTheme` is the theme saved in the user's account. When it loads it
// wins, so the same theme follows the user to every device. `onChange` is
// called when the user toggles, to save the choice to the account.
export function useTheme(accountTheme, onChange) {
  const [theme, setTheme] = useState(readSavedTheme);

  useEffect(() => {
    if (accountTheme) setTheme(accountTheme);
  }, [accountTheme]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // Storage can be unavailable (private mode); the theme still applies.
    }
  }, [theme]);

  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    onChange?.(next);
  };
  return { theme, toggleTheme };
}
