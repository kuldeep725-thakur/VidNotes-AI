import { useState } from 'react';

// YouTube does not have a max-resolution thumbnail for every video, so fall
// back to the always-available hqdefault image, then to an empty frame.
export default function Thumbnail({ src, youtubeId, lazy = false }) {
  const fallback = `https://i.ytimg.com/vi/${youtubeId}/hqdefault.jpg`;
  const [current, setCurrent] = useState(src || fallback);

  if (!current) return null;
  return (
    <img
      src={current}
      alt=""
      loading={lazy ? 'lazy' : undefined}
      onError={() => setCurrent(current === fallback ? null : fallback)}
    />
  );
}
