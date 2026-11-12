import { ArrowRight, BookOpenText, Clock, FileText, ListChecks, MessagesSquare, Sparkles } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import NoteRow from '../components/NoteRow.jsx';
import UrlForm from '../components/UrlForm.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { listVideos } from '../services/api.js';
import '../styles/home.css';
import '../styles/pages.css';

const FEATURES = [
  { icon: FileText, title: 'Summary', text: 'Overview, topics, key concepts and takeaways.' },
  { icon: BookOpenText, title: 'Study notes', text: 'Headings, definitions, points and examples.' },
  { icon: ListChecks, title: 'Quiz', text: 'MCQs with scoring and explanations.' },
  { icon: MessagesSquare, title: 'Exam Q&A', text: 'Important questions with clear answers.' },
  { icon: Clock, title: 'Timestamps', text: 'Jump straight to key moments.' },
];

const STEPS = [
  { title: 'Paste a link', text: 'Any public YouTube video with captions or clear speech.' },
  { title: 'We read the transcript', text: 'Long videos are split into parts so nothing is skipped.' },
  { title: 'Study your way', text: 'Switch between English and Hinglish, take the quiz, export a PDF.' },
];

export default function HomePage() {
  const inputRef = useRef(null);
  const location = useLocation();
  const [recent, setRecent] = useState([]);
  const { status } = useAuth();

  useEffect(() => {
    if (location.hash === '#analyze') {
      inputRef.current?.focus();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, [location]);

  useEffect(() => {
    // Recent notes are a convenience; the page works fine without them.
    if (status !== 'signedIn') {
      setRecent([]);
      return;
    }
    listVideos()
      .then((videos) => setRecent(videos.filter((v) => v.status === 'completed').slice(0, 3)))
      .catch(() => setRecent([]));
  }, [status]);

  return (
    <>
      <section className="hero">
        <div className="container">
          <span className="hero-eyebrow">
            <Sparkles size={13} /> YouTube to study material
          </span>
          <h1 className="hero-title">
            Learn smarter. <em>Not longer.</em>
          </h1>
          <p className="hero-description">
            Turn any YouTube video into structured notes, summaries, quizzes and study material.
          </p>
          <UrlForm inputRef={inputRef} />
        </div>
      </section>

      <div className="container">
        <div className="features">
          {FEATURES.map(({ icon: Icon, title, text }, index) => (
            <div key={title} className="feature" style={{ '--i': index }}>
              <Icon size={18} />
              <h3>{title}</h3>
              <p>{text}</p>
            </div>
          ))}
        </div>

        <section className="section">
          <div className="section-head">
            <h2 className="section-title">How it works</h2>
          </div>
          <div className="steps">
            {STEPS.map((step, index) => (
              <div key={step.title} className="step">
                <span className="step-number">0{index + 1}</span>
                <h3>{step.title}</h3>
                <p>{step.text}</p>
              </div>
            ))}
          </div>
        </section>

        {recent.length > 0 && (
          <section className="section">
            <div className="section-head">
              <h2 className="section-title">Continue studying</h2>
              <Link to="/notes" className="link-arrow">
                All notes <ArrowRight size={14} />
              </Link>
            </div>
            <ul className="note-list">
              {recent.map((video, index) => (
                <NoteRow key={video.id} video={video} index={index} />
              ))}
            </ul>
          </section>
        )}
      </div>
    </>
  );
}
