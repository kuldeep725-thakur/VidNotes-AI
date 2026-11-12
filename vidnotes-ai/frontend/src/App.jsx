import { Link, Route, Routes } from 'react-router-dom';
import ProtectedRoute from './components/ProtectedRoute.jsx';
import AppLayout from './layouts/AppLayout.jsx';
import AboutPage from './pages/AboutPage.jsx';
import AuthCallbackPage from './pages/AuthCallbackPage.jsx';
import ForgotPasswordPage from './pages/ForgotPasswordPage.jsx';
import HomePage from './pages/HomePage.jsx';
import LoginPage from './pages/LoginPage.jsx';
import NotesListPage from './pages/NotesListPage.jsx';
import ProfilePage from './pages/ProfilePage.jsx';
import ResetPasswordPage from './pages/ResetPasswordPage.jsx';
import SignupPage from './pages/SignupPage.jsx';
import TodosPage from './pages/TodosPage.jsx';
import VideoPage from './pages/VideoPage.jsx';

function NotFound() {
  return (
    <div className="container">
      <header className="page-header">
        <h1 className="page-title">Page not found</h1>
        <p className="page-subtitle">
          <Link to="/" className="link-arrow">
            Go back home
          </Link>
        </p>
      </header>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<HomePage />} />
        <Route path="about" element={<AboutPage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="signup" element={<SignupPage />} />
        <Route path="forgot-password" element={<ForgotPasswordPage />} />
        <Route path="reset-password" element={<ResetPasswordPage />} />
        <Route path="auth/callback" element={<AuthCallbackPage />} />
        <Route element={<ProtectedRoute />}>
          <Route path="notes" element={<NotesListPage />} />
          <Route path="notes/:id" element={<VideoPage />} />
          <Route path="todos" element={<TodosPage />} />
          <Route path="profile" element={<ProfilePage />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
