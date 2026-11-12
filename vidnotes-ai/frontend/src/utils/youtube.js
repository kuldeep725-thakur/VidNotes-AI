const VIDEO_ID = /^[A-Za-z0-9_-]{11}$/;
const YOUTUBE_HOSTS = ['youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com'];
const PATH_PREFIXES = ['/shorts/', '/embed/', '/live/', '/v/'];

// Mirrors the backend check so users get instant feedback. The backend
// still validates every request.
export function isValidYouTubeUrl(value) {
  let url;
  try {
    url = new URL(value.includes('://') ? value.trim() : `https://${value.trim()}`);
  } catch {
    return false;
  }
  if (!['http:', 'https:'].includes(url.protocol)) return false;

  let candidate = '';
  if (url.hostname === 'youtu.be') {
    candidate = url.pathname.slice(1).split('/')[0];
  } else if (YOUTUBE_HOSTS.includes(url.hostname)) {
    if (url.pathname === '/watch') {
      candidate = url.searchParams.get('v') ?? '';
    } else {
      const prefix = PATH_PREFIXES.find((p) => url.pathname.startsWith(p));
      if (prefix) candidate = url.pathname.slice(prefix.length).split('/')[0];
    }
  }
  return VIDEO_ID.test(candidate);
}
