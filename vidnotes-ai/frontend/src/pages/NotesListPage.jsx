import { BookOpen, Search } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import NoteRow from '../components/NoteRow.jsx';
import Notice from '../components/Notice.jsx';
import { SkeletonRows } from '../components/Skeleton.jsx';
import { deleteVideo, listVideos } from '../services/api.js';
import '../styles/pages.css';

const SEARCH_DELAY_MS = 250;

export default function NotesListPage() {
  const [videos, setVideos] = useState(null);
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');
  const [deletingId, setDeletingId] = useState(null);

  useEffect(() => {
    let cancelled = false;
    // Wait until the user pauses typing before searching.
    const timer = setTimeout(() => {
      listVideos(search.trim())
        .then((data) => {
          if (!cancelled) {
            setVideos(data);
            setError('');
          }
        })
        .catch((err) => !cancelled && setError(err.message));
    }, SEARCH_DELAY_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [search]);

  async function handleDelete(video) {
    if (!window.confirm(`Delete the notes for "${video.title}"? This cannot be undone.`)) return;
    setDeletingId(video.id);
    try {
      await deleteVideo(video.id);
      setVideos((current) => current.filter((v) => v.id !== video.id));
    } catch (err) {
      setError(err.message);
    } finally {
      setDeletingId(null);
    }
  }

  const isSearching = search.trim().length > 0;

  return (
    <div className="container">
      <header className="page-header notes-header">
        <div>
          <h1 className="page-title">My Notes</h1>
          <p className="page-subtitle">Every video you analyze is saved here.</p>
        </div>
        <label className="search-field">
          <Search size={16} />
          <span className="visually-hidden">Search notes by title</span>
          <input
            className="input"
            type="search"
            placeholder="Search by title"
            value={search}
            maxLength={100}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
      </header>

      {error && (
        <Notice variant="error" title="Something went wrong">
          {error}
        </Notice>
      )}

      {!videos && !error && <SkeletonRows count={3} label="Loading your notes" />}

      {videos && videos.length > 0 && (
        <ul className="note-list">
          {videos.map((video, index) => (
            <NoteRow
              key={video.id}
              video={video}
              index={index}
              onDelete={handleDelete}
              deleting={deletingId === video.id}
            />
          ))}
        </ul>
      )}

      {videos && videos.length === 0 && (
        <div className="empty-state">
          <BookOpen size={28} />
          <h2>{isSearching ? 'No matching notes' : 'No notes yet'}</h2>
          <p>{isSearching ? `Nothing found for "${search.trim()}".` : 'Analyze a video and it will appear here.'}</p>
          {!isSearching && (
            <Link to="/#analyze" className="btn btn-primary">
              Analyze a video
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
