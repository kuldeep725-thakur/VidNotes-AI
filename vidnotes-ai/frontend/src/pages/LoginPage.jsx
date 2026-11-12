import { LoaderCircle } from 'lucide-react';
import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import AuthCard, { Divider, GoogleButton, PasswordInput } from '../components/AuthCard.jsx';
import Notice from '../components/Notice.jsx';
import { useAuth } from '../context/AuthContext.jsx';

export default function LoginPage() {
  const { status, mode, signInWithGoogle, signInWithPassword } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const nextPath = location.state?.from || '/notes';
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  if (status === 'signedIn') return <Navigate to={mode === 'local' ? '/' : nextPath} replace />;

  async function run(action) {
    setBusy(true);
    setError('');
    try {
      await action();
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    run(async () => {
      await signInWithPassword(email.trim(), password);
      navigate(nextPath, { replace: true });
    });
  }

  return (
    <AuthCard
      title="Welcome back"
      subtitle={location.state?.reason || 'Log in to open your notes, quizzes and tasks on any device.'}
      footer={
        <>
          New to VidNotes? <Link to="/signup" state={location.state}>Create an account</Link>
        </>
      }
    >
      <GoogleButton onClick={() => run(() => signInWithGoogle(nextPath))} disabled={busy} />
      <Divider />
      <form className="auth-form" onSubmit={handleSubmit}>
        <label htmlFor="login-email">Email</label>
        <input
          id="login-email"
          className="input"
          type="email"
          autoComplete="email"
          placeholder="you@example.com"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />
        <div className="label-row">
          <label htmlFor="login-password">Password</label>
          <Link to="/forgot-password" className="auth-link-small">
            Forgot password?
          </Link>
        </div>
        <PasswordInput id="login-password" value={password} onChange={setPassword} autoComplete="current-password" />
        {error && <Notice variant="error">{error}</Notice>}
        <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
          {busy && <LoaderCircle size={16} className="spin" />}
          Log in
        </button>
      </form>
    </AuthCard>
  );
}
