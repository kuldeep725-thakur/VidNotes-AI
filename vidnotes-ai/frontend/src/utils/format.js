export function formatTimestamp(totalSeconds) {
  const seconds = Math.max(0, Math.floor(totalSeconds));
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = String(seconds % 60).padStart(2, '0');
  return h ? `${h}:${String(m).padStart(2, '0')}:${s}` : `${m}:${s}`;
}

export function formatDuration(totalSeconds) {
  if (!totalSeconds) return null;
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.round((totalSeconds % 3600) / 60);
  if (h) return `${h} hr ${m} min`;
  return m ? `${m} min` : `${totalSeconds} sec`;
}

export function formatDate(isoString) {
  return new Date(isoString).toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

export function videoLinkAt(videoUrl, seconds) {
  return `${videoUrl}&t=${Math.floor(seconds)}s`;
}

// Due dates are plain "YYYY-MM-DD" values. Parsing them as local dates avoids
// the off-by-one-day shift that new Date("YYYY-MM-DD") (UTC) can cause.
function parseLocalDate(dateString) {
  const [year, month, day] = dateString.split('-').map(Number);
  return new Date(year, month - 1, day);
}

export function formatDueDate(dateString) {
  return parseLocalDate(dateString).toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
}

export function isOverdue(dateString) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return parseLocalDate(dateString) < today;
}
