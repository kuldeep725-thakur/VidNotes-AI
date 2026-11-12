import { CheckCircle2 } from 'lucide-react';

export default function SummaryView({ summary }) {
  const paragraphs = summary.overview.split('\n').filter((p) => p.trim());

  return (
    <div className="reading">
      <section className="block">
        <h2 className="block-title">Overview</h2>
        {paragraphs.map((paragraph, index) => (
          <p key={index} className="prose">
            {paragraph}
          </p>
        ))}
      </section>

      <section className="block">
        <h2 className="block-title">Topics covered</h2>
        <ol className="topic-list">
          {summary.topics.map((topic, index) => (
            <li key={index}>
              <span className="topic-index">{String(index + 1).padStart(2, '0')}</span>
              <div>
                <h3>{topic.title}</h3>
                <p>{topic.explanation}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="block">
        <h2 className="block-title">Important concepts</h2>
        <dl className="concepts">
          {summary.key_concepts.map((concept, index) => (
            <div key={index} className="concept">
              <dt>{concept.term}</dt>
              <dd>{concept.explanation}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="block">
        <h2 className="block-title">Key takeaways</h2>
        <ul className="takeaways">
          {summary.key_takeaways.map((takeaway, index) => (
            <li key={index}>
              <CheckCircle2 size={16} />
              <span>{takeaway}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
