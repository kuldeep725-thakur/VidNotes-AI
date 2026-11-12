import { Lightbulb } from 'lucide-react';
import { formatTimestamp, videoLinkAt } from '../../utils/format.js';

function TimeLink({ seconds, videoUrl }) {
  return (
    <a className="time-chip" href={videoLinkAt(videoUrl, seconds)} target="_blank" rel="noreferrer">
      {formatTimestamp(seconds)}
    </a>
  );
}

export default function NotesView({ notes, videoUrl }) {
  return (
    <div className="notes-layout">
      <nav className="notes-toc" aria-label="Sections">
        <p className="eyebrow">Contents</p>
        <ol>
          {notes.sections.map((section, index) => (
            <li key={index}>
              <a href={`#section-${index}`}>{section.heading}</a>
            </li>
          ))}
        </ol>
      </nav>

      <div className="notes-body">
        {notes.sections.map((section, index) => (
          <section key={index} id={`section-${index}`} className="note-section">
            <div className="note-section-head">
              <h2>{section.heading}</h2>
              <TimeLink seconds={section.start_seconds} videoUrl={videoUrl} />
            </div>
            {section.introduction && <p className="prose">{section.introduction}</p>}

            {section.subsections.map((sub, subIndex) => (
              <div key={subIndex} className="note-sub">
                <h3>{sub.heading}</h3>
                {sub.definition && (
                  <p className="definition">
                    <span>Definition</span>
                    {sub.definition}
                  </p>
                )}
                {sub.points.length > 0 && (
                  <ul className="note-points">
                    {sub.points.map((point, pointIndex) => (
                      <li key={pointIndex}>{point}</li>
                    ))}
                  </ul>
                )}
                {sub.example && (
                  <p className="example">
                    <Lightbulb size={15} />
                    <span>
                      <strong>Example</strong> {sub.example}
                    </span>
                  </p>
                )}
              </div>
            ))}
          </section>
        ))}
      </div>
    </div>
  );
}
