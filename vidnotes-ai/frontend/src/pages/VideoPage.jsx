import { ArrowLeft, RotateCcw } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import Notice from '../components/Notice.jsx';
import ProgressPanel from '../components/ProgressPanel.jsx';
import ResultTabs from '../components/ResultTabs.jsx';
import { SkeletonRows } from '../components/Skeleton.jsx';
import VideoHeader from '../components/VideoHeader.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { useVideo } from '../hooks/useVideo.js';
import { analyzeVideo } from '../services/api.js';
import '../styles/results.css';
import '../styles/video.css';

export default function VideoPage() {
  const { id } = useParams();
  const { video, error, reload } = useVideo(id);
  const { preferences } = useAuth();
  const [language, setLanguage] = useState(preferences.default_language);
  const [retryError, setRetryError] = useState('');
  const [retrying, setRetrying] = useState(false);

  // Open in the account's preferred language once preferences have loaded.
  useEffect(() => setLanguage(preferences.default_language), [preferences.default_language]);

  async function retry() {
    setRetrying(true);
    setRetryError('');
    try {
      await analyzeVideo(video.url, preferences.default_quiz_count);
      reload();
    } catch (err) {
      setRetryError(err.message);
    } finally {
      setRetrying(false);
    }
  }

  return (
    <div className="container video-page">
      <Link to="/notes" className="back-link">
        <ArrowLeft size={14} /> My Notes
      </Link>

      {error && (
        <Notice variant="error" title="Could not load these notes">
          {error}
        </Notice>
      )}

      {!error && !video && <SkeletonRows count={1} label="Loading notes" />}

      {video && (
        <>
          <VideoHeader video={video} language={language} onLanguageChange={setLanguage} />

          {video.status === 'processing' && (
            <ProgressPanel progress={video.progress} message={video.progress_message} />
          )}

          {video.status === 'failed' && (
            <Notice
              variant="error"
              title="We could not generate notes for this video"
              actions={
                <button type="button" className="btn btn-sm" onClick={retry} disabled={retrying}>
                  <RotateCcw size={14} /> {retrying ? 'Restarting…' : 'Try again'}
                </button>
              }
            >
              {retryError || video.error_message}
            </Notice>
          )}

          {video.status === 'completed' && video.content?.[language] && (
            <ResultTabs
              content={video.content[language]}
              videoId={video.id}
              videoUrl={video.url}
              language={language}
            />
          )}
        </>
      )}
    </div>
  );
}
