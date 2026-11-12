import { useState } from 'react';

function initials(name, email) {
  const source = name?.trim() || email || '?';
  const parts = source.split(/[\s@._-]+/).filter(Boolean);
  return ((parts[0]?.[0] ?? '?') + (parts[1]?.[0] ?? '')).toUpperCase();
}

// Google profile picture when available, otherwise the user's initials.
export default function Avatar({ name, email, url, size = 32 }) {
  const [broken, setBroken] = useState(false);
  return (
    <span className="avatar" style={{ '--size': `${size}px` }} aria-hidden="true">
      {url && !broken ? (
        <img src={url} alt="" referrerPolicy="no-referrer" onError={() => setBroken(true)} />
      ) : (
        initials(name, email)
      )}
    </span>
  );
}
