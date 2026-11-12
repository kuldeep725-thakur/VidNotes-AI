import { Play } from 'lucide-react';
import { formatTimestamp, videoLinkAt } from '../../utils/format.js';

export default function TimestampsView({ timestamps, videoUrl }) {
  if (timestamps.length === 0) {
    return <p className="muted">No reliable timestamps could be extracted from this transcript.</p>;
  }

  return (
    <div className="reading">
      <p className="muted timestamps-intro">Click a moment to open the video at that point on YouTube.</p>
      <ol className="timeline">
        {timestamps.map((stamp) => (
          <li key={stamp.seconds}>
            <a href={videoLinkAt(videoUrl, stamp.seconds)} target="_blank" rel="noreferrer" className="timeline-item">
              <span className="timeline-time">{formatTimestamp(stamp.seconds)}</span>
              <span className="timeline-body">
                <span className="timeline-title">{stamp.title}</span>
                <span className="timeline-description">{stamp.description}</span>
              </span>
              <Play size={14} className="timeline-play" />
            </a>
          </li>
        ))}
      </ol>
    </div>
  );
}
