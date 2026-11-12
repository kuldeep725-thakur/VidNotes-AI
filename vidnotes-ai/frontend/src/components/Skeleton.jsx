// Shimmering placeholders shown while data loads.

export function SkeletonRows({ count = 3, label = 'Loading' }) {
  return (
    <ul className="skeleton-list" aria-busy="true" aria-label={label}>
      {Array.from({ length: count }, (_, index) => (
        <li key={index} className="skeleton-row" style={{ '--i': index }}>
          <span className="skeleton skeleton-thumb" />
          <span className="skeleton-lines">
            <span className="skeleton skeleton-line" />
            <span className="skeleton skeleton-line short" />
          </span>
        </li>
      ))}
    </ul>
  );
}

export function PageLoader() {
  return (
    <div className="page-loader" role="status" aria-label="Loading">
      <span className="loader-dots">
        <span />
        <span />
        <span />
      </span>
    </div>
  );
}
