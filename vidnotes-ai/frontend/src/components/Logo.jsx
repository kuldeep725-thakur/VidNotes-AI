import { Link } from 'react-router-dom';

// An open book whose right page carries a small play triangle.
function LogoMark() {
  return (
    <svg className="logo-mark" width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M3 5.5c2.9-1 5.8-.8 8.3.8v13.2c-2.5-1.6-5.4-1.8-8.3-.8z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path
        d="M21 5.5c-2.9-1-5.8-.8-8.3.8v13.2c2.5-1.6 5.4-1.8 8.3-.8z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path d="M15.2 10.2v4.6l3.6-2.3z" fill="var(--color-blue)" />
    </svg>
  );
}

export default function Logo() {
  return (
    <Link to="/" className="logo" aria-label="VidNotes AI home">
      <LogoMark />
      <span className="logo-text">
        VidNotes <span className="logo-ai">AI</span>
      </span>
    </Link>
  );
}
