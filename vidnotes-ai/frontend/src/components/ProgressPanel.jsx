import { Check, LoaderCircle } from 'lucide-react';

// Each stage is complete once the backend progress passes its threshold.
const STAGES = [
  { label: 'Fetch transcript', doneAt: 20 },
  { label: 'Write study notes', doneAt: 55 },
  { label: 'Summary, quiz & exam questions', doneAt: 70 },
  { label: 'Hinglish version', doneAt: 100 },
];

export default function ProgressPanel({ progress, message }) {
  const activeIndex = STAGES.findIndex((stage) => progress < stage.doneAt);

  return (
    <section className="progress-panel" aria-live="polite">
      <div className="progress-head">
        <div>
          <p className="progress-title">Generating your study material</p>
          <p className="progress-message">{message}…</p>
        </div>
        <span className="progress-value">{progress}%</span>
      </div>
      <div
        className="progress-track"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={progress}
      >
        <div className="progress-fill" style={{ width: `${Math.max(progress, 3)}%` }} />
      </div>
      <ol className="progress-stages">
        {STAGES.map((stage, index) => {
          const state = index < activeIndex || activeIndex === -1 ? 'done' : index === activeIndex ? 'active' : '';
          return (
            <li key={stage.label} className={state}>
              <span className="stage-icon">
                {state === 'done' && <Check size={12} />}
                {state === 'active' && <LoaderCircle size={12} className="spin" />}
              </span>
              {stage.label}
            </li>
          );
        })}
      </ol>
      <p className="progress-note">
        Long videos can take a few minutes. You can leave this page — the notes will appear in My Notes.
      </p>
    </section>
  );
}
