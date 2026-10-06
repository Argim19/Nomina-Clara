export default function Skeleton({ rows = 4 }) {
  return <div className="skeleton-wrap">{Array.from({ length: rows }, (_, i) => <div className="skeleton" key={i} />)}</div>;
}

