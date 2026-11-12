import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import AuthCard from '../components/AuthCard.jsx';
import Notice from '../components/Notice.jsx';
import { PageLoader } from '../components/Skeleton.jsx';
import { takeNextPath, useAuth } from '../context/AuthContext.jsx';

// Google sign-in and email confirmation links return here. Supabase finishes
// the sign-in from the URL; this page then continues to where the user was.
export default function AuthCallbackPage() {
  const { status } = useAuth();
  const navigate = useNavigate();
  const [providerError] = useState(() => {
    const params = new URLSearchParams(window.location.search + window.location.hash.replace('#', '&'));
    return params.get('error_description') || params.get('error');
  });

  useEffect(() => {
    if (status === 'signedIn') navigate(takeNextPath(), { replace: true });
  }, [status, navigate]);

  if (status === 'loading' || (status === 'signedIn' && !providerError)) return <PageLoader />;

  return (
    <AuthCard title="Sign-in did not finish" footer={<Link to="/login">Back to log in</Link>}>
      <Notice variant="error">
        {providerError || 'The sign-in link is invalid or has expired. Please try again.'}
      </Notice>
    </AuthCard>
  );
}
