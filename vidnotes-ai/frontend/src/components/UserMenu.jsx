import { BookOpen, ListTodo, LogOut, UserRound } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import Avatar from './Avatar.jsx';

export default function UserMenu() {
  const { profile, user, signOut } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const menuRef = useRef(null);

  const name = profile?.full_name || user?.user_metadata?.full_name || 'Your account';
  const email = profile?.email || user?.email;
  const avatarUrl = profile?.avatar_url || user?.user_metadata?.avatar_url;

  useEffect(() => {
    if (!open) return undefined;
    const close = (event) => {
      if (event.type === 'keydown' ? event.key === 'Escape' : !menuRef.current?.contains(event.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', close);
    return () => {
      document.removeEventListener('mousedown', close);
      document.removeEventListener('keydown', close);
    };
  }, [open]);

  async function handleSignOut() {
    setOpen(false);
    await signOut();
    navigate('/login', { replace: true });
  }

  return (
    <div className="user-menu" ref={menuRef}>
      <button
        type="button"
        className="user-menu-trigger"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Account menu"
        onClick={() => setOpen((value) => !value)}
      >
        <Avatar name={name} email={email} url={avatarUrl} />
      </button>
      {open && (
        <div className="menu" role="menu">
          <div className="menu-header">
            <Avatar name={name} email={email} url={avatarUrl} size={36} />
            <div>
              <p className="menu-name">{name}</p>
              {email && <p className="menu-email">{email}</p>}
            </div>
          </div>
          <Link role="menuitem" to="/profile" className="menu-item" onClick={() => setOpen(false)}>
            <UserRound size={15} /> Profile & preferences
          </Link>
          <Link role="menuitem" to="/notes" className="menu-item" onClick={() => setOpen(false)}>
            <BookOpen size={15} /> My Notes
          </Link>
          <Link role="menuitem" to="/todos" className="menu-item" onClick={() => setOpen(false)}>
            <ListTodo size={15} /> To-Do
          </Link>
          <button role="menuitem" type="button" className="menu-item danger" onClick={handleSignOut}>
            <LogOut size={15} /> Sign out
          </button>
        </div>
      )}
    </div>
  );
}
