import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import Notice from './Notice.jsx';
import { PageLoader } from './Skeleton.jsx';

// Pages inside this route need a signed-in user (always true in local mode).
export default function ProtectedRoute() {
  const { status, error } = useAuth();
  const location = useLocation();

  if (status === 'loading') return <PageLoader />;
  if (status === 'error') {
    return (
      <div className="container page-header">
        <Notice variant="error" title="Could not start VidNotes">
          {error}
        </Notice>
      </div>
    );
  }
  if (status === 'signedOut') {
    return <Navigate to="/login" replace state={{ from: `${location.pathname}${location.search}` }} />;
  }
  return <Outlet />;
}
