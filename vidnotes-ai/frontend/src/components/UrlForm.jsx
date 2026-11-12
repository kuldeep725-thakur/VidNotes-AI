import { ArrowRight, Link2, LoaderCircle } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { analyzeVideo } from '../services/api.js';
import { isValidYouTubeUrl } from '../utils/youtube.js';

const QUIZ_SIZES = [5, 10, 15, 20];

export default function UrlForm({ inputRef }) {
  const navigate = useNavigate();
  const { status, preferences } = useAuth();
  const [url, setUrl] = useState('');
  const [quizCount, setQuizCount] = useState(preferences.default_quiz_count);

  // Use the account's default once preferences have loaded.
  useEffect(() => setQuizCount(preferences.default_quiz_count), [preferences.default_quiz_count]);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!url.trim()) {
      setError('Paste a YouTube link to get started.');
      return;
    }
    if (!isValidYouTubeUrl(url)) {
      setError('That does not look like a YouTube video link.');
      return;
    }

    if (status === 'signedOut') {
      navigate('/login', { state: { from: '/', reason: 'Log in to analyze videos and save your notes.' } });
      return;
    }

    setError('');
    setSubmitting(true);
    try {
      const video = await analyzeVideo(url.trim(), quizCount);
      navigate(`/notes/${video.id}`);
    } catch (err) {
      setError(err.message);
      setSubmitting(false);
    }
  }

  return (
    <form className="url-form" onSubmit={handleSubmit} noValidate>
      <div className={`url-bar${error ? ' has-error' : ''}`}>
        <Link2 className="url-icon" size={18} aria-hidden="true" />
        <label htmlFor="video-url" className="visually-hidden">
          YouTube video URL
        </label>
        <input
          ref={inputRef}
          id="video-url"
          className="url-input"
          type="url"
          inputMode="url"
          autoComplete="off"
          placeholder="https://www.youtube.com/watch?v=..."
          value={url}
          onChange={(event) => {
            setUrl(event.target.value);
            if (error) setError('');
          }}
          aria-invalid={Boolean(error)}
          aria-describedby="url-hint"
          disabled={submitting}
        />
        <label htmlFor="quiz-count" className="visually-hidden">
          Number of quiz questions
        </label>
        <select
          id="quiz-count"
          className="quiz-count"
          value={quizCount}
          onChange={(event) => setQuizCount(Number(event.target.value))}
          disabled={submitting}
        >
          {QUIZ_SIZES.map((size) => (
            <option key={size} value={size}>
              {size} questions
            </option>
          ))}
        </select>
        <button type="submit" className="btn btn-primary url-submit" disabled={submitting}>
          {submitting ? <LoaderCircle size={16} className="spin" /> : <ArrowRight size={16} />}
          {submitting ? 'Starting…' : 'Analyze Video'}
        </button>
      </div>
      <p id="url-hint" className={`form-hint${error ? ' error' : ''}`} aria-live="polite">
        {error || 'Works with any public YouTube video that has captions or speech.'}
      </p>
    </form>
  );
}
