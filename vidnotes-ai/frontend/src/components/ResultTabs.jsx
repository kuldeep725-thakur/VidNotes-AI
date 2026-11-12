import { BookOpenText, Clock, FileText, ListChecks, MessagesSquare } from 'lucide-react';
import { useState } from 'react';
import NotesView from './results/NotesView.jsx';
import QAView from './results/QAView.jsx';
import QuizView from './results/QuizView.jsx';
import SummaryView from './results/SummaryView.jsx';
import TimestampsView from './results/TimestampsView.jsx';

const TABS = [
  { id: 'summary', label: 'Summary', icon: FileText },
  { id: 'notes', label: 'Study Notes', icon: BookOpenText },
  { id: 'quiz', label: 'Quiz', icon: ListChecks, count: (c) => c.quiz.length },
  { id: 'qa', label: 'Questions & Answers', icon: MessagesSquare, count: (c) => c.qa.length },
  { id: 'timestamps', label: 'Timestamps', icon: Clock, count: (c) => c.timestamps.length },
];

export default function ResultTabs({ content, videoId, videoUrl, language }) {
  const [activeTab, setActiveTab] = useState('summary');

  return (
    <section className="results">
      <div className="tabs" role="tablist" aria-label="Study material">
        {TABS.map(({ id, label, icon: Icon, count }) => (
          <button
            key={id}
            id={`tab-${id}`}
            type="button"
            role="tab"
            aria-selected={activeTab === id}
            aria-controls={`panel-${id}`}
            className={`tab${activeTab === id ? ' active' : ''}`}
            onClick={() => setActiveTab(id)}
          >
            <Icon size={15} />
            {label}
            {count && <span className="tab-count">{count(content)}</span>}
          </button>
        ))}
      </div>

      <div id={`panel-${activeTab}`} role="tabpanel" aria-labelledby={`tab-${activeTab}`} className="tab-panel">
        {activeTab === 'summary' && <SummaryView summary={content.summary} />}
        {activeTab === 'notes' && <NotesView notes={content.notes} videoUrl={videoUrl} />}
        {/* The key resets quiz answers when the language changes. */}
        {activeTab === 'quiz' && (
          <QuizView key={language} questions={content.quiz} videoId={videoId} language={language} />
        )}
        {activeTab === 'qa' && <QAView items={content.qa} />}
        {activeTab === 'timestamps' && <TimestampsView timestamps={content.timestamps} videoUrl={videoUrl} />}
      </div>
    </section>
  );
}
