import { BookOpen, Home, Info, ListTodo, Moon, Sun } from 'lucide-react';
import { Link, NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import Logo from './Logo.jsx';
import UserMenu from './UserMenu.jsx';

const LINKS = [
  { to: '/', label: 'Home', icon: Home, end: true, className: 'nav-home' },
  { to: '/notes', label: 'My Notes', icon: BookOpen, needsAccount: true },
  { to: '/todos', label: 'To-Do', icon: ListTodo, needsAccount: true },
  { to: '/about', label: 'About', icon: Info },
];

function AccountActions() {
  const { mode, status } = useAuth();
  if (mode === 'cloud' && status === 'signedIn') return <UserMenu />;
  if (mode === 'cloud' && status === 'signedOut') {
    return (
      <>
        <Link to="/login" className="btn btn-ghost btn-sm nav-login">
          Log in
        </Link>
        <Link to="/signup" className="btn btn-primary btn-sm nav-get-started">
          Get Started
        </Link>
      </>
    );
  }
  // Local mode (and while loading): the original call to action.
  return (
    <Link to="/#analyze" className="btn btn-primary btn-sm nav-get-started">
      Get Started
    </Link>
  );
}

export default function Navbar({ theme, onToggleTheme }) {
  const { mode, status } = useAuth();
  const isDark = theme === 'dark';
  // Signed-out visitors only see pages they can open without an account.
  const links = LINKS.filter((link) => !(link.needsAccount && mode === 'cloud' && status === 'signedOut'));

  return (
    <header className="navbar">
      <div className="container navbar-inner">
        <Logo />
        <nav className="nav-links" aria-label="Main">
          {links.map(({ to, label, icon: Icon, end, className = '' }) => (
            <NavLink key={to} to={to} end={end} className={`nav-link ${className}`} aria-label={label}>
              <Icon size={16} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="nav-actions">
          <button
            type="button"
            className="btn btn-ghost btn-icon"
            onClick={onToggleTheme}
            aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
            title={isDark ? 'Light theme' : 'Dark theme'}
          >
            {isDark ? <Sun size={17} /> : <Moon size={17} />}
          </button>
          <AccountActions />
        </div>
      </div>
    </header>
  );
}
