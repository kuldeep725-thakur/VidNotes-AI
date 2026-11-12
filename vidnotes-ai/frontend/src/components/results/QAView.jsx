import { ChevronDown } from 'lucide-react';
import { useState } from 'react';

export default function QAView({ items }) {
  const [openItems, setOpenItems] = useState(() => new Set([0]));
  const allOpen = openItems.size === items.length;

  function toggle(index) {
    setOpenItems((current) => {
      const next = new Set(current);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }

  function toggleAll() {
    setOpenItems(allOpen ? new Set() : new Set(items.map((_, index) => index)));
  }

  return (
    <div className="reading">
      <div className="qa-toolbar">
        <p>Exam-oriented questions with model answers from the video.</p>
        <button type="button" className="btn btn-sm btn-ghost" onClick={toggleAll}>
          {allOpen ? 'Collapse all' : 'Expand all'}
        </button>
      </div>
      <ol className="qa-list">
        {items.map((item, index) => {
          const open = openItems.has(index);
          return (
            <li key={index} className={`qa-item${open ? ' open' : ''}`}>
              <button
                type="button"
                className="qa-question"
                aria-expanded={open}
                aria-controls={`qa-answer-${index}`}
                onClick={() => toggle(index)}
              >
                <span className="question-number">Q{index + 1}</span>
                <span className="qa-question-text">{item.question}</span>
                <ChevronDown size={16} className="qa-chevron" />
              </button>
              {open && (
                <p id={`qa-answer-${index}`} className="qa-answer">
                  {item.answer}
                </p>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
