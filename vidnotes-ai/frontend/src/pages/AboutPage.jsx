import { Link } from 'react-router-dom';
import '../styles/pages.css';

export default function AboutPage() {
  return (
    <div className="container">
      <article className="about">
        <header className="page-header">
          <p className="eyebrow">About</p>
          <h1 className="page-title">Study from videos without rewatching them.</h1>
        </header>

        <p className="prose">
          VidNotes AI reads the transcript of a YouTube video and turns it into material you can revise from: a
          summary, topic-wise study notes, important concepts, a quiz, exam-style questions and clickable timestamps.
          Everything is available in English and in Hinglish.
        </p>

        <h2>How the content is made</h2>
        <p className="prose">
          The transcript is fetched with Supadata. Google Gemini then writes the notes using only what is said in the
          video, and Groq can optionally step in when Gemini is busy or out of quota. Long videos are split into parts,
          each part is turned into detailed notes, and the parts are combined so later topics are not lost. The
          Hinglish version is translated from the English notes, so both teach exactly the same concepts.
        </p>

        <h2>Good to know</h2>
        <ul className="about-list">
          <li>Videos need captions or clear speech. Music-only videos cannot be summarised.</li>
          <li>AI can make mistakes. Check important facts against the video using the timestamps.</li>
          <li>Your notes are stored locally in a SQLite database on the machine running the backend.</li>
          <li>API keys stay on the backend and are never sent to the browser.</li>
        </ul>

        <Link to="/#analyze" className="btn btn-primary">
          Analyze a video
        </Link>
      </article>
    </div>
  );
}
