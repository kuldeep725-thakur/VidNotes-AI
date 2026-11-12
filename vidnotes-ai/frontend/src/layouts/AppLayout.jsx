import { Outlet, useLocation } from 'react-router-dom';
import Navbar from '../components/Navbar.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { useTheme } from '../hooks/useTheme.js';

export default function AppLayout() {
  const { status, preferences, updatePreferences } = useAuth();
  const { theme, toggleTheme } = useTheme(preferences.theme, (next) => {
    // Saved to the account in the background; the toggle works either way.
    if (status === 'signedIn') updatePreferences({ theme: next }).catch(() => {});
  });
  const location = useLocation();

  return (
    <div className="app-shell">
      <Navbar theme={theme} onToggleTheme={toggleTheme} />
      {/* Keyed by path so each page gets a short entrance transition. */}
      <main key={location.pathname} className="app-main page-enter">
        <Outlet />
      </main>
      <footer className="footer">
        <div className="container footer-inner">
          <span>VidNotes AI — Turn videos into knowledge.</span>
          <span>Generated content is based on the video transcript. Always verify important facts.</span>
        </div>
      </footer>
    </div>
  );
}
