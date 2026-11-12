import { LoaderCircle, MailCheck } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import AuthCard from '../components/AuthCard.jsx';
import Notice from '../components/Notice.jsx';
import { useAuth } from '../context/AuthContext.jsx';

export default function ForgotPasswordPage() {
  const { sendPasswordReset } = useAuth();
  const [email, setEmail] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [sent, setSent] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      await sendPasswordReset(email.trim());
      setSent(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthCard
      title="Reset your password"
      subtitle={sent ? null : "Enter your account's email and we'll send you a link to choose a new password."}
      footer={<Link to="/login">Back to log in</Link>}
    >
      {sent ? (
        <div className="auth-success">
          <MailCheck size={28} />
          <p>
            If an account exists for <strong>{email.trim()}</strong>, a reset link is on its way. Open it in this
            browser.
          </p>
        </div>
      ) : (
        <form className="auth-form" onSubmit={handleSubmit}>
          <label htmlFor="reset-email">Email</label>
          <input
            id="reset-email"
            className="input"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
          {error && <Notice variant="error">{error}</Notice>}
          <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
            {busy && <LoaderCircle size={16} className="spin" />}
            Send reset link
          </button>
        </form>
      )}
    </AuthCard>
  );
}
