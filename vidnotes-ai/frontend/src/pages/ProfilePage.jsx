import { Check, Cloud, HardDrive, LoaderCircle, LogOut, Pencil } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Avatar from '../components/Avatar.jsx';
import Notice from '../components/Notice.jsx';
import { PageLoader } from '../components/Skeleton.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { updateProfile } from '../services/api.js';
import { formatDate } from '../utils/format.js';
import '../styles/pages.css';

const PROVIDERS = { google: 'Google', email: 'Email and password', local: 'Local mode' };
const STAT_LABELS = [
  ['videos', 'Videos'],
  ['quizzes_taken', 'Quizzes taken'],
  ['open_tasks', 'Open tasks'],
  ['done_tasks', 'Completed tasks'],
];

function Segmented({ label, value, options, onChange }) {
  return (
    <div className="segmented" role="radiogroup" aria-label={label}>
      {options.map(([optionValue, optionLabel]) => (
        <button
          key={optionValue}
          type="button"
          role="radio"
          aria-checked={value === optionValue}
          className={value === optionValue ? 'active' : ''}
          onClick={() => onChange(optionValue)}
        >
          {optionLabel}
        </button>
      ))}
    </div>
  );
}

export default function ProfilePage() {
  const { profile, setProfile, preferences, updatePreferences, mode, cloudSync, signOut } = useAuth();
  const navigate = useNavigate();
  const [editingName, setEditingName] = useState(false);
  const [name, setName] = useState('');
  const [saveState, setSaveState] = useState({ status: 'idle', message: '' });

  if (!profile) return <PageLoader />;

  async function savePreference(changes) {
    setSaveState({ status: 'saving', message: '' });
    try {
      await updatePreferences(changes);
      setSaveState({ status: 'saved', message: '' });
    } catch (error) {
      setSaveState({ status: 'error', message: error.message });
    }
  }

  async function saveName(event) {
    event.preventDefault();
    try {
      setProfile(await updateProfile(name));
      setEditingName(false);
    } catch (error) {
      setSaveState({ status: 'error', message: error.message });
    }
  }

  async function handleSignOut() {
    await signOut();
    navigate('/login', { replace: true });
  }

  const isLocal = mode === 'local';

  return (
    <div className="container profile-page">
      <header className="page-header profile-header">
        <Avatar name={profile.full_name} email={profile.email} url={profile.avatar_url} size={72} />
        <div className="profile-identity">
          {editingName ? (
            <form className="profile-name-form" onSubmit={saveName}>
              <input
                className="input"
                value={name}
                maxLength={200}
                onChange={(event) => setName(event.target.value)}
                aria-label="Your name"
                autoFocus
              />
              <button type="submit" className="btn btn-sm btn-primary" disabled={!name.trim()}>
                Save
              </button>
              <button type="button" className="btn btn-sm btn-ghost" onClick={() => setEditingName(false)}>
                Cancel
              </button>
            </form>
          ) : (
            <h1 className="page-title">
              {profile.full_name || 'Your profile'}
              {!isLocal && (
                <button
                  type="button"
                  className="btn btn-ghost btn-icon"
                  aria-label="Edit name"
                  onClick={() => {
                    setName(profile.full_name ?? '');
                    setEditingName(true);
                  }}
                >
                  <Pencil size={15} />
                </button>
              )}
            </h1>
          )}
          <p className="page-subtitle">
            {profile.email && <span>{profile.email} · </span>}
            {PROVIDERS[profile.provider] ?? 'Email and password'}
            {!isLocal && <span> · Member since {formatDate(profile.created_at)}</span>}
          </p>
        </div>
        {!isLocal && (
          <button type="button" className="btn" onClick={handleSignOut}>
            <LogOut size={15} /> Sign out
          </button>
        )}
      </header>

      <ul className="stat-grid">
        {STAT_LABELS.map(([key, label], index) => (
          <li key={key} className="stat" style={{ '--i': index }}>
            <span className="stat-value">{profile.stats[key]}</span>
            <span className="stat-label">{label}</span>
          </li>
        ))}
      </ul>

      <section className="settings">
        <div className="settings-head">
          <h2 className="section-title">Preferences</h2>
          <span className={`save-state ${saveState.status}`} aria-live="polite">
            {saveState.status === 'saving' && (
              <>
                <LoaderCircle size={13} className="spin" /> Saving
              </>
            )}
            {saveState.status === 'saved' && (
              <>
                <Check size={13} /> Saved
              </>
            )}
          </span>
        </div>
        {saveState.status === 'error' && <Notice variant="error">{saveState.message}</Notice>}

        <div className="setting">
          <div>
            <p className="setting-label">Theme</p>
            <p className="setting-help">Used on every device you sign in to.</p>
          </div>
          <Segmented
            label="Theme"
            value={preferences.theme ?? 'dark'}
            options={[['dark', 'Dark'], ['light', 'Light']]}
            onChange={(theme) => savePreference({ theme })}
          />
        </div>
        <div className="setting">
          <div>
            <p className="setting-label">Notes language</p>
            <p className="setting-help">The language a video opens in.</p>
          </div>
          <Segmented
            label="Notes language"
            value={preferences.default_language}
            options={[['en', 'English'], ['hinglish', 'Hinglish']]}
            onChange={(language) => savePreference({ default_language: language })}
          />
        </div>
        <div className="setting">
          <div>
            <p className="setting-label">Quiz questions</p>
            <p className="setting-help">Default number of questions for new videos.</p>
          </div>
          <select
            className="input setting-select"
            aria-label="Default number of quiz questions"
            value={preferences.default_quiz_count}
            onChange={(event) => savePreference({ default_quiz_count: Number(event.target.value) })}
          >
            {[5, 10, 15, 20].map((count) => (
              <option key={count} value={count}>
                {count} questions
              </option>
            ))}
          </select>
        </div>
      </section>

      <p className="sync-note">
        {isLocal ? (
          <>
            <HardDrive size={14} /> Local mode: your data is saved on this computer only. Set up Supabase (see
            README) to sign in and sync across devices.
          </>
        ) : cloudSync ? (
          <>
            <Cloud size={14} /> Your notes, quizzes, tasks and preferences are saved to your account and sync across
            devices.
          </>
        ) : (
          <>
            <HardDrive size={14} /> Signed in, but the server stores data locally. Set DATABASE_URL to your Supabase
            database to sync across devices.
          </>
        )}
      </p>
    </div>
  );
}
