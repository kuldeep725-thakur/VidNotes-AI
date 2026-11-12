import { Clock, Download, ExternalLink, LoaderCircle, User } from 'lucide-react';
import { useState } from 'react';
import { downloadPdf } from '../services/api.js';
import { formatDuration } from '../utils/format.js';
import LanguageToggle from './LanguageToggle.jsx';
import StatusBadge from './StatusBadge.jsx';
import Thumbnail from './Thumbnail.jsx';

function PdfButton({ videoId, language }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function handleClick() {
    setBusy(true);
    setError('');
    try {
      await downloadPdf(videoId, language);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button type="button" className="btn btn-sm" onClick={handleClick} disabled={busy}>
        {busy ? <LoaderCircle size={14} className="spin" /> : <Download size={14} />}
        {language === 'en' ? 'English PDF' : 'Hinglish PDF'}
      </button>
      {error && (
        <span className="inline-error" role="alert">
          {error}
        </span>
      )}
    </>
  );
}

export default function VideoHeader({ video, language, onLanguageChange }) {
  const ready = video.status === 'completed';
  const duration = formatDuration(video.duration_seconds);
  const title = video.title && video.title !== 'Untitled video' ? video.title : 'Fetching video details…';

  return (
    <section className="video-header">
      <a className="video-thumb" href={video.url} target="_blank" rel="noreferrer" aria-label="Watch on YouTube">
        <Thumbnail key={video.thumbnail_url} src={video.thumbnail_url} youtubeId={video.youtube_id} />
      </a>

      <div className="video-info">
        <StatusBadge status={video.status} />
        <h1 className="video-title">{title}</h1>
        <ul className="video-meta">
          {video.channel_name && (
            <li>
              <User size={14} /> {video.channel_name}
            </li>
          )}
          {duration && (
            <li>
              <Clock size={14} /> {duration}
            </li>
          )}
        </ul>

        <div className="video-actions">
          {ready && <LanguageToggle value={language} onChange={onLanguageChange} />}
          {ready && <PdfButton videoId={video.id} language={language} />}
          <a className="btn btn-sm btn-ghost" href={video.url} target="_blank" rel="noreferrer">
            <ExternalLink size={14} />
            YouTube
          </a>
        </div>
      </div>
    </section>
  );
}
