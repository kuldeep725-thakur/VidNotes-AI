import { LoaderCircle, MailCheck } from 'lucide-react';
import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import AuthCard, { Divider, GoogleButton, PasswordInput } from '../components/AuthCard.jsx';
import Notice from '../components/Notice.jsx';
import { useAuth } from '../context/AuthContext.jsx';

const MIN_PASSWORD_LENGTH = 8;

export default function SignupPage() {
  const { status, mode, signInWithGoogle, signUp } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const nextPath = location.state?.from || '/notes';
  const [form, setForm] = useState({ name: '', email: '', password: '' });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [sentTo, setSentTo] = useState('');

  if (status === 'signedIn' && !sentTo) return <Navigate to={mode === 'local' ? '/' : nextPath} replace />;

  const update = (field) => (value) => setForm((current) => ({ ...current, [field]: value }));

  async function handleSubmit(event) {
    event.preventDefault();
    if (form.password.length < MIN_PASSWORD_LENGTH) {
      setError(`Use at least ${MIN_PASSWORD_LENGTH} characters for your password.`);
      return;
    }
    setBusy(true);
    setError('');
    try {
      const { needsConfirmation } = await signUp(form.name.trim(), form.email.trim(), form.password);
      if (needsConfirmation) setSentTo(form.email.trim());
      else navigate(nextPath, { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleGoogle() {
    setError('');
    try {
      await signInWithGoogle(nextPath);
    } catch (err) {
      setError(err.message);
    }
  }

  if (sentTo) {
    return (
      <AuthCard title="Check your inbox" footer={<Link to="/login">Back to log in</Link>}>
        <div className="auth-success">
          <MailCheck size={28} />
          <p>
            We sent a confirmation link to <strong>{sentTo}</strong>. Open it to activate your account, then log in.
          </p>
        </div>
      </AuthCard>
    );
  }

  return (
    <AuthCard
      title="Create your account"
      subtitle="Save your notes, quizzes and tasks, and open them on any device."
      footer={
        <>
          Already have an account? <Link to="/login" state={location.state}>Log in</Link>
        </>
      }
    >
      <GoogleButton onClick={handleGoogle} disabled={busy} />
      <Divider />
      <form className="auth-form" onSubmit={handleSubmit}>
        <label htmlFor="signup-name">Name</label>
        <input
          id="signup-name"
          className="input"
          autoComplete="name"
          placeholder="Your name"
          maxLength={200}
          value={form.name}
          onChange={(event) => update('name')(event.target.value)}
          required
        />
        <label htmlFor="signup-email">Email</label>
        <input
          id="signup-email"
          className="input"
          type="email"
          autoComplete="email"
          placeholder="you@example.com"
          value={form.email}
          onChange={(event) => update('email')(event.target.value)}
          required
        />
        <label htmlFor="signup-password">Password</label>
        <PasswordInput
          id="signup-password"
          value={form.password}
          onChange={update('password')}
          autoComplete="new-password"
          placeholder={`At least ${MIN_PASSWORD_LENGTH} characters`}
        />
        {error && <Notice variant="error">{error}</Notice>}
        <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
          {busy && <LoaderCircle size={16} className="spin" />}
          Create account
        </button>
      </form>
    </AuthCard>
  );
}
