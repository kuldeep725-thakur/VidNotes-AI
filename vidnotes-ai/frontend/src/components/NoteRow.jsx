import { Trash2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { formatDate, formatDuration } from '../utils/format.js';
import StatusBadge from './StatusBadge.jsx';
import Thumbnail from './Thumbnail.jsx';

export default function NoteRow({ video, index = 0, onDelete, deleting = false }) {
  const details = [video.channel_name, formatDuration(video.duration_seconds), formatDate(video.created_at)];

  return (
    <li className="note-row" style={{ '--i': index }}>
      <Link to={`/notes/${video.id}`} className="note-row-link">
        <span className="note-row-thumb">
          <Thumbnail src={video.thumbnail_url} youtubeId={video.youtube_id} lazy />
        </span>
        <span className="note-row-text">
          <span className="note-row-title">{video.title}</span>
          <span className="note-row-meta">{details.filter(Boolean).join(' · ')}</span>
        </span>
        <StatusBadge status={video.status} />
      </Link>
      {onDelete && (
        <button
          type="button"
          className="btn btn-ghost btn-icon note-row-delete"
          onClick={() => onDelete(video)}
          disabled={deleting || video.status === 'processing'}
          aria-label={`Delete notes for ${video.title}`}
          title={video.status === 'processing' ? 'Wait for processing to finish' : 'Delete'}
        >
          <Trash2 size={16} />
        </button>
      )}
    </li>
  );
}
