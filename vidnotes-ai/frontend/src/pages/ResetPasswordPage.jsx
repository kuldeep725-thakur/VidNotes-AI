import { CheckCircle2, LoaderCircle } from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import AuthCard, { PasswordInput } from '../components/AuthCard.jsx';
import Notice from '../components/Notice.jsx';
import { PageLoader } from '../components/Skeleton.jsx';
import { useAuth } from '../context/AuthContext.jsx';

const MIN_PASSWORD_LENGTH = 8;

// Opened from the reset email. Supabase signs the user in from the link, so
// the new password can be saved with updateUser.
export default function ResetPasswordPage() {
  const { status, updatePassword } = useAuth();
  const navigate = useNavigate();
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);

  if (status === 'loading') return <PageLoader />;

  if (status !== 'signedIn') {
    return (
      <AuthCard title="Link expired" footer={<Link to="/forgot-password">Request a new link</Link>}>
        <Notice variant="error">
          This reset link is invalid or has expired. Links work once, and only in the browser where you requested
          them.
        </Notice>
      </AuthCard>
    );
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(`Use at least ${MIN_PASSWORD_LENGTH} characters for your password.`);
      return;
    }
    if (password !== confirmation) {
      setError('The two passwords do not match.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      await updatePassword(password);
      setDone(true);
      setTimeout(() => navigate('/notes', { replace: true }), 1500);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <AuthCard title="Choose a new password">
      {done ? (
        <div className="auth-success">
          <CheckCircle2 size={28} />
          <p>Your password was updated. Taking you to your notes…</p>
        </div>
      ) : (
        <form className="auth-form" onSubmit={handleSubmit}>
          <label htmlFor="new-password">New password</label>
          <PasswordInput
            id="new-password"
            value={password}
            onChange={setPassword}
            autoComplete="new-password"
            placeholder={`At least ${MIN_PASSWORD_LENGTH} characters`}
          />
          <label htmlFor="confirm-password">Confirm new password</label>
          <PasswordInput
            id="confirm-password"
            value={confirmation}
            onChange={setConfirmation}
            autoComplete="new-password"
            placeholder="Repeat the password"
          />
          {error && <Notice variant="error">{error}</Notice>}
          <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
            {busy && <LoaderCircle size={16} className="spin" />}
            Save new password
          </button>
        </form>
      )}
    </AuthCard>
  );
}
