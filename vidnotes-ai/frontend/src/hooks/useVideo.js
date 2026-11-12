import { useCallback, useEffect, useState } from 'react';
import { getVideo, getVideoStatus } from '../services/api.js';

const POLL_INTERVAL_MS = 2500;

// Loads a video and, while it is processing, polls the lightweight status
// endpoint. The full content is fetched once, when processing finishes.
export function useVideo(id) {
  const [video, setVideo] = useState(null);
  const [error, setError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let timer;

    async function poll() {
      try {
        const status = await getVideoStatus(id);
        if (cancelled) return;
        if (status.status === 'processing') {
          setVideo((current) => ({ ...current, ...status }));
          timer = setTimeout(poll, POLL_INTERVAL_MS);
        } else {
          const full = await getVideo(id);
          if (!cancelled) setVideo(full);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }

    async function load() {
      setError('');
      try {
        const full = await getVideo(id);
        if (cancelled) return;
        setVideo(full);
        if (full.status === 'processing') timer = setTimeout(poll, POLL_INTERVAL_MS);
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }

    load();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [id, reloadKey]);

  const reload = useCallback(() => setReloadKey((key) => key + 1), []);
  return { video, error, reload };
}
