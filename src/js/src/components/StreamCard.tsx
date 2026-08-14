import { Link } from "react-router-dom";
import type { Stream } from "../types";
import StatusBadge from "./StatusBadge";

export default function StreamCard({ stream }: { stream: Stream }) {
  return (
    <div className="card stream-card">
      <Link
        to={`/watch/${stream.streamId}`}
        className="stream-card__thumb"
        aria-label={`Watch ${stream.title}`}
      >
        {stream.thumbnail ? (
          <img
            src={stream.thumbnail}
            alt=""
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        ) : (
          <span>QLive</span>
        )}
      </Link>

      <div className="stream-card__meta">
        <StatusBadge status={stream.status} />
        {stream.viewers > 0 && (
          <span>{stream.viewers.toLocaleString()} watching</span>
        )}
      </div>

      <Link to={`/watch/${stream.streamId}`} className="stream-card__title">
        {stream.title}
      </Link>

      <div className="stream-card__meta">
        <Link to={`/profile/${stream.publisher}`}>{stream.publisher}</Link>
        <span>·</span>
        <span>{stream.category}</span>
      </div>
    </div>
  );
}
