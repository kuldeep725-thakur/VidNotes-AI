import { Check, Cloud, RotateCcw, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { listQuizResults, saveQuizResult } from '../../services/api.js';
import { formatDate } from '../../utils/format.js';

const LETTERS = ['A', 'B', 'C', 'D'];

function scoreMessage(percent) {
  if (percent >= 80) return 'Excellent work.';
  if (percent >= 50) return 'Good effort — review the explanations below.';
  return 'Revise the notes and try again.';
}

function optionState(question, optionIndex, selected, submitted) {
  if (!submitted) return selected === optionIndex ? 'selected' : '';
  if (optionIndex === question.correct_index) return 'correct';
  if (optionIndex === selected) return 'incorrect';
  return 'dimmed';
}

function AttemptHistory({ attempts }) {
  if (attempts.length === 0) return null;
  return (
    <section className="attempts">
      <p className="eyebrow">Your attempts</p>
      <ol>
        {attempts.map((attempt, index) => (
          <li key={attempt.id} style={{ '--i': index }}>
            <span className="attempt-score">
              {attempt.score}/{attempt.total}
            </span>
            <span className="attempt-bar" aria-hidden="true">
              <span style={{ width: `${Math.round((attempt.score / attempt.total) * 100)}%` }} />
            </span>
            <span className="attempt-meta">
              {attempt.language === 'en' ? 'English' : 'Hinglish'} · {formatDate(attempt.created_at)}
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}

export default function QuizView({ questions, videoId, language }) {
  const [answers, setAnswers] = useState({});
  const [submitted, setSubmitted] = useState(false);
  const [attempts, setAttempts] = useState([]);
  const [saveStatus, setSaveStatus] = useState('');

  useEffect(() => {
    let cancelled = false;
    listQuizResults(videoId)
      .then((results) => !cancelled && setAttempts(results))
      .catch(() => !cancelled && setAttempts([]));
    return () => {
      cancelled = true;
    };
  }, [videoId]);

  const answeredCount = Object.keys(answers).length;
  const score = questions.filter((q, index) => answers[index] === q.correct_index).length;
  const percent = Math.round((score / questions.length) * 100);

  function choose(questionIndex, optionIndex) {
    if (!submitted) setAnswers((current) => ({ ...current, [questionIndex]: optionIndex }));
  }

  async function submit() {
    setSubmitted(true);
    window.scrollTo({ top: 0, behavior: 'smooth' });
    // The server re-scores the answers and keeps the attempt in the account.
    setSaveStatus('saving');
    try {
      const saved = await saveQuizResult(videoId, language, questions.map((_, index) => answers[index] ?? null));
      setAttempts((current) => [saved, ...current].slice(0, 10));
      setSaveStatus('saved');
    } catch {
      setSaveStatus('error');
    }
  }

  function retry() {
    setAnswers({});
    setSubmitted(false);
    setSaveStatus('');
  }

  return (
    <div className="reading quiz">
      {submitted ? (
        <div className="score-panel">
          <div>
            <p className="eyebrow">Your score</p>
            <p className="score-value">
              {score} <span>/ {questions.length}</span>
            </p>
          </div>
          <div className="score-bar" aria-hidden="true">
            <div style={{ width: `${percent}%` }} />
          </div>
          <p className="score-text">
            {percent}% correct. {scoreMessage(percent)}
            {saveStatus === 'saved' && (
              <span className="score-saved">
                <Cloud size={13} /> Saved to your progress
              </span>
            )}
            {saveStatus === 'error' && <span className="inline-error"> Could not save this attempt.</span>}
          </p>
          <button type="button" className="btn btn-sm" onClick={retry}>
            <RotateCcw size={14} /> Retry quiz
          </button>
        </div>
      ) : (
        <p className="quiz-intro">
          Answer all {questions.length} questions, then submit to see your score and explanations.
        </p>
      )}

      <ol className="question-list">
        {questions.map((question, questionIndex) => {
          const selected = answers[questionIndex];
          const isCorrect = selected === question.correct_index;
          return (
            <li key={questionIndex} className="question">
              <div className="question-head">
                <span className="question-number">Q{questionIndex + 1}</span>
                <p>{question.question}</p>
                {submitted && (
                  <span className={`result-icon ${isCorrect ? 'correct' : 'incorrect'}`}>
                    {isCorrect ? <Check size={14} /> : <X size={14} />}
                  </span>
                )}
              </div>
              <div className="options" role="radiogroup" aria-label={`Question ${questionIndex + 1}`}>
                {question.options.map((option, optionIndex) => (
                  <button
                    key={optionIndex}
                    type="button"
                    role="radio"
                    aria-checked={selected === optionIndex}
                    className={`option ${optionState(question, optionIndex, selected, submitted)}`}
                    onClick={() => choose(questionIndex, optionIndex)}
                    disabled={submitted}
                  >
                    <span className="option-letter">{LETTERS[optionIndex]}</span>
                    <span>{option}</span>
                  </button>
                ))}
              </div>
              {submitted && (
                <p className="explanation">
                  {selected === undefined && <strong>Not answered. </strong>}
                  <strong>Answer {LETTERS[question.correct_index]}.</strong> {question.explanation}
                </p>
              )}
            </li>
          );
        })}
      </ol>

      {!submitted && (
        <div className="quiz-footer">
          <span>
            {answeredCount} of {questions.length} answered
          </span>
          <button type="button" className="btn btn-primary" onClick={submit} disabled={answeredCount === 0}>
            Submit answers
          </button>
        </div>
      )}

      <AttemptHistory attempts={attempts} />
    </div>
  );
}
